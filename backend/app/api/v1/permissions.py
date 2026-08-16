"""权限字典 API。

关联 spec: docs/superpowers/specs/2026-08-12-system-admin-design.md §3.1
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_permission
from app.models.group import Permission


router = APIRouter(prefix="/permissions", tags=["permissions"])


DB = Annotated[Session, Depends(get_db)]


class PermissionOut(BaseModel):
    id: int
    code: str
    description: str | None
    is_builtin: bool


@router.get("", response_model=list[PermissionOut])
def list_permissions(
    _: Annotated[dict, Depends(require_permission("users:read"))],
    db: DB,
):
    rows = db.query(Permission).order_by(Permission.id).all()
    return [
        PermissionOut(
            id=p.id, code=p.code, description=p.description, is_builtin=p.is_builtin,
        )
        for p in rows
    ]