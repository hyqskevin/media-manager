"""搜索周配额用量表。

关联 spec: docs/superpowers/specs/2026-07-25-crawl-rate-limit-design.md

- week_key 为 Asia/Shanghai 时区的 ISO 年-周（如 "2026-W30"），全局跨任务累计；
- 每次 adapter.search_recent 调用成功后 count +1。
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SearchUsage(Base):
    __tablename__ = "search_usage"
    id: Mapped[int] = mapped_column(primary_key=True)
    week_key: Mapped[str] = mapped_column(String(8), unique=True, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
