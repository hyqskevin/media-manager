"""platform-accounts CRUD + check-login + nurture + favorites endpoints (v0.2)."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin
from app.models.nurture_task import NurtureTask
from app.models.platform_account import FavoriteSnapshot, PlatformAccount, PlatformType
from app.schemas.platform_account import (
    CheckLoginResultOut,
    FavoriteSnapshotOut,
    NurtureRequest,
    NurtureTaskCreated,
    PlatformAccountCreate,
    PlatformAccountOut,
    PlatformAccountUpdate,
)
from app.services.platforms import registry
from app.tasks.nurture_task import nurture_account_task

router = APIRouter(prefix="/platform-accounts", tags=["platform-accounts"])

Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[dict, Depends(require_admin)]


def _get_account_or_404(db: Session, account_id: int) -> PlatformAccount:
    account = db.get(PlatformAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="account_not_found")
    return account


@router.get("", response_model=list[PlatformAccountOut])
async def list_platform_accounts(
    db: Db,
    _: Admin,
    platform: PlatformType | None = Query(default=None),
) -> list[PlatformAccount]:
    """List accounts, optionally filtered by ?platform=xhs."""
    query = select(PlatformAccount).order_by(PlatformAccount.priority.desc(), PlatformAccount.id)
    if platform is not None:
        query = query.where(PlatformAccount.platform == platform)
    return list(db.scalars(query))


@router.post("", response_model=PlatformAccountOut, status_code=status.HTTP_201_CREATED)
async def create_platform_account(
    payload: PlatformAccountCreate,
    db: Db,
    _: Admin,
) -> PlatformAccount:
    """Create an account (name + platform). session_name auto-generated unique."""
    account = PlatformAccount(
        name=payload.name,
        platform=payload.platform,
        session_name=f"{payload.platform.value}-{uuid.uuid4().hex[:12]}",
        enabled=payload.enabled,
        priority=payload.priority,
        daily_quota_seconds=payload.daily_quota_seconds,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.put("/{account_id}", response_model=PlatformAccountOut)
async def update_platform_account(
    account_id: int,
    payload: PlatformAccountUpdate,
    db: Db,
    _: Admin,
) -> PlatformAccount:
    """Update enabled / priority / daily_quota_seconds / name."""
    account = _get_account_or_404(db, account_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(account, field, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_platform_account(
    account_id: int,
    db: Db,
    _: Admin,
) -> None:
    """Delete an account (cascades to favorite_snapshots)."""
    account = _get_account_or_404(db, account_id)
    db.delete(account)
    db.commit()


@router.post("/{account_id}/check-login", response_model=CheckLoginResultOut)
def check_login(
    account_id: int,
    db: Db,
    _: Admin,
) -> CheckLoginResultOut:
    """Real login check: launch stealth browser with stored storage_state and
    invoke adapter.check_login(context). Updates DB login_status accordingly.

    NOTE: this is a *synchronous* route so we can use asyncio.run; the request
    blocks until the real browser finishes (typically 5-15s).
    """
    import asyncio
    from app.tasks.nurture_task import _storage_state_path  # noqa: PLC0415
    from patchright.async_api import async_playwright  # noqa: PLC0415
    from app.anti_detection.context import new_stealth_context  # noqa: PLC0415

    account = _get_account_or_404(db, account_id)
    adapter = registry.get(account.platform)
    if adapter is None:
        raise HTTPException(status_code=400, detail="platform_not_supported")

    if adapter.status == "stub":
        # No real check; echo stored status (consistent with old behaviour for stubs)
        return CheckLoginResultOut(logged_in=account.login_status == "valid", error="")

    storage_state = _storage_state_path(account.session_name)

    async def _run() -> CheckLoginResultOut:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled",
                      "--lang=zh-CN", "--no-sandbox"],
            )
            context = await new_stealth_context(
                browser, storage_state=str(storage_state) if storage_state else None,
                headless=True,
            )
            try:
                result = await adapter.check_login(context)
                return CheckLoginResultOut(
                    logged_in=result.logged_in,
                    user_id=result.user_id or account.platform_user_id or "",
                    nickname=result.nickname or "",
                    error=result.error or "",
                )
            finally:
                await context.close()
                await browser.close()

    try:
        out = asyncio.run(_run())
    except Exception as e:
        out = CheckLoginResultOut(logged_in=False, error=str(e))

    # Persist result back to DB (login_status + platform_user_id if returned)
    account.login_status = "valid" if out.logged_in else "cookie_invalid"
    if out.user_id:
        account.platform_user_id = out.user_id
    account.last_login_check_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(account)
    return out


@router.post("/{account_id}/nurture", response_model=NurtureTaskCreated)
async def enqueue_nurture(
    account_id: int,
    payload: NurtureRequest,
    db: Db,
    _: Admin,
) -> NurtureTaskCreated:
    """Asynchronously enqueue a nurture task; writes a real NurtureTask record.

    The record is created as `pending` and its status is driven by the Celery
    worker (running -> completed/failed/skipped), so it shows up on the
    执行中 / 历史 pages immediately.
    """
    account = _get_account_or_404(db, account_id)
    actions = [a.value for a in payload.actions]
    record = NurtureTask(
        celery_task_id="",  # backfilled after dispatch
        account_id=account_id,
        platform=account.platform.value,
        actions_json=json.dumps(actions),
        duration_minutes=payload.duration_minutes,
        status="pending",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    async_result = nurture_account_task.delay(
        account_id=account_id,
        actions=actions,
        duration_minutes=payload.duration_minutes,
        post_url=payload.post_url,
        task_id=record.id,
    )
    record.celery_task_id = async_result.id
    db.commit()
    return NurtureTaskCreated(task_id=async_result.id)


@router.get("/{account_id}/favorites", response_model=FavoriteSnapshotOut)
async def latest_favorite_snapshot(
    account_id: int,
    db: Db,
    _: Admin,
) -> FavoriteSnapshotOut:
    """Return the most recent favorite snapshot for an account (404 if none)."""
    _get_account_or_404(db, account_id)
    snapshot = db.scalars(
        select(FavoriteSnapshot)
        .where(FavoriteSnapshot.account_id == account_id)
        .order_by(FavoriteSnapshot.captured_at.desc())
        .limit(1)
    ).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="no_snapshot")
    return _to_snapshot_out(snapshot)


@router.get("/{account_id}/favorites/history", response_model=list[FavoriteSnapshotOut])
async def favorite_snapshot_history(
    account_id: int,
    db: Db,
    _: Admin,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[FavoriteSnapshotOut]:
    """Paginated favorite snapshot history for an account."""
    _get_account_or_404(db, account_id)
    snapshots = db.scalars(
        select(FavoriteSnapshot)
        .where(FavoriteSnapshot.account_id == account_id)
        .order_by(FavoriteSnapshot.captured_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_to_snapshot_out(s) for s in snapshots]


def _to_snapshot_out(snapshot: FavoriteSnapshot) -> FavoriteSnapshotOut:
    try:
        items = json.loads(snapshot.items_json or "[]")
    except json.JSONDecodeError:
        items = []
    return FavoriteSnapshotOut(
        id=snapshot.id,
        account_id=snapshot.account_id,
        platform=PlatformType(snapshot.platform),
        captured_at=snapshot.captured_at,
        item_count=snapshot.item_count,
        items=items,
        error=snapshot.error,
    )