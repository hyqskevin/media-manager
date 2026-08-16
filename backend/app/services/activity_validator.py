"""校验活动是否合法入库，并区分零活动原因。

关联 spec: docs/superpowers/specs/2026-07-21-zero-activity-and-window-fix-design.md

- 活动日期 < Note.published_at：视为 OCR 错识，跳过。
- Note.published_at IS NULL：时间未知，全部接收。
- 没有活动：根据正文是否含有活动信号，区分 'minimax_empty_retryable' 与 'no_activity_signals'。
"""
from datetime import datetime, timezone
from typing import Any
import re


_ACTIVITY_SIGNAL_PATTERNS = (
    r"市集", r"展览", r"演出", r"沙龙", r"工作坊", r"讲座", r"见面会",
    r"开放日", r"开幕", r"闭幕", r"音乐节", r"书展", r"咖啡节",
    r"\d{1,2}[-/.月]\d{1,2}(?:日)?",  # 形如 7.18 7/18 7月18日
    r"\d+\s*(?:元|免费)",
    r"(?:地点|地址|时间|报名)",
)


def _has_activity_signal(body: str, raw_data: dict[str, Any]) -> bool:
    haystack = (body or "") + "\n" + " ".join(str(v) for v in raw_data.values() if isinstance(v, str))
    if not haystack.strip():
        return False
    for pattern in _ACTIVITY_SIGNAL_PATTERNS:
        if re.search(pattern, haystack):
            return True
    return False


def _is_before_publish(activity: dict[str, Any], published_at: datetime | None) -> bool:
    if published_at is None:
        return False
    raw = activity.get("start_time")
    if not raw:
        return False
    try:
        parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.astimezone(timezone.utc).date() < published_at.astimezone(timezone.utc).date()


def classify_zero_activity(note: Any, extracted: list[dict[str, Any]]) -> str:
    """返回 0 活动原因或 'ok'。

    - 'ok'：有通过校验的活动
    - 'all_before_publish'：全部活动早于发布时间
    - 'minimax_empty_retryable'：MiniMax 空，正文有活动信号
    - 'no_activity_signals'：正文无活动信号
    """
    if extracted:
        if all(_is_before_publish(activity, getattr(note, "published_at", None)) for activity in extracted):
            return "all_before_publish"
        return "ok"
    has_signals = _has_activity_signal(getattr(note, "content", "") or "", getattr(note, "raw_data", {}) or {})
    return "minimax_empty_retryable" if has_signals else "no_activity_signals"


def validate_activities(
    note: Any,
    activities: list[dict[str, Any]],
    *,
    future_window_days: int = 60,
) -> tuple[list[dict[str, Any]], list[str]]:
    """返回 (accepted, rejected_messages)。

    判定口径：按"日期"比较，活动 ``start_time`` 与 ``note.published_at`` 同日或之后即视为合法；
    仅当活动日期严格早于推文发布时间所在日期才拒绝（避免同日合法活动被误杀）。
    """
    published_at = getattr(note, "published_at", None)
    if published_at is None:
        return list(activities), []
    accepted: list[dict[str, Any]] = []
    rejected: list[str] = []
    published_utc = published_at.astimezone(timezone.utc)
    published_date = published_utc.date()
    for activity in activities:
        raw = activity.get("start_time")
        if not raw:
            accepted.append(activity)
            continue
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            rejected.append(f"无法解析 start_time={raw!r}")
            continue
        parsed_utc = parsed.astimezone(timezone.utc)
        if parsed_utc.date() < published_date:
            rejected.append(
                f"活动 {activity.get('name')!r} 日期 {parsed_utc.date().isoformat()} "
                f"早于推文发布时间 {published_date.isoformat()}"
            )
            continue
        # 不再硬性限定 "活动距离发布时间" 上限；保留 future_window_days 参数兼容性，无副作用
        accepted.append(activity)
    return accepted, rejected
