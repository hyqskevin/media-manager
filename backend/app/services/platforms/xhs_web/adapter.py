"""XHS web adapter skeleton (v0.2).

Full implementation in Task 5 (browse/like/favorite/fetch_favorites).
This skeleton provides stub methods that return error results without launching
real browser, used by registry.test_platform_registry.
"""
from app.models.platform_account import PlatformType
from app.services.platforms.base import (
    PlatformAdapter,
    CheckLoginResult,
    BrowseResult,
    FavoriteItem,
)


class XhsWebAdapter(PlatformAdapter):
    platform = PlatformType.XHS
    display_name = "小红书"
    icon = "🔴"
    status = "implemented"

    XHS_HOME_URL = "https://www.xiaohongshu.com/"
    XHS_EXPLORE_URL = "https://www.xiaohongshu.com/explore"
    XHS_FAVORITES_URL = "https://www.xiaohongshu.com/user/notes/favorite?type=note"

    async def check_login(self, context) -> CheckLoginResult:
        # TODO(Task 5): real implementation via patchright + stealth
        return CheckLoginResult(logged_in=False, error="xhs-web not yet implemented (Task 5)")

    async def browse_home(self, context, duration_seconds: int) -> BrowseResult:
        return BrowseResult(error="xhs-web not yet implemented (Task 5)")

    async def like_post(self, context, post_url: str) -> bool:
        return False

    async def favorite_post(self, context, post_url: str) -> bool:
        return False

    async def fetch_favorites(self, context, max_items: int = 100) -> list[FavoriteItem]:
        return []