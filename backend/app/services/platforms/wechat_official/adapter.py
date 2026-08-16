"""微信公众号 platform adapter (v0.2 stub)."""
from app.models.platform_account import PlatformType
from app.services.platforms.base import (
    PlatformAdapter,
    CheckLoginResult,
    BrowseResult,
    FavoriteItem,
)


class WechatOfficialAdapter(PlatformAdapter):
    platform = PlatformType.WECHAT_OFFICIAL
    display_name = "微信公众号"
    icon = "📰"
    status = "stub"

    async def check_login(self, context):
        raise NotImplementedError("微信公众号 v0.3 实现")

    async def browse_home(self, context, duration_seconds):
        raise NotImplementedError("微信公众号 v0.3 实现")

    async def like_post(self, context, post_url):
        raise NotImplementedError("微信公众号 v0.3 实现")

    async def favorite_post(self, context, post_url):
        raise NotImplementedError("微信公众号 v0.3 实现")

    async def fetch_favorites(self, context, max_items):
        raise NotImplementedError("微信公众号 v0.3 实现")
