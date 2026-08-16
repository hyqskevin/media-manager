"""Shared v0.3 services: risk config persistence + audit logging."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.system_config import SystemConfig

RISK_CONFIG_KEY = "risk_config"

DEFAULT_RISK_CONFIG: dict = {
    "nurture_global_enabled": False,
    "silent_hour_start": 0,
    "silent_hour_end": 6,
    "max_daily_seconds": 14400,
    "min_action_interval_s": 3,
    "max_likes_per_hour": 10,
    "max_likes_per_day": 50,
}


def get_risk_config(db: Session) -> dict:
    """Return the persisted risk config (falls back to defaults, seeds if missing)."""
    row = db.scalars(
        select(SystemConfig).where(SystemConfig.key == RISK_CONFIG_KEY)
    ).first()
    if row is None:
        cfg = dict(DEFAULT_RISK_CONFIG)
        db.add(SystemConfig(key=RISK_CONFIG_KEY, value=json.dumps(cfg)))
        db.commit()
        return cfg
    try:
        data = json.loads(row.value)
    except json.JSONDecodeError:
        data = {}
    merged = dict(DEFAULT_RISK_CONFIG)
    merged.update(data)
    return merged


def save_risk_config(db: Session, updates: dict) -> dict:
    """Merge updates into persisted risk config and commit."""
    cfg = get_risk_config(db)
    cfg.update(updates)
    row = db.scalars(
        select(SystemConfig).where(SystemConfig.key == RISK_CONFIG_KEY)
    ).first()
    if row is None:
        row = SystemConfig(key=RISK_CONFIG_KEY, value=json.dumps(cfg))
        db.add(row)
    else:
        row.value = json.dumps(cfg)
    db.commit()
    return cfg


def write_audit_log(
    db: Session,
    *,
    operator: str,
    action: str,
    entity_type: str = "",
    entity_id: int | None = None,
    changes: dict | None = None,
    ip: str = "",
    user_agent: str = "",
) -> AuditLog:
    """Persist an audit log entry (read-only trail)."""
    log = AuditLog(
        operator=operator,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes_json=json.dumps(changes or {}, ensure_ascii=False),
        ip=ip,
        user_agent=user_agent,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def now_utc() -> datetime:
    return datetime.now(timezone.utc)