"""v0.3 notification endpoints (list / mark read / read-all / unread-count)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.notification import Notification
from app.schemas.full_features import NotificationOut, NotificationPage, UnreadCountOut

router = APIRouter(prefix="/notifications", tags=["notifications"])

Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[dict, Depends(require_admin)]


def _out(n: Notification) -> NotificationOut:
    return NotificationOut(
        id=n.id, severity=n.severity, title=n.title, body=n.body,
        related_entity_type=n.related_entity_type, related_entity_id=n.related_entity_id,
        created_at=n.created_at, read_at=n.read_at, is_read=n.is_read,
    )


@router.get("", response_model=NotificationPage)
async def list_notifications(
    db: Db,
    _: Admin,
    is_read: bool | None = Query(default=None),
    severity: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> NotificationPage:
    query = select(Notification)
    if is_read is not None:
        query = query.where(
            Notification.read_at.is_not(None) if is_read else Notification.read_at.is_(None)
        )
    if severity:
        query = query.where(Notification.severity == severity)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    query = query.order_by(Notification.created_at.desc(), Notification.id.desc())
    items = db.scalars(query.offset((page - 1) * page_size).limit(page_size))
    return NotificationPage(
        total=total, page=page, page_size=page_size, items=[_out(n) for n in items]
    )


@router.patch("/{notification_id}/read", response_model=NotificationOut)
async def mark_notification_read(notification_id: int, db: Db, _: Admin) -> NotificationOut:
    n = db.get(Notification, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="notification_not_found")
    if not n.is_read:
        n.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(n)
    return _out(n)


@router.post("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(db: Db, _: Admin, is_read: bool | None = None) -> dict:
    now = datetime.now(timezone.utc)
    if is_read is False:
        # Re-open unread for testing conveniences; default marks all read.
        db.execute(update(Notification).values(read_at=None))
    else:
        db.execute(
            update(Notification)
            .where(Notification.read_at.is_(None))
            .values(read_at=now)
        )
    db.commit()
    return {"ok": True}


@router.get("/unread-count", response_model=UnreadCountOut)
async def notifications_unread_count(db: Db, _: Admin) -> UnreadCountOut:
    count = db.scalar(
        select(func.count()).select_from(Notification).where(Notification.read_at.is_(None))
    ) or 0
    return UnreadCountOut(unread=count)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: int, db: Db, _: Admin) -> None:
    n = db.get(Notification, notification_id)
    if not n:
        raise HTTPException(status_code=404, detail="notification_not_found")
    db.delete(n)
    db.commit()