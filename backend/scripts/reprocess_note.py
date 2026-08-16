import argparse
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.activity import Activity
from app.models.note import Note, NoteImage
from app.models.task import CrawlTask
from app.services.archive import archive_task_result, resolve_storage_path
from app.services.dedup import create_duplicate_candidates
from app.services.extraction import extract_activities
from app.services.minimax import MiniMaxClient


def parse_time(value, fallback=None):
    if not value:
        return fallback
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def main():
    parser = argparse.ArgumentParser(description="Re-extract all concrete activities from an existing OCR note")
    parser.add_argument("note_id", type=int)
    parser.add_argument("--archive-only", action="store_true", help="Rebuild files from already extracted activities without calling MiniMax")
    args = parser.parse_args()
    settings = get_settings(); db = SessionLocal()
    try:
        note = db.get(Note, args.note_id)
        if note is None: raise SystemExit(f"note {args.note_id} not found")
        task = db.get(CrawlTask, note.task_id)
        images = list(db.scalars(select(NoteImage).where(NoteImage.note_id == note.id).order_by(NoteImage.id)).all())
        created=list(db.scalars(select(Activity).where(Activity.note_id==note.id).order_by(Activity.id)).all())
        if not args.archive_only:
            combined = f"标题：{note.title}\n正文：{note.content}\n" + "\n".join(f"[IMAGE {index}]\n{image.ocr_text}" for index, image in enumerate(images, 1) if image.ocr_text)
            fields_list = extract_activities(combined, datetime.now(timezone.utc), MiniMaxClient(settings).extract_many)
            db.execute(delete(Activity).where(Activity.source_url == note.source_url))
            db.flush(); created = []
            for fields in fields_list:
                activity = Activity(
                note_id=note.id,
                name=fields["name"],
                city_code=note.city_code,
                start_time=parse_time(fields.get("start_time"), datetime.now(timezone.utc)),
                end_time=parse_time(fields.get("end_time")),
                location=fields.get("location") or "",
                price=fields.get("price") or "",
                type=fields.get("type") or "其他",
                source_url=note.source_url,
                source_image_indexes=fields.get("source_image_indexes") or [],
                summary=fields.get("summary") or "",
                confidence=float(fields.get("confidence") or 0),
                )
                db.add(activity); db.flush(); create_duplicate_candidates(db, activity); created.append(activity)
        image_rows=[]
        for image in images:
            path=resolve_storage_path(settings.data_dir,settings.image_dir,image.storage_key)
            if path.exists(): image_rows.append((path,image))
        started_at=(task.started_at if task else None) or note.created_at
        folder=archive_task_result(settings.archive_dir,started_at,note.task_id,note,image_rows,created)
        db.commit()
        print({"note_id":note.id,"activities":len(created),"archive":str(folder),"names":[item.name for item in created]})
    finally:
        db.close()


if __name__ == "__main__":
    main()
