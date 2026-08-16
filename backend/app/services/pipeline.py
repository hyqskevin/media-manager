import time
from collections.abc import Callable, Iterable
from typing import Any, TypeVar

from app.services.crawler import AuthenticationRequired
from app.services.note_identity import canonicalize_note_url, extract_platform_note_id

T = TypeVar("T")


def title_matches_keywords(title: str, keywords: list[str]) -> bool:
    normalized = (title or "").strip().casefold()
    return bool(normalized) and any(
        keyword.strip().casefold() in normalized
        for keyword in keywords
        if keyword.strip()
    )


def run_stage(operation: Callable[[], T], attempts: int, delay_seconds: float) -> T:
    last_error: Exception | None = None
    for attempt in range(max(1, attempts)):
        try:
            return operation()
        except AuthenticationRequired:
            raise
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts and delay_seconds > 0:
                time.sleep(delay_seconds)
    assert last_error is not None
    raise last_error


def deduplicate_results(rows: Iterable[tuple[str, dict[str, Any]]]) -> list[tuple[str, dict[str, Any]]]:
    seen: dict[str, dict[str, Any]] = {}
    unique = []
    for city, item in rows:
        url = str(item.get("url") or "")
        if not url:
            continue
        platform_note_id = extract_platform_note_id(url)
        identity = f"{city}:{platform_note_id}" if platform_note_id else f"{city}:{canonicalize_note_url(url)}"
        if identity in seen:
            target = seen[identity]
            keywords = target.setdefault("_matched_keywords", [])
            for keyword in item.get("_matched_keywords", []):
                if keyword not in keywords:
                    keywords.append(keyword)
            # Keep the newest signed URL so detail retrieval uses the freshest token.
            target["url"] = url
            continue
        copied = dict(item)
        if "_matched_keywords" in copied:
            copied["_matched_keywords"] = list(dict.fromkeys(copied["_matched_keywords"]))
        seen[identity] = copied
        unique.append((city, copied))
    return unique

