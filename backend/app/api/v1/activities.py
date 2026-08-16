from datetime import date, datetime, time, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.activity import Activity
from app.models.note import Note, NoteImage
from app.schemas.activity import ActivityRead, ActivityUpdate


router = APIRouter(prefix="/activities", tags=["activities"])
auth = Annotated[dict[str, str], Depends(get_current_user)]
database = Annotated[Session, Depends(get_db)]


class BatchDeleteRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)


def serialize(activity: Activity) -> dict[str, object]:
    return ActivityRead.model_validate(activity).model_dump(mode="json")


def find_activity(db: Session, activity_id: int, include_deleted: bool = False) -> Activity:
    query = select(Activity).where(Activity.id == activity_id)
    if not include_deleted:
        query = query.where(Activity.deleted_at.is_(None))
    activity = db.scalar(query)
    if activity is None:
        raise HTTPException(status_code=404, detail="活动不存在")
    return activity


@router.get("")
def list_activities(
    _: auth,
    db: database,
    city: str | None = None,
    type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    filters = [Activity.deleted_at.is_(None)]
    if city:
        filters.append(Activity.city_code == city)
    if type:
        filters.append(Activity.type == type)
    if start_date:
        filters.append(Activity.start_time >= datetime.combine(start_date, time.min))
    if end_date:
        filters.append(Activity.start_time <= datetime.combine(end_date, time.max))
    total = db.scalar(select(func.count()).select_from(Activity).where(*filters)) or 0
    items = db.scalars(select(Activity).where(*filters).order_by(Activity.start_time.is_(None), Activity.start_time, Activity.id).offset((page - 1) * page_size).limit(page_size)).all()
    return {"code": 200, "message": "success", "data": {"items": [serialize(item) for item in items]}, "pagination": {"page": page, "page_size": page_size, "total": total}}


@router.delete("/batch", deprecated=True)
def batch_delete_activities(payload: BatchDeleteRequest, _: auth, db: database):
    ids = list(dict.fromkeys(payload.ids))
    activities = list(db.scalars(select(Activity).where(Activity.id.in_(ids), Activity.deleted_at.is_(None))).all())
    if not activities:
        raise HTTPException(status_code=404, detail="没有可删除的活动")
    changed_at = datetime.now(timezone.utc)
    for activity in activities:
        activity.deleted_at = changed_at
        activity.updated_at = changed_at
    db.commit()
    deleted_ids = [activity.id for activity in activities]
    return {"code": 200, "message": "success", "data": {"deleted_ids": deleted_ids, "deleted_count": len(deleted_ids)}}


@router.post("/batch/approve", deprecated=True)
def batch_approve_activities(payload: BatchDeleteRequest, _: auth, db: database):
    raise HTTPException(status_code=410, detail="活动审核已迁到推文维度，请使用 /api/v1/notes/{id}/review")


@router.get("/{activity_id}")
def get_activity(activity_id: int, include_deleted: bool = False, _: auth = None, db: database = None):
    activity = find_activity(db, activity_id, include_deleted=include_deleted)
    data = serialize(activity)
    note = db.get(Note, activity.note_id) if activity.note_id else None
    images = list(db.scalars(select(NoteImage).where(NoteImage.note_id == note.id).order_by(NoteImage.id)).all()) if note else []
    data.update({
        "note": {
            "id": note.id,
            "title": note.title,
            "content": note.content,
            "source_url": note.source_url,
            "status": note.status,
        } if note else None,
        "images": [{
            "id": image.id,
            "ocr_status": image.ocr_status,
            "ocr_text": image.ocr_text,
            "url": f"/activities/{activity.id}/images/{image.id}",
        } for image in images],
    })
    return {"code": 200, "message": "success", "data": data}


@router.get("/{activity_id}/images/{image_id}")
def get_activity_image(activity_id: int, image_id: int, _: auth, db: database):
    activity = find_activity(db, activity_id)
    if activity.note_id is None:
        raise HTTPException(status_code=404, detail="图片不存在")
    image = db.scalar(select(NoteImage).where(NoteImage.id == image_id, NoteImage.note_id == activity.note_id))
    if image is None or not image.storage_key:
        raise HTTPException(status_code=404, detail="图片不存在")
    data_root = get_settings().data_dir.resolve()
    image_path = (data_root / image.storage_key).resolve()
    if not image_path.is_relative_to(data_root) or not image_path.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(image_path)


@router.put("/{activity_id}")
def update_activity(activity_id: int, payload: ActivityUpdate, _: auth, db: database):
    activity = find_activity(db, activity_id)
    # model_config=extra='forbid' 已自动拒绝 status 字段
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(activity, key, value)
    activity.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(activity)
    return {"code": 200, "message": "success", "data": serialize(activity)}


@router.delete("/{activity_id}")
def delete_activity(activity_id: int, _: auth, db: database):
    activity = find_activity(db, activity_id)
    now = datetime.now(timezone.utc)
    activity.deleted_at = now
    activity.updated_at = now
    db.commit()
    return {"code": 200, "message": "success", "data": {"id": activity_id}}
