"""v0.3 nurture endpoints: running / history / task detail / cancel / rerun /
delete / logs / export."""
from __future__ import annotations

import csv
import io
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.nurture_task import NurtureActionLog, NurtureTask
from app.schemas.full_features import (
    NurtureActionLogOut,
    NurtureTaskOut,
    NurtureTaskPage,
    TaskCreatedOut,
)
from app.services.full_features import write_audit_log
from app.tasks.nurture_task import nurture_account_task

router = APIRouter(prefix="/nurture", tags=["nurture"])

Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[dict, Depends(require_admin)]


def _operator(admin) -> str:
    return getattr(admin, "username", "admin")


def _find_task(db: Session, task_id: str) -> NurtureTask:
    task = db.scalars(
        select(NurtureTask).where(
            (NurtureTask.id == task_id) | (NurtureTask.celery_task_id == task_id)
        )
    ).first()
    if not task:
        raise HTTPException(status_code=404, detail="task_not_found")
    return task


def _task_out(t: NurtureTask) -> NurtureTaskOut:
    try:
        actions = json.loads(t.actions_json or "[]")
    except json.JSONDecodeError:
        actions = []
    return NurtureTaskOut(
        id=t.id,
        celery_task_id=t.celery_task_id,
        account_id=t.account_id,
        platform=t.platform,
        actions=actions,
        duration_minutes=t.duration_minutes,
        status=t.status,
        current_action=t.current_action,
        progress_pct=t.progress_pct,
        started_at=t.started_at,
        finished_at=t.finished_at,
        error=t.error,
        items_collected=t.items_collected,
        created_at=t.created_at,
    )


@router.get("/running", response_model=list[NurtureTaskOut])
async def nurture_running(db: Db, _: Admin) -> list[NurtureTaskOut]:
    """Running + queued tasks."""
    tasks = db.scalars(
        select(NurtureTask)
        .where(NurtureTask.status.in_(["pending", "running"]))
        .order_by(NurtureTask.started_at.desc(), NurtureTask.id.desc())
    )
    return [_task_out(t) for t in tasks]


@router.get("/history", response_model=NurtureTaskPage)
async def nurture_history(
    db: Db,
    _: Admin,
    status_: str | None = Query(default=None, alias="status"),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
    account_id: int | None = Query(default=None),
    platform: str | None = Query(default=None),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> NurtureTaskPage:
    query = select(NurtureTask)
    if status_:
        query = query.where(NurtureTask.status == status_)
    if from_:
        query = query.where(NurtureTask.started_at >= from_)
    if to:
        query = query.where(NurtureTask.started_at <= to)
    if account_id:
        query = query.where(NurtureTask.account_id == account_id)
    if platform:
        query = query.where(NurtureTask.platform == platform)
    if q:
        query = query.where(
            NurtureTask.celery_task_id.contains(q) | NurtureTask.actions_json.contains(q)
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    query = query.order_by(NurtureTask.started_at.desc(), NurtureTask.id.desc())
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size))
    return NurtureTaskPage(
        total=total, page=page, page_size=page_size, items=[_task_out(t) for t in items]
    )


@router.get("/tasks/{task_id}", response_model=NurtureTaskOut)
async def nurture_task_detail(task_id: str, db: Db, _: Admin) -> NurtureTaskOut:
    return _task_out(_find_task(db, task_id))


@router.get("/tasks/{task_id}/logs", response_model=list[NurtureActionLogOut])
async def nurture_task_logs(task_id: str, db: Db, _: Admin) -> list[NurtureActionLogOut]:
    task = _find_task(db, task_id)
    logs = db.scalars(
        select(NurtureActionLog)
        .where(NurtureActionLog.task_id == task.id)
        .order_by(NurtureActionLog.sequence)
    )
    out = []
    for log in logs:
        try:
            result = json.loads(log.result_json or "{}")
        except json.JSONDecodeError:
            result = {}
        out.append(NurtureActionLogOut(
            id=log.id, task_id=log.task_id, action=log.action, status=log.status,
            sequence=log.sequence, started_at=log.started_at, finished_at=log.finished_at,
            result=result, error=log.error,
        ))
    return out


@router.post("/tasks/{task_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def nurture_task_cancel(task_id: str, db: Db, admin: Admin, request: Request) -> None:
    task = _find_task(db, task_id)
    if task.status not in ("pending", "running"):
        raise HTTPException(status_code=409, detail="task_not_cancellable")
    task.status = "cancelled"
    task.finished_at = __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc
    )
    db.commit()
    write_audit_log(
        db, operator=_operator(admin), action="cancel_nurture", entity_type="task",
        entity_id=task.id, ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )


@router.post(
    "/tasks/{task_id}/rerun",
    response_model=TaskCreatedOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def nurture_task_rerun(task_id: str, db: Db, _: Admin) -> TaskCreatedOut:
    task = _find_task(db, task_id)
    try:
        actions = json.loads(task.actions_json or "[]")
    except json.JSONDecodeError:
        actions = []
    async_result = nurture_account_task.delay(
        account_id=task.account_id,
        actions=actions,
        duration_minutes=task.duration_minutes,
    )
    return TaskCreatedOut(task_id=async_result.id)


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def nurture_task_delete(task_id: str, db: Db, admin: Admin, request: Request) -> None:
    task = _find_task(db, task_id)
    db.delete(task)
    db.commit()
    write_audit_log(
        db, operator=_operator(admin), action="delete_nurture", entity_type="task",
        entity_id=task.id, ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )


@router.get("/export")
async def nurture_history_export(
    db: Db,
    _: Admin,
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
) -> Response:
    query = select(NurtureTask)
    if from_:
        query = query.where(NurtureTask.started_at >= from_)
    if to:
        query = query.where(NurtureTask.started_at <= to)
    tasks = db.scalars(query.order_by(NurtureTask.started_at.desc()))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["task_id", "account_id", "platform", "status", "duration_minutes",
                     "started_at", "finished_at", "items_collected", "error"])
    for t in tasks:
        writer.writerow([t.celery_task_id, t.account_id, t.platform, t.status,
                         t.duration_minutes, t.started_at, t.finished_at,
                         t.items_collected, t.error or ""])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=nurture_history.csv"},
    )