"""账号加载与 Chrome CDP 端点解析。

- ``load_xhs_accounts`` 加载启用账号（按 priority、id 排序）；
- ``_account_cdp_endpoint`` / ``_resolve_cdp_endpoint_for_account`` 静态/动态解析 CDP 端点；
- ``_make_chrome_pool_for_task`` 为当前任务启动 ChromePool（复用全局单例）。
"""
from __future__ import annotations

from sqlalchemy import select

from app.models.xhs_account import XhsAccount
from app.services.chrome_pool import ChromeLaunchError, ChromePool, get_global_chrome_pool


def load_xhs_accounts(db) -> list:
    """加载已启用的 XhsAccount 列表，按 priority 升序、id 升序排列。

    无账号配置时返回空列表，调用方负责回退到默认 session 'xhs-crawler'。
    """
    return list(db.scalars(
        select(XhsAccount)
        .where(XhsAccount.enabled.is_(True))
        .order_by(XhsAccount.priority, XhsAccount.id)
    ).all())


def _account_cdp_endpoint(account) -> str | None:
    """从 XhsAccount.cdp_port 推导 CDP 端点（仅基于账号行静态推导，不依赖 pool 实例）；None 表示回退默认 Chrome Browser Bridge。"""
    port = getattr(account, "cdp_port", None)
    if port is None:
        return None
    return f"http://127.0.0.1:{port}"


def _resolve_cdp_endpoint_for_account(account, chrome_pool) -> str | None:
    """优先用 chrome_pool 中已启动实例的端点（动态端口）；fallback 到账号行的 cdp_port。"""
    if chrome_pool is not None:
        instance = chrome_pool.get(account.session_name)
        if instance is not None:
            return instance.cdp_endpoint
    return _account_cdp_endpoint(account)


def _make_chrome_pool_for_task(settings, db, accounts) -> ChromePool:
    """为当前任务启动 ChromePool（每个有 cdp_port 的账号一个实例）。

    使用全局 ChromePool 单例——API 端点（如 check-login）和 crawl_task 共享同一池，
    避免重复启动 Chrome 实例导致端口冲突。
    """
    pool = get_global_chrome_pool()
    # 同步端口到 DB（持久化，供下次复用）
    for account in accounts:
        port = getattr(account, "cdp_port", None)
        if port is None:
            continue
        try:
            instance = pool.acquire(account.session_name)
        except ChromeLaunchError:
            raise
        # 同步实际分配端口（避免 ChromePool 分配与 cdp_port 不一致）
        if instance.port != port:
            account.cdp_port = instance.port
            db.commit()
    return pool
