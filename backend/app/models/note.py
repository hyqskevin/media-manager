from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(Integer, index=True)
    platform_note_id: Mapped[str] = mapped_column(String(128), unique=True)
    title: Mapped[str] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(String(512))
    city_code: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32))
    review_status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    merged_into_note_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # 2026-08-13: 推文抓取来源（matched_*） + 互动数（engagement）
    # 配迁移 0022；与 crawl_task 写入新列落地后必须手动重启 celery worker
    matched_keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    matched_blogger_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    matched_blogger_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    like_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collect_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

class NoteImage(Base):
    __tablename__ = "note_images"
    id: Mapped[int] = mapped_column(primary_key=True)
    note_id: Mapped[int] = mapped_column(Integer, index=True)
    storage_key: Mapped[str] = mapped_column(String(512))
    original_url: Mapped[str] = mapped_column(String(512), default="")
    ocr_text: Mapped[str] = mapped_column(Text, default="")
    ocr_status: Mapped[str] = mapped_column(String(32), default="pending")
    ocr_error: Mapped[str] = mapped_column(Text, default="")
