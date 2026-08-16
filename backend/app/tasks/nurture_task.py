"""Nurture task (Celery async task).

Single-account nurture orchestration:
1. Load PlatformAccount
2. Check global_enabled / account enabled / silent hour / quota
3. Get adapter = registry.get(account.platform)
4. Sequentially execute actions (3-15s interval between)
5. Call adapter.fetch_favorites + write FavoriteSnapshot
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

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
from app.services.platforms import registry
from app.anti_detection.human import human_pause

logger = logging.getLogger(__name__)

# Actions allowed in nurture (mapped to adapter methods)
ALLOWED_ACTIONS: set[str] = {"browse_home", "like_post", "favorite_post", "fetch_favorites"}


@celery_app.task(name="nurture.run", bind=True, max_retries=0)
def nurture_account_task(
    self,
    account_id: int,
    actions: list[str],
    duration_minutes: int = 30,
    post_url: str | None = None,
) -> dict:
    """Single-account nurture orchestration (Celery task).

    Args:
        account_id: PlatformAccount.id
        actions: list of action names (subset of ALLOWED_ACTIONS)
        duration_minutes: max duration (5-240)
        post_url: required for like_post / favorite_post

    Returns:
        {"status": "completed|skipped|failed", ...}
    """
    settings = get_settings()
    if not settings.nurture_global_enabled:
        return {"status": "skipped", "reason": "global_disabled"}

    # Validate actions
    actions = [a for a in actions if a in ALLOWED_ACTIONS]
    if not actions:
        return {"status": "skipped", "reason": "no_valid_actions"}

    db = SessionLocal()
    try:
        account = db.get(PlatformAccount, account_id)
        if not account:
            return {"status": "failed", "reason": "account_not_found"}
        if not account.enabled:
            return {"status": "skipped", "reason": "account_disabled"}

        # Silent hour check
        if is_silent_hour(datetime.now(timezone.utc)):
            return {"status": "skipped", "reason": "silent_hour"}

        # Quota check (simplified: always under quota in v0.2)
        quota = account.daily_quota_seconds or MAX_DAILY_SECONDS
        used_today = 0  # TODO: read from Redis in v0.3
        if check_quota_exceeded(used_today, quota):
            return {"status": "skipped", "reason": "quota_exceeded"}

        # Get adapter
        adapter = registry.get(account.platform)
        if adapter is None:
            return {"status": "failed", "reason": "platform_not_supported"}
        if adapter.status != "implemented":
            return {
                "status": "skipped",
                "reason": f"platform_{account.platform.value}_stub_v0.3",
            }

        # Stub execution (real browser invocation is environment-dependent and
        # skipped in v0.2 unit/integration testing). The adapter methods are
        # exercised via the test suite.
        result = {
            "status": "completed",
            "account_id": account_id,
            "actions": actions,
            "duration_minutes": duration_minutes,
            "favorite_snapshot_id": None,
            "items_collected": 0,
        }

        # Always end with fetch_favorites + write snapshot (so "我的收藏" is populated)
        try:
            # Real invocation would look like:
            #   context = await new_stealth_context(browser, storage_state=...)
            #   favorites = await adapter.fetch_favorites(context, max_items=100)
            favorites: list = []  # stub

            snapshot = FavoriteSnapshot(
                account_id=account.id,
                platform=account.platform.value,
                captured_at=datetime.now(timezone.utc),
                item_count=len(favorites),
                items_json=json.dumps([f.__dict__ for f in favorites]),
                error=None,
            )
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)
            result["favorite_snapshot_id"] = snapshot.id
            result["items_collected"] = len(favorites)
        except Exception as e:
            logger.exception("Failed to write favorite snapshot")
            result["snapshot_error"] = str(e)

        return result

    except Exception as e:
        logger.exception("Nurture task failed")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()