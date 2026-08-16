"""Parse 小红书真实发布时间 from OpenCLI note detail payload.

关联 spec: docs/superpowers/specs/2026-07-21-parse-real-published-at-design.md

解析规则：
- 绝对日期：2025-07-20 / 2025/07/20 / 2025年7月20日（可带时分）
- 月-日：07-20 / 7/20 / 7月20日，结合 now_local 推断年份（未来回退 1 年）
- 相对时间：N天前 / N小时前 / N分钟前，基于 now_local 回推

一律解析为 Asia/Shanghai 时区的北京墙钟时间（与雪花路径、库存储口径一致，
SQLite DateTime 落库时丢弃 tzinfo 即为北京墙钟 naive）。
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Any


SHANGHAI = timezone(timedelta(hours=8))


@dataclass(frozen=True)
class PublishedAtResult:
    value: datetime | None
    confidence: float
    source: str


_ABSOLUTE = re.compile(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})(?:日)?(?:[ T](\d{1,2}):(\d{1,2}))?")
_MONTH_DAY = re.compile(r"(?<!\d)(\d{1,2})[-/.月](\d{1,2})(?:日)?(?:[ T](\d{1,2}):(\d{1,2}))?")
_REL_DAY = re.compile(r"(\d{1,2})\s*天前")
_REL_HOUR = re.compile(r"(\d{1,2})\s*小时前")
_REL_MIN = re.compile(r"(\d{1,2})\s*分钟前")


def parse_published_at(raw_text: str, *, now_local: datetime | None = None) -> PublishedAtResult:
    """Parse 小红书页面中的发布时间文本。

    Args:
        raw_text: 拼接后的页面文本（title / content / snippet 等）
        now_local: 任务基准时间（Asia/Shanghai），无时区时假设 Asia/Shanghai

    Returns:
        PublishedAtResult，value 为 Asia/Shanghai 时区的 datetime（失败时 None）
    """
    text = (raw_text or "").strip()
    if not text:
        return PublishedAtResult(None, 0.0, "none")
    now = (now_local or datetime.now(SHANGHAI)).astimezone(SHANGHAI)

    match = _ABSOLUTE.search(text)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        hour = int(match.group(4) or 0); minute = int(match.group(5) or 0)
        try:
            local = datetime(year, month, day, hour, minute, tzinfo=SHANGHAI)
        except ValueError:
            return PublishedAtResult(None, 0.0, "none")
        return PublishedAtResult(local, 1.0, "absolute")

    match = _MONTH_DAY.search(text)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        hour = int(match.group(3) or 0); minute = int(match.group(4) or 0)
        year = now.year
        try:
            local = datetime(year, month, day, hour, minute, tzinfo=SHANGHAI)
        except ValueError:
            return PublishedAtResult(None, 0.0, "none")
        # 若日期在 now + 2 天之外，回退 1 年
        if local > now + timedelta(days=2):
            local = local.replace(year=year - 1)
        return PublishedAtResult(local, 0.85, "month_day")

    match = _REL_DAY.search(text)
    if match:
        days = int(match.group(1))
        return PublishedAtResult(now - timedelta(days=days), 0.7, "relative_day")
    match = _REL_HOUR.search(text)
    if match:
        hours = int(match.group(1))
        return PublishedAtResult(now - timedelta(hours=hours), 0.7, "relative_hour")
    match = _REL_MIN.search(text)
    if match:
        minutes = int(match.group(1))
        return PublishedAtResult(now - timedelta(minutes=minutes), 0.6, "relative_minute")

    return PublishedAtResult(None, 0.0, "none")


def extract_published_at(detail: dict[str, Any], *, fallback_now: datetime) -> datetime | None:
    """从 OpenCLI 详情数据中推断真实发布时间。失败返回 None，不回退到 created_at。"""
    raw = detail or {}

    candidates: list[str] = []
    for key in ("published_at", "publishedAt", "publish_time", "publishTime", "date", "time"):
        value = raw.get(key)
        if value:
            candidates.append(str(value))
    for key in ("content", "title", "snippet"):
        value = raw.get(key)
        if isinstance(value, str) and value:
            candidates.append(value)
    text = " ".join(candidates)
    result = parse_published_at(text, now_local=fallback_now.astimezone(SHANGHAI))
    return result.value
