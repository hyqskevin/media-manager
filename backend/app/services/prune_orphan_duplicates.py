"""一次性脚本服务：把指向已不可见 note 的 pending 去重候选标为 superseded。

关联 spec: docs/superpowers/specs/2026-07-30-duplicates-orphan-candidates-design.md
"""
from datetime import datetime, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.models.duplicate import NoteDuplicateCandidate
from app.models.note import Note


_NOT_VISIBLE_STATUSES = ["DELETED", "MERGED"]


def prune_orphan_duplicates(db: Session) -> dict[str, int]:
    """返回 {pruned: N, kept: M, scanned: K}，幂等。"""
    pending_rows = db.scalars(
        select(NoteDuplicateCandidate).where(NoteDuplicateCandidate.status == "pending")
    ).all()
    pruned = 0
    kept = 0
    now = datetime.now(timezone.utc)
    for cand in pending_rows:
        a = db.get(Note, cand.note_a_id)
        b = db.get(Note, cand.note_b_id)
        if a is None or b is None or a.review_status in _NOT_VISIBLE_STATUSES or b.review_status in _NOT_VISIBLE_STATUSES:
            cand.status = "superseded"
            cand.resolved_at = now
            pruned += 1
        else:
            kept += 1
    db.commit()
    return {"pruned": pruned, "kept": kept, "scanned": len(pending_rows)}