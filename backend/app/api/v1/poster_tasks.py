"""海报任务路由 + 渲染 + 预览。

关联 spec: docs/superpowers/specs/2026-07-21-poster-generation-design.md
- 任务 CRUD（draft / rendered / failed）
- candidates / note-images（前端 wizard 用）
- preview（拼装 HTML）
- render（Playwright / opencli 兜底；写 data/posters/{id}.png）
- download（PNG 流）
"""
import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import require_admin
from app.models.note import Note, NoteImage
from app.models.poster import PosterTask, PosterTemplate
from app.services.poster_renderer import (
    _render_html_to_png,
    render_poster_preview_html,
    render_task_to_png,
    resolve_item_image_urls,
)

router = APIRouter(tags=["poster-tasks"])
Admin = Annotated[dict[str, str], Depends(require_admin)]
DB = Annotated[Session, Depends(get_db)]


class PosterTaskIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    template_id: int
    items: list[dict[str, Any]] = Field(default_factory=list)
    override_html: str | None = None


class PosterTaskPatch(BaseModel):
    name: str | None = None
    status: str | None = None
    items: list[dict[str, Any]] | None = None
    override_html: str | None = None


def _dump_task(t: PosterTask) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "status": t.status,
        "template_id": t.template_id,
        "items": t.items,
        "override_html": t.override_html,
        "output_path": t.output_path,
        "output_format": t.output_format,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


@router.get("/poster-tasks")
def list_poster_tasks(_: Admin, db: DB) -> dict:
    rows = db.scalars(select(PosterTask).order_by(PosterTask.id.desc())).all()
    return {"code": 200, "message": "success", "data": {"items": [_dump_task(r) for r in rows]}}


@router.get("/poster-tasks/candidates")
def candidates(
    _: Admin,
    db: DB,
    city_code: str | None = Query(None),
    q: str | None = Query(None),
    page_size: int = Query(20, le=50),
) -> dict:
    """返回可选 note / activity 列表。前端 wizard 选活动用。

    每项含 type, id (note or activity id), title, image_count 与必要时 note_id。
    """
    stmt = select(Note).order_by(Note.id.desc()).limit(page_size)
    if city_code:
        stmt = stmt.where(Note.city_code == city_code)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Note.title.ilike(like)) | (Note.content.ilike(like)))
    notes = db.scalars(stmt).all()
    items: list[dict] = []
    for note in notes:
        image_urls = _note_image_urls(db, note.id)
        img_count = len(image_urls)
        items.append({
            "type": "note",
            "id": note.id,
            "title": note.title or f"Note #{note.id}",
            "city_code": note.city_code,
            "image_count": img_count,
            "image_urls": image_urls,
        })
    return {"code": 200, "message": "success", "data": {"items": items}}


def _note_image_urls(db: Session, note_id: int) -> list[str]:
    images = db.scalars(
        select(NoteImage).where(NoteImage.note_id == note_id).order_by(NoteImage.id)
    ).all()
    return [
        f"/api/v1/posters/note-image-by-id/{image.id}"
        for image in images
    ]


@router.get("/posters/note-image-by-id/{image_id}")
def note_image_by_id(image_id: int, _: Admin, db: DB) -> StreamingResponse:
    image = db.get(NoteImage, image_id)
    if image is None:
        raise HTTPException(404, "图片不存在")
    settings = get_settings()
    base = Path(settings.data_dir).resolve()
    target = (base / image.storage_key).resolve()
    if not target.is_relative_to(base) or not target.is_file():
        raise HTTPException(404, "图片文件不存在")
    return StreamingResponse(target.open("rb"), media_type="image/jpeg")


@router.get("/posters/note-images/{note_id}")
def note_images(note_id: int, _: Admin, db: DB) -> dict:
    note = db.get(Note, note_id)
    if note is None:
        raise HTTPException(404, "推文不存在")
    image_urls = _note_image_urls(db, note_id)
    return {"code": 200, "message": "success", "data": {"note_id": note_id, "image_urls": image_urls}}


@router.get("/poster-tasks/{task_id}")
def get_poster_task(task_id: int, _: Admin, db: DB) -> dict:
    t = db.get(PosterTask, task_id)
    if t is None:
        raise HTTPException(404, "任务不存在")
    return {"code": 200, "message": "success", "data": _dump_task(t)}


@router.post("/poster-tasks")
def create_poster_task(payload: PosterTaskIn, _: Admin, db: DB) -> dict:
    if db.get(PosterTemplate, payload.template_id) is None:
        raise HTTPException(422, "模板不存在")
    t = PosterTask(
        name=payload.name,
        template_id=payload.template_id,
        items=payload.items,
        override_html=payload.override_html,
        status="draft",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return {"code": 200, "message": "success", "data": _dump_task(t)}


@router.put("/poster-tasks/{task_id}")
def update_poster_task(task_id: int, payload: PosterTaskPatch, _: Admin, db: DB) -> dict:
    t = db.get(PosterTask, task_id)
    if t is None:
        raise HTTPException(404, "任务不存在")
    if payload.name is not None:
        t.name = payload.name
    if payload.status is not None:
        t.status = payload.status
    if payload.items is not None:
        from sqlalchemy.orm.attributes import flag_modified

        t.items = payload.items
        flag_modified(t, "items")
    if payload.override_html is not None:
        t.override_html = payload.override_html
    db.commit()
    db.refresh(t)
    return {"code": 200, "message": "success", "data": _dump_task(t)}


@router.delete("/poster-tasks/{task_id}")
def delete_poster_task(task_id: int, _: Admin, db: DB) -> dict:
    t = db.get(PosterTask, task_id)
    if t is None:
        raise HTTPException(404, "任务不存在")
    if t.output_path and Path(t.output_path).exists():
        try:
            Path(t.output_path).unlink()
        except OSError:
            pass
    db.delete(t)
    db.commit()
    return {"code": 200, "message": "success", "data": {"deleted_id": task_id}}


@router.get("/poster-tasks/{task_id}/preview")
def preview(task_id: int, _: Admin, db: DB) -> dict:
    t = db.get(PosterTask, task_id)
    if t is None:
        raise HTTPException(404, "任务不存在")
    template = db.get(PosterTemplate, t.template_id)
    if template is None:
        raise HTTPException(422, "模板已删除")
    html = render_poster_preview_html(template, t)
    return {
        "code": 200,
        "message": "success",
        "data": {"html": html, "items_count": len(t.items or [])},
    }


@router.post("/poster-tasks/{task_id}/render")
async def render_task(task_id: int, _: Admin, db: DB) -> dict:
    t = db.get(PosterTask, task_id)
    if t is None:
        raise HTTPException(404, "任务不存在")
    template = db.get(PosterTemplate, t.template_id)
    if template is None:
        raise HTTPException(422, "模板已删除")
    settings = get_settings()

    # 在主线解析图片 URL（base64 模式，兼容 Playwright 和 opencli HTTP 渲染）
    resolved_items = resolve_item_image_urls(
        t.items or [], db, str(settings.data_dir), mode="base64"
    )

    # 渲染是重 CPU 阻塞操作，丢到 thread pool
    def _render() -> str:
        out_dir = Path(settings.data_dir) / "posters"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{t.id}.png"
        html = render_poster_preview_html(template, t, items_override=resolved_items)
        return _render_html_to_png(html, str(out_path))

    try:
        path = await asyncio.to_thread(_render)
    except RuntimeError as exc:
        t.status = "failed"
        db.commit()
        raise HTTPException(503, str(exc)) from exc
    t.output_path = path
    t.status = "rendered"
    db.commit()
    db.refresh(t)
    return {
        "code": 200,
        "message": "success",
        "data": {
            "id": t.id,
            "output_path": path,
            "url": f"/api/v1/poster-tasks/{t.id}/download",
        },
    }


@router.get("/poster-tasks/{task_id}/download")
def download(task_id: int, _: Admin, db: DB) -> FileResponse:
    t = db.get(PosterTask, task_id)
    if t is None or not t.output_path:
        raise HTTPException(404, "产物不存在")
    p = Path(t.output_path)
    if not p.exists():
        raise HTTPException(404, "产物文件已被清理")
    return FileResponse(str(p), media_type="image/png", filename=f"poster-{t.id}.png")
