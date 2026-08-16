from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"
    id: Mapped[int] = mapped_column(primary_key=True)
    activity_a_id: Mapped[int] = mapped_column(Integer, index=True)
    activity_b_id: Mapped[int] = mapped_column(Integer, index=True)
    similarity: Mapped[float] = mapped_column(Float)
    matched_fields: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    merged_activity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NoteDuplicateCandidate(Base):
    __tablename__ = "note_duplicate_candidates"
    __table_args__ = (UniqueConstraint("note_a_id", "note_b_id", name="uq_note_duplicate_pair"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    note_a_id: Mapped[int] = mapped_column(Integer, index=True)
    note_b_id: Mapped[int] = mapped_column(Integer, index=True)
    similarity: Mapped[float] = mapped_column(Float)
    matched_fields: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    kept_note_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
