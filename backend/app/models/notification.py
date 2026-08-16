"""Notification model — aggregated system notifications.

v0.3: notifications for login expiry, nurture failures, quota warnings, and
snapshot saves. is_read derived from read_at.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Notification(Base):
    """A single system notification."""
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_severity", "severity"),
        Index("ix_notifications_read_at", "read_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    severity: Mapped[str] = mapped_column(String(16), default="info")  # critical|warning|info
    title: Mapped[str] = mapped_column(String(128))
    body: Mapped[str] = mapped_column(Text, default="")
    related_entity_type: Mapped[str] = mapped_column(String(32), default="")
    related_entity_id: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    @property
    def is_read(self) -> bool:
        return self.read_at is not None