import re
from urllib.parse import urlsplit, urlunsplit


_NOTE_PATTERNS = (
    re.compile(r"/(?:explore|search_result)/([^/?#]+)"),
    re.compile(r"/discovery/item/([^/?#]+)"),
    re.compile(r"/user/profile/[^/?#]+/([^/?#]+)"),
)


def extract_platform_note_id(url: str) -> str | None:
    path = urlsplit((url or "").strip()).path
    for pattern in _NOTE_PATTERNS:
        match = pattern.search(path)
        if match:
            return match.group(1)
    return None


def canonicalize_note_url(url: str) -> str:
    parsed = urlsplit((url or "").strip())
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path.rstrip("/"), "", ""))
