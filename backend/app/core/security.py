"""JWT 认证 + 密码哈希 + 依赖注入。"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.user import User

settings = get_settings()
pwd_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_password(plain: str) -> str:
    return pwd_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_hash.verify(plain, hashed)


def create_access_token(subject: str, claims: dict | None = None) -> str:
    """签发 JWT。"""
    payload = {
        "sub": subject,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.jwt_expires_hours),
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    """FastAPI 依赖：从 JWT 解析当前用户。"""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_token")
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"invalid_token: {e}")

    db = SessionLocal()
    try:
        user = db.get(User, int(payload["sub"]))
    finally:
        db.close()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found")
    return user


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """FastAPI 依赖：要求 admin 权限（v0.2 简化：仅检查 user.is_admin）。"""
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    return current_user