"""XHS web adapter (v0.2 fully implemented).

6 methods: check_login / browse_home / like_post / favorite_post / fetch_favorites.
All browser operations use anti_detection.human utilities (NEVER raw page.click/fill).
"""
from __future__ import annotations

import logging

from app.anti_detection.human import human_pause, human_click, random_scroll
from app.anti_detection.human import human_type
from app.models.platform_account import PlatformType
from app.services.platforms.base import (
    PlatformAdapter,
    CheckLoginResult,
    BrowseResult,
    FavoriteItem,
)

logger = logging.getLogger(__name__)


class XhsWebAdapter(PlatformAdapter):
    platform = PlatformType.XHS
    display_name = "小红书"
    icon = "🔴"
    status = "implemented"

    XHS_HOME_URL = "https://www.xiaohongshu.com/"
    XHS_EXPLORE_URL = "https://www.xiaohongshu.com/explore"
    XHS_FAVORITES_URL = "https://www.xiaohongshu.com/user/notes/favorite?type=note"

    # CSS selectors (xhs public web; update if site structure changes)
    SEL_USER_INFO = ".user-info, .user-info-container, [class*='user-info']"
    SEL_FEED_ITEM = "section.note-item, [class*='note-item']"
    SEL_LIKE_BTN = "[class*='like'], .like-icon, .interaction-info .like"
    SEL_COLLECT_BTN = "[class*='collect'], [class*='fav'], .interaction-info .collect"
    SEL_TITLE = ".title, [class*='title']"
    SEL_AUTHOR = ".author, [class*='author']"

    async def check_login(self, context) -> CheckLoginResult:
        """Visit xhs home, detect user-info element to determine login state."""
        page = await context.new_page()
        try:
            await page.goto(self.XHS_HOME_URL, wait_until="domcontentloaded", timeout=15000)
            await human_pause(2.0, 4.0)

            user_info_count = await page.locator(self.SEL_USER_INFO).count()
            logged_in = user_info_count > 0
            return CheckLoginResult(logged_in=logged_in)
        except Exception as e:
            logger.exception("XHS check_login failed")
            return CheckLoginResult(logged_in=False, error=str(e))
        finally:
            await page.close()

    async def browse_home(self, context, duration_seconds: int) -> BrowseResult:
        """Browse xhs explore feed, scroll + pause to simulate reading."""
        page = await context.new_page()
        elapsed = 0
        pages_visited = 0
        try:
            await page.goto(self.XHS_EXPLORE_URL, wait_until="domcontentloaded", timeout=15000)
            await human_pause(2.0, 4.0)

            while elapsed < duration_seconds:
                await random_scroll(page)
                await human_pause(5.0, 15.0)
                elapsed += 10
                pages_visited += 1

            return BrowseResult(pages_visited=pages_visited, duration_seconds=elapsed)
        except Exception as e:
            logger.exception("XHS browse_home failed")
            return BrowseResult(error=str(e))
        finally:
            await page.close()

    async def like_post(self, context, post_url: str) -> bool:
        """Visit a post and click the like button."""
        page = await context.new_page()
        try:
            await page.goto(post_url, wait_until="domcontentloaded", timeout=15000)
            await human_pause(2.0, 4.0)

            like_btn = page.locator(self.SEL_LIKE_BTN).first
            if await like_btn.count() == 0:
                return False

            await human_click(page, self.SEL_LIKE_BTN)
            await human_pause(1.0, 2.0)
            return True
        except Exception:
            logger.exception("XHS like_post failed")
            return False
        finally:
            await page.close()

    async def favorite_post(self, context, post_url: str) -> bool:
        """Visit a post and click the favorite (collect) button."""
        page = await context.new_page()
        try:
            await page.goto(post_url, wait_until="domcontentloaded", timeout=15000)
            await human_pause(2.0, 4.0)

            fav_btn = page.locator(self.SEL_COLLECT_BTN).first
            if await fav_btn.count() == 0:
                return False

            await human_click(page, self.SEL_COLLECT_BTN)
            await human_pause(1.0, 2.0)
            return True
        except Exception:
            logger.exception("XHS favorite_post failed")
            return False
        finally:
            await page.close()

    async def fetch_favorites(self, context, max_items: int = 100) -> list[FavoriteItem]:
        """Visit favorites page, scroll-load, extract note items."""
        page = await context.new_page()
        items: list[FavoriteItem] = []
        try:
            await page.goto(self.XHS_FAVORITES_URL, wait_until="domcontentloaded", timeout=15000)
            await human_pause(3.0, 5.0)

            for _ in range(5):  # max 5 scroll rounds
                note_items = page.locator(self.SEL_FEED_ITEM)
                count = await note_items.count()
                for i in range(count):
                    if len(items) >= max_items:
                        break
                    item = note_items.nth(i)

                    note_id = await item.get_attribute("data-note-id") or ""
                    title_el = item.locator(self.SEL_TITLE).first
                    title = (await title_el.text_content() or "").strip() if await title_el.count() else ""
                    author_el = item.locator(self.SEL_AUTHOR).first
                    author = (await author_el.text_content() or "").strip() if await author_el.count() else ""
                    link_el = item.locator("a").first
                    url = await link_el.get_attribute("href") if await link_el.count() else ""
                    if url and not url.startswith("http"):
                        url = f"https://www.xiaohongshu.com{url}"

                    items.append(FavoriteItem(
                        note_id=note_id or f"item-{i}",
                        title=title or "(无标题)",
                        author=author or "(未知作者)",
                        url=url or "",
                    ))

                await random_scroll(page)
                await human_pause(2.0, 4.0)

            return items
        except Exception:
            logger.exception("XHS fetch_favorites failed")
            return items  # partial success
        finally:
            await page.close()