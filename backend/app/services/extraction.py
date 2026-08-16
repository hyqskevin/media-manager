import re
from datetime import datetime, timedelta
from typing import Any, Callable


LLM = Callable[[str], dict[str, Any]]


def normalize_activity_datetime(value: Any, now: datetime, future_window_days: int = 60) -> str | None:
    """解析活动日期。

    支持：
    - 绝对日期（含年）：2025-07-20、2025/07/20、2025年7月20日（可带时分）
    - 无年份格式：MM-DD / M.DD / 7月18日，结合 `now` 推断年份
      - 解析结果超过 now 2 天，回退 1 年
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).isoformat()
    except ValueError:
        pass
    match = re.fullmatch(r"(?:(20\d{2})[-/.年])?(\d{1,2})(?:[-/.月])(\d{1,2})(?:日)?(?:[ T]?(\d{1,2})(?::(\d{1,2}))?)?", text)
    if not match:
        return None
    try:
        explicit_year = match.group(1)
        parsed = datetime(
            int(explicit_year or now.year),
            int(match.group(2)),
            int(match.group(3)),
            int(match.group(4) or 0),
            int(match.group(5) or 0),
        )
        if not explicit_year:
            now_naive = now.replace(tzinfo=None) if isinstance(now, datetime) else now
            # 无年份：先按当前年解析；若早于 now（比如 7-17 推断 1-5），加 1 年（指向未来）
            if parsed < now_naive:
                parsed = parsed.replace(year=parsed.year + 1)
        return parsed.isoformat()
    except ValueError:
        return None


def normalize_activity_row(row: dict[str, Any], now: datetime, future_window_days: int = 60) -> dict[str, Any]:
    item = dict(row)
    item["name"] = str(item.get("name") or "").strip()
    item["start_time"] = normalize_activity_datetime(item.get("start_time"), now, future_window_days)
    item["end_time"] = normalize_activity_datetime(item.get("end_time"), now, future_window_days)
    if item["start_time"] and item["end_time"] and datetime.fromisoformat(item["end_time"]) < datetime.fromisoformat(item["start_time"]):
        item["end_time"] = None
    item["source_image_indexes"] = sorted({int(value) for value in item.get("source_image_indexes", []) if str(value).isdigit()})
    confidence = item.get("confidence", 0)
    if isinstance(confidence, str):
        confidence = {"high": 0.9, "medium": 0.6, "low": 0.3}.get(confidence.lower(), 0)
    item["confidence"] = max(0.0, min(1.0, float(confidence or 0)))
    return item


def extract_activity_fields(text: str, now: datetime, llm: LLM | None) -> dict[str, Any]:
    iso = re.search(r"(20\d{2})[-/.](\d{1,2})[-/.](\d{1,2})(?:\s+(\d{1,2}):(\d{2}))?", text)
    cn = re.search(r"(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2}):(\d{2}))?", text)
    short_dot = re.search(r"(?<!\d)(\d{1,2})\.(\d{1,2})(?:[ T]?(\d{1,2}):(\d{1,2}))?", text)
    start_time = None
    # 三个分支都可能匹配到非法日期（如 2月30日、2026-02-30、13月1日），统一用 try/except 容忍
    if iso:
        try:
            start_time = datetime(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)), int(iso.group(4) or 0), int(iso.group(5) or 0)).isoformat()
        except ValueError:
            start_time = None
    elif cn:
        try:
            start_time = datetime(now.year, int(cn.group(1)), int(cn.group(2)), int(cn.group(3) or 0), int(cn.group(4) or 0)).isoformat()
        except ValueError:
            start_time = None
    elif short_dot:
        try:
            candidate = datetime(now.year, int(short_dot.group(1)), int(short_dot.group(2)), int(short_dot.group(3) or 0), int(short_dot.group(4) or 0))
            now_naive = now.replace(tzinfo=None) if isinstance(now, datetime) else now
            if candidate < now_naive:
                candidate = candidate.replace(year=candidate.year + 1)
            start_time = candidate.isoformat()
        except ValueError:
            start_time = None
    price_match = re.search(r"(免费|\d+(?:\.\d+)?\s*元(?:起)?)", text)
    location_match = re.search(r"(?:地点[:：]?\s*)?([一-龥]{2,}(?:中心|滨江|广场|公园|书局|剧场|博物馆))", text)
    kind = "演出" if re.search(r"音乐|演出|相声|乐队", text) else "展览" if re.search(r"展览|艺术展", text) else "其他"
    result: dict[str, Any] = {"name": text.strip()[:30] or None, "start_time": start_time, "location": location_match.group(1) if location_match else None, "price": price_match.group(1) if price_match else None, "type": kind}
    if (not result["start_time"] or not result["location"]) and llm:
        result.update({key: value for key, value in llm(text).items() if value is not None})
    return normalize_activity_row(result, now)


def extract_activities(text: str, now: datetime, llm: LLM | None) -> list[dict[str, Any]]:
    """Extract every concrete activity; retain a rules-only single result when no LLM is configured."""
    if llm is None:
        result = extract_activity_fields(text, now, None)
        result["source_image_indexes"] = []
        return [result]
    payload = llm(text)
    rows = payload.get("activities") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        raise ValueError("MiniMax multi-activity response must contain an activities array")
    normalized = []
    for row in rows:
        if not isinstance(row, dict) or not str(row.get("name") or "").strip():
            continue
        normalized.append(normalize_activity_row(row, now))
    return normalized
