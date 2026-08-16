from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

def now(): return datetime.now(timezone.utc)

class City(Base):
    __tablename__ = "cities"
    __table_args__ = (Index("ix_cities_name_unique", "name", unique=True),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    recent_filter: Mapped[str] = mapped_column(String(16), default="一周内")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Blogger(Base):
    __tablename__ = "bloggers"
    id: Mapped[int] = mapped_column(primary_key=True)
    platform_user_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, default=None)
    username: Mapped[str] = mapped_column(String(128))
    profile_url: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
    city_code: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True, default=None)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    max_notes_per_crawl: Mapped[int] = mapped_column(Integer, default=0)  # 0 = 不限制
