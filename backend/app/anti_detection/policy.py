"""风控守则常量与判定函数。

详见 reference/anti-detection-notes.md §5。
"""
from __future__ import annotations

from datetime import datetime

# ── 常量 ──────────────────────────────────────────────────────────────────
MAX_DAILY_SECONDS: int = 14400                # 单账号单日最多养号时长（4 小时）
SILENT_HOURS: tuple[int, int] = (0, 6)        # 静默时段（人类睡觉）0-6 点
MIN_ACTION_INTERVAL_S: int = 3                # 单次操作最小间隔（秒）
MAX_LIKES_PER_HOUR: int = 10                  # 单账号每小时最多点赞
MAX_LIKES_PER_DAY: int = 50                   # 单账号单日最多点赞


def is_silent_hour(dt: datetime) -> bool:
    """判断给定时间是否在静默时段（0-6 点）。"""
    h = dt.hour
    return SILENT_HOURS[0] <= h < SILENT_HOURS[1]


def check_quota_exceeded(used_seconds: int, quota_seconds: int) -> bool:
    """检查是否已用满当日配额。"""
    return used_seconds >= quota_seconds