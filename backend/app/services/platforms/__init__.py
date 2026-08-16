"""Platform adapters (one per social media platform)."""
from app.services.platforms.base import (
    PlatformAdapter,
    CheckLoginResult,
    BrowseResult,
    FavoriteItem,
)
from app.services.platforms import registry

__all__ = ["PlatformAdapter", "CheckLoginResult", "BrowseResult", "FavoriteItem", "registry"]