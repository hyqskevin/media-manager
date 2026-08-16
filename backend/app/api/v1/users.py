"""操作账号管理 API。

关联 spec: docs/superpowers/specs/2026-08-12-system-admin-design.md
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password, require_permission,
)
from app.models.group import Group, UserGroup
from app.models.user import User
from app.services.audit import record_audit


router = APIRouter(prefix="/users", tags=["users"])

DB = Annotated[Session, Depends(get_db)]


# ---- Schemas ----

class UserOut(BaseModel):
    id: int
    username: str
    display_name: str | None
    enabled: bool
    role: str
    groups: list[str]


class UserCreateIn(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=8)
    display_name: str | None = None
    is_admin: bool = True
    group_ids: list[int] = []


class UserUpdateIn(BaseModel):
    display_name: str | None = None
    enabled: bool | None = None
    password: str | None = None


class GroupIdsIn(BaseModel):
    group_ids: list[int]


# ---- Helpers ----

def _user_to_out(db: Session, user: User) -> UserOut:
    rows = (
        db.query(Group.name)
        .join(UserGroup, UserGroup.group_id == Group.id)
        .filter(UserGroup.user_id == user.id)
        .all()
    )
    return UserOut(
        id=user.id, username=user.username,
        display_name=user.display_name, enabled=user.enabled,
        role=user.role, groups=[g for (g,) in rows],
    )


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "127.0.0.1"


# ---- Endpoints ----

@router.get("", response_model=list[UserOut])
def list_users(
    _: Annotated[dict, Depends(require_permission("users:read"))],
    db: DB,
):
    users = db.query(User).order_by(User.id).all()
    return [_user_to_out(db, u) for u in users]


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreateIn,
    request: Request,
    actor: Annotated[dict, Depends(require_permission("users:manage"))],
    db: DB,
):
    if db.query(User).filter_by(username=payload.username).first():
        raise HTTPException(409, "用户名已存在")
    # 按 group_ids（含 Administrators）+ is_admin 决定 role
    admin_gid = db.query(Group).filter_by(name="Administrators").one().id
    is_admin_member = payload.is_admin or admin_gid in payload.group_ids
    role = "admin" if is_admin_member else "editor"
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name or payload.username,
        enabled=True,
        role=role,
    )
    db.add(user)
    db.flush()
    # 关联分组：is_admin 自动入 Administrators；否则按 payload.group_ids；
    # 若 group_ids 包含 Administrators（且 is_admin=False）也带过去
    if is_admin_member:
        final_group_ids = sorted(set(payload.group_ids + [admin_gid]))
    else:
        final_group_ids = list(payload.group_ids)
    for gid in final_group_ids:
        db.add(UserGroup(user_id=user.id, group_id=gid))
    db.commit()
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="user_created",
        resource_type="user", resource_id=user.id,
        target_label=user.username,
        method="POST", path="/api/v1/users", status_code=201,
        client_ip=_client_ip(request),
        extra={"is_admin": payload.is_admin, "group_ids": payload.group_ids, "role": role},
    )
    return _user_to_out(db, user)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    _: Annotated[dict, Depends(require_permission("users:read"))],
    db: DB,
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    return _user_to_out(db, user)


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdateIn,
    request: Request,
    actor: Annotated[dict, Depends(require_permission("users:manage"))],
    db: DB,
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.enabled is not None:
        user.enabled = payload.enabled
    if payload.password:
        user.password_hash = hash_password(payload.password)
    db.commit()
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="user_updated",
        resource_type="user", resource_id=user_id,
        target_label=user.username,
        method="PUT", path=f"/api/v1/users/{user_id}", status_code=200,
        client_ip=_client_ip(request),
        extra={"fields": list(payload.model_dump(exclude_none=True).keys())},
    )
    return _user_to_out(db, user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    request: Request,
    actor: Annotated[dict, Depends(require_permission("users:manage"))],
    db: DB,
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    if user.username == "admin":
        raise HTTPException(403, "内置 admin 用户不可删除")
    if user.username == actor["username"]:
        raise HTTPException(403, "不能删除当前登录账号")
    username = user.username
    db.delete(user)
    db.commit()
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="user_deleted",
        resource_type="user", resource_id=user_id, target_label=username,
        method="DELETE", path=f"/api/v1/users/{user_id}", status_code=204,
        client_ip=_client_ip(request),
    )


@router.put("/{user_id}/groups", response_model=UserOut)
def update_user_groups(
    user_id: int,
    payload: GroupIdsIn,
    request: Request,
    actor: Annotated[dict, Depends(require_permission("users:manage"))],
    db: DB,
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    admin_gid = db.query(Group).filter_by(name="Administrators").one().id
    # builtin admin 保护：永远保留在 Administrators 组
    if user.username == "admin" and admin_gid not in payload.group_ids:
        raise HTTPException(400, "内置 admin 用户必须保留在 Administrators 组")
    old_names = [
        n for (n,) in db.query(Group.name)
        .join(UserGroup, UserGroup.group_id == Group.id)
        .filter(UserGroup.user_id == user_id).all()
    ]
    db.query(UserGroup).filter_by(user_id=user_id).delete()
    for gid in payload.group_ids:
        g = db.get(Group, gid)
        if g is None:
            raise HTTPException(422, f"分组 {gid} 不存在")
        db.add(UserGroup(user_id=user_id, group_id=gid))
    # 同步 role：进 Administrators → admin；离开 Administrators → editor
    new_role = "admin" if admin_gid in payload.group_ids else "editor"
    if user.role != new_role:
        user.role = new_role
    db.commit()
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="user_group_changed",
        resource_type="user", resource_id=user_id,
        target_label=user.username,
        method="PUT", path=f"/api/v1/users/{user_id}/groups", status_code=200,
        client_ip=_client_ip(request),
        extra={"before_groups": old_names, "after_group_ids": payload.group_ids, "new_role": new_role},
    )
    return _user_to_out(db, user)