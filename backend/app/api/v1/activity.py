"""v0.3 account-activity aggregation endpoints (KPI / heatmap / action counts)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.login_check_log import LoginCheckLog
from app.models.nurture_task import NurtureActionLog, NurtureTask
from app.schemas.full_features import (
    ActionCount,
    ActivityKpiOut,
    HeatmapCell,
    PlatformCount,
)

router = APIRouter(prefix="/accounts/activity", tags=["activity"])

Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[dict, Depends(require_admin)]


@router.get("/kpi", response_model=ActivityKpiOut)
async def activity_kpi(
    db: Db,
    _: Admin,
    account_id: int | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
) -> ActivityKpiOut:
    login_q = select(func.count()).select_from(LoginCheckLog).where(
        LoginCheckLog.logged_in.is_(True)
    )
    task_q = select(func.count()).select_from(NurtureTask)
    like_q = select(func.count()).select_from(NurtureActionLog).where(
        NurtureActionLog.action.contains("like")
    )
    favorite_q = select(func.count()).select_from(NurtureActionLog).where(
        NurtureActionLog.action.contains("favorite")
    )
    if account_id:
        login_q = login_q.where(LoginCheckLog.account_id == account_id)
        task_q = task_q.where(NurtureTask.account_id == account_id)
        like_q = like_q.where(
            NurtureActionLog.task_id.in_(
                select(NurtureTask.id).where(NurtureTask.account_id == account_id)
            )
        )
        favorite_q = favorite_q.where(
            NurtureActionLog.task_id.in_(
                select(NurtureTask.id).where(NurtureTask.account_id == account_id)
            )
        )

    login_count = db.scalar(login_q) or 0
    nurture_task_count = db.scalar(task_q) or 0

    # total nurture seconds across completed tasks
    nature_seconds = 0
    tasks = db.scalars(
        select(NurtureTask).where(NurtureTask.status == "completed")
    )
    for t in tasks:
        if t.started_at and t.finished_at:
            nature_seconds += int((t.finished_at - t.started_at).total_seconds())
        elif t.duration_minutes:
            nature_seconds += t.duration_minutes * 60

    return ActivityKpiOut(
        login_count=login_count,
        nurture_seconds=nature_seconds,
        like_count=db.scalar(like_q) or 0,
        favorite_count=db.scalar(favorite_q) or 0,
        nurture_task_count=nurture_task_count,
    )


@router.get("/heatmap", response_model=list[HeatmapCell])
async def activity_heatmap(
    db: Db, _: Admin, account_id: int | None = Query(default=None)
) -> list[HeatmapCell]:
    """Daily activity heatmap cells (login checks intensity per account per day)."""
    query = select(LoginCheckLog)
    if account_id:
        query = query.where(LoginCheckLog.account_id == account_id)
    cells: dict[tuple[int, str], int] = {}
    for log in db.scalars(query):
        d = log.checked_at.date().isoformat()
        key = (log.account_id, d)
        cells[key] = cells.get(key, 0) + 1
    return [
        HeatmapCell(account_id=aid, date=date, intensity=cnt)
        for (aid, date), cnt in sorted(cells.items(), key=lambda kv: (kv[0][1], kv[0][0]))
    ]


@router.get("/action-counts", response_model=list[ActionCount])
async def activity_action_counts(
    db: Db, _: Admin, account_id: int | None = Query(default=None)
) -> list[ActionCount]:
    query = select(NurtureActionLog.action, func.count()).group_by(NurtureActionLog.action)
    if account_id:
        query = query.where(
            NurtureActionLog.task_id.in_(
                select(NurtureTask.id).where(NurtureTask.account_id == account_id)
            )
        )
    return [
        ActionCount(action_type=action, count=count)
        for action, count in db.execute(query)
    ]


@router.get("/platform-counts", response_model=list[PlatformCount])
async def activity_platform_counts(db: Db, _: Admin) -> list[PlatformCount]:
    query = select(NurtureTask.platform, func.count()).group_by(NurtureTask.platform)
    return [
        PlatformCount(platform=platform, count=count)
        for platform, count in db.execute(query)
    ]