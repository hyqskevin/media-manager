"""抓取范围计算：根据 task_params 与城市 enabled 配置生成最终的
关键词列表与博主列表。

调用方：
- run_crawl：拿到 effective_keywords / effective_bloggers 后真正执行抓取。
- tasks.py:crawl：入口校验，二者都为空时 422。
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.blogger_city import BloggerCity
from app.models.blogger_group import BloggerGroup, BloggerGroupMember
from app.models.config import Blogger, City
from app.models.keyword_group import KeywordGroup, KeywordGroupCity, KeywordGroupWord


@dataclass
class CrawlScope:
    keywords: list[str]
    bloggers: list[Blogger]


def _resolve_from_keyword_groups(
    db: Session, city: City | None, keyword_group_ids: list[int]
) -> list[str]:
    """根据 keyword_group_ids 求并集。

    - city 不为 None：只取挂在该城市的组词（向后兼容）
    - city 为 None（不限城市）：取所有 enabled 组的并集，不做城市过滤
    """
    if not keyword_group_ids:
        return []
    stmt = (
        select(KeywordGroupWord.word)
        .join(
            KeywordGroup,
            KeywordGroup.id == KeywordGroupWord.keyword_group_id,
        )
        .where(
            KeywordGroup.id.in_(keyword_group_ids),
            KeywordGroup.enabled.is_(True),
            KeywordGroupWord.enabled.is_(True),
        )
    )
    if city is not None:
        stmt = stmt.join(
            KeywordGroupCity,
            KeywordGroupCity.keyword_group_id == KeywordGroup.id,
        ).where(
            KeywordGroupCity.city_code == city.code,
            KeywordGroupCity.enabled.is_(True),
        )
    return list(dict.fromkeys(db.scalars(stmt).all()))


def resolve_effective_keywords(db: Session, city: City | None, task_params: dict) -> list[str]:
    """规则：
    - "keywords" 键存在 → 显式词（去空白去重）；空列表 = 显式禁用关键词
    - "keyword_group_ids" 键存在 → 叠加组并集（显式词 ∪ 组词，都选都抓）
    - 两个键都不存在 → 返回空列表（legacy keywords 表已废弃）

    city 为 None 时表示不限城市，关键词组按"全 enabled 组"取并集。
    """
    has_keywords_key = "keywords" in task_params
    has_groups_key = "keyword_group_ids" in task_params
    if not has_keywords_key and not has_groups_key:
        return []
    explicit = [word.strip() for word in (task_params.get("keywords") or []) if str(word).strip()]
    group_words: list[str] = []
    ids = task_params.get("keyword_group_ids") or []
    if isinstance(ids, list) and ids:
        group_words = _resolve_from_keyword_groups(db, city, ids)
    return list(dict.fromkeys([*explicit, *group_words]))


def resolve_effective_bloggers(db: Session, city: City | None, task_params: dict) -> list[Blogger]:
    """规则（用户明确，2026-08-13 修订）：
    - task_params 含 "blogger_ids" 键 → 按 ID 过滤
    - task_params 含 "blogger_group_ids" 键 → 按组并集过滤
    - 两个键都缺省：
        - 有 city → 取该城市 enabled 博主（基于 blogger_cities 多对多表）
        - 无 city → 不取任何博主（避免全平台博主雪崩）
    - "blogger_ids" 显式传空列表 = 显式禁用博主（仅关键词生效）

    city 为 None（不限城市）时：
    - blogger_ids → 仅校验 Blogger.enabled
    - blogger_group_ids → 仅校验 BloggerGroup.enabled（组不绑城市）
    """
    ids = task_params.get("blogger_ids") or []
    group_ids = task_params.get("blogger_group_ids") or []
    has_ids_key = "blogger_ids" in task_params
    has_group_ids_key = "blogger_group_ids" in task_params

    if not has_ids_key and not has_group_ids_key:
        # 没指定博主来源：按 city 兜底
        if city is None:
            return []
        stmt = (
            select(Blogger)
            .join(BloggerCity, BloggerCity.blogger_id == Blogger.id)
            .where(
                BloggerCity.city_code == city.code,
                BloggerCity.enabled.is_(True),
                Blogger.enabled.is_(True),
            )
            .order_by(Blogger.id)
        )
        return list(db.scalars(stmt).all())

    # 有显式博主来源：ID ∪ 组并集
    blogger_id_set: set[int] = set()

    if has_ids_key and ids:
        if city is not None:
            stmt = (
                select(Blogger.id)
                .join(BloggerCity, BloggerCity.blogger_id == Blogger.id)
                .where(
                    Blogger.id.in_(ids),
                    Blogger.enabled.is_(True),
                    BloggerCity.city_code == city.code,
                    BloggerCity.enabled.is_(True),
                )
            )
        else:
            stmt = select(Blogger.id).where(
                Blogger.id.in_(ids),
                Blogger.enabled.is_(True),
            )
        blogger_id_set.update(db.scalars(stmt).all())

    if has_group_ids_key and group_ids:
        # 博主组不绑城市，只校验组自身 enabled
        if city is not None:
            # 有 city 时博主组当作博主 ID 池，再用 city 过滤
            stmt = (
                select(BloggerGroupMember.blogger_id)
                .join(BloggerGroup, BloggerGroup.id == BloggerGroupMember.group_id)
                .where(
                    BloggerGroup.id.in_(group_ids),
                    BloggerGroup.enabled.is_(True),
                )
            )
            member_ids = set(db.scalars(stmt).all())
            if member_ids:
                # 进一步按 city 过滤
                stmt2 = (
                    select(Blogger.id)
                    .join(BloggerCity, BloggerCity.blogger_id == Blogger.id)
                    .where(
                        Blogger.id.in_(member_ids),
                        Blogger.enabled.is_(True),
                        BloggerCity.city_code == city.code,
                        BloggerCity.enabled.is_(True),
                    )
                )
                blogger_id_set.update(db.scalars(stmt2).all())
        else:
            # 不限城市：组内成员都收
            stmt = (
                select(BloggerGroupMember.blogger_id)
                .join(BloggerGroup, BloggerGroup.id == BloggerGroupMember.group_id)
                .where(
                    BloggerGroup.id.in_(group_ids),
                    BloggerGroup.enabled.is_(True),
                    Blogger.enabled.is_(True),
                )
                .join(Blogger, Blogger.id == BloggerGroupMember.blogger_id)
            )
            blogger_id_set.update(db.scalars(stmt).all())

    if not blogger_id_set:
        return []
    stmt = select(Blogger).where(Blogger.id.in_(blogger_id_set)).order_by(Blogger.id)
    return list(db.scalars(stmt).all())


def resolve_crawl_scope(db: Session, city: City | None, task_params: dict) -> CrawlScope:
    return CrawlScope(
        keywords=resolve_effective_keywords(db, city, task_params),
        bloggers=resolve_effective_bloggers(db, city, task_params),
    )
