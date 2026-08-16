from datetime import date, datetime, time, timezone as tz
from typing import Annotated, Literal

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import bindparam, delete, func, or_, select, text, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.activity import Activity
from app.models.blogger_group import BloggerGroup, BloggerGroupMember
from app.models.config import Blogger, City
from app.models.keyword_group import KeywordGroup, KeywordGroupWord
from app.models.note import Note, NoteImage
from app.schemas.activity import ActivityRead
from app.services.extraction import extract_activities
from app.services.minimax import MiniMaxClient


router = APIRouter(prefix="/notes", tags=["notes"])
Auth = Annotated[dict[str, str], Depends(get_current_user)]
DB = Annotated[Session, Depends(get_db)]
logger = logging.getLogger(__name__)


class BatchRequest(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=100)


class NoteUpdate(BaseModel):
    title: str = Field(max_length=512)
    content: str
    city_code: str = Field(min_length=1, max_length=32)
    published_at: datetime | None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("标题不能为空")
        return value


class NoteReviewRequest(BaseModel):
    status: Literal["APPROVED", "REJECTED"]


class ActivityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=256)
    location: str = Field(default="", max_length=256)
    start_time: datetime | None = None
    end_time: datetime | None = None
    type: str = Field(min_length=1, max_length=64)
    summary: str = Field(default="", max_length=2000)


def _visible_note(db: Session, note_id: int) -> Note:
    note = db.scalar(select(Note).where(Note.id == note_id, Note.review_status.notin_(["DELETED", "MERGED"])))
    if note is None:
        raise HTTPException(404, "推文不存在")
    return note


def _summary(note: Note, activity_count: int, ocr_texts: list[str] | None = None) -> dict:
    """为列表行构造轻量级 summary；超过 4 KiB 会被截断，并附 `summary_truncated=True`。

    详情接口 `_detail_data` 不走此函数，仍返回全部 OCR。
    """
    MAX_OCR_BLOCKS = 5
    MAX_SUMMARY_BYTES = 4096
    ocr_list = ocr_texts or []
    parts: list[str] = []
    if note.content:
        parts.append(f"正文：{note.content}")
    ocr_count = 0
    for index, text in enumerate(ocr_list, 1):
        if not text:
            continue
        if ocr_count >= MAX_OCR_BLOCKS:
            break
        parts.append(f"[图片 {index} OCR] {text}")
        ocr_count += 1
    text = "\n".join(parts)
    encoded = text.encode("utf-8")
    truncated = False
    if len(encoded) > MAX_SUMMARY_BYTES:
        truncated = True
        omission = "…(摘要已截断" + ("，共省略多张图片 OCR)" if ocr_count < len([t for t in ocr_list if t]) else ")")
        omission_bytes = omission.encode("utf-8")
        keep_bytes = max(0, MAX_SUMMARY_BYTES - len(omission_bytes) - 1)  # 留 1 byte 给前缀换行
        truncated_body = encoded[:keep_bytes].decode("utf-8", errors="ignore")
        text = truncated_body + "\n" + omission
    return {
        "id": note.id,
        "title": note.title,
        "city_code": note.city_code,
        "published_at": note.published_at,
        "created_at": note.created_at,
        "processing_status": note.status,
        "review_status": note.review_status,
        "activity_count": activity_count,
        "source_url": note.source_url,
        "summary": text,
        "summary_truncated": truncated,
        "like_count": note.like_count,
        "collect_count": note.collect_count,
        "comment_count": note.comment_count,
    }


def _detail_data(db: Session, note: Note) -> dict:
    activities = list(db.scalars(select(Activity).where(Activity.note_id == note.id, Activity.deleted_at.is_(None)).order_by(Activity.id)).all())
    images = list(db.scalars(select(NoteImage).where(NoteImage.note_id == note.id).order_by(NoteImage.id)).all())
    ocr_texts = [image.ocr_text for image in images]
    data = _summary(note, len(activities), ocr_texts)
    data.update({
        "content": note.content,
        "activities": [ActivityRead.model_validate(item).model_dump(mode="json") for item in activities],
        "images": [{"id": image.id, "ocr_status": image.ocr_status, "ocr_text": image.ocr_text, "url": f"/notes/{note.id}/images/{image.id}"} for image in images],
    })
    return data


@router.get("")
def list_notes(
    _: Auth,
    db: DB,
    city: str | None = None,
    review_status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    keyword: str | None = None,
    keyword_group_ids: Annotated[list[int] | None, Query()] = None,
    blogger_id: int | None = None,
    blogger_group_ids: Annotated[list[int] | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    # 互斥校验
    if keyword and keyword_group_ids:
        raise HTTPException(status_code=422, detail="参数冲突：keyword 与 keyword_group_ids 不能同时传")
    if blogger_id is not None and blogger_group_ids:
        raise HTTPException(status_code=422, detail="参数冲突：blogger_id 与 blogger_group_ids 不能同时传")

    filters = [Note.review_status.notin_(["DELETED", "MERGED"])]
    if city:
        filters.append(Note.city_code == city)
    if review_status:
        filters.append(Note.review_status == review_status)
    published = Note.published_at
    if start_date:
        filters.append(Note.published_at >= datetime.combine(start_date, time.min))
    if end_date:
        filters.append(Note.published_at <= datetime.combine(end_date, time.max))

    # 关键词组筛选：取所有选中 enabled 组的 words 并集
    if keyword_group_ids:
        words_stmt = (
            select(KeywordGroupWord.word)
            .join(KeywordGroup, KeywordGroup.id == KeywordGroupWord.keyword_group_id)
            .where(
                KeywordGroup.id.in_(keyword_group_ids),
                KeywordGroup.enabled.is_(True),
                KeywordGroupWord.enabled.is_(True),
            )
            .distinct()
        )
        word_set = [w for w in db.scalars(words_stmt).all() if w]
        if not word_set:
            return {"code": 200, "message": "success", "data": {"items": []}, "pagination": {"page": page, "page_size": page_size, "total": 0}}
        # 展开绑定参数：IN :word_set 自动渲染为 IN (?, ?, ...) 而非单参数
        # SQLAlchemy 1.2+ 行为：expanding=True 把 sequence 渲染为多个 `?`
        stmt = text(
            "EXISTS (SELECT 1 FROM json_each(notes.matched_keywords) WHERE json_each.value IN :word_set)"
        ).bindparams(bindparam("word_set", expanding=True))
        filters.append(stmt.bindparams(word_set=tuple(word_set)))

    # 博主组筛选：取所有选中 enabled 组的成员 blogger id 并集
    if blogger_group_ids:
        blogger_ids_stmt = (
            select(BloggerGroupMember.blogger_id)
            .join(BloggerGroup, BloggerGroup.id == BloggerGroupMember.group_id)
            .where(
                BloggerGroup.id.in_(blogger_group_ids),
                BloggerGroup.enabled.is_(True),
            )
            .distinct()
        )
        blogger_id_set = list(db.scalars(blogger_ids_stmt).all())
        if not blogger_id_set:
            return {"code": 200, "message": "success", "data": {"items": []}, "pagination": {"page": page, "page_size": page_size, "total": 0}}
        filters.append(Note.matched_blogger_id.in_(blogger_id_set))

    if keyword:
        stripped = keyword.strip()
        if stripped:
            pattern = f"%{stripped}%"
            filters.append(or_(Note.title.ilike(pattern), Note.content.ilike(pattern)))
    if blogger_id is not None:
        blogger = db.scalar(select(Blogger).where(Blogger.id == blogger_id))
        if blogger is None:
            raise HTTPException(404, "博主不存在")
        if not blogger.profile_url:
            # 博主无主页地址，无法匹配任何推文
            return {"code": 200, "message": "success", "data": {"items": []}, "pagination": {"page": page, "page_size": page_size, "total": 0}}
        filters.append(Note.source_url.like(blogger.profile_url + "%"))

    total = db.scalar(select(func.count()).select_from(Note).where(*filters)) or 0
    activity_counts = (
        select(Activity.note_id, func.count(Activity.id).label("activity_count"))
        .where(Activity.deleted_at.is_(None))
        .group_by(Activity.note_id)
        .subquery()
    )
    rows = db.execute(
        select(Note, func.coalesce(activity_counts.c.activity_count, 0))
        .outerjoin(activity_counts, activity_counts.c.note_id == Note.id)
        .where(*filters)
        .order_by(published.desc(), Note.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    note_ids = [note.id for note, _ in rows]
    ocr_map: dict[int, list[str]] = {}
    if note_ids:
        try:
            image_rows = db.execute(
                select(NoteImage.note_id, NoteImage.ocr_text)
                .where(NoteImage.note_id.in_(note_ids))
                .order_by(NoteImage.note_id, NoteImage.id)
            ).all()
            for note_id, ocr_text in image_rows:
                ocr_map.setdefault(note_id, []).append(ocr_text)
        except Exception as exc:
            # OCR 聚合失败不影响主列表读取，但必须留下可查日志
            logger.warning("笔记列表 OCR 聚合失败 note_ids=%s: %s", note_ids, exc)
            ocr_map = {}
    return {"code": 200, "message": "success", "data": {"items": [_summary(note, count, ocr_map.get(note.id, [])) for note, count in rows]}, "pagination": {"page": page, "page_size": page_size, "total": total}}


@router.get("/{note_id}")
def get_note(note_id: int, _: Auth, db: DB):
    note = _visible_note(db, note_id)
    return {"code": 200, "message": "success", "data": _detail_data(db, note)}


@router.put("/{note_id}")
def update_note(note_id: int, payload: NoteUpdate, _: Auth, db: DB):
    note = _visible_note(db, note_id)
    city = db.scalar(select(City).where(City.code == payload.city_code, City.enabled.is_(True)))
    if city is None:
        raise HTTPException(status_code=422, detail="城市不存在或未启用")
    note.title = payload.title
    note.content = payload.content
    note.city_code = payload.city_code
    note.published_at = payload.published_at
    db.commit()
    db.refresh(note)
    return {"code": 200, "message": "success", "data": _detail_data(db, note)}


@router.post("/{note_id}/review")
def review_note(note_id: int, payload: NoteReviewRequest, _: Auth, db: DB):
    note = _visible_note(db, note_id)
    note.review_status = payload.status
    db.commit()
    return {"code": 200, "message": "success", "data": {"id": note.id, "review_status": note.review_status}}


@router.post("/{note_id}/reprocess")
def reprocess_note(note_id: int, _: Auth, db: DB):
    """将状态异常的推文标记为可重跑。

    适用：note.status in (NO_ACTIVITIES, EMPTY_RESULT_RETRYABLE)。
    实际重新抓取需要走 /api/v1/tasks/{id}/restart 重新触发 worker。
    """
    note = db.get(Note, note_id)
    if note is None or note.review_status in {"DELETED", "MERGED"}:
        raise HTTPException(status_code=404, detail="推文不存在")
    if note.status not in {"NO_ACTIVITIES", "EMPTY_RESULT_RETRYABLE"}:
        raise HTTPException(status_code=409, detail=f"推文状态 {note.status} 不需要重新处理")
    # 清除 OCR/详情/活动记录，重新走抓取阶段
    db.execute(delete(NoteImage).where(NoteImage.note_id == note_id))
    db.execute(delete(Activity).where(Activity.note_id == note_id))
    note.status = "PENDING"
    note.published_at = None
    db.commit()
    return {"code": 202, "message": "success", "data": {"id": note.id, "status": note.status}}


@router.post("/{note_id}/re-extract")
def re_extract_note(note_id: int, _: Auth, db: DB):
    """对单条推文重新提取活动（使用已有 OCR 数据，不重抓图片）。"""
    note = _visible_note(db, note_id)
    images = list(db.scalars(
        select(NoteImage).where(NoteImage.note_id == note_id).order_by(NoteImage.id)
    ).all())

    # 拼合 OCR 文本
    ocr_texts: list[str] = []
    for image in images:
        if image.ocr_text:
            ocr_texts.append(f"[IMAGE {image.id}]\n{image.ocr_text}")
    combined = f"标题：{note.title}\n正文：{note.content}\n" + "\n".join(ocr_texts)

    # 提取活动
    settings = get_settings()
    reference_now = note.published_at.replace(tzinfo=None) if note.published_at else datetime.now(tz.utc).replace(tzinfo=None)
    if settings.minimax_api_key:
        client = MiniMaxClient(settings)
        try:
            extracted = extract_activities(combined, reference_now, lambda text: client.extract_many(text, datetime.now(tz.utc)))
        except Exception as exc:
            logger.warning("re-extract MiniMax 失败，降级规则提取 note_id=%s: %s", note_id, exc)
            extracted = extract_activities(combined, reference_now, None)
    else:
        extracted = extract_activities(combined, reference_now, None)

    # 校验
    from app.services.activity_validator import classify_zero_activity, validate_activities

    classification = classify_zero_activity(note, extracted)
    if classification in {"all_before_publish", "no_activity_signals"}:
        note.status = "NO_ACTIVITIES"
        db.commit()
        return {
            "code": 200, "message": "success",
            "data": {"status": note.status, "activities": [], "extracted_count": 0, "reason": classification},
        }
    if classification == "minimax_empty_retryable":
        note.status = "EMPTY_RESULT_RETRYABLE"
        db.commit()
        return {
            "code": 200, "message": "success",
            "data": {"status": note.status, "activities": [], "extracted_count": 0, "reason": classification},
        }

    accepted, rejected = validate_activities(note, extracted)
    for reason in rejected:
        logger.info("re-extract 跳过活动 note_id=%s 原因=%s", note_id, reason)
    if not accepted:
        note.status = "NO_ACTIVITIES"
        db.commit()
        return {
            "code": 200, "message": "success",
            "data": {"status": note.status, "activities": [], "extracted_count": 0, "reason": "all_filtered"},
        }

    # 软删除旧活动，写入新活动
    now = datetime.now(tz.utc)
    db.execute(
        update(Activity).where(Activity.note_id == note_id, Activity.deleted_at.is_(None))
        .values(deleted_at=now)
    )
    new_activities: list[dict] = []
    for fields in accepted:
        activity = Activity(
            note_id=note.id,
            name=fields.get("name") or note.title,
            city_code=note.city_code,
            start_time=datetime.fromisoformat(fields["start_time"]) if fields.get("start_time") else None,
            end_time=datetime.fromisoformat(fields["end_time"]) if fields.get("end_time") else None,
            location=fields.get("location") or "",
            type=fields.get("type") or "其他",
            source_url=note.source_url,
            source_image_indexes=fields.get("source_image_indexes") or [],
            summary=fields.get("summary") or note.content[:300],
            confidence=float(fields.get("confidence") or 0),
        )
        db.add(activity)
        db.flush()
        new_activities.append(ActivityRead.model_validate(activity).model_dump(mode="json"))

    note.status = "PROCESSED"
    db.commit()
    return {
        "code": 200, "message": "success",
        "data": {"status": note.status, "activities": new_activities, "extracted_count": len(new_activities)},
    }


@router.post("/{note_id}/activities", status_code=201)
def create_activity_for_note(note_id: int, payload: ActivityCreate, _: Auth, db: DB):
    """手动为推文新增一条子活动。"""
    note = _visible_note(db, note_id)
    activity = Activity(
        note_id=note.id,
        name=payload.name,
        city_code=note.city_code,
        start_time=payload.start_time,
        end_time=payload.end_time,
        location=payload.location,
        type=payload.type,
        source_url=note.source_url,
        summary=payload.summary,
        confidence=1.0,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return {"code": 201, "message": "success", "data": ActivityRead.model_validate(activity).model_dump(mode="json")}


@router.get("/{note_id}/images/{image_id}")
def get_note_image(note_id: int, image_id: int, _: Auth, db: DB):
    _visible_note(db, note_id)
    image = db.scalar(select(NoteImage).where(NoteImage.id == image_id, NoteImage.note_id == note_id))
    if image is None or not image.storage_key:
        raise HTTPException(404, "图片不存在")
    data_root = get_settings().data_dir.resolve()
    path = (data_root / image.storage_key).resolve()
    if not path.is_relative_to(data_root) or not path.is_file():
        raise HTTPException(404, "图片不存在")
    return FileResponse(path)


def _batch_status(db: Session, ids: list[int], target: str) -> list[int]:
    notes = list(db.scalars(select(Note).where(Note.id.in_(set(ids)), Note.review_status.notin_(["DELETED", "MERGED"]))).all())
    if not notes:
        raise HTTPException(404, "没有可操作的推文")
    for note in notes:
        note.review_status = target
    db.commit()
    return [note.id for note in notes]


@router.post("/batch/approve")
def approve_notes(payload: BatchRequest, _: Auth, db: DB):
    notes = list(db.scalars(select(Note).where(Note.id.in_(set(payload.ids)), Note.review_status.notin_(["DELETED", "MERGED"]))).all())
    if not notes:
        raise HTTPException(404, "没有可操作的推文")
    approved: list[int] = []
    for note in notes:
        note.review_status = "APPROVED"
        approved.append(note.id)
    db.commit()
    return {"code": 200, "message": "success", "data": {"approved_ids": approved, "approved_count": len(approved)}}


@router.delete("/batch")
def delete_notes(payload: BatchRequest, _: Auth, db: DB):
    ids = _batch_status(db, payload.ids, "DELETED")
    return {"code": 200, "message": "success", "data": {"deleted_ids": ids, "deleted_count": len(ids)}}
