"""从小红书 note ID（ObjectID 雪花算法）解析推文发布时间。

小红书 note ID 是 24 hex 的 mongo-like ObjectID：前 8 个 hex 字符是 epoch 秒。
按 UTC+8 解读，返回 Asia/Shanghai 时区的北京墙钟 datetime（与库存储口径一致）。

注意 URL 形态：博主主页链接 /user/profile/<用户ID 24hex>/<笔记ID 24hex>
含两个 24 hex，必须取路径中**最后一个**（笔记 ID）；取第一个会解出博主
账号注册时间（生产事故：任务 #19 同博主 15 篇笔记发布时间全是注册日）。"""
import re
from datetime import datetime
from urllib.parse import urlsplit

from app.services.published_at import SHANGHAI


_NOTE_ID_RE = re.compile(r"[0-9a-f]{24}", re.IGNORECASE)


def note_id_published_at(note_id_or_url: str | None) -> datetime | None:
    """从 note ID 或完整 URL 中提取笔记 ID；前 8 hex = epoch 秒。

    提取规则：剥离 query string，只在 URL path 中匹配，取**最后一个** 24 hex。
    - /user/profile/<uid>/<noteid> → noteid
    - /explore/<noteid>、/search_result/<noteid> → 唯一一个
    - 裸 24 hex 字符串 → 其本身

    返回 Asia/Shanghai 时区的 datetime（北京墙钟），精度到秒。
    非法输入（None/空/无 24hex/全 0/超出合理 epoch 范围）返回 None。
    """
    if not note_id_or_url:
        return None
    text = note_id_or_url.strip()
    # 是 URL 时只取 path 部分，防止 query（xsec_token 等）中的 24hex 干扰
    if "://" in text:
        text = urlsplit(text).path
    matches = _NOTE_ID_RE.findall(text)
    if not matches:
        return None
    hex_prefix = matches[-1][:8]
    try:
        ts = int(hex_prefix, 16)
    except ValueError:
        return None
    if ts < 1_000_000_000 or ts > 4_000_000_000:
        return None
    # 复现 OpenCLI noteIdToDate 算法：epoch 秒按 UTC+8 解读即为北京墙钟发布时间。
    # 0x697f6c74 = 1769958516 → 2026-02-01 23:08:36 +08:00。
    return datetime.fromtimestamp(ts, tz=SHANGHAI)
