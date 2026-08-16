"""定时抓取任务模型。

- day_of_week 采用 ISO 1-7（1=周一），与 dispatcher 的 now.isoweekday() 对齐；
- keyword_group_ids / blogger_group_ids 为 JSON list[int]，两组至少选一（API 层校验）；
- recent_filter 为 NULL 时回退到城市配置（run_crawl 已有该回退）；
- last_fired_slot 记录最近一次触发的 "YYYY-MM-DDTHH:MM"，用于 beat 重复 tick / 重启幂等。

关联 spec: docs/superpowers/specs/2026-07-25-scheduled-crawls-and-dashboard-charts-design.md
"""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ScheduledCrawl(Base):
    __tablename__ = "scheduled_crawls"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    enabled: Mapped[bool] = mapped_column(default=True)
    day_of_week: Mapped[int] = mapped_column(Integer)  # ISO 1-7，1=周一
    hour: Mapped[int] = mapped_column(Integer)  # 0-23
    minute: Mapped[int] = mapped_column(Integer)  # 0-59
    city_code: Mapped[str] = mapped_column(String(32), index=True)
    keyword_group_ids: Mapped[list] = mapped_column(JSON, default=list)
    blogger_group_ids: Mapped[list] = mapped_column(JSON, default=list)
    recent_filter: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)
    last_fired_slot: Mapped[str | None] = mapped_column(String(16), nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
