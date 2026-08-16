"""博主组 CRUD + 批量删除。

端点（URL 不变）：
- GET    /settings/blogger-groups
- GET    /settings/blogger-groups/{group_id}
- POST   /settings/blogger-groups
- PUT    /settings/blogger-groups/{group_id}/members
- DELETE /settings/blogger-groups/{group_id}
- POST   /settings/blogger-groups/batch-delete
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.models.blogger_group import BloggerGroup, BloggerGroupMember
from app.models.config import Blogger
from app.services.audit import record_audit
from app.api.v1.settings._deps import (
    Admin,
    BatchDeleteIdsIn,
    BatchDeleteOut,
    DB,
)
from app.core.security import get_current_user

LoggedInUser = Annotated[dict, Depends(get_current_user)]

router = APIRouter(tags=["settings"])


class BloggerGroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    blogger_ids: list[int] = Field(default_factory=list)
    enabled: bool = True


class BloggerGroupMembersIn(BaseModel):
    blogger_ids: list[int] = Field(default_factory=list)


def _dump_blogger_group(db, group: BloggerGroup) -> dict:
    blogger_ids = sorted(
        row.blogger_id for row in db.scalars(
            select(BloggerGroupMember).where(BloggerGroupMember.group_id == group.id)
        ).all()
    )
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "enabled": group.enabled,
        "blogger_ids": blogger_ids,
        "created_at": group.created_at,
    }


def _validate_blogger_ids(db, blogger_ids: list[int]) -> None:
    for blogger_id in dict.fromkeys(blogger_ids):
        if db.get(Blogger, blogger_id) is None:
            raise HTTPException(422, f"博主 id={blogger_id} 不存在")


@router.get("/settings/blogger-groups")
def list_blogger_groups(_user: LoggedInUser = None, db: DB = None) -> dict:
    groups = db.scalars(select(BloggerGroup).order_by(BloggerGroup.id)).all()
    return {
        "code": 200,
        "message": "success",
        "data": {"items": [_dump_blogger_group(db, g) for g in groups]},
    }


@router.get("/settings/blogger-groups/{group_id}")
def get_blogger_group(group_id: int, _: Admin, db: DB) -> dict:
    group = db.get(BloggerGroup, group_id)
    if group is None:
        raise HTTPException(404, "博主组不存在")
    return {"code": 200, "message": "success", "data": _dump_blogger_group(db, group)}


@router.post("/settings/blogger-groups")
def create_blogger_group(payload: BloggerGroupIn, _: Admin, db: DB) -> dict:
    existing = db.scalar(select(BloggerGroup).where(BloggerGroup.name == payload.name))
    if existing is not None:
        raise HTTPException(409, f"博主组名称 '{payload.name}' 已存在")
    _validate_blogger_ids(db, payload.blogger_ids)
    group = BloggerGroup(name=payload.name, description=payload.description, enabled=payload.enabled)
    db.add(group)
    db.flush()
    for blogger_id in dict.fromkeys(payload.blogger_ids):
        db.add(BloggerGroupMember(group_id=group.id, blogger_id=blogger_id))
    db.commit()
    db.refresh(group)
    return {"code": 200, "message": "success", "data": _dump_blogger_group(db, group)}


@router.put("/settings/blogger-groups/{group_id}/members")
def replace_blogger_group_members(group_id: int, payload: BloggerGroupMembersIn, _: Admin, db: DB) -> dict:
    group = db.get(BloggerGroup, group_id)
    if group is None:
        raise HTTPException(404, "博主组不存在")
    _validate_blogger_ids(db, payload.blogger_ids)
    db.execute(delete(BloggerGroupMember).where(BloggerGroupMember.group_id == group_id))
    for blogger_id in dict.fromkeys(payload.blogger_ids):
        db.add(BloggerGroupMember(group_id=group_id, blogger_id=blogger_id))
    db.commit()
    db.refresh(group)
    return {"code": 200, "message": "success", "data": _dump_blogger_group(db, group)}


@router.delete("/settings/blogger-groups/{group_id}")
def delete_blogger_group(group_id: int, _: Admin, db: DB) -> dict:
    group = db.get(BloggerGroup, group_id)
    if group is None:
        raise HTTPException(404, "博主组不存在")
    db.execute(delete(BloggerGroupMember).where(BloggerGroupMember.group_id == group_id))
    db.delete(group)
    db.commit()
    return {"code": 200, "message": "success", "data": {"deleted_id": group_id}}


@router.post("/settings/blogger-groups/batch-delete", response_model=BatchDeleteOut)
def batch_delete_blogger_groups(
    payload: BatchDeleteIdsIn,
    request: Request,
    actor: Admin,
    db: DB,
):
    """批量删除博主组。

    关联清理：先 delete BloggerGroupMember where group_id IN (...)，
    再 delete BloggerGroup where id IN (...)。

    部分 id 不存在 → 404 整体回滚（一致性优先）。

    关联 spec: docs/superpowers/specs/2026-08-13-settings-batch-delete-design.md §2.1
    """
    rows = db.scalars(select(BloggerGroup).where(BloggerGroup.id.in_(payload.ids))).all()
    if len(rows) != len(set(payload.ids)):
        raise HTTPException(404, "部分博主组不存在，已取消")
    deleted_ids = [r.id for r in rows]
    db.execute(delete(BloggerGroupMember).where(BloggerGroupMember.group_id.in_(deleted_ids)))
    for r in rows:
        db.delete(r)
    db.commit()
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="blogger_groups_batch_deleted",
        resource_type="blogger_group",
        target_label=f"batch of {len(deleted_ids)}",
        method="POST",
        path="/api/v1/settings/blogger-groups/batch-delete",
        status_code=200,
        client_ip=request.client.host if request.client else "127.0.0.1",
        extra={"deleted_ids": deleted_ids, "deleted_count": len(deleted_ids)},
    )
    return BatchDeleteOut(deleted_count=len(rows))
