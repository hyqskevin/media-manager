from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def now() -> datetime:
    return datetime.now(timezone.utc)


class BloggerCity(Base):
    __tablename__ = "blogger_cities"
    __table_args__ = (
        UniqueConstraint("blogger_id", "city_code", name="uq_blogger_city"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    blogger_id: Mapped[int] = mapped_column(
        ForeignKey("bloggers.id", ondelete="CASCADE")
    )
    city_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("cities.code", ondelete="CASCADE")
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)