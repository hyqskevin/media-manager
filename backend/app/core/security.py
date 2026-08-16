import re
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash

from app.core.config import get_settings


password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hash.verify(password, encoded)


def validate_password_strength(password: str) -> bool:
    return bool(len(password) >= 8 and re.search(r"[A-Z]", password) and re.search(r"[a-z]", password) and re.search(r"\d", password) and re.search(r"[^A-Za-z0-9]", password))


def create_access_token(data: dict[str, object], expires_delta: timedelta | None = None) -> str:
    settings = get_settings()
    payload = dict(data)
    payload["exp"] = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=settings.jwt_expire_hours))
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def get_current_user(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> dict[str, object]:
    if credentials is None:
        raise HTTPException(status_code=401, detail="未提供认证凭据")
    try:
        payload = jwt.decode(credentials.credentials, get_settings().secret_key, algorithms=["HS256"])
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail="认证凭据无效或已过期") from exc
    return {
        "username": str(payload["sub"]),
        "role": str(payload.get("role", "editor")),
        "permissions": [str(p) for p in payload.get("permissions", [])],
    }


def require_permission(code: str):
    """返回 FastAPI Depends，校验当前用户具备指定权限码（* 通配）。"""
    def _checker(
        user: Annotated[dict[str, object], Depends(get_current_user)],
    ) -> dict[str, object]:
        perms = set(user.get("permissions", []))
        if "*" in perms or code in perms:
            return user
        raise HTTPException(status_code=403, detail=f"需要权限 {code}")
    return _checker


def require_admin(user: Annotated[dict[str, object], Depends(get_current_user)]) -> dict[str, object]:
    """兼容旧 API：permissions 含 * 即放行（role 字段不再授权，仅展示用）。

    关联 spec: docs/superpowers/specs/2026-08-13-permission-only-from-groups-design.md
    """
    if "*" in set(user.get("permissions", [])):
        return user
    raise HTTPException(status_code=403, detail="权限不足")
