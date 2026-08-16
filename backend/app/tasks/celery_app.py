from celery import Celery
from celery.schedules import crontab

from app.core.config import Settings, get_settings


def create_celery_app(settings: Settings) -> Celery:
    settings.ensure_runtime_directories()
    queue_folder = settings.celery_folder / "queue"
    processed_folder = settings.celery_folder / "processed"

    app = Celery("xhs_info_crawl", broker=settings.celery_broker_url)
    app.conf.update(
        broker_transport_options={
            "data_folder_in": str(queue_folder),
            "data_folder_out": str(queue_folder),
            "data_folder_processed": str(processed_folder),
        },
        imports=("app.tasks.health", "app.tasks.crawl_task"),
        timezone=settings.celery_timezone,
        enable_utc=True,
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        beat_schedule={
            "scheduled-crawl-dispatch": {
                "task": "app.tasks.crawl_task.scheduled_dispatch",
                "schedule": crontab(minute="*"),
            }
        },
    )
    return app


celery_app = create_celery_app(get_settings())
