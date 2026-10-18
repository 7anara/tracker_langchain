import os
import secrets
from datetime import datetime, timedelta, timezone

# Configure before importing the app. No development database or secret is used.
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['SECRET_KEY'] = secrets.token_urlsafe(48)

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import main
from mysite.api.auth import verify_password
from mysite.config import settings
from mysite.database.db import Base, get_db
from mysite.database.models import UserProfile


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine(
        f'sqlite:///{tmp_path / "test.db"}',
        connect_args={'check_same_thread': False},
    )
    factory = sessionmaker(bind=engine)

    def override_db():
        with factory() as db:
            yield db

    monkeypatch.setattr(main, 'engine', engine)
    main.app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(main.app) as http:
            yield http, factory
    finally:
        main.app.dependency_overrides.clear()
        engine.dispose()


USER = {'full_name': ' Ada Lovelace ', 'email': 'ada@example.com',
        'password': 'safe-password-123'}


def test_register_login_me_and_health(client):
    http, factory = client
    response = http.post('/auth/register', json=USER)
    assert response.status_code == 201
    public = response.json()
    assert set(public) == {'id', 'full_name', 'email', 'created_at'}
    assert public['full_name'] == 'Ada Lovelace'
    assert datetime.fromisoformat(public['created_at']).utcoffset() == timedelta(0)
    with factory() as db:
        user = db.scalar(select(UserProfile))
        assert user.password.startswith('$argon2id$')
        assert user.password != USER['password']
        assert verify_password(USER['password'], user.password)
        assert user.created_at.tzinfo == timezone.utc
    login = http.post('/auth/login', data={
        'username': 'ADA@example.com', 'password': USER['password']})
    assert login.status_code == 200
    assert set(login.json()) == {'access_token', 'token_type'}
    assert login.json()['token_type'] == 'bearer'
    token = login.json()['access_token']
    claims = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=['HS256'])
    assert claims['exp'] - claims['iat'] == settings.access_token_expire_minutes * 60
    me = http.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me.status_code == 200
    assert me.json() == public
    assert http.get('/health').json() == {'status': 'ok'}
    schema = http.get('/openapi.json').json()
    assert set(schema['paths']) == {'/health', '/auth/register', '/auth/login', '/auth/me'}


def test_duplicate_and_unique_conflict(client, monkeypatch):
    http, factory = client
    assert http.post('/auth/register', json=USER).status_code == 201
    assert http.post('/auth/register', json={**USER, 'email': 'ADA@example.com'}).status_code == 409
    # Simulate another request winning after the existence check: the INSERT
    # must still be rejected by SQLite's unique index and rolled back.
    with factory() as db:
        monkeypatch.setattr(db, 'scalar', lambda *args, **kwargs: None)

        def override():
            yield db

        main.app.dependency_overrides[get_db] = override
        assert http.post('/auth/register', json=USER).status_code == 409
        assert db.is_active
    with factory() as db:
        assert len(db.scalars(select(UserProfile)).all()) == 1


@pytest.mark.parametrize('changes', [
    {'full_name': ''}, {'full_name': '   '}, {'email': 'invalid'},
    {'password': 'short'}, {'password': '        '}, {'email': ''},
    {'full_name': 'a' * 101}, {'password': 'a' * 129},
])
def test_invalid_registration(client, changes):
    http, _ = client
    assert http.post('/auth/register', json={**USER, **changes}).status_code == 422


def test_invalid_credentials(client):
    http, _ = client
    http.post('/auth/register', json=USER)
    responses = [http.post('/auth/login', data={'username': email, 'password': 'wrong'})
                 for email in [USER['email'], 'absent@example.com']]
    assert all(r.status_code == 401 for r in responses)
    assert responses[0].json() == responses[1].json()
    assert http.get('/auth/me').status_code == 401


@pytest.mark.parametrize('kind', [
    'invalid', 'expired', 'wrong_signature', 'missing_exp', 'missing_sub',
    'malformed_sub', 'huge_sub', 'deleted_user', 'wrong_algorithm',
])
def test_reject_tokens(client, kind):
    http, _ = client
    claims = {'sub': '999', 'exp': datetime.now(timezone.utc) + timedelta(minutes=1)}
    key = settings.secret_key.get_secret_value()
    algorithm = 'HS256'
    if kind == 'expired':
        claims['exp'] = datetime.now(timezone.utc) - timedelta(seconds=1)
    elif kind == 'wrong_signature':
        key = secrets.token_urlsafe(48)
    elif kind == 'missing_exp':
        del claims['exp']
    elif kind == 'missing_sub':
        del claims['sub']
    elif kind == 'malformed_sub':
        claims['sub'] = 'not-a-user-id'
    elif kind == 'huge_sub':
        claims['sub'] = '9' * 100
    elif kind == 'wrong_algorithm':
        algorithm = 'HS384'
    token = 'invalid.token' if kind == 'invalid' else jwt.encode(claims, key, algorithm=algorithm)
    result = http.get('/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert result.status_code == 401
    assert result.headers['www-authenticate'] == 'Bearer'


def test_database_failure_and_rollback(client, monkeypatch):
    from sqlalchemy.exc import OperationalError

    http, factory = client
    with factory() as db:
        def fail(*args, **kwargs):
            raise OperationalError('SELECT', {}, Exception('private database detail'))

        monkeypatch.setattr(db, 'scalar', fail)

        def override():
            yield db

        main.app.dependency_overrides[get_db] = override
        for path, kwargs in [
            ('/auth/register', {'json': USER}),
            ('/auth/login', {'data': {'username': USER['email'], 'password': USER['password']}}),
        ]:
            response = http.post(path, **kwargs)
            assert response.status_code == 503
            assert response.json() == {'detail': 'Database unavailable'}
            assert db.is_active
