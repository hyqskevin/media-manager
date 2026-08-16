"""NurtureActionSet model — reusable action combinations.

v0.3: saved action combos (e.g. "浏览+点赞") reused by nurture tasks.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class NurtureActionSet(Base):
    """A named, ordered collection of nurture actions for a platform."""
    __tablename__ = "nurture_action_sets"
    __table_args__ = (
        Index("ix_nurture_action_sets_platform", "platform"),
        Index("ix_nurture_action_sets_platform_name", "platform", "name", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(64))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    actions_json: Mapped[str] = mapped_column(Text, default="[]")
    actions_order_json: Mapped[str] = mapped_column(Text, default="[0,1,2,3]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )