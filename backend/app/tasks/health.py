from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.health.ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}
