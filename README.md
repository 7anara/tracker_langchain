# AI Personal Assistant Agent

Python 3.12, FastAPI, SQLite, and SQLAlchemy. Step 2 adds user registration and
JWT authentication. AI, tasks, and diet planning are not implemented.

## Local setup

```bash
uv sync --locked
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Paste the generated value into `SECRET_KEY` in your ignored `.env` file. Generate
it once and keep it stable across restarts. Never commit or share the value.
The application fails configuration validation if it is missing or too short.
HS256 is the only allowed signing algorithm; token lifetime defaults to 30 minutes.

```bash
uv run --locked uvicorn main:app --reload
```

Run from the repository root so `.env` and `sqlite:///./assistant.db` resolve
consistently. SQLAlchemy creates missing tables at startup, preserving existing
ones. `create_all()` does not migrate existing schemas. There is one engine,
Base, session factory, and `get_db` dependency. SQLite user timestamps are stored
in UTC and restored as timezone-aware datetimes when loaded.

## Verify with Swagger UI

Open `/docs` on your running server.

1. Execute `POST /auth/register` with `full_name`, a valid `email`, and a password
   of 8–128 characters. Expect HTTP 201 with no password in the response.
2. Execute `POST /auth/login` using the email as the form's `username` and the
   password. Expect a bearer access token. Other OAuth form fields are optional.
3. Click **Authorize**, enter the same email in `username` and the password,
   and authorize. Swagger obtains and sends the token automatically.
4. Execute `GET /auth/me`. Expect the authenticated user's public profile.
5. Execute `GET /health`. Expect `{"status":"ok"}`.

Duplicate emails return 409, invalid registration data returns 422, and invalid
credentials or tokens return 401. Emails are normalized to lowercase. Passwords
use Argon2; JWTs contain the user ID and expiration, not a password. Database
failures return 503 without exposing internal errors. `/health` checks SQLite
with `SELECT 1` and continues to return exactly `{"status":"ok"}`.

## Tests

```bash
uv run --locked python -m pytest -q
```

Tests use temporary SQLite files, an ephemeral test-only signing key, and an
engine/session override. They never delete or change development user data.

## Important files

- `main.py`: FastAPI application, lifespan table initialization, and health check.
- `mysite/config.py`: Pydantic settings for SQLite and JWT configuration.
- `mysite/database/db.py`: shared engine, Base, session factory, and `get_db`.
- `mysite/database/models.py`: `UserProfile` and SQLite UTC timestamp handling.
- `mysite/schemas/agent_schema.py`: registration, public user, and token schemas.
- `mysite/api/auth.py`: router, password hashing, JWT creation, `get_current_user`.
- `tests/test_auth.py`: isolated authentication and health regression tests.
- `pyproject.toml` and `uv.lock`: dependencies and reproducible versions.

Task management (Step 3) requires separate approval.
