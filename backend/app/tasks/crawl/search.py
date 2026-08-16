"""搜索阶段：搜索 + 博主发现。

- ``throttled_search`` 单次搜索的频率与周配额闸门；
- ``_collect_crawl_results`` 执行 SEARCHING 阶段，遍历城市/关键词/博主；
- ``_collect_cities_from_groups`` / ``_expand_blogger_groups`` 城市/博主组展开。
"""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy import select

from app.models.blogger_city import BloggerCity
from app.models.blogger_group import BloggerGroup, BloggerGroupMember
from app.models.config import Blogger, City
from app.models.keyword_group import KeywordGroupCity
from app.models.task import CrawlTask
from app.services.crawler import AuthenticationRequired, CrawlHalted
from app.services.crawl_scope import resolve_crawl_scope
from app.services.opencli_adapter import OpenCLIAdapter
from app.services.search_rate_limit import (
    SearchRateLimiter,
    increment_weekly_search,
    iso_week_key,
    weekly_search_count,
)

from app.tasks.crawl.runtime import assert_execution_active, log, rate_limit_sleep


def _collect_cities_from_groups(db, task_params: dict) -> list[str]:
    """不限城市（city 为空）时，从博主组/关键词组挂的城市合并出抓取城市列表。

    - 博主组 → 从 BloggerCity 取组内博主挂的城市（去重保留顺序）
    - 关键词组 → 从 KeywordGroupCity 取组挂的城市
    """
    city_codes: list[str] = []
    seen: set[str] = set()

    # 博主组：组内所有博主挂的城市
    blogger_group_ids = task_params.get("blogger_group_ids") or []
    if blogger_group_ids:
        stmt = (
            select(BloggerCity.city_code)
            .join(BloggerGroupMember, BloggerGroupMember.blogger_id == BloggerCity.blogger_id)
            .where(
                BloggerGroupMember.group_id.in_(blogger_group_ids),
                BloggerCity.enabled.is_(True),
            )
            .distinct()
        )
        for code in db.scalars(stmt).all():
            if code not in seen:
                seen.add(code)
                city_codes.append(code)

    # 关键词组：组挂的城市
    keyword_group_ids = task_params.get("keyword_group_ids") or []
    if keyword_group_ids:
        stmt = (
            select(KeywordGroupCity.city_code)
            .where(
                KeywordGroupCity.keyword_group_id.in_(keyword_group_ids),
                KeywordGroupCity.enabled.is_(True),
            )
            .distinct()
        )
        for code in db.scalars(stmt).all():
            if code not in seen:
                seen.add(code)
                city_codes.append(code)

    return city_codes


def _expand_blogger_groups(db, city_code: str | None, group_ids: list[int]) -> list[int]:
    """博主组展开。

    - city_code 给出：组内 enabled 博主 ∩ 该城市 blogger_cities.enabled 博主
    - city_code=None：组内 enabled 博主（不限城市）
    """
    if not group_ids:
        return []
    stmt = (
        select(Blogger.id)
        .join(BloggerGroupMember, BloggerGroupMember.blogger_id == Blogger.id)
        .join(BloggerGroup, BloggerGroup.id == BloggerGroupMember.group_id)
        .where(
            BloggerGroupMember.group_id.in_(group_ids),
            BloggerGroup.enabled.is_(True),
            Blogger.enabled.is_(True),
        )
    )
    if city_code:
        stmt = stmt.join(
            BloggerCity, BloggerCity.blogger_id == Blogger.id
        ).where(
            BloggerCity.city_code == city_code,
            BloggerCity.enabled.is_(True),
        )
    stmt = stmt.order_by(Blogger.id)
    return list(dict.fromkeys(db.scalars(stmt).all()))


def throttled_search(db, settings, task, adapter, query, recent, run_token=None, rate_limiter=None) -> list[dict] | None:
    """模块级 throttled_search：搜索的频率与周配额闸门；返回 None 表示本周超限。

    注：原位于 run_crawl 闭包内，提取为模块级以便测试 monkeypatch；行为完全等价。
    rate_limiter 必须由调用方复用同一个实例，否则 monkeypatch 不生效。
    """
    week_key = iso_week_key()
    if weekly_search_count(db, week_key) >= settings.weekly_search_limit:
        log(db, task.id, "WARNING", f"本周搜索量已达上限（{settings.weekly_search_limit}），跳过 {query!r} 及后续关键词搜索")
        return None
    if rate_limiter is None:
        rate_limiter = SearchRateLimiter(settings.search_interval_min, settings.search_interval_max)
    delay = rate_limiter.next_delay()
    if delay and run_token is not None:
        rate_limit_sleep(delay, guard=lambda: assert_execution_active(db, task.id, run_token))
    found = adapter.search_recent(query, recent)
    increment_weekly_search(db, week_key)
    return found


def _collect_crawl_results(
    db,
    settings,
    task: CrawlTask,
    adapter: OpenCLIAdapter,
    throttled_search: Callable[[str, str], list[dict] | None],
    run_token: str,
) -> tuple[list[tuple[str, dict]], int]:
    """执行搜索/博主发现阶段，返回 (results, discovery_failures)。

    - results: list of (city_code, item)；item 含 _matched_keywords 字段
    - discovery_failures: 博主层失败计数（连续失败熔断在调用方处理）
    - CrawlHalted 由博主层连续失败触发，由调用方捕获
    """
    results: list[tuple[str, dict]] = []
    discovery_failures = 0
    consecutive_failures = 0
    # city/cities 优先级：city 优先；若 city 为 ''（不限城市）→ 视为未指定，按 keyword_group_ids/blogger_group_ids 各自挂的城市展开
    requested_cities: list[str] = []
    if task.params.get("city"):
        requested_cities = [task.params["city"]]
    elif task.params.get("cities"):
        requested_cities = task.params["cities"]
    else:
        # city='' 或未设置：从博主组挂的城市 / 关键词组挂的城市合并
        group_cities = _collect_cities_from_groups(db, task.params)
        if group_cities:
            requested_cities = group_cities
    city_query = select(City).where(City.enabled.is_(True))
    if requested_cities:
        city_query = city_query.where(City.code.in_(requested_cities))
    cities = list(db.scalars(city_query.order_by(City.id)).all())
    if cities:
        for city in cities:
            scope = resolve_crawl_scope(db, city, task.params)
            override = "任务参数" if ("keywords" in task.params or "blogger_ids" in task.params) else "配置默认"
            log(db, task.id, "INFO", f"抓取范围生效：keywords={len(scope.keywords)} bloggers={len(scope.bloggers)} (override={override})")
            # 博主挂在 blogger_cities 多对多表，按当前 scope 里的 blogger.id 批量反查 enabled 城市。
            # 避免 N+1 查询；也不依赖 Blogger.cities 这个 relationship（模型没定义）。
            blogger_id_to_cities: dict[int, list[str]] = {}
            if scope.bloggers:
                from collections import defaultdict
                rows = db.execute(
                    select(BloggerCity.blogger_id, BloggerCity.city_code)
                    .where(
                        BloggerCity.blogger_id.in_([b.id for b in scope.bloggers]),
                        BloggerCity.enabled.is_(True),
                    )
                ).all()
                bucket: dict[int, list[str]] = defaultdict(list)
                for row in rows:
                    bucket[row.blogger_id].append(row.city_code)
                blogger_id_to_cities = dict(bucket)
            recent_filter = task.params.get("recent_filter") or city.recent_filter
            for keyword in scope.keywords:
                found = throttled_search(f"{city.name} {keyword}", recent_filter)
                if found is None:
                    break
                for item in found:
                    tagged = dict(item)
                    tagged["_matched_keywords"] = [keyword]
                    results.append((city.code, tagged))
                assert_execution_active(db, task.id, run_token)
            for blogger in scope.bloggers:
                username = (blogger.username or "").strip()
                if not username:
                    log(db, task.id, "WARNING", f"跳过博主：username 为空 id={blogger.id}")
                    continue
                try:
                    items = adapter.blogger_notes(username, blogger.profile_url or "")
                except (AuthenticationRequired, ExecutionStopped, ExecutionSuperseded):
                    raise
                except Exception as exc:
                    discovery_failures += 1
                    task.error_message = f"博主 {username!r} 抓取失败：{exc}"
                    db.commit()
                    log(db, task.id, "ERROR", task.error_message)
                    consecutive_failures += 1
                    if consecutive_failures >= settings.consecutive_note_failure_limit:
                        raise CrawlHalted(
                            f"已连续 {consecutive_failures} 次抓取失败（最近一次：博主 {username!r}）。"
                            f"CDP session / 浏览器标签页可能已过期，请在 Chrome 重新打开小红书后"
                            f"点击「检测登录并继续」，或「结束抓取」。最后一次错误：{exc}"
                        )
                    continue
                consecutive_failures = 0
                assert_execution_active(db, task.id, run_token)
                log(db, task.id, "INFO", f"博主 {username!r} 命中 {len(items)} 篇（带 xsec_token 的）")
                if blogger.max_notes_per_crawl and blogger.max_notes_per_crawl > 0 and len(items) > blogger.max_notes_per_crawl:
                    log(db, task.id, "INFO", f"博主 {username!r} 抓取上限 {blogger.max_notes_per_crawl}，截断至 {blogger.max_notes_per_crawl} 篇")
                    items = items[:blogger.max_notes_per_crawl]
                for item in items:
                    tagged = dict(item)
                    tagged["_matched_blogger_id"] = blogger.id
                    tagged["_matched_blogger_username"] = blogger.username
                    # 多城市博主：博主可能挂 nb + hz 两个城市，但当前任务是 nb 调度；
                    # city.code 直接写 nb 会让 hz 笔记误归 nb。这里用任务城市标注，
                    # 把"博主挂的真实城市列表"一起带上，方便下游重新核对或纠正。
                    tagged["_matched_blogger_cities"] = sorted(
                        blogger_id_to_cities.get(blogger.id, [])
                    )
                    results.append((city.code, tagged))
    else:
        for city_code in requested_cities:
            quota_exceeded = False
            for keyword in task.params.get("keywords", []):
                found = throttled_search(f"{city_code} {keyword}", "一周内")
                if found is None:
                    quota_exceeded = True
                    break
                for item in found:
                    tagged = dict(item)
                    tagged["_matched_keywords"] = [keyword]
                    results.append((city_code, tagged))
                assert_execution_active(db, task.id, run_token)
            if quota_exceeded:
                break
    return results, discovery_failures
