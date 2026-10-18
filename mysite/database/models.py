from datetime import datetime, timezone

from sqlalchemy import DateTime, String, TypeDecorator
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column

from mysite.database.db import Base


class UTCDateTime(TypeDecorator[datetime]):
    """Restore UTC timezone information that SQLite does not preserve."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("A timezone-aware datetime is required")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        return value.replace(tzinfo=timezone.utc) if value is not None else None


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), default=lambda: datetime.now(timezone.utc)
    )
