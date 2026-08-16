from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.duplicate import DuplicateCandidate
from app.models.note import Note
from app.models.task import CrawlTask
from app.services.activity_window import ActivityWindow
from app.services.archive import archive_task_folder, write_activity_exports


@dataclass(frozen=True)
class CleanupSummary:
    scanned: int
    deleted: int
    retained: int
    task_ids: list[int]


def rebuild_task_activity_exports(db: Session, settings, task_id: int) -> None:
    task = db.get(CrawlTask, task_id)
    if task is None:
        return
    started_at = task.started_at or task.created_at
    city_code = (task.params or {}).get("city") or ""
    folders = set()
    if city_code:
        folders.add(archive_task_folder(settings.archive_dir, started_at, task_id, city_code))
    # 兼容旧版单层目录（archive/{date}/task-{id}）与新版城市/周目录
    folders.update(settings.archive_dir.glob(f"*/task-{task_id}"))
    folders.update(settings.archive_dir.glob(f"*/*/task-{task_id}"))
    activities = list(db.scalars(
        select(Activity)
        .join(Note, Note.id == Activity.note_id)
        .where(Note.task_id == task_id)
        .order_by(Activity.start_time.is_(None), Activity.start_time, Activity.id)
    ).all())
    notes = {note.id: note for note in db.scalars(select(Note).where(Note.task_id == task_id)).all()}
    for folder in folders:
        links: dict[int, list[str]] = {}
        for activity in activities:
            note = notes.get(activity.note_id)
            if note is None:
                continue
            values = []
            for index in activity.source_image_indexes or []:
                matches = sorted((folder / "images").glob(f"{note.platform_note_id}_{index:02d}.*"))
                if matches:
                    values.append(f"[来源图片 {index}](images/{matches[0].name})")
                else:
                    values.append(f"来源图片 {index}")
            links[activity.id or 0] = values
        write_activity_exports(folder, task_id, activities, links)


def cleanup_activity_dates(db: Session, settings, reference: datetime) -> CleanupSummary:
    window = ActivityWindow(reference, settings.activity_future_window_days, settings.celery_timezone)
    rows = list(db.scalars(select(Activity).where(Activity.note_id.is_not(None))).all())
    targets = [activity for activity in rows if window.classify(
        activity.start_time.isoformat() if activity.start_time else None,
        activity.end_time.isoformat() if activity.end_time else None,
    ) in {"past", "future"}]
    target_ids = [activity.id for activity in targets if activity.id is not None]
    task_ids = sorted(set(db.scalars(
        select(Note.task_id).where(Note.id.in_([activity.note_id for activity in rows]))
    ).all())) if rows else []
    if target_ids:
        db.execute(delete(DuplicateCandidate).where(or_(
            DuplicateCandidate.activity_a_id.in_(target_ids),
            DuplicateCandidate.activity_b_id.in_(target_ids),
            DuplicateCandidate.merged_activity_id.in_(target_ids),
        )))
        db.execute(delete(Activity).where(Activity.id.in_(target_ids)))
        db.commit()
    for task_id in task_ids:
        rebuild_task_activity_exports(db, settings, task_id)
    return CleanupSummary(
        scanned=len(rows),
        deleted=len(targets),
        retained=len(rows) - len(targets),
        task_ids=task_ids,
    )
