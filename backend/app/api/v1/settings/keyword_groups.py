"""关键词组 CRUD + 批量删除。

端点（URL 不变）：
- GET    /settings/keyword-groups
- GET    /settings/keyword-groups/{kg_id}
- POST   /settings/keyword-groups
- PUT    /settings/keyword-groups/{kg_id}/words
- PUT    /settings/keyword-groups/{kg_id}/cities
- DELETE /settings/keyword-groups/{kg_id}
- POST   /settings/keyword-groups/batch-delete
- PATCH  /settings/keyword-groups/{kg_id}
"""
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.models.config import City
from app.models.keyword_group import KeywordGroup, KeywordGroupCity, KeywordGroupWord
from app.services.audit import record_audit
from typing import Annotated

from app.api.v1.settings._deps import (
    Admin,
    BatchDeleteIdsIn,
    BatchDeleteOut,
    DB,
)
from app.core.security import get_current_user

# 仅要求已登录用户（GET 用），不再 Admin-only
LoggedInUser = Annotated[dict, Depends(get_current_user)]

router = APIRouter(tags=["settings"])


def _parse_excluded_words(json_text: str | None) -> list[str]:
    if not json_text:
        return []
    try:
        parsed = json.loads(json_text)
        return [str(item).strip() for item in parsed if str(item).strip()]
    except (TypeError, ValueError, json.JSONDecodeError):
        return []


def _serialize_excluded_words(words: list[str]) -> str:
    return json.dumps(sorted(set(str(w).strip() for w in words if str(w).strip())), ensure_ascii=False)


class KeywordGroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    city_codes: list[str] = Field(default_factory=list)
    words: list[str] = Field(default_factory=list)
    # 排除词：命中关键词的笔记若内容含任一排除词则被过滤
    excluded_words: list[str] = Field(default_factory=list)
    enabled: bool = True


class KeywordGroupUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    enabled: bool | None = None


class KeywordGroupWordsIn(BaseModel):
    words: list[str]


class KeywordGroupCitiesIn(BaseModel):
    city_codes: list[str]


def _dump_keyword_group(db, kg: KeywordGroup) -> dict:
    # outer join City 取 name；City 不存在时 name=None 兜底为 code
    city_rows = db.execute(
        select(KeywordGroupCity.city_code, City.name)
        .outerjoin(City, City.code == KeywordGroupCity.city_code)
        .where(KeywordGroupCity.keyword_group_id == kg.id)
        .order_by(KeywordGroupCity.city_code)
    ).all()
    cities = [{"code": code, "name": name or code} for code, name in city_rows]
    city_codes = [c["code"] for c in cities]
    words = sorted(
        row.word for row in db.scalars(
            select(KeywordGroupWord).where(KeywordGroupWord.keyword_group_id == kg.id)
        ).all()
    )
    return {
        "id": kg.id,
        "name": kg.name,
        "description": kg.description,
        "enabled": kg.enabled,
        "city_codes": city_codes,
        "cities": cities,
        "words": words,
        "excluded_words": _parse_excluded_words(kg.excluded_words_json),
        "created_at": kg.created_at,
    }


@router.get("/settings/keyword-groups")
def list_keyword_groups(
    city_code: str | None = None,
    db: DB = None,
    _user: LoggedInUser = None,
) -> dict:
    # GET 改为仅要求已登录用户（不再 Admin-only），方便 Dashboard 选关键词组；
    # 写操作（POST/PUT/DELETE/PATCH/batch-delete）仍保持 Admin-only。
    stmt = select(KeywordGroup).order_by(KeywordGroup.id)
    if city_code:
        stmt = stmt.join(
            KeywordGroupCity, KeywordGroupCity.keyword_group_id == KeywordGroup.id
        ).where(KeywordGroupCity.city_code == city_code)
    groups = db.scalars(stmt.distinct()).all()
    return {
        "code": 200,
        "message": "success",
        "data": {"items": [_dump_keyword_group(db, g) for g in groups]},
    }


@router.get("/settings/keyword-groups/{kg_id}")
def get_keyword_group(kg_id: int, _: Admin, db: DB) -> dict:
    kg = db.get(KeywordGroup, kg_id)
    if kg is None:
        raise HTTPException(404, "关键词组不存在")
    return {"code": 200, "message": "success", "data": _dump_keyword_group(db, kg)}


@router.post("/settings/keyword-groups")
def create_keyword_group(payload: KeywordGroupIn, _: Admin, db: DB) -> dict:
    existing = db.scalar(select(KeywordGroup).where(KeywordGroup.name == payload.name))
    if existing is not None:
        raise HTTPException(409, f"关键词组名称 '{payload.name}' 已存在")

    kg = KeywordGroup(
        name=payload.name,
        description=payload.description,
        enabled=payload.enabled,
        excluded_words_json=_serialize_excluded_words(payload.excluded_words),
    )
    db.add(kg)
    db.flush()
    for code in dict.fromkeys(payload.city_codes):
        if db.scalar(select(City).where(City.code == code)) is None:
            raise HTTPException(422, f"城市代码 '{code}' 不存在")
        db.add(KeywordGroupCity(keyword_group_id=kg.id, city_code=code, enabled=True))
    for word in dict.fromkeys(payload.words):
        if not word.strip():
            continue
        db.add(KeywordGroupWord(keyword_group_id=kg.id, word=word.strip(), enabled=True))
    db.commit()
    db.refresh(kg)
    return {"code": 200, "message": "success", "data": _dump_keyword_group(db, kg)}


@router.put("/settings/keyword-groups/{kg_id}/words")
def replace_keyword_group_words(kg_id: int, payload: KeywordGroupWordsIn, _: Admin, db: DB) -> dict:
    kg = db.get(KeywordGroup, kg_id)
    if kg is None:
        raise HTTPException(404, "关键词组不存在")
    db.execute(delete(KeywordGroupWord).where(KeywordGroupWord.keyword_group_id == kg_id))
    for word in dict.fromkeys(payload.words):
        if not word.strip():
            continue
        db.add(KeywordGroupWord(keyword_group_id=kg_id, word=word.strip(), enabled=True))
    db.commit()
    db.refresh(kg)
    return {"code": 200, "message": "success", "data": _dump_keyword_group(db, kg)}


@router.put("/settings/keyword-groups/{kg_id}/cities")
def replace_keyword_group_cities(kg_id: int, payload: KeywordGroupCitiesIn, _: Admin, db: DB) -> dict:
    kg = db.get(KeywordGroup, kg_id)
    if kg is None:
        raise HTTPException(404, "关键词组不存在")
    db.execute(delete(KeywordGroupCity).where(KeywordGroupCity.keyword_group_id == kg_id))
    for code in dict.fromkeys(payload.city_codes):
        if db.scalar(select(City).where(City.code == code)) is None:
            raise HTTPException(422, f"城市代码 '{code}' 不存在")
        db.add(KeywordGroupCity(keyword_group_id=kg_id, city_code=code, enabled=True))
    db.commit()
    db.refresh(kg)
    return {"code": 200, "message": "success", "data": _dump_keyword_group(db, kg)}


class KeywordGroupExcludedWordsIn(BaseModel):
    excluded_words: list[str] = Field(default_factory=list)


@router.put("/settings/keyword-groups/{kg_id}/excluded-words")
def replace_keyword_group_excluded_words(kg_id: int, payload: KeywordGroupExcludedWordsIn, _: Admin, db: DB) -> dict:
    kg = db.get(KeywordGroup, kg_id)
    if kg is None:
        raise HTTPException(404, "关键词组不存在")
    kg.excluded_words_json = _serialize_excluded_words(payload.excluded_words)
    db.commit()
    db.refresh(kg)
    return {"code": 200, "message": "success", "data": _dump_keyword_group(db, kg)}


@router.delete("/settings/keyword-groups/{kg_id}")
def delete_keyword_group(kg_id: int, _: Admin, db: DB) -> dict:
    kg = db.get(KeywordGroup, kg_id)
    if kg is None:
        raise HTTPException(404, "关键词组不存在")
    db.execute(delete(KeywordGroupWord).where(KeywordGroupWord.keyword_group_id == kg_id))
    db.execute(delete(KeywordGroupCity).where(KeywordGroupCity.keyword_group_id == kg_id))
    db.delete(kg)
    db.commit()
    return {"code": 200, "message": "success", "data": {"deleted_id": kg_id}}


@router.post("/settings/keyword-groups/batch-delete", response_model=BatchDeleteOut)
def batch_delete_keyword_groups(
    payload: BatchDeleteIdsIn,
    request: Request,
    actor: Admin,
    db: DB,
):
    """批量删除关键词组。

    关联清理：先 delete KeywordGroupWord / KeywordGroupCity where keyword_group_id IN (...)，
    再 delete KeywordGroup where id IN (...)。

    部分 id 不存在 → 404 整体回滚（一致性优先）。

    关联 spec: docs/superpowers/specs/2026-08-13-settings-batch-delete-design.md §2.1
    """
    rows = db.scalars(select(KeywordGroup).where(KeywordGroup.id.in_(payload.ids))).all()
    if len(rows) != len(set(payload.ids)):
        raise HTTPException(404, "部分关键词组不存在，已取消")
    deleted_ids = [r.id for r in rows]
    db.execute(delete(KeywordGroupWord).where(KeywordGroupWord.keyword_group_id.in_(deleted_ids)))
    db.execute(delete(KeywordGroupCity).where(KeywordGroupCity.keyword_group_id.in_(deleted_ids)))
    for r in rows:
        db.delete(r)
    db.commit()
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="keyword_groups_batch_deleted",
        resource_type="keyword_group",
        target_label=f"batch of {len(deleted_ids)}",
        method="POST",
        path="/api/v1/settings/keyword-groups/batch-delete",
        status_code=200,
        client_ip=request.client.host if request.client else "127.0.0.1",
        extra={"deleted_ids": deleted_ids, "deleted_count": len(deleted_ids)},
    )
    return BatchDeleteOut(deleted_count=len(rows))


@router.patch("/settings/keyword-groups/{kg_id}")
def patch_keyword_group(kg_id: int, payload: KeywordGroupUpdateIn, _: Admin, db: DB) -> dict:
    """更新关键词组基础字段（name/description/enabled）。

    name 重名返回 409；其他字段为 None 时不动。
    """
    kg = db.get(KeywordGroup, kg_id)
    if kg is None:
        raise HTTPException(404, "关键词组不存在")
    if payload.name is not None and payload.name != kg.name:
        existing = db.scalar(select(KeywordGroup).where(KeywordGroup.name == payload.name))
        if existing:
            raise HTTPException(409, "关键词组名称已存在")
        kg.name = payload.name
    if payload.description is not None:
        kg.description = payload.description
    if payload.enabled is not None:
        kg.enabled = payload.enabled
    db.commit()
    db.refresh(kg)
    return {"code": 200, "message": "success", "data": _dump_keyword_group(db, kg)}
