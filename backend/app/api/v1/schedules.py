"""定时抓取任务（/schedules）API。

关联 spec: docs/superpowers/specs/2026-07-25-scheduled-crawls-and-dashboard-charts-design.md

语义：有关键词组抓关键词，有博主（白名单）组抓博主，都有则都抓；
两组皆空 422。触发由 app.tasks.crawl_task.scheduled_dispatch 每分钟 tick 完成。
"""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.blogger_group import BloggerGroup
from app.models.config import City
from app.models.keyword_group import KeywordGroup
from app.models.schedule import ScheduledCrawl
from app.models.task import CrawlTask

router = APIRouter(prefix="/schedules", tags=["schedules"])
Admin = Annotated[dict[str, str], Depends(require_admin)]
DB = Annotated[Session, Depends(get_db)]
RecentFilter = Literal["不限", "一天内", "一周内", "半年内"]


class ScheduleIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    day_of_week: int = Field(ge=1, le=8)  # ISO 1-7=周一至周日，8=每天
    hour: int = Field(ge=0, le=23)
    minute: int = Field(ge=0, le=59)
    city_code: str = Field(min_length=1, max_length=32)
    keyword_group_ids: list[int] = Field(default_factory=list)
    blogger_group_ids: list[int] = Field(default_factory=list)
    recent_filter: RecentFilter | None = None
    enabled: bool = True


def _validate_scope(db: Session, payload: ScheduleIn) -> None:
    if not payload.keyword_group_ids and not payload.blogger_group_ids:
        raise HTTPException(422, "请至少选择一个关键词组或博主组")
    city = db.scalar(select(City).where(City.code == payload.city_code, City.enabled.is_(True)))
    if city is None:
        raise HTTPException(422, f"城市 '{payload.city_code}' 不存在或未启用")
    for group_id in dict.fromkeys(payload.keyword_group_ids):
        group = db.get(KeywordGroup, group_id)
        if group is None or not group.enabled:
            raise HTTPException(422, f"关键词组 id={group_id} 不存在或未启用")
    for group_id in dict.fromkeys(payload.blogger_group_ids):
        group = db.get(BloggerGroup, group_id)
        if group is None or not group.enabled:
            raise HTTPException(422, f"博主组 id={group_id} 不存在或未启用")


def _last_task(db: Session, schedule_id: int) -> dict | None:
    """按 params.schedule_id 匹配最新 CrawlTask（Python 过滤，避免 SQLite json_extract 方言绑定）。"""
    tasks = db.scalars(select(CrawlTask).order_by(CrawlTask.id.desc()).limit(200)).all()
    for task in tasks:
        if (task.params or {}).get("schedule_id") == schedule_id:
            return {"id": task.id, "status": task.status, "started_at": task.started_at}
    return None


def _dump(db: Session, schedule: ScheduledCrawl, with_last_task: bool = False) -> dict:
    data = {
        "id": schedule.id,
        "name": schedule.name,
        "enabled": schedule.enabled,
        "day_of_week": schedule.day_of_week,
        "hour": schedule.hour,
        "minute": schedule.minute,
        "city_code": schedule.city_code,
        "keyword_group_ids": schedule.keyword_group_ids or [],
        "blogger_group_ids": schedule.blogger_group_ids or [],
        "recent_filter": schedule.recent_filter,
        "created_at": schedule.created_at,
        "updated_at": schedule.updated_at,
    }
    if with_last_task:
        data["last_task"] = _last_task(db, schedule.id)
    return data


@router.get("")
def list_schedules(_: Admin = None, db: DB = None) -> dict:
    schedules = db.scalars(select(ScheduledCrawl).order_by(ScheduledCrawl.id)).all()
    return {
        "code": 200,
        "message": "success",
        "data": {"items": [_dump(db, s, with_last_task=True) for s in schedules]},
    }


@router.post("")
def create_schedule(payload: ScheduleIn, _: Admin, db: DB) -> dict:
    _validate_scope(db, payload)
    schedule = ScheduledCrawl(
        name=payload.name,
        enabled=payload.enabled,
        day_of_week=payload.day_of_week,
        hour=payload.hour,
        minute=payload.minute,
        city_code=payload.city_code,
        keyword_group_ids=list(dict.fromkeys(payload.keyword_group_ids)),
        blogger_group_ids=list(dict.fromkeys(payload.blogger_group_ids)),
        recent_filter=payload.recent_filter,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return {"code": 200, "message": "success", "data": _dump(db, schedule, with_last_task=True)}


@router.put("/{schedule_id}")
def update_schedule(schedule_id: int, payload: ScheduleIn, _: Admin, db: DB) -> dict:
    schedule = db.get(ScheduledCrawl, schedule_id)
    if schedule is None:
        raise HTTPException(404, "定时任务不存在")
    _validate_scope(db, payload)
    schedule.name = payload.name
    schedule.enabled = payload.enabled
    schedule.day_of_week = payload.day_of_week
    schedule.hour = payload.hour
    schedule.minute = payload.minute
    schedule.city_code = payload.city_code
    schedule.keyword_group_ids = list(dict.fromkeys(payload.keyword_group_ids))
    schedule.blogger_group_ids = list(dict.fromkeys(payload.blogger_group_ids))
    schedule.recent_filter = payload.recent_filter
    db.commit()
    db.refresh(schedule)
    return {"code": 200, "message": "success", "data": _dump(db, schedule, with_last_task=True)}


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, _: Admin, db: DB) -> dict:
    schedule = db.get(ScheduledCrawl, schedule_id)
    if schedule is None:
        raise HTTPException(404, "定时任务不存在")
    db.delete(schedule)
    db.commit()
    return {"code": 200, "message": "success", "data": {"deleted_id": schedule_id}}
