"""小宇宙 platform adapter (v0.2 stub)."""
from app.models.platform_account import PlatformType
from app.services.platforms.base import (
    PlatformAdapter,
    CheckLoginResult,
    BrowseResult,
    FavoriteItem,
)


class XiaoyuzhouAdapter(PlatformAdapter):
    platform = PlatformType.XIAOYUZHOU
    display_name = "小宇宙"
    icon = "🎙️"
    status = "stub"

    async def check_login(self, context):
        raise NotImplementedError("小宇宙 v0.3 实现")

    async def browse_home(self, context, duration_seconds):
        raise NotImplementedError("小宇宙 v0.3 实现")

    async def like_post(self, context, post_url):
        raise NotImplementedError("小宇宙 v0.3 实现")

    async def favorite_post(self, context, post_url):
        raise NotImplementedError("小宇宙 v0.3 实现")

    async def fetch_favorites(self, context, max_items):
        raise NotImplementedError("小宇宙 v0.3 实现")
