"""海报模板路由（独立 router，避免与 settings/{kind} 路径冲突）。

路径: /api/v1/settings/poster-templates/*
依赖: app.core.security.require_admin
"""
import base64
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import require_admin
from app.models.poster import PosterTemplate
from app.services.minimax import MiniMaxClient, MiniMaxError

router = APIRouter(prefix="/settings/poster-templates", tags=["poster-templates"])
Admin = Annotated[dict[str, str], Depends(require_admin)]
DB = Annotated[Session, Depends(get_db)]


class PosterTemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    html_template: str
    css_text: str | None = None
    parsed_meta: dict | None = None


def _dump(t: PosterTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "html_template": t.html_template,
        "css_text": t.css_text,
        "thumbnail_path": t.thumbnail_path,
        "parsed_meta": t.parsed_meta,
        "source": t.source,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
    }


@router.get("")
def list_poster_templates(_: Admin, db: DB) -> dict:
    rows = db.scalars(select(PosterTemplate).order_by(PosterTemplate.id.desc())).all()
    return {"code": 200, "message": "success", "data": {"items": [_dump(r) for r in rows]}}


@router.get("/{tpl_id}")
def get_poster_template(tpl_id: int, _: Admin, db: DB) -> dict:
    row = db.get(PosterTemplate, tpl_id)
    if row is None:
        raise HTTPException(404, "海报模板不存在")
    return {"code": 200, "message": "success", "data": _dump(row)}


@router.post("")
def create_poster_template(payload: PosterTemplateIn, _: Admin, db: DB) -> dict:
    if db.scalar(select(PosterTemplate).where(PosterTemplate.name == payload.name)) is not None:
        raise HTTPException(409, f"模板名 '{payload.name}' 已存在")
    row = PosterTemplate(
        name=payload.name,
        description=payload.description,
        html_template=payload.html_template,
        css_text=payload.css_text,
        parsed_meta=payload.parsed_meta,
        source="manual",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"code": 200, "message": "success", "data": _dump(row)}


@router.put("/{tpl_id}")
def update_poster_template(tpl_id: int, payload: PosterTemplateIn, _: Admin, db: DB) -> dict:
    row = db.get(PosterTemplate, tpl_id)
    if row is None:
        raise HTTPException(404, "海报模板不存在")
    row.name = payload.name
    row.description = payload.description
    row.html_template = payload.html_template
    row.css_text = payload.css_text
    if payload.parsed_meta is not None:
        row.parsed_meta = payload.parsed_meta
    db.commit()
    db.refresh(row)
    return {"code": 200, "message": "success", "data": _dump(row)}


@router.delete("/{tpl_id}")
def delete_poster_template(tpl_id: int, _: Admin, db: DB) -> dict:
    row = db.get(PosterTemplate, tpl_id)
    if row is None:
        raise HTTPException(404, "海报模板不存在")
    db.delete(row)
    db.commit()
    return {"code": 200, "message": "success", "data": {"deleted_id": tpl_id}}


@router.post("/parse-from-image")
async def parse_from_image(
    image: UploadFile = File(...),
    name: str | None = None,
    _: Admin = None,
    db: DB = None,
) -> dict:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(415, "上传文件必须是图片")
    raw = await image.read()
    if len(raw) > 6 * 1024 * 1024:
        raise HTTPException(413, "图片不能超过 6 MiB")
    mime = image.content_type or "image/jpeg"
    image_b64 = base64.b64encode(raw).decode("ascii")
    settings = get_settings()
    if not settings.minimax_api_key:
        raise HTTPException(503, "MiniMax API key 未配置；请设置 MINIMAX_API_KEY 或手动编写 HTML")

    instruction = (
        "你是一名视觉设计师。给一张小红书/活动海报图，"
        "推断 排版布局/颜色/字体/emoji/背景元素/文字位置/图片位置，"
        "用 HTML+CSS 还原成可填充的模板，并指出 parsed_meta。"
        "返回 JSON：{ html_template: '<div>...</div>', css_text: '...', "
        "parsed_meta: { fonts:[...], colors:{primary, bg, text}, emoji:[...], "
        "layout_blocks:[{type, x, y, w, h}] }, "
        "name_suggestion: '例如:橙橙周末合集' }。"
    )
    client = MiniMaxClient(settings)
    try:
        result = client.vision_chat(
            image_b64=image_b64,
            mime_type=mime,
            instruction=instruction,
            max_tokens=4096,
        )
    except MiniMaxError as exc:
        raise HTTPException(503, f"AI 解析失败：{exc}") from exc

    return {
        "code": 200,
        "message": "success",
        "data": {
            "html_template": result.get("html_template", ""),
            "css_text": result.get("css_text", ""),
            "parsed_meta": result.get("parsed_meta", {}),
            "name_suggestion": result.get("name_suggestion") or name or "未命名模板",
        },
    }
