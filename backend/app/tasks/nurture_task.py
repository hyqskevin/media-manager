"""Nurture task (Celery async task).

Single-account nurture orchestration:
1. Load PlatformAccount
2. Check global_enabled / account enabled / silent hour / quota
3. Get adapter = registry.get(account.platform)
4. Sequentially execute actions via REAL browser automation (patchright)
5. End with fetch_favorites → write FavoriteSnapshot (REAL items, not hard-coded [])

Browser launching is isolated into `_run_browser_actions` so tests can monkeypatch
it without needing a real Chromium binary.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from app.anti_detection.policy import (
    is_silent_hour,
    check_quota_exceeded,
    MAX_DAILY_SECONDS,
    MIN_ACTION_INTERVAL_S,
)
from app.tasks.celery_app import celery_app  # noqa: F401  (registers task)
from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.platform_account import PlatformAccount, FavoriteSnapshot
from app.models.nurture_task import NurtureTask, NurtureActionLog
from app.models.notification import Notification
from app.services.platforms import registry
from app.services.platforms.base import FavoriteItem
from app.anti_detection.human import human_pause
from app.anti_detection.context import new_stealth_context

logger = logging.getLogger(__name__)

# Actions allowed in nurture (mapped to adapter methods)
ALLOWED_ACTIONS: set[str] = {"browse_home", "like_post", "favorite_post", "fetch_favorites"}

# Project-internal storage_state directory (AGENTS.md: never use /tmp)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = ROOT_DIR / "data" / "storage_states"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Map action -> adapter method name
ACTION_TO_METHOD: dict[str, str] = {
    "browse_home": "browse_home",
    "like_post": "like_post",
    "favorite_post": "favorite_post",
    "fetch_favorites": "fetch_favorites",
}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _storage_state_path(session_name: str) -> Path | None:
    """Resolve storage_state json path for a session. Returns None if missing."""
    p = STORAGE_DIR / f"{session_name}.json"
    return p if p.exists() else None


def update_task(task_id: int | None, **fields) -> None:
    """Persist status/progress on a NurtureTask record (no-op when task_id is None).

    Emits a Notification when a task transitions to `failed`.
    """
    if task_id is None:
        return
    db = SessionLocal()
    try:
        task = db.get(NurtureTask, task_id)
        if not task:
            return
        for k, v in fields.items():
            setattr(task, k, v)
        db.commit()
        if fields.get("status") == "failed":
            db.add(Notification(
                severity="critical",
                title="养号任务失败",
                body=f"账号 #{task.account_id} 养号失败：{fields.get('error') or '未知错误'}",
                related_entity_type="task",
                related_entity_id=task.id,
            ))
            db.commit()
    finally:
        db.close()


def append_action_log(
    task_id: int | None, action: str, sequence: int, status: str,
    *, error: str | None = None,
) -> None:
    """Persist a per-action NurtureActionLog row (no-op when task_id is None)."""
    if task_id is None:
        return
    db = SessionLocal()
    try:
        now = _now_utc()
        db.add(NurtureActionLog(
            task_id=task_id, action=action, status=status, sequence=sequence,
            started_at=now, finished_at=now if status != "running" else None,
            result_json="{}", error=error,
        ))
        db.commit()
    finally:
        db.close()


async def _run_adapter_actions_async(
    adapter, storage_state: Path | None, actions: list[str],
    post_url: str | None, duration_minutes: int, max_items: int,
) -> list[FavoriteItem]:
    """Real browser automation: launch patchright chromium, run actions sequentially,
    return the favorites list (real, not hard-coded []).

    Raises if any step fails fatally; per-action errors are caught by the caller.
    """
    # Lazy import to keep test env light (patchright not needed for unit tests)
    from patchright.async_api import async_playwright  # noqa: PLC0415

    favorites: list[FavoriteItem] = []
    async with async_playwright() as p:
        # Headless unless XHS_NURTURE_HEADED=1 (debug / visible browser)
        headed = os.environ.get("XHS_NURTURE_HEADED") == "1"
        browser = await p.chromium.launch(
            headless=not headed,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--lang=zh-CN",
                "--no-sandbox",
            ],
        )
        context = await new_stealth_context(
            browser,
            storage_state=str(storage_state) if storage_state else None,
            headless=not headed,
        )
        try:
            for action in actions:
                method_name = ACTION_TO_METHOD.get(action)
                if not method_name:
                    continue
                method = getattr(adapter, method_name, None)
                if method is None:
                    logger.warning("Adapter %s missing method %s", adapter.platform, method_name)
                    continue

                if action == "browse_home":
                    await method(context, duration_seconds=duration_minutes * 60 // max(len(actions), 1))
                elif action in {"like_post", "favorite_post"}:
                    if post_url:
                        await method(context, post_url)
                elif action == "fetch_favorites":
                    favorites = await method(context, max_items=max_items)
        finally:
            await context.close()
            await browser.close()
    return favorites


def _run_browser_actions(
    adapter, storage_state: Path | None, actions: list[str],
    post_url: str | None, duration_minutes: int, max_items: int,
) -> list[FavoriteItem]:
    """Synchronous wrapper around `_run_adapter_actions_async` for Celery worker."""
    return asyncio.run(_run_adapter_actions_async(
        adapter, storage_state, actions, post_url, duration_minutes, max_items,
    ))


@celery_app.task(name="nurture.run", bind=True, max_retries=0)
def nurture_account_task(
    self,
    account_id: int,
    actions: list[str],
    duration_minutes: int = 30,
    post_url: str | None = None,
    task_id: int | None = None,
) -> dict:
    """Single-account nurture orchestration (Celery task)."""
    settings = get_settings()
    if not settings.nurture_global_enabled:
        return {"status": "skipped", "reason": "global_disabled"}

    actions = [a for a in actions if a in ALLOWED_ACTIONS]
    if not actions:
        update_task(task_id, status="skipped", finished_at=_now_utc())
        return {"status": "skipped", "reason": "no_valid_actions"}

    db = SessionLocal()
    try:
        account = db.get(PlatformAccount, account_id)
        if not account:
            update_task(task_id, status="failed", error="account_not_found",
                        finished_at=_now_utc())
            return {"status": "failed", "reason": "account_not_found"}
        if not account.enabled:
            update_task(task_id, status="skipped", finished_at=_now_utc())
            return {"status": "skipped", "reason": "account_disabled"}

        if is_silent_hour(datetime.now(timezone.utc)):
            update_task(task_id, status="skipped", finished_at=_now_utc())
            return {"status": "skipped", "reason": "silent_hour"}

        quota = account.daily_quota_seconds or MAX_DAILY_SECONDS
        used_today = 0  # TODO: read from Redis in v0.3
        if check_quota_exceeded(used_today, quota):
            update_task(task_id, status="skipped", finished_at=_now_utc())
            return {"status": "skipped", "reason": "quota_exceeded"}

        adapter = registry.get(account.platform)
        if adapter is None:
            update_task(task_id, status="failed", error="platform_not_supported",
                        finished_at=_now_utc())
            return {"status": "failed", "reason": "platform_not_supported"}
        if adapter.status != "implemented":
            reason = f"platform_{account.platform.value}_stub_v0.3"
            update_task(task_id, status="skipped", finished_at=_now_utc())
            return {"status": "skipped", "reason": reason}

        storage_state = _storage_state_path(account.session_name)

        # Real record lifecycle
        now = _now_utc()
        update_task(
            task_id,
            status="running",
            started_at=now,
            current_action=actions[0] if actions else None,
            progress_pct=10,
        )
        for seq, action in enumerate(actions):
            append_action_log(task_id, action, seq, "running")

        # REAL browser automation (this is the heart of the change)
        result = {
            "status": "completed",
            "account_id": account_id,
            "actions": actions,
            "duration_minutes": duration_minutes,
            "favorite_snapshot_id": None,
            "items_collected": 0,
        }
        favorites: list[FavoriteItem] = []
        snapshot_error: str | None = None

        try:
            favorites = _run_browser_actions(
                adapter=adapter,
                storage_state=storage_state,
                actions=actions,
                post_url=post_url,
                duration_minutes=duration_minutes,
                max_items=100,
            )
        except Exception as e:
            logger.exception("Browser automation failed")
            snapshot_error = str(e)
            update_task(
                task_id, status="failed", error=str(e), finished_at=_now_utc()
            )
            return {"status": "failed", "error": str(e)}

        # Mark each action as completed (or failed if snapshot_error)
        for seq, action in enumerate(actions):
            err = snapshot_error if action == "fetch_favorites" and snapshot_error else None
            append_action_log(task_id, action, seq, "failed" if err else "completed",
                              error=err)

        # Persist REAL favorites to DB
        try:
            snapshot = FavoriteSnapshot(
                account_id=account.id,
                platform=account.platform.value,
                captured_at=_now_utc(),
                item_count=len(favorites),
                items_json=json.dumps([f.__dict__ for f in favorites]),
                error=snapshot_error,
            )
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)
            result["favorite_snapshot_id"] = snapshot.id
            result["items_collected"] = len(favorites)
        except Exception as e:
            logger.exception("Failed to write favorite snapshot")
            result["snapshot_error"] = str(e)

        update_task(
            task_id,
            status="completed",
            finished_at=_now_utc(),
            progress_pct=100,
            items_collected=result["items_collected"],
        )
        return result

    except Exception as e:
        logger.exception("Nurture task failed")
        update_task(task_id, status="failed", error=str(e), finished_at=_now_utc())
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()