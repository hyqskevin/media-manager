"""PlatformAdapter abstract base class + data models.

All platform adapters must implement 6 methods (v0.2 scope).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.models.platform_account import PlatformType


@dataclass
class CheckLoginResult:
    """check_login execution result."""
    logged_in: bool = False
    user_id: str = ""
    nickname: str = ""
    error: str = ""


@dataclass
class BrowseResult:
    """browse_home execution result."""
    pages_visited: int = 0
    duration_seconds: int = 0
    error: str = ""


@dataclass
class FavoriteItem:
    """Favorite item (cross-platform common shape)."""
    note_id: str
    title: str
    author: str
    url: str
    cover_url: str = ""
    liked_at: str = ""  # ISO 8601


class PlatformAdapter(ABC):
    """Abstract base class for all platform adapters.

    Attributes:
        platform: PlatformType enum value
        display_name: Chinese display name
        icon: emoji icon
        status: "implemented" (xhs only) or "stub" (rest)
    """

    platform: PlatformType
    display_name: str
    icon: str
    status: str = "stub"

    @abstractmethod
    async def check_login(self, context) -> CheckLoginResult: ...

    @abstractmethod
    async def browse_home(self, context, duration_seconds: int) -> BrowseResult: ...

    @abstractmethod
    async def like_post(self, context, post_url: str) -> bool: ...

    @abstractmethod
    async def favorite_post(self, context, post_url: str) -> bool: ...

    @abstractmethod
    async def fetch_favorites(self, context, max_items: int = 100) -> list[FavoriteItem]: ...