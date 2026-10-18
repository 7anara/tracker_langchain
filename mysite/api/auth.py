from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from mysite.config import settings
from mysite.database.db import get_db
from mysite.database.models import UserProfile
from mysite.schemas.agent_schema import (
    TokenSchema,
    UserRegisterSchema,
    UserResponseSchema,
)

auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
password_hash = PasswordHash.recommended()
# Verify a hash even for unknown emails to reduce account enumeration by timing.
DUMMY_HASH = password_hash.hash("unused-dummy-password")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
DbSession = Annotated[Session, Depends(get_db)]


def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return password_hash.verify(password, hashed_password)
    except (UnknownHashError, ValueError):
        return False


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "iat": now,
            "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
        },
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm,
    )


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: DbSession
) -> UserProfile:
    unauthorized = HTTPException(
        status_code=401,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require": ["sub", "exp"]},
        )
        subject = payload["sub"]
        if (
            not isinstance(subject, str)
            or not subject.isascii()
            or not subject.isdigit()
        ):
            raise unauthorized
        user_id = int(subject)
        if not 0 < user_id <= 9223372036854775807:
            raise unauthorized
    except (InvalidTokenError, ValueError) as exc:
        raise unauthorized from exc
    try:
        user = db.get(UserProfile, user_id)
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database unavailable") from exc
    if user is None:
        raise unauthorized
    return user


@auth_router.post("/register", response_model=UserResponseSchema, status_code=201)
def register(data: UserRegisterSchema, db: DbSession) -> UserProfile:
    try:
        if db.scalar(select(UserProfile).where(UserProfile.email == data.email)):
            raise HTTPException(409, "Email already registered")
        user = UserProfile(
            full_name=data.full_name,
            email=str(data.email),
            password=get_password_hash(data.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        # The unique index also protects simultaneous registrations.
        if getattr(exc.orig, "sqlite_errorname", "") in {
            "SQLITE_CONSTRAINT_UNIQUE",
        }:
            raise HTTPException(409, "Email already registered") from exc
        raise HTTPException(503, "Database unavailable") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(503, "Database unavailable") from exc
    return user


@auth_router.post("/login", response_model=TokenSchema)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession
) -> TokenSchema:
    try:
        user = db.scalar(
            select(UserProfile).where(UserProfile.email == form.username.strip().lower())
        )
    except SQLAlchemyError as exc:
        raise HTTPException(503, "Database unavailable") from exc
    valid = verify_password(form.password, user.password if user else DUMMY_HASH)
    if user is None or not valid:
        raise HTTPException(
            401, "Invalid email or password", headers={"WWW-Authenticate": "Bearer"}
        )
    return TokenSchema(access_token=create_access_token(user.id))


@auth_router.get("/me", response_model=UserResponseSchema)
def me(user: Annotated[UserProfile, Depends(get_current_user)]) -> UserProfile:
    return user
