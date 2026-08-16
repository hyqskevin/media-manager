"""v0.3 action-set endpoints (CRUD + clone)."""
from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.nurture_action_set import NurtureActionSet
from app.schemas.full_features import ActionSetCreate, ActionSetOut, ActionSetUpdate
from app.services.full_features import write_audit_log

router = APIRouter(prefix="/nurture/action-sets", tags=["action-sets"])

Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[dict, Depends(require_admin)]


def _operator(admin) -> str:
    return getattr(admin, "username", "admin")


def _out(a: NurtureActionSet) -> ActionSetOut:
    try:
        actions = json.loads(a.actions_json or "[]")
    except json.JSONDecodeError:
        actions = []
    try:
        order = json.loads(a.actions_order_json or "[]")
    except json.JSONDecodeError:
        order = []
    return ActionSetOut(
        id=a.id, platform=a.platform, name=a.name, duration_minutes=a.duration_minutes,
        actions=actions, actions_order=order, created_at=a.created_at, updated_at=a.updated_at,
    )


def _get_or_404(db: Session, aid: int) -> NurtureActionSet:
    a = db.get(NurtureActionSet, aid)
    if not a:
        raise HTTPException(status_code=404, detail="action_set_not_found")
    return a


@router.get("", response_model=list[ActionSetOut])
async def list_action_sets(
    db: Db, _: Admin, platform: str | None = Query(default=None)
) -> list[ActionSetOut]:
    query = select(NurtureActionSet)
    if platform:
        query = query.where(NurtureActionSet.platform == platform)
    query = query.order_by(NurtureActionSet.id.desc())
    return [_out(a) for a in db.scalars(query)]


@router.post("", response_model=ActionSetOut, status_code=status.HTTP_201_CREATED)
async def create_action_set(payload: ActionSetCreate, db: Db, admin: Admin, request: Request) -> ActionSetOut:
    dup = db.scalars(
        select(func.count()).select_from(NurtureActionSet).where(
            (NurtureActionSet.platform == payload.platform) & (NurtureActionSet.name == payload.name)
        )
    ).one()
    if dup:
        raise HTTPException(status_code=409, detail="action_set_name_exists")
    a = NurtureActionSet(
        platform=payload.platform,
        name=payload.name,
        duration_minutes=payload.duration_minutes,
        actions_json=json.dumps(payload.actions),
        actions_order_json=json.dumps(payload.actions_order or list(range(len(payload.actions)))),
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    write_audit_log(
        db, operator=_operator(admin), action="create_action_set", entity_type="action_set",
        entity_id=a.id, changes={"after": {"name": a.name, "actions": payload.actions}},
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    return _out(a)


@router.get("/{action_set_id}", response_model=ActionSetOut)
async def get_action_set(action_set_id: int, db: Db, _: Admin) -> ActionSetOut:
    return _out(_get_or_404(db, action_set_id))


@router.patch("/{action_set_id}", response_model=ActionSetOut)
async def update_action_set(
    action_set_id: int, payload: ActionSetUpdate, db: Db, admin: Admin, request: Request
) -> ActionSetOut:
    a = _get_or_404(db, action_set_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        a.name = data["name"]
    if "duration_minutes" in data:
        a.duration_minutes = data["duration_minutes"]
    if "actions" in data:
        a.actions_json = json.dumps(data["actions"])
        a.actions_order_json = json.dumps(list(range(len(data["actions"]))))
    if "actions_order" in data and data["actions_order"]:
        a.actions_order_json = json.dumps(data["actions_order"])
    db.commit()
    db.refresh(a)
    write_audit_log(
        db, operator=_operator(admin), action="update_action_set", entity_type="action_set",
        entity_id=a.id, changes={"after": {"name": a.name}},
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    return _out(a)


@router.delete("/{action_set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action_set(action_set_id: int, db: Db, admin: Admin, request: Request) -> None:
    a = _get_or_404(db, action_set_id)
    db.delete(a)
    db.commit()
    write_audit_log(
        db, operator=_operator(admin), action="delete_action_set", entity_type="action_set",
        entity_id=action_set_id, ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )


@router.post("/{action_set_id}/clone", response_model=ActionSetOut, status_code=status.HTTP_201_CREATED)
async def clone_action_set(action_set_id: int, db: Db, _: Admin) -> ActionSetOut:
    a = _get_or_404(db, action_set_id)
    new = NurtureActionSet(
        platform=a.platform,
        name=f"{a.name} (副本)",
        duration_minutes=a.duration_minutes,
        actions_json=a.actions_json,
        actions_order_json=a.actions_order_json,
    )
    db.add(new)
    db.commit()
    db.refresh(new)
    return _out(new)