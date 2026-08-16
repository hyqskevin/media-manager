"""一次性回填脚本：从小红书 note ID 反算 published_at。

扫描 `notes` 表里 published_at IS NULL 且 platform_note_id 是 24 hex 的记录，用
`app.services.note_id_published_at` 反算并写回。

幂等：published_at 已经是 None 的才回填；已经写过的不会再覆盖。
输出 before/after 统计，便于审计。
"""
import json
import sys

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.note import Note
from app.services.note_id_published_at import note_id_published_at


def run_migration(db) -> dict:
    before_nulls = db.scalar(select(func.count()).select_from(Note).where(Note.published_at.is_(None))) or 0
    fixed = 0
    skipped_no_id = 0
    notes = db.execute(
        select(Note).where(Note.published_at.is_(None), Note.platform_note_id.is_not(None))
    ).scalars()
    for note in notes:
        ts = note_id_published_at(note.platform_note_id)
        if ts is None:
            skipped_no_id += 1
            continue
        note.published_at = ts
        fixed += 1
    db.commit()
    after_nulls = db.scalar(select(func.count()).select_from(Note).where(Note.published_at.is_(None))) or 0
    return {
        "before_nulls": before_nulls,
        "fixed": fixed,
        "skipped_no_id": skipped_no_id,
        "after_nulls": after_nulls,
    }


def main() -> None:
    db = SessionLocal()
    try:
        stats = run_migration(db)
        print(json.dumps(stats, ensure_ascii=False))
    finally:
        db.close()


if __name__ == "__main__":
    main()
