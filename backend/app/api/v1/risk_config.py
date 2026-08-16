"""v0.3 risk-config endpoints (GET/PUT/reload) with audit logging."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.schemas.full_features import RiskConfigOut, RiskConfigUpdate
from app.services.full_features import (
    get_risk_config,
    save_risk_config,
    write_audit_log,
)

router = APIRouter(prefix="/risk-config", tags=["risk-config"])

Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[dict, Depends(require_admin)]


def _operator(admin) -> str:
    return getattr(admin, "username", "admin")


@router.get("", response_model=RiskConfigOut)
async def get_risk_config_endpoint(db: Db, _: Admin) -> RiskConfigOut:
    return RiskConfigOut(**get_risk_config(db))


@router.put("", response_model=RiskConfigOut)
async def update_risk_config(
    payload: RiskConfigUpdate,
    db: Db,
    admin: Admin,
    request: Request,
) -> RiskConfigOut:
    before = get_risk_config(db)
    updates = payload.model_dump(exclude_unset=True)
    cfg = save_risk_config(db, updates)
    write_audit_log(
        db,
        operator=_operator(admin),
        action="update_config",
        entity_type="config",
        changes={"before": before, "after": cfg},
        ip=request.client.host if request.client else "",
        user_agent=request.headers.get("user-agent", ""),
    )
    return RiskConfigOut(**cfg)


@router.post("/reload", response_model=RiskConfigOut)
async def reload_risk_config(db: Db, _: Admin) -> RiskConfigOut:
    """Re-read config (worker reloads on restart; returns live values)."""
    return RiskConfigOut(**get_risk_config(db))