"""Stealth context wrapper: each BrowserContext automatically injects stealth.min.js
+ anti-detection launch args.

Reference: reference/anti-detection-notes.md §2.2 and §4.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

# Path to the bundled stealth.min.js (puppeteer-extra auto-generated)
STEALTH_JS_PATH: Path = Path(__file__).parent / "stealth.min.js"

# Key launch args (reference social-auto-upload/browser_hook.py)
STEALTH_LAUNCH_ARGS: list[str] = [
    "--disable-blink-features=AutomationControlled",
    "--lang=zh-CN",
    "--disable-infobars",
    "--start-maximized",
    "--no-sandbox",
]


async def new_stealth_context(
    browser,
    storage_state: Optional[str] = None,
    headless: bool = True,
):
    """Create BrowserContext and inject stealth.min.js.

    Args:
        browser: patchright.async_api.Browser instance
        storage_state: Playwright storage_state JSON path (cookie file for nurture)
        headless: headless mode (True required for nurture)

    Returns:
        BrowserContext (with stealth injected)
    """
    kwargs: dict = {}
    if storage_state:
        kwargs["storage_state"] = storage_state

    context = await browser.new_context(**kwargs)
    await context.add_init_script(path=str(STEALTH_JS_PATH))
    return context