"""真人行为随机化工具（参考 reference/anti-detection-notes.md §2.3）。

所有 PlatformAdapter 的 browser 操作（点击 / 输入 / 滚动）必须通过本模块，
禁止直接调用 page.click / page.fill，否则会被风控识别。
"""
from __future__ import annotations

import asyncio
import random


def random_jitter(base_ms: int, jitter_ratio: float = 0.5) -> int:
    """在 [base*(1-jitter), base*(1+jitter)] 范围内随机返回毫秒数。

    例: random_jitter(100) → [50, 150]
    """
    low = int(base_ms * (1 - jitter_ratio))
    high = int(base_ms * (1 + jitter_ratio))
    return random.randint(low, high)


def random_delay(min_s: float, max_s: float) -> float:
    """在 [min_s, max_s] 范围内随机返回秒数。"""
    return random.uniform(min_s, max_s)


async def human_pause(min_s: float = 3.0, max_s: float = 15.0) -> None:
    """模拟真人操作的随机停顿。"""
    await asyncio.sleep(random_delay(min_s, max_s))


async def human_type(page, selector: str, text: str, per_char_ms: int = 80) -> None:
    """逐字输入（30-150ms/字符），模拟真实键盘。"""
    locator = page.locator(selector)
    await locator.click()
    await human_pause(0.3, 0.8)
    for ch in text:
        await locator.type(ch, delay=random_jitter(per_char_ms))
        await asyncio.sleep(0.01)


async def human_click(page, selector: str) -> None:
    """模拟真人点击：先移到目标附近，停 0.5-1.5s，再点击。"""
    box = await page.locator(selector).bounding_box()
    if box:
        # 偏移到中心 + 随机 ±5px
        offset_x = box["x"] + box["width"] / 2 + random.uniform(-5, 5)
        offset_y = box["y"] + box["height"] / 2 + random.uniform(-5, 5)
        await page.mouse.move(offset_x, offset_y)
    await human_pause(0.5, 1.5)
    await page.locator(selector).click()


async def random_scroll(page, min_pixels: int = 200, max_pixels: int = 800) -> None:
    """模拟真人滚动：随机方向 + 随机像素数 + 停顿。"""
    direction = random.choice([1, -1])
    pixels = random.randint(min_pixels, max_pixels) * direction
    await page.mouse.wheel(0, pixels)
    await human_pause(0.5, 2.0)