from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


class ActivityWindow:
    def __init__(self, reference: datetime, days: int, timezone_name: str) -> None:
        timezone = ZoneInfo(timezone_name)
        if reference.tzinfo is not None:
            reference = reference.astimezone(timezone).replace(tzinfo=None)
        reference_date = reference.date()
        self.start = datetime.combine(reference_date, time.min)
        self.end = datetime.combine(reference_date + timedelta(days=days), time.max)
        self.timezone = timezone

    def _local_naive(self, value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(self.timezone).replace(tzinfo=None)
        return parsed

    def classify(self, start_time: str | None, end_time: str | None) -> str:
        if not start_time:
            return "unknown"
        start = self._local_naive(start_time)
        end = self._local_naive(end_time) if end_time else start
        if end < start:
            end = start
        if end < self.start:
            return "past"
        if start > self.end:
            return "future"
        return "valid"
