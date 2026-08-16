"""Platform adapter registry (auto-discovery + lookup)."""
from __future__ import annotations

import logging
from typing import Optional

from app.models.platform_account import PlatformType
from app.services.platforms.base import PlatformAdapter

logger = logging.getLogger(__name__)

_ADAPTERS: dict[PlatformType, PlatformAdapter] = {}
_LOADED: bool = False


def register(adapter: PlatformAdapter) -> None:
    """Register a platform adapter."""
    _ADAPTERS[adapter.platform] = adapter


def get(platform: PlatformType) -> Optional[PlatformAdapter]:
    """Get platform adapter (None if not registered)."""
    load_all()
    return _ADAPTERS.get(platform)


def all_implemented() -> list[PlatformAdapter]:
    """List all registered adapters in PlatformType order."""
    load_all()
    return [_ADAPTERS[pt] for pt in PlatformType if pt in _ADAPTERS]


def load_all() -> None:
    """Import all platform modules to trigger register() (idempotent)."""
    global _LOADED
    if _LOADED:
        return
    # Import in alphabetical order
    for mod in (
        "bilibili",
        "douyin",
        "twitter",
        "wechat_official",
        "weibo",
        "xhs_web",
        "xiaoyuzhou",
        "zhihu",
    ):
        try:
            __import__(f"app.services.platforms.{mod}", fromlist=["register"])
        except ImportError as e:
            logger.warning(f"Failed to load platform {mod}: {e}")
    _LOADED = True