"""操作日志查询/批量删除 API。

关联 spec:
- docs/superpowers/specs/2026-08-12-system-admin-design.md §3.3 (GET)
- docs/superpowers/specs/2026-08-13-admin-feature-batch-design.md §2.1 (DELETE)
"""
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import require_permission
from app.models.audit import AuditLog
from app.services.audit import record_audit


# 防审计黑洞：5 秒窗口内的日志视为「当前 session 刚产生」，不允许通过本次 DELETE 删除
_RECENT_SKIP_WINDOW = timedelta(seconds=5)


router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


class AuditLogOut(BaseModel):
    id: int
    actor_user_id: int | None
    actor_username: str
    action: str
    resource_type: str | None
    resource_id: int | None
    target_label: str | None
    method: str
    path: str
    status_code: int
    client_ip: str
    user_agent: str | None
    extra: str | None
    created_at: datetime


class AuditLogPage(BaseModel):
    total: int
    items: list[AuditLogOut]


@router.get("", response_model=AuditLogPage)
def list_audit_logs(
    actor_username: str | None = Query(None),
    action: list[str] | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    _: Annotated[dict, Depends(require_permission("users:manage"))] = None,
    db=Depends(get_db),
):
    stmt = select(AuditLog)
    count_stmt = select(AuditLog)
    if actor_username:
        stmt = stmt.where(AuditLog.actor_username.contains(actor_username))
        count_stmt = count_stmt.where(AuditLog.actor_username.contains(actor_username))
    if action:
        stmt = stmt.where(AuditLog.action.in_(action))
        count_stmt = count_stmt.where(AuditLog.action.in_(action))
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= date_from)
        count_stmt = count_stmt.where(AuditLog.created_at >= date_from)
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= date_to)
        count_stmt = count_stmt.where(AuditLog.created_at <= date_to)
    total = len(db.execute(count_stmt).scalars().all())
    rows = (
        db.execute(stmt.order_by(AuditLog.id.desc()).offset((page - 1) * size).limit(size))
        .scalars()
        .all()
    )
    return AuditLogPage(
        total=total,
        items=[
            AuditLogOut(
                id=r.id, actor_user_id=r.actor_user_id, actor_username=r.actor_username,
                action=r.action, resource_type=r.resource_type, resource_id=r.resource_id,
                target_label=r.target_label, method=r.method, path=r.path,
                status_code=r.status_code, client_ip=r.client_ip,
                user_agent=r.user_agent, extra=r.extra, created_at=r.created_at,
            ) for r in rows
        ],
    )


class AuditLogDeleteIn(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)


class AuditLogDeleteOut(BaseModel):
    deleted_count: int


@router.delete("", response_model=AuditLogDeleteOut)
def delete_audit_logs(
    payload: AuditLogDeleteIn,
    request: Request,
    actor: Annotated[dict, Depends(require_permission("users:manage"))],
    db=Depends(get_db),
):
    """批量删除审计日志。

    防审计黑洞：created_at 在 5 秒窗口内的行（视为本次 session 刚产生的记录）不删除；
    其余 id 即使不存在也静默忽略（仅按真实命中的行数返回 deleted_count）。

    关联 spec: docs/superpowers/specs/2026-08-13-admin-feature-batch-design.md §2.1
    """
    cutoff = datetime.now(timezone.utc) - _RECENT_SKIP_WINDOW
    # 只删 id 命中且 created_at 早于 5s 窗口的行
    target_ids = set(payload.ids)
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.id.in_(target_ids))
        .filter(AuditLog.created_at < cutoff)
        .all()
    )
    deleted_ids: list[int] = []
    for row in rows:
        deleted_ids.append(row.id)
        db.delete(row)
    db.commit()
    client_ip = request.client.host if request.client else "127.0.0.1"
    record_audit(
        actor_user_id=None,
        actor_username=actor["username"],
        action="audit_logs_deleted",
        resource_type="audit_log",
        target_label=f"batch of {len(deleted_ids)}",
        method="DELETE",
        path="/api/v1/audit-logs",
        status_code=200,
        client_ip=client_ip,
        extra={"deleted_ids": deleted_ids, "deleted_count": len(deleted_ids)},
    )
    return AuditLogDeleteOut(deleted_count=len(deleted_ids))