"""Celery app initialization (v0.2)."""
from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "media-manager",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
)

# Auto-discover tasks in app.tasks package
celery_app.autodiscover_tasks(["app.tasks"])