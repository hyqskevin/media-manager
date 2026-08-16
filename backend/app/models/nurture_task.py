"""NurtureTask / NurtureActionLog models — real nurture task records.

v0.3: replaces the "stub execution" of v0.2 with real task records that track
status (pending/running/completed/failed/skipped/cancelled), progress, current
action, and per-action logs. Powering 执行中(running) / 历史(history) pages.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class NurtureTask(Base):
    """One nurture task execution record."""
    __tablename__ = "nurture_tasks"
    __table_args__ = (
        Index("ix_nurture_tasks_account_status", "account_id", "status"),
        Index("ix_nurture_tasks_started", "started_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    celery_task_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("platform_accounts.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(16), index=True)
    actions_json: Mapped[str] = mapped_column(Text, default="[]")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)
    current_action: Mapped[str | None] = mapped_column(String(32), default=None)
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    error: Mapped[str | None] = mapped_column(Text, default=None)
    items_collected: Mapped[int] = mapped_column(Integer, default=0)
    action_set_id: Mapped[int | None] = mapped_column(Integer, default=None, index=True)
    triggered_by_schedule_id: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    action_logs: Mapped[list["NurtureActionLog"]] = relationship(
        "NurtureActionLog", back_populates="task", cascade="all, delete-orphan"
    )


class NurtureActionLog(Base):
    """Per-action execution log within a nurture task."""
    __tablename__ = "nurture_action_logs"
    __table_args__ = (
        Index("ix_nurture_action_logs_task_seq", "task_id", "sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("nurture_tasks.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), default="running")
    sequence: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error: Mapped[str | None] = mapped_column(Text, default=None)

    task: Mapped["NurtureTask"] = relationship("NurtureTask", back_populates="action_logs")