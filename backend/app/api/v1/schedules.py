"""v0.3 nurture-schedule endpoints (CRUD + enable/disable + manual trigger)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.nurture_schedule import NurtureSchedule
from app.models.nurture_task import NurtureTask
from app.schemas.full_features import (
    ScheduleCreate,
    ScheduleOut,
    SchedulePage,
    ScheduleUpdate,
    TaskCreatedOut,
)
from app.services.full_features import write_audit_log
from app.tasks.nurture_task import nurture_account_task

router = APIRouter(prefix="/nurture/schedules", tags=["schedules"])

Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[dict, Depends(require_admin)]


def _operator(admin) -> str:
    return getattr(admin, "username", "admin")


def _out(s: NurtureSchedule) -> ScheduleOut:
    try:
        actions = json.loads(s.actions_json or "[]")
    except json.JSONDecodeError:
        actions = []
    return ScheduleOut(
        id=s.id, platform=s.platform, account_id=s.account_id, name=s.name, cron=s.cron,
        duration_minutes=s.duration_minutes, actions=actions, action_set_id=s.action_set_id,
        enabled=s.enabled, next_run_at=s.next_run_at, created_at=s.created_at,
        updated_at=s.updated_at,
    )


def _get_or_404(db: Session, sid: int) -> NurtureSchedule:
    s = db.get(NurtureSchedule, sid)
    if not s:
        raise HTTPException(status_code=404, detail="schedule_not_found")
    return s


@router.get("", response_model=SchedulePage)
async def list_schedules(
    db: Db, _: Admin, platform: str | None = None, page: int = 1, page_size: int = 20
) -> SchedulePage:
    query = select(NurtureSchedule)
    if platform:
        query = query.where(NurtureSchedule.platform == platform)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    query = query.order_by(NurtureSchedule.id.desc())
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size))
    return SchedulePage(
        total=total, page=page, page_size=page_size, items=[_out(s) for s in items]
    )


@router.post("", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: ScheduleCreate, db: Db, admin: Admin, request: Request
) -> ScheduleOut:
    s = NurtureSchedule(
        platform=payload.platform,
        account_id=payload.account_id,
        name=payload.name,
        cron=payload.cron,
        duration_minutes=payload.duration_minutes,
        actions_json=json.dumps(payload.actions),
        action_set_id=payload.action_set_id,
        enabled=payload.enabled,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    write_audit_log(
        db, operator=_operator(admin), action="create_schedule", entity_type="schedule",
        entity_id=s.id, changes={"after": {"name": s.name, "cron": s.cron}},
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    return _out(s)


@router.get("/{schedule_id}", response_model=ScheduleOut)
async def get_schedule(schedule_id: int, db: Db, _: Admin) -> ScheduleOut:
    return _out(_get_or_404(db, schedule_id))


@router.patch("/{schedule_id}", response_model=ScheduleOut)
async def update_schedule(
    schedule_id: int, payload: ScheduleUpdate, db: Db, admin: Admin, request: Request
) -> ScheduleOut:
    s = _get_or_404(db, schedule_id)
    data = payload.model_dump(exclude_unset=True)
    for field in ("name", "cron", "duration_minutes", "action_set_id", "enabled"):
        if field in data:
            setattr(s, field, data[field])
    if "actions" in data:
        s.actions_json = json.dumps(data["actions"])
    db.commit()
    db.refresh(s)
    write_audit_log(
        db, operator=_operator(admin), action="update_schedule", entity_type="schedule",
        entity_id=s.id, changes={"after": {"name": s.name, "cron": s.cron}},
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    return _out(s)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: int, db: Db, admin: Admin, request: Request) -> None:
    s = _get_or_404(db, schedule_id)
    db.delete(s)
    db.commit()
    write_audit_log(
        db, operator=_operator(admin), action="delete_schedule", entity_type="schedule",
        entity_id=schedule_id, ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )


@router.post("/{schedule_id}/disable", response_model=ScheduleOut)
async def disable_schedule(schedule_id: int, db: Db, _: Admin) -> ScheduleOut:
    s = _get_or_404(db, schedule_id)
    s.enabled = False
    db.commit()
    db.refresh(s)
    return _out(s)


@router.post("/{schedule_id}/enable", response_model=ScheduleOut)
async def enable_schedule(schedule_id: int, db: Db, _: Admin) -> ScheduleOut:
    s = _get_or_404(db, schedule_id)
    s.enabled = True
    db.commit()
    db.refresh(s)
    return _out(s)


@router.post("/{schedule_id}/trigger", response_model=TaskCreatedOut, status_code=status.HTTP_202_ACCEPTED)
async def trigger_schedule(schedule_id: int, db: Db, _: Admin) -> TaskCreatedOut:
    """Manually run a schedule now: create a NurtureTask record + dispatch celery."""
    s = _get_or_404(db, schedule_id)
    try:
        actions = json.loads(s.actions_json or "[]")
    except json.JSONDecodeError:
        actions = []
    async_result = nurture_account_task.delay(
        account_id=s.account_id,
        actions=actions,
        duration_minutes=s.duration_minutes,
    )
    task = NurtureTask(
        celery_task_id=async_result.id,
        account_id=s.account_id,
        platform=s.platform,
        actions_json=json.dumps(actions),
        duration_minutes=s.duration_minutes,
        status="pending",
        action_set_id=s.action_set_id,
        triggered_by_schedule_id=s.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(task)
    db.commit()
    return TaskCreatedOut(task_id=async_result.id)