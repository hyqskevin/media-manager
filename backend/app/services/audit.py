"""操作审计：record_audit 帮助函数。

失败降级：写不进 DB 时只 logger.warning，不影响主业务。
"""
import json
import logging
from typing import Any

from app.core.database import SessionLocal
from app.models.audit import AuditLog


logger = logging.getLogger(__name__)


# 模块级别名，方便测试 patch 拦截（unittest.mock.patch 路径为
# "app.services.audit._SessionLocal"）。直接 patch 原
# app.core.database.SessionLocal 在跨模块时易碎。
_SessionLocal = SessionLocal


def record_audit(
    *,
    actor_user_id: int | None,
    actor_username: str,
    action: str,
    method: str,
    path: str,
    status_code: int,
    client_ip: str,
    resource_type: str | None = None,
    resource_id: int | None = None,
    target_label: str | None = None,
    user_agent: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """写入一条审计日志。失败时 WARN，不抛异常。"""
    extra_json = json.dumps(extra, ensure_ascii=False) if extra is not None else None
    try:
        with _SessionLocal() as session:
            session.add(AuditLog(
                actor_user_id=actor_user_id,
                actor_username=actor_username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                target_label=target_label,
                method=method,
                path=path,
                status_code=status_code,
                client_ip=client_ip,
                user_agent=user_agent,
                extra=extra_json,
            ))
            session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit log write failed: %s", exc)