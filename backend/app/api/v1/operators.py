"""v0.3 operator endpoints (current operator / password change / audit export)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, require_admin, verify_password
from app.models.user import User
from app.schemas.full_features import OperatorMeOut, PasswordChange
from app.services.full_features import write_audit_log

router = APIRouter(prefix="/operators", tags=["operators"])

Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]


@router.get("/me", response_model=OperatorMeOut)
async def get_me(admin: Admin) -> OperatorMeOut:
    return OperatorMeOut(id=admin.id, username=admin.username, is_admin=admin.is_admin)


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    payload: PasswordChange, db: Db, admin: Admin, request: Request
) -> dict:
    if not verify_password(payload.old_password, admin.password_hash):
        raise HTTPException(status_code=400, detail="old_password_incorrect")
    admin.password_hash = hash_password(payload.new_password)
    db.commit()
    write_audit_log(
        db, operator=admin.username, action="change_password", entity_type="user",
        entity_id=admin.id, ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    return {"ok": True}