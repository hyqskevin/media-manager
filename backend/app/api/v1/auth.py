from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.user import User
from app.services.audit import record_audit


router = APIRouter(prefix="/auth", tags=["auth"])


# 登录失败限流(仅适用单机部署;阶段二换 Redis)
# 关联 spec: docs/superpowers/specs/2026-08-15-login-rate-limit-design.md
_failed_attempts: dict[tuple[str, str], list[float]] = {}
"""(client_ip, username) → 最近 60 秒内的失败时间戳列表"""

_lock_until: dict[tuple[str, str], float] = {}
"""(client_ip, username) → 解锁时刻 (epoch seconds)"""

_RATE_WINDOW_SECONDS = 60
_RATE_MAX_FAILURES = 5
_RATE_LOCK_DURATION = 300  # 5 分钟


class LoginRequest(BaseModel):
    username: str
    password: str


def _client_meta(request: Request) -> tuple[str, str | None]:
    """提取登录端点用的 client_ip / user_agent。"""
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent")
    return client_ip, user_agent


def compute_user_permissions(session: Session, user_id: int) -> list[str]:
    """返回用户所有所属分组的权限码并集。

    不再读 role 字段——* 必须由 group 自己 grant(Administrators 组绑定了 10 条具体权限码,
    在 require_permission 端点上与 * 等价)。role 字段仅作为展示/日志用,不再参与授权。

    关联 spec: docs/superpowers/specs/2026-08-13-permission-only-from-groups-design.md
    """
    from app.models.group import GroupPermission, Permission, UserGroup

    codes: set[str] = set()
    rows = (
        session.query(Permission.code)
        .join(GroupPermission, GroupPermission.permission_id == Permission.id)
        .join(UserGroup, UserGroup.group_id == GroupPermission.group_id)
        .filter(UserGroup.user_id == user_id)
        .all()
    )
    codes.update(c for (c,) in rows)
    return sorted(codes)


def _record_login_failure(key: tuple[str, str], now: float) -> int:
    """记录一次失败,返回当前窗口内累计失败次数;达到阈值时设置锁定。"""
    attempts = _failed_attempts.setdefault(key, [])
    attempts.append(now)
    # 仅保留窗口内的时间戳
    cutoff = now - _RATE_WINDOW_SECONDS
    attempts[:] = [t for t in attempts if t > cutoff]
    if len(attempts) >= _RATE_MAX_FAILURES:
        _lock_until[key] = now + _RATE_LOCK_DURATION
        return len(attempts)
    return len(attempts)


@router.post("/login")
def login(
    payload: LoginRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    import time

    client_ip, user_agent = _client_meta(request)
    rate_key = (client_ip, payload.username)
    now = time.time()

    # 1. 先检查是否处于锁定状态
    locked_until = _lock_until.get(rate_key, 0.0)
    if locked_until > now:
        remaining = int(locked_until - now) + 1
        # 直接返回 JSONResponse 以保留 Retry-After 头(全局 HTTPException
        # handler 不会透传 headers)
        return JSONResponse(
            status_code=429,
            content={"code": 429, "message": f"登录尝试过多,请 {remaining} 秒后重试", "data": {}},
            headers={"Retry-After": str(remaining)},
        )

    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None:
        record_audit(
            actor_user_id=None,
            actor_username=payload.username,
            action="login_failed",
            method="POST", path="/api/v1/auth/login", status_code=401,
            client_ip=client_ip, user_agent=user_agent,
            extra={"reason": "user_not_found"},
        )
        # 记录失败次数;达到阈值立即锁定
        _record_login_failure(rate_key, now)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not verify_password(payload.password, user.password_hash):
        record_audit(
            actor_user_id=None,
            actor_username=payload.username,
            action="login_failed",
            method="POST", path="/api/v1/auth/login", status_code=401,
            client_ip=client_ip, user_agent=user_agent,
            extra={"reason": "wrong_password"},
        )
        _record_login_failure(rate_key, now)
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.enabled:
        # 账号停用属于业务状态,不计入失败次数(避免被故意锁死合法账号)
        record_audit(
            actor_user_id=user.id,
            actor_username=user.username,
            action="login_failed",
            resource_type="user", resource_id=user.id, target_label=user.username,
            method="POST", path="/api/v1/auth/login", status_code=403,
            client_ip=client_ip, user_agent=user_agent,
            extra={"reason": "disabled"},
        )
        raise HTTPException(status_code=403, detail="账号已停用")
    settings = get_settings()
    permissions = compute_user_permissions(db, user.id)
    token = create_access_token({"sub": user.username, "role": user.role, "permissions": permissions})
    record_audit(
        actor_user_id=user.id,
        actor_username=user.username,
        action="login_success",
        resource_type="user", resource_id=user.id, target_label=user.username,
        method="POST", path="/api/v1/auth/login", status_code=200,
        client_ip=client_ip, user_agent=user_agent,
    )
    # 登录成功 → 清零该 (ip, username) 的失败计数与锁定
    _failed_attempts.pop(rate_key, None)
    _lock_until.pop(rate_key, None)
    return {"code": 200, "message": "success", "data": {"access_token": token, "token_type": "bearer", "expires_in": settings.jwt_expire_hours * 3600}}