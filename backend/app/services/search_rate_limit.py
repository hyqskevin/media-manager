"""搜索频率与周配额控制。

关联 spec: docs/superpowers/specs/2026-07-25-crawl-rate-limit-design.md

- SearchRateLimiter：任务内"搜索之间"的随机间隔（首次搜索不等待），uniform 可注入；
- search_usage 表：按 ISO 周（Asia/Shanghai）全局累计搜索次数，超 weekly_search_limit 跳过。
"""
import random
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.search_usage import SearchUsage

_TZ = ZoneInfo("Asia/Shanghai")


class SearchRateLimiter:
    """任务内关键词搜索间隔控制：第一次 next_delay() 返回 None，之后返回 uniform(min, max)。"""

    def __init__(self, interval_min: float, interval_max: float, uniform=None):
        self._min = interval_min
        self._max = interval_max
        self._uniform = uniform or random.uniform
        self._calls = 0

    def next_delay(self) -> float | None:
        self._calls += 1
        if self._calls == 1:
            return None
        return self._uniform(self._min, self._max)


def iso_week_key(now: datetime | None = None) -> str:
    now = (now or datetime.now(_TZ)).astimezone(_TZ)
    year, week, _ = now.isocalendar()
    return f"{year}-W{week:02d}"


def weekly_search_count(db: Session, week_key: str) -> int:
    usage = db.scalar(select(SearchUsage).where(SearchUsage.week_key == week_key))
    return usage.count if usage else 0


def increment_weekly_search(db: Session, week_key: str, n: int = 1) -> int:
    usage = db.scalar(select(SearchUsage).where(SearchUsage.week_key == week_key))
    if usage is None:
        usage = SearchUsage(week_key=week_key, count=0)
        db.add(usage)
    usage.count += n
    db.commit()
    return usage.count
