#!/usr/bin/env -S uv run --project ../backend python
"""xhs 登录态引导：手动登录一次，保存 storage_state 给养号任务复用。

用法：
    uv run --project ../backend python scripts/xhs_login_setup.py [account_label]

输出：
    data/storage_states/xhs_<account_label>.json

环境：
    需要已经 `uv run --project ../backend patchright install chromium`
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

# ROOT_DIR = 项目根（含 data/）
ROOT_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = ROOT_DIR / "data" / "storage_states"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

XHS_HOME = "https://www.xiaohongshu.com/"
XHS_LOGIN_URL = "https://www.xiaohongshu.com/login"
SEL_USER_INFO = ".user-info, .user-info-container, [class*='user-info']"

MAX_WAIT_LOGIN_SECONDS = 180  # 给用户 3 分钟扫码/输账号


async def main(label: str = "main") -> int:
    from patchright.async_api import async_playwright  # noqa: PLC0415
    from app.anti_detection.context import new_stealth_context  # noqa: PLC0415

    target = STORAGE_DIR / f"xhs_{label}.json"
    if target.exists() and not "--force" in sys.argv:
        age_days = (time.time() - target.stat().st_mtime) / 86400
        print(f"[SKIP] 已存在登录态 {target}（{age_days:.1f} 天前保存）")
        print("       传 --force 强制重新登录")
        return 0

    print(f"[BOOT] 启动 headed chromium（headless=False）...")
    print(f"       登录态将保存到 {target}")
    print(f"       浏览器里请访问 {XHS_LOGIN_URL} 完成登录")
    print(f"       最多等 {MAX_WAIT_LOGIN_SECONDS}s，超时自动退出")

    async with async_playwright() as p:
        # headed 模式必须有 GUI（你本机能直接看）
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN"],
        )
        context = await new_stealth_context(browser, headless=False)
        page = await context.new_page()
        await page.goto(XHS_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        print("[WAIT] 请在弹出的浏览器里扫码或手机号登录...")

        # 轮询直到出现 user-info 元素（登录成功标志）
        start = time.time()
        logged_in = False
        while time.time() - start < MAX_WAIT_LOGIN_SECONDS:
            try:
                count = await page.locator(SEL_USER_INFO).count()
                if count > 0:
                    logged_in = True
                    break
            except Exception:
                pass
            await asyncio.sleep(2)
            elapsed = int(time.time() - start)
            print(f"       ...已等 {elapsed}s", end="\r")

        if not logged_in:
            print(f"\n[TIMEOUT] {MAX_WAIT_LOGIN_SECONDS}s 内未检测到登录状态")
            await context.close()
            await browser.close()
            return 1

        # 保存 storage_state
        state = await context.storage_state(path=str(target))
        print(f"\n[OK] 登录成功，storage_state 保存到 {target}")
        print(f"     origin={state.get('origins', [])[:1]} cookies={len(state.get('cookies', []))}")

        await context.close()
        await browser.close()

    return 0


if __name__ == "__main__":
    label = sys.argv[1] if len(sys.argv) > 1 else "main"
    sys.exit(asyncio.run(main(label)))