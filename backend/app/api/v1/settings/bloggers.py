"""博主白名单 CRUD + 批量删除 + 导入/补充端点。

端点（URL 不变）：
- GET    /settings/bloggers/import-template
- POST   /settings/bloggers/import
- POST   /settings/bloggers/{item_id}/enrich
- POST   /settings/bloggers/batch-delete
- GET    /settings/bloggers   （通过 ``/{kind}`` 通用路由）
- POST   /settings/bloggers   （通过 ``/{kind}`` 通用路由）
- PUT    /settings/bloggers/{item_id}   （通过 ``/{kind}/{item_id}`` 通用路由）
- DELETE /settings/bloggers/{item_id}   （通过 ``/{kind}/{item_id}`` 通用路由）
"""
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.models.blogger_city import BloggerCity
from app.models.blogger_group import BloggerGroupMember
from app.models.config import Blogger, City
from app.services.audit import record_audit
from app.services.blogger_enricher import enrich_bloggers
from app.services.blogger_import import BloggerImportError, generate_blogger_template, import_bloggers
from app.services.opencli_adapter import OpenCLIAdapter
from app.api.v1.settings._deps import (
    Admin,
    BatchDeleteIdsIn,
    BatchDeleteOut,
    DB,
)
from app.core.config import get_settings as _get_settings

# Re-export so ``app.api.v1.settings.get_settings`` is monkeypatchable from tests.
get_settings = _get_settings

router = APIRouter(tags=["settings"])


class BloggerIn(BaseModel):
    platform_user_id: str | None = None
    username: str
    profile_url: str | None = None
    city_codes: list[str] = Field(default_factory=list)
    enabled: bool = True
    max_notes_per_crawl: int = Field(default=0, ge=0)


MODELS = {"bloggers": Blogger}
SCHEMAS = {"bloggers": BloggerIn}


def _dump(item):
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}


def _sync_blogger_cities(db, blogger_id: int, city_codes: list[str]) -> None:
    """全量替换某博主的城市绑定。"""
    db.execute(delete(BloggerCity).where(BloggerCity.blogger_id == blogger_id))
    for code in city_codes:
        if code:
            db.add(BloggerCity(blogger_id=blogger_id, city_code=code, enabled=True))


def _dump_blogger_with_cities(blogger: Blogger, db) -> dict:
    data = _dump(blogger)
    # outer join City 取 name；City 不存在时 name=None 兜底为 code
    city_rows = db.execute(
        select(BloggerCity.city_code, City.name)
        .outerjoin(City, City.code == BloggerCity.city_code)
        .where(BloggerCity.blogger_id == blogger.id)
        .order_by(BloggerCity.city_code)
    ).all()
    cities = [{"code": code, "name": name or code} for code, name in city_rows]
    data["city_codes"] = [c["code"] for c in cities]
    data["cities"] = cities
    return data


# ── 具体路径（必须在 ``/{kind}`` 之前注册，避免被通用路由吞掉） ──────────


@router.get("/settings/bloggers/import-template")
def download_blogger_import_template(_: Admin):
    return Response(
        generate_blogger_template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="blogger-import-template.xlsx"'},
    )


@router.post("/settings/bloggers/import", status_code=status.HTTP_201_CREATED)
async def import_blogger_settings(request: Request, filename: str, _: Admin, db: DB):
    content = await request.body()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(413, "导入文件不能超过 2 MiB")
    try:
        result = import_bloggers(db, content, filename)
    except BloggerImportError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"code": 201, "message": "success", "data": result}


@router.post("/settings/bloggers/{item_id}/enrich")
def enrich_blogger(item_id: int, _: Admin, db: DB):
    """按博主用户名调用 opencli search，回填 platform_user_id 与 profile_url。

    仅当 profile_url 为空时才需要补充；已配置完整的返回 200 + 不变数据。
    """
    item = db.get(Blogger, item_id)
    if item is None:
        raise HTTPException(404, "博主不存在")
    if (item.profile_url or "").strip():
        return {
            "code": 200,
            "message": "博主信息已完整，无需补充",
            "data": _dump_blogger_with_cities(item, db),
        }

    def runner(args: list[str]) -> list[dict]:
        # 关键：从包级命名空间查找，兼容测试中 monkeypatch 的写法
        from app.api.v1.settings import get_settings
        adapter = OpenCLIAdapter(get_settings())
        result = adapter.run(args)
        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "items" in result:
            return list(result["items"])
        return []

    try:
        filled = enrich_bloggers(db, [item], search_runner=runner, limit=5)
    except Exception as exc:
        raise HTTPException(503, f"补充失败：{exc}") from exc

    db.refresh(item)
    if not filled:
        raise HTTPException(422, f"未找到匹配 '{item.username}' 的博主主页")
    return {"code": 200, "message": "success", "data": _dump_blogger_with_cities(item, db)}


@router.post("/settings/bloggers/batch-delete", response_model=BatchDeleteOut)
def batch_delete_bloggers(
    payload: BatchDeleteIdsIn,
    request: Request,
    actor: Admin,
    db: DB,
):
    """批量删除博主白名单。

    关联清理：先 delete BloggerCity / BloggerGroupMember where blogger_id IN (...)，
    再 delete Blogger where id IN (...)。

    部分 id 不存在 → 404 整体回滚（一致性优先）。

    关联 spec: docs/superpowers/specs/2026-08-13-settings-batch-delete-design.md §2.1
    """
    rows = db.scalars(select(Blogger).where(Blogger.id.in_(payload.ids))).all()
    if len(rows) != len(set(payload.ids)):
        raise HTTPException(404, "部分博主不存在，已取消")
    deleted_ids = [r.id for r in rows]
    db.execute(delete(BloggerCity).where(BloggerCity.blogger_id.in_(deleted_ids)))
    db.execute(delete(BloggerGroupMember).where(BloggerGroupMember.blogger_id.in_(deleted_ids)))
    for r in rows:
        db.delete(r)
    db.commit()
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="bloggers_batch_deleted",
        resource_type="blogger",
        target_label=f"batch of {len(deleted_ids)}",
        method="POST",
        path="/api/v1/settings/bloggers/batch-delete",
        status_code=200,
        client_ip=request.client.host if request.client else "127.0.0.1",
        extra={"deleted_ids": deleted_ids, "deleted_count": len(deleted_ids)},
    )
    return BatchDeleteOut(deleted_count=len(rows))


# ── 通用 ``/{kind}`` 路由（kind 仅支持 "bloggers"） ────────────────────────


@router.get("/settings/{kind}")
def list_settings(kind: Literal["bloggers"], _: Admin, db: DB):
    if kind == "bloggers":
        rows = db.scalars(select(Blogger).order_by(Blogger.id)).all()
        return {
            "code": 200,
            "message": "success",
            "data": [_dump_blogger_with_cities(b, db) for b in rows],
        }
    rows = db.scalars(select(MODELS[kind]).order_by(MODELS[kind].id)).all()
    return {"code": 200, "message": "success", "data": [_dump(row) for row in rows]}


@router.post("/settings/{kind}", status_code=status.HTTP_201_CREATED)
def create_setting(kind: Literal["bloggers"], payload: dict, _: Admin, db: DB):
    data = SCHEMAS[kind].model_validate(payload)
    fields = data.model_dump()
    if kind == "bloggers":
        city_codes = fields.pop("city_codes", [])
        fields.pop("city_code", None)  # 兼容旧字段（如有）
        item = Blogger(**fields)
    else:
        item = MODELS[kind](**fields)
    db.add(item)
    db.flush()
    if kind == "bloggers":
        _sync_blogger_cities(db, item.id, city_codes)
    db.commit()
    db.refresh(item)
    if kind == "bloggers":
        return {"code": 201, "message": "success", "data": _dump_blogger_with_cities(item, db)}
    return {"code": 201, "message": "success", "data": _dump(item)}


@router.put("/settings/{kind}/{item_id}")
def update_setting(kind: Literal["bloggers"], item_id: int, payload: dict, _: Admin, db: DB):
    item = db.get(MODELS[kind], item_id)
    if item is None:
        raise HTTPException(404, "配置不存在")
    data = SCHEMAS[kind].model_validate(payload)
    fields = data.model_dump()
    if kind == "bloggers":
        city_codes = fields.pop("city_codes", None)
        fields.pop("city_code", None)
        for key, value in fields.items():
            setattr(item, key, value)
        if city_codes is not None:
            _sync_blogger_cities(db, item.id, city_codes)
    else:
        for key, value in fields.items():
            setattr(item, key, value)
    db.commit()
    db.refresh(item)
    if kind == "bloggers":
        return {"code": 200, "message": "success", "data": _dump_blogger_with_cities(item, db)}
    return {"code": 200, "message": "success", "data": _dump(item)}


@router.delete("/settings/{kind}/{item_id}")
def delete_setting(kind: Literal["bloggers"], item_id: int, _: Admin, db: DB):
    item = db.get(MODELS[kind], item_id)
    if item is not None:
        if kind == "bloggers":
            db.execute(delete(BloggerCity).where(BloggerCity.blogger_id == item.id))
            db.execute(delete(BloggerGroupMember).where(BloggerGroupMember.blogger_id == item.id))
        db.delete(item)
        db.commit()
    return {"code": 200, "message": "success", "data": {"id": item_id}}
