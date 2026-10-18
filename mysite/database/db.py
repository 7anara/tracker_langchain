from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from mysite.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """Shared base for the models introduced in later steps."""


def get_db() -> Generator[Session, None, None]:
    """Provide one database session per request and always close it."""
    with SessionLocal() as db:
        yield db
