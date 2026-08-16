"""账号分组 API。

关联 spec: docs/superpowers/specs/2026-08-12-system-admin-design.md §3.1
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.group import Group, GroupPermission, Permission, UserGroup
from app.services.audit import record_audit


router = APIRouter(prefix="/groups", tags=["groups"])


DB = Annotated[Session, Depends(get_db)]


# ---- Schemas ----

class GroupOut(BaseModel):
    id: int
    name: str
    description: str | None
    is_builtin: bool
    permission_codes: list[str]


class GroupCreateIn(BaseModel):
    name: str
    description: str | None = None


class GroupUpdateIn(BaseModel):
    description: str | None = None


class PermissionCodesIn(BaseModel):
    permission_codes: list[str]


# ---- Helpers ----

def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "127.0.0.1"


def _group_to_out(db: Session, g: Group) -> GroupOut:
    rows = (
        db.query(Permission.code)
        .join(GroupPermission, GroupPermission.permission_id == Permission.id)
        .filter(GroupPermission.group_id == g.id)
        .all()
    )
    return GroupOut(
        id=g.id,
        name=g.name,
        description=g.description,
        is_builtin=g.is_builtin,
        permission_codes=[c for (c,) in rows],
    )


# ---- Endpoints ----

@router.get("", response_model=list[GroupOut])
def list_groups(
    _: Annotated[dict, Depends(require_permission("users:read"))],
    db: DB,
):
    groups = db.query(Group).order_by(Group.id).all()
    return [_group_to_out(db, g) for g in groups]


@router.post("", response_model=GroupOut, status_code=201)
def create_group(
    payload: GroupCreateIn,
    request: Request,
    actor: Annotated[dict, Depends(require_permission("users:manage"))],
    db: DB,
):
    if db.query(Group).filter_by(name=payload.name).first():
        raise HTTPException(409, "分组名已存在")
    g = Group(
        name=payload.name, description=payload.description, is_builtin=False,
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="group_created",
        resource_type="group", resource_id=g.id, target_label=g.name,
        method="POST", path="/api/v1/groups", status_code=201,
        client_ip=_client_ip(request),
    )
    return _group_to_out(db, g)


@router.put("/{group_id}", response_model=GroupOut)
def update_group(
    group_id: int,
    payload: GroupUpdateIn,
    db: DB,
    _: Annotated[dict, Depends(require_permission("users:manage"))],
):
    g = db.get(Group, group_id)
    if g is None:
        raise HTTPException(404, "分组不存在")
    if payload.description is not None:
        g.description = payload.description
    db.commit()
    db.refresh(g)
    return _group_to_out(db, g)


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    request: Request,
    actor: Annotated[dict, Depends(require_permission("users:manage"))],
    db: DB,
):
    g = db.get(Group, group_id)
    if g is None:
        raise HTTPException(404, "分组不存在")
    if g.is_builtin:
        raise HTTPException(403, "内置分组不可删除")
    in_use = db.query(UserGroup).filter_by(group_id=group_id).first()
    if in_use:
        raise HTTPException(409, "请先迁移用户后再删除")
    name = g.name
    db.delete(g)
    db.commit()
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="group_deleted",
        resource_type="group", resource_id=group_id, target_label=name,
        method="DELETE", path=f"/api/v1/groups/{group_id}", status_code=204,
        client_ip=_client_ip(request),
    )


@router.put("/{group_id}/permissions", response_model=GroupOut)
def update_group_permissions(
    group_id: int,
    payload: PermissionCodesIn,
    request: Request,
    actor: Annotated[dict, Depends(require_permission("users:manage"))],
    db: DB,
):
    g = db.get(Group, group_id)
    if g is None:
        raise HTTPException(404, "分组不存在")
    old_codes = sorted([
        c for (c,) in db.query(Permission.code)
        .join(GroupPermission, GroupPermission.permission_id == Permission.id)
        .filter(GroupPermission.group_id == group_id).all()
    ])
    # 校验权限码存在
    if payload.permission_codes:
        rows = (
            db.query(Permission)
            .filter(Permission.code.in_(payload.permission_codes))
            .all()
        )
        if len(rows) != len(set(payload.permission_codes)):
            existing = {p.code for p in rows}
            missing = set(payload.permission_codes) - existing
            raise HTTPException(422, f"权限码不存在: {sorted(missing)}")
    else:
        rows = []
    # 全量替换
    db.query(GroupPermission).filter_by(group_id=group_id).delete()
    for p in rows:
        db.add(GroupPermission(group_id=group_id, permission_id=p.id))
    db.commit()
    db.refresh(g)
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="group_permission_changed",
        resource_type="group", resource_id=group_id, target_label=g.name,
        method="PUT", path=f"/api/v1/groups/{group_id}/permissions",
        status_code=200,
        client_ip=_client_ip(request),
        extra={"before": old_codes, "after": sorted(payload.permission_codes)},
    )
    return _group_to_out(db, g)