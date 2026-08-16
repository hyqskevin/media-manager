"""城市配置 CRUD + 批量删除。

端点（URL 不变）：
- GET    /settings/cities
- POST   /settings/cities
- PUT    /settings/cities/{item_id}
- DELETE /settings/cities/{item_id}
- POST   /settings/cities/batch-delete
"""
from hashlib import sha1
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.models.blogger_city import BloggerCity
from app.models.config import City
from app.models.keyword_group import KeywordGroupCity
from app.services.audit import record_audit
from app.api.v1.settings._deps import (
    Admin,
    BatchDeleteIdsIn,
    BatchDeleteOut,
    DB,
)

router = APIRouter(tags=["settings"])
RecentFilter = Literal["不限", "一天内", "一周内", "半年内"]


class CityIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    recent_filter: RecentFilter = "一周内"
    enabled: bool = True


def _dump(item):
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}


def generate_city_code(name: str, db) -> str:
    base = f"city-{sha1(name.strip().encode('utf-8')).hexdigest()[:8]}"
    code = base
    suffix = 2
    while db.scalar(select(City.id).where(City.code == code)) is not None:
        code = f"{base[:29]}-{suffix}"
        suffix += 1
    return code


def dump_city(city: City, db) -> dict[str, object]:
    return _dump(city)


@router.get("/settings/cities")
def list_cities(_: Admin, db: DB):
    cities = db.scalars(select(City).order_by(City.id)).all()
    return {"code": 200, "message": "success", "data": [dump_city(city, db) for city in cities]}


@router.post("/settings/cities", status_code=status.HTTP_201_CREATED)
def create_city(payload: CityIn, _: Admin, db: DB):
    city = City(
        name=payload.name.strip(),
        code=generate_city_code(payload.name, db),
        recent_filter=payload.recent_filter,
        enabled=payload.enabled,
    )
    db.add(city)
    db.commit()
    db.refresh(city)
    return {"code": 201, "message": "success", "data": dump_city(city, db)}


@router.put("/settings/cities/{item_id}")
def update_city(item_id: int, payload: CityIn, _: Admin, db: DB):
    city = db.get(City, item_id)
    if city is None:
        raise HTTPException(404, "配置不存在")
    city.name = payload.name.strip()
    city.recent_filter = payload.recent_filter
    city.enabled = payload.enabled
    db.commit()
    db.refresh(city)
    return {"code": 200, "message": "success", "data": dump_city(city, db)}


@router.delete("/settings/cities/{item_id}")
def delete_city(item_id: int, _: Admin, db: DB):
    city = db.get(City, item_id)
    if city is not None:
        db.execute(delete(BloggerCity).where(BloggerCity.city_code == city.code))
        db.execute(delete(KeywordGroupCity).where(KeywordGroupCity.city_code == city.code))
        db.delete(city)
        db.commit()
    return {"code": 200, "message": "success", "data": {"id": item_id}}


@router.post("/settings/cities/batch-delete", response_model=BatchDeleteOut)
def batch_delete_cities(
    payload: BatchDeleteIdsIn,
    request: Request,
    actor: Admin,
    db: DB,
):
    """批量删除城市配置。

    关联清理：先 delete BloggerCity / KeywordGroupCity where city_code IN (...)，
    再 delete City where id IN (...)。

    部分 id 不存在 → 404 整体回滚（一致性优先）。

    关联 spec: docs/superpowers/specs/2026-08-13-settings-batch-delete-design.md §2.1
    """
    rows = db.scalars(select(City).where(City.id.in_(payload.ids))).all()
    if len(rows) != len(set(payload.ids)):
        raise HTTPException(404, "部分城市不存在，已取消")
    city_codes = [c.code for c in rows]
    deleted_ids = [c.id for c in rows]
    db.execute(delete(BloggerCity).where(BloggerCity.city_code.in_(city_codes)))
    db.execute(delete(KeywordGroupCity).where(KeywordGroupCity.city_code.in_(city_codes)))
    for c in rows:
        db.delete(c)
    db.commit()
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="cities_batch_deleted",
        resource_type="city",
        target_label=f"batch of {len(deleted_ids)}",
        method="POST",
        path="/api/v1/settings/cities/batch-delete",
        status_code=200,
        client_ip=request.client.host if request.client else "127.0.0.1",
        extra={"deleted_ids": deleted_ids, "deleted_count": len(deleted_ids)},
    )
    return BatchDeleteOut(deleted_count=len(rows))
