"""多小红书账号配置 CRUD + check-login 端点。

关联 spec:
- docs/superpowers/specs/2026-08-10-multi-xhs-account-design.md
- docs/superpowers/specs/2026-08-12-xhs-account-registration.md
"""
import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import require_admin
from app.models.xhs_account import XhsAccount
from app.services.audit import record_audit
from app.services.crawler import AuthenticationRequired, VerificationRequired
from app.services.opencli_adapter import OpenCLIAdapter
from app.services.chrome_pool import ChromePool, ChromeLaunchError, get_global_chrome_pool

router = APIRouter(prefix="/xhs-accounts", tags=["xhs-accounts"])
Admin = Annotated[dict[str, str], Depends(require_admin)]


# ── 工具函数 ──────────────────────────────────────────────────────────────


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    """从 name 派生 session_name 候选：小写 + 仅保留 [a-z0-9] + 折叠连续分隔符 + 去首尾分隔符。

    例: "hanamaki" → "hanamaki"；"测试 账号" → ""；"My Account!" → "my-account"
    """
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug


def _next_available_session_name(db: Session, name: str) -> str:
    """根据 name 自动生成不重复的 session_name（xhs-<slug> 或 xhs-<slug>-N）。

    - 第一个同名：xhs-<slug>
    - 重名：xhs-<slug>-2、-3、...
    - 若 name slugify 后为空（纯中文/空格）：使用 xhs-account-<id> 兜底
    """
    base_slug = _slugify(name)
    if not base_slug:
        # name 全部是非 ASCII 字符（中文）→ 取 XhsAccount 表当前最大 id + 1 作为兜底后缀
        max_id = db.scalar(select(XhsAccount.id).order_by(XhsAccount.id.desc())) or 0
        base_slug = f"account-{max_id + 1}"
    candidate = f"xhs-{base_slug}"
    existing = set(
        db.scalars(
            select(XhsAccount.session_name).where(XhsAccount.session_name.like(f"{candidate}%"))
        ).all()
    )
    if candidate not in existing:
        return candidate
    n = 2
    while f"{candidate}-{n}" in existing:
        n += 1
    return f"{candidate}-{n}"
DB = Annotated[Session, Depends(get_db)]


_CDP_PORT_START = 9223
_CDP_PORT_RANGE = 100  # 与 chrome_pool.py 同口径：9223-9322 范围分配


def _next_available_cdp_port(db: Session) -> int:
    """从 9223 开始扫描，跳过已被占用的端口，返回第一个空闲端口。"""
    used = set(
        db.scalars(
            select(XhsAccount.cdp_port).where(XhsAccount.cdp_port.is_not(None))
        ).all()
    )
    for offset in range(_CDP_PORT_RANGE):
        candidate = _CDP_PORT_START + offset
        if candidate not in used:
            return candidate
    raise HTTPException(507, "CDP 端口池（9223-9322）已用尽，请先禁用部分账号")


class XhsAccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    remark: str = Field(default="", max_length=256)
    # 可选：不填则按 name 自动生成 xhs-<slug>（重名追加 -2/-3）
    session_name: str | None = Field(default=None, min_length=1, max_length=64)
    # 小红书用户 ID；可手动填，也可由 check-login 调 whoami 自动覆盖
    platform_user_id: str | None = Field(default=None, max_length=64)
    enabled: bool = True
    priority: int = 0


class XhsAccountUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    remark: str | None = Field(default=None, max_length=256)
    # 高级字段：允许用户事后绑定/修改小红书用户 ID
    platform_user_id: str | None = Field(default=None, max_length=64)
    enabled: bool | None = None
    priority: int | None = None


def _dump(account: XhsAccount) -> dict[str, Any]:
    return {
        "id": account.id,
        "name": account.name,
        "remark": account.remark,
        "session_name": account.session_name,
        "platform_user_id": account.platform_user_id,
        "login_status": account.login_status,
        "enabled": account.enabled,
        "priority": account.priority,
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


@router.get("")
def list_xhs_accounts(_: Admin, db: DB) -> dict:
    rows = db.scalars(
        select(XhsAccount).order_by(XhsAccount.priority, XhsAccount.id)
    ).all()
    # 与 /settings/{kind} 口径一致：data 直接返回数组，前端 rows.value = res.data.data
    return {"code": 200, "message": "success", "data": [_dump(r) for r in rows]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_xhs_account(payload: XhsAccountIn, _: Admin, db: DB) -> dict:
    # session_name 不填 → 自动按 name 生成 xhs-<slug>（重名追加 -2/-3）
    # 显式传入 → 校验唯一性
    if payload.session_name:
        existing = db.scalar(
            select(XhsAccount).where(XhsAccount.session_name == payload.session_name)
        )
        if existing is not None:
            raise HTTPException(409, f"session_name '{payload.session_name}' 已存在")
        session_name = payload.session_name
    else:
        session_name = _next_available_session_name(db, payload.name)
    account = XhsAccount(
        name=payload.name,
        remark=payload.remark,
        session_name=session_name,
        platform_user_id=payload.platform_user_id,
        enabled=payload.enabled,
        priority=payload.priority,
        cdp_port=_next_available_cdp_port(db),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return {"code": 201, "message": "success", "data": _dump(account)}


@router.put("/{account_id}")
def update_xhs_account(account_id: int, payload: XhsAccountUpdateIn, _: Admin, db: DB) -> dict:
    account = db.get(XhsAccount, account_id)
    if account is None:
        raise HTTPException(404, "账号不存在")
    if payload.name is not None:
        account.name = payload.name
    if payload.remark is not None:
        account.remark = payload.remark
    if payload.platform_user_id is not None:
        account.platform_user_id = payload.platform_user_id or None
    if payload.enabled is not None:
        account.enabled = payload.enabled
    if payload.priority is not None:
        account.priority = payload.priority
    db.commit()
    db.refresh(account)
    return {"code": 200, "message": "success", "data": _dump(account)}


@router.delete("/{account_id}")
def delete_xhs_account(account_id: int, _: Admin, db: DB) -> dict:
    account = db.get(XhsAccount, account_id)
    if account is not None:
        db.delete(account)
        db.commit()
    return {"code": 200, "message": "success", "data": {"id": account_id}}


# ── 批量删除 ──────────────────────────────────────────────────────────────


class BatchDeleteIdsIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)


class BatchDeleteOut(BaseModel):
    deleted_count: int


@router.post("/batch-delete", response_model=BatchDeleteOut)
def batch_delete_xhs_accounts(
    payload: BatchDeleteIdsIn,
    request: Request,
    actor: Admin,
    db: DB,
):
    """批量删除小红书账号配置。

    无关联表清理（XhsAccount 无外键关联）。部分 id 不存在 → 404 整体回滚。

    关联 spec: docs/superpowers/specs/2026-08-13-settings-batch-delete-design.md §2.1
    """
    rows = db.scalars(select(XhsAccount).where(XhsAccount.id.in_(payload.ids))).all()
    if len(rows) != len(set(payload.ids)):
        raise HTTPException(404, "部分账号不存在，已取消")
    deleted_ids = [r.id for r in rows]
    for r in rows:
        db.delete(r)
    db.commit()
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="xhs_accounts_batch_deleted",
        resource_type="xhs_account",
        target_label=f"batch of {len(deleted_ids)}",
        method="POST",
        path="/api/v1/xhs-accounts/batch-delete",
        status_code=200,
        client_ip=request.client.host if request.client else "127.0.0.1",
        extra={"deleted_ids": deleted_ids, "deleted_count": len(deleted_ids)},
    )
    return BatchDeleteOut(deleted_count=len(rows))


@router.post("/{account_id}/check-login")
def check_login(account_id: int, _: Admin, db: DB) -> dict:
    """检查指定账号的登录状态（调 opencli whoami）。

    成功：login_status='logged_in'，返回 logged_in=True + whoami 原始数据。
    未登录/风控：login_status='logged_out'，返回 logged_in=False + 错误信息。
    其他异常：503。

    成功时若 whoami 返回了 user_id 且数据库 platform_user_id 尚未登记，自动落库。
    """
    account = db.get(XhsAccount, account_id)
    if account is None:
        raise HTTPException(404, "账号不存在")
    settings = get_settings()
    # 用账号的 cdp_port 路由到对应的独立 Chrome 实例（ChromePool），
    # 这样每个账号检测的是自己的 cookie，而不是默认 Chrome Browser Bridge
    cdp_endpoint = (
        f"http://127.0.0.1:{account.cdp_port}"
        if account.cdp_port is not None
        else None
    )
    # 若账号配置了 cdp_port 但 Chrome 实例还没启动，先启动它，让用户能扫码登录
    # 使用全局 ChromePool 单例（API + crawl_task 共享），避免端口冲突和重复启动
    if account.cdp_port is not None:
        try:
            chrome_pool = get_global_chrome_pool()
            chrome_pool.acquire(account.session_name)
        except ChromeLaunchError as exc:
            raise HTTPException(503, f"Chrome 实例启动失败：{exc}") from exc
    try:
        raw = OpenCLIAdapter(
            settings,
            session=account.session_name,
            cdp_endpoint=cdp_endpoint,
        ).check_login(foreground=True)
        account.login_status = "logged_in"
        # whoami 返回结构依 opencli 版本而异；常见字段：user_id / userId / id
        whoami_user_id = (
            (raw or {}).get("user_id")
            or (raw or {}).get("userId")
            or (raw or {}).get("id")
        )
        if whoami_user_id and not account.platform_user_id:
            account.platform_user_id = str(whoami_user_id)
        db.commit()
        db.refresh(account)
        # 返回完整 account dump，前端可直接合并到 rows；同时带 login_status 便于 ElTag 刷新
        return {"code": 200, "message": "success", "data": {**_dump(account), "logged_in": True, "raw": raw}}
    except (AuthenticationRequired, VerificationRequired) as exc:
        account.login_status = "logged_out"
        db.commit()
        db.refresh(account)
        return {"code": 200, "message": "success", "data": {**_dump(account), "logged_in": False, "error": str(exc)}}
    except Exception as exc:
        raise HTTPException(503, f"登录检查失败：{exc}") from exc
    finally:
        # 注意：不调用 chrome_pool.release_all()——保持 Chrome 实例运行让用户扫码登录
        # ChromePool 会在任务结束（crawl_task）或后端停止时被 release
        pass


@router.post("/{account_id}/open-login")
def open_login(account_id: int, _: Admin, db: DB) -> dict:
    """打开小红书登录页（让用户扫码登录该账号）。

    强制路由到该账号的独立 Chrome 实例（ChromePool）——保证扫码后 cookie
    写入该账号对应的 user-data-dir，下次抓取自动使用。
    """
    account = db.get(XhsAccount, account_id)
    if account is None:
        raise HTTPException(404, "账号不存在")
    settings = get_settings()
    cdp_endpoint = (
        f"http://127.0.0.1:{account.cdp_port}"
        if account.cdp_port is not None
        else None
    )
    if account.cdp_port is not None:
        try:
            chrome_pool = get_global_chrome_pool()
            instance = chrome_pool.acquire(account.session_name)
        except ChromeLaunchError as exc:
            raise HTTPException(503, f"Chrome 实例启动失败：{exc}") from exc
        # 同步端口回 DB
        if instance.port != account.cdp_port:
            account.cdp_port = instance.port
            db.commit()
    # 打开小红书登录页（在 Chrome 实例中打开，foreground=True 拉前台）
    try:
        adapter = OpenCLIAdapter(
            settings,
            session=account.session_name,
            cdp_endpoint=cdp_endpoint,
        )
        ok = adapter.run(["browser", account.session_name, "open", settings.xhs_login_url, "--window", "foreground"])
        if not ok:
            raise HTTPException(503, "opencli 打开登录页失败")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"打开登录页失败：{exc}") from exc
    return {"code": 200, "message": "success", "data": {"url": settings.xhs_login_url, "session": account.session_name}}
