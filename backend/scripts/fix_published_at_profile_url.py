"""一次性矫正脚本：修复博主链接笔记的错误 published_at（TODO#14）。

根因：旧版 `note_id_published_at` 对 /user/profile/<uid>/<noteid> 链接取第一个
24hex（用户 ID），解出的是博主注册时间而非笔记发布时间。修复后的函数取路径
最后一个 24hex（笔记 ID）。本脚本用修复后的函数对 profile 链接笔记重算并写回。

幂等：重算值与库存值相同则跳过；explore/search_result 链接行为不变不受影响。
用法：
    python -m scripts.fix_published_at_profile_url --dry-run   # 只统计不写库
    python -m scripts.fix_published_at_profile_url             # 正式矫正
"""
import argparse
import json
from datetime import timezone

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.note import Note
from app.services.note_id_published_at import note_id_published_at


def _naive_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def run_fix(db, *, dry_run: bool = False) -> dict:
    notes = db.execute(
        select(Note).where(Note.source_url.like("%/user/profile/%"))
    ).scalars().all()
    scanned = len(notes)
    updated = 0
    unchanged = 0
    unparseable = 0
    for note in notes:
        recomputed = note_id_published_at(note.source_url)
        if recomputed is None:
            unparseable += 1
            continue
        if _naive_utc(recomputed) == _naive_utc(note.published_at):
            unchanged += 1
            continue
        if not dry_run:
            note.published_at = recomputed
        updated += 1
    if not dry_run:
        db.commit()
    return {
        "dry_run": dry_run,
        "scanned_profile_url_notes": scanned,
        "updated": updated,
        "unchanged": unchanged,
        "unparseable": unparseable,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只统计不写库")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        print(json.dumps(run_fix(db, dry_run=args.dry_run), ensure_ascii=False))
    finally:
        db.close()


if __name__ == "__main__":
    main()
