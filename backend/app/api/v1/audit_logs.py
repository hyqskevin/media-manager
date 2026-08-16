"""v0.3 audit-log endpoints (read-only list / detail / export)."""
from __future__ import annotations

import csv
import io
import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.audit_log import AuditLog
from app.schemas.full_features import AuditLogOut, AuditLogPage

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])

Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[dict, Depends(require_admin)]


def _out(a: AuditLog) -> AuditLogOut:
    try:
        changes = json.loads(a.changes_json or "{}")
    except json.JSONDecodeError:
        changes = {}
    return AuditLogOut(
        id=a.id, created_at=a.created_at, operator=a.operator, action=a.action,
        entity_type=a.entity_type, entity_id=a.entity_id, changes=changes,
        ip=a.ip, user_agent=a.user_agent,
    )


@router.get("", response_model=AuditLogPage)
async def list_audit_logs(
    db: Db,
    _: Admin,
    operator: str | None = Query(default=None),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AuditLogPage:
    query = select(AuditLog)
    if operator:
        query = query.where(AuditLog.operator == operator)
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    query = query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size))
    return AuditLogPage(
        total=total, page=page, page_size=page_size, items=[_out(a) for a in items]
    )


@router.get("/export")
async def export_audit_logs(
    db: Db, _: Admin, operator: str | None = Query(default=None),
    action: str | None = Query(default=None),
) -> Response:
    query = select(AuditLog)
    if operator:
        query = query.where(AuditLog.operator == operator)
    if action:
        query = query.where(AuditLog.action == action)
    logs = db.scalars(query.order_by(AuditLog.created_at.desc()))
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "created_at", "operator", "action", "entity_type", "entity_id", "ip"])
    for a in logs:
        writer.writerow([a.id, a.created_at, a.operator, a.action, a.entity_type,
                         a.entity_id or "", a.ip or ""])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs.csv"},
    )


@router.get("/{log_id}", response_model=AuditLogOut)
async def get_audit_log(log_id: int, db: Db, _: Admin) -> AuditLogOut:
    a = db.get(AuditLog, log_id)
    if not a:
        raise HTTPException(status_code=404, detail="audit_log_not_found")
    return _out(a)