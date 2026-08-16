"""海报模板与海报任务 ORM。

设计依据 spec: docs/superpowers/specs/2026-07-21-poster-generation-design.md
- poster_templates：HTML 模板库
- poster_tasks：每次生成流程的快照（含 items、字段、展示图、override_html、渲染产物）
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PosterTemplate(Base):
    __tablename__ = "poster_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    html_template: Mapped[str] = mapped_column(Text)
    css_text: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    thumbnail_path: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
    parsed_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=None)
    source: Mapped[str] = mapped_column(String(32), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )


class PosterTask(Base):
    __tablename__ = "poster_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("poster_templates.id", ondelete="RESTRICT"), index=True
    )
    items: Mapped[list] = mapped_column(JSON, default=list)
    override_html: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    output_path: Mapped[str | None] = mapped_column(String(512), nullable=True, default=None)
    output_format: Mapped[str] = mapped_column(String(16), default="png")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
