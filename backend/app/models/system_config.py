"""SystemConfig model — key-value store for risk config & feature switches.

v0.3: persists risk_config / nurture_global_enabled so the API and Celery
worker read the same live values instead of hardcoded policy constants.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SystemConfig(Base):
    """Generic key-value configuration row."""
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )