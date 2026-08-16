"""博主自动补全：用 opencli search 把只填了 username 的博主补上 platform_user_id/profile_url。

约定：
- 只补"profile_url 为空"的博主；已有 URL 的不动。
- platform_user_id 已存在时不覆盖（保留人工填的真实 ID）；但 profile_url 仍可补。
- search 失败 / 找不到匹配 → 跳过，记日志（由调用方负责日志）。
"""

from collections.abc import Callable
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.config import Blogger

SearchRunner = Callable[[list[str]], list[dict]]


def _extract_user_id_and_clean_url(author_url: str) -> tuple[str | None, str | None]:
    """从 author_url 提取 user_id 和清理后的 profile_url。

    输入可能带 query string（?channel_type=...&xsec_token=...）。
    返回 (user_id, profile_url)；任一缺失返回 (None, None)。
    """
    if not author_url or "/user/profile/" not in author_url:
        return None, None
    try:
        parsed = urlparse(author_url)
    except ValueError:
        return None, None
    parts = [p for p in parsed.path.split("/") if p]
    if "profile" not in parts:
        return None, None
    user_id = parts[-1] if parts else None
    if not user_id:
        return None, None
    clean_url = f"https://www.xiaohongshu.com/user/profile/{user_id}"
    return user_id, clean_url


def _search_for_username(search_runner: SearchRunner, username: str, limit: int) -> list[dict]:
    """用 search 命令按用户名查找笔记，返回 author/author_url 列表。"""
    try:
        return search_runner(["xiaohongshu", "search", username, "-f", "json", "--window", "background", "--limit", str(limit)])
    except Exception:
        return []


def enrich_bloggers(db: Session, bloggers: list[Blogger], *, search_runner: SearchRunner, limit: int = 5) -> list[int]:
    """补全博主信息。返回成功填充的 blogger.id 列表。

    只处理 profile_url 为空的博主（已有完整信息的跳过）。
    platform_user_id 已存在时不覆盖。
    """
    filled_ids: list[int] = []
    # 用 cache 避免同一关键词重复 search（博主去重）
    cache: dict[str, list[dict]] = {}

    for b in bloggers:
        if (b.profile_url or "").strip():
            continue  # 已有 profile_url，跳过
        if b.username not in cache:
            cache[b.username] = _search_for_username(search_runner, b.username, limit)
        results = cache[b.username]
        for item in results:
            author = (item.get("author") or "").strip()
            if author.replace(" ", "") != b.username.replace(" ", ""):
                continue
            user_id, profile_url = _extract_user_id_and_clean_url(item.get("author_url", ""))
            if not user_id or not profile_url:
                continue
            if not b.platform_user_id:
                b.platform_user_id = user_id
            b.profile_url = profile_url
            filled_ids.append(b.id)
            break
    if filled_ids:
        db.commit()
    return filled_ids