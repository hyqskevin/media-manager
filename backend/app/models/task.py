from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class CrawlTask(Base):
    __tablename__ = "crawl_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), index=True)
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    run_token: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid4()), index=True)
    total_notes: Mapped[int] = mapped_column(Integer, default=0)
    downloaded_notes: Mapped[int] = mapped_column(Integer, default=0)
    ocr_notes: Mapped[int] = mapped_column(Integer, default=0)
    extracted_notes: Mapped[int] = mapped_column(Integer, default=0)
    success_notes: Mapped[int] = mapped_column(Integer, default=0)
    failed_notes: Mapped[int] = mapped_column(Integer, default=0)
    skipped_notes: Mapped[int] = mapped_column(Integer, default=0)
    skipped_activities: Mapped[int] = mapped_column(Integer, default=0)
    current_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

class TaskLog(Base):
    __tablename__ = "task_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, index=True)
    level: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
