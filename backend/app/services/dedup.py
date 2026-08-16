from difflib import SequenceMatcher
from typing import Any, Literal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.duplicate import NoteDuplicateCandidate
from app.models.note import Note


def similarity_score(left: dict[str, Any], right: dict[str, Any]) -> float:
    if left.get("city_code") != right.get("city_code"):
        return 0.0
    name = SequenceMatcher(None, str(left.get("name", "")), str(right.get("name", ""))).ratio()
    location = SequenceMatcher(None, str(left.get("location", "")), str(right.get("location", ""))).ratio()
    left_start = left.get("start_time")
    right_start = right.get("start_time")
    date_match = bool(left_start and right_start and str(left_start)[:10] == str(right_start)[:10])
    return round(name * 0.55 + location * 0.2 + (0.25 if date_match else 0), 4)


def classify_similarity(score: float) -> Literal["auto_merge", "manual_review", "distinct"]:
    if score >= 0.7:
        return "auto_merge"
    if score >= 0.4:
        return "manual_review"
    return "distinct"


def merge_activities(left: dict[str, Any], right: dict[str, Any], keep: Literal["a", "b"] = "a") -> dict[str, Any]:
    selected = dict(left if keep == "a" else right)
    note_ids = list(dict.fromkeys([*left.get("related_note_ids", []), *right.get("related_note_ids", [])]))
    selected["related_note_ids"] = note_ids
    selected.pop("status", None)
    return selected


def create_note_duplicate_candidates(db: Session, note: Note) -> list[NoteDuplicateCandidate]:
    created = []
    others = db.scalars(select(Note).where(Note.id != note.id, Note.city_code == note.city_code, Note.review_status.notin_(["DELETED", "MERGED"]))).all()
    for other in others:
        title_score = SequenceMatcher(None, note.title or "", other.title or "").ratio()
        content_score = SequenceMatcher(None, note.content or "", other.content or "").ratio()
        score = round(title_score * 0.65 + content_score * 0.35, 4)
        if score < 0.55:
            continue
        a, b = sorted((note.id, other.id))
        exists = db.scalar(select(NoteDuplicateCandidate).where(NoteDuplicateCandidate.note_a_id == a, NoteDuplicateCandidate.note_b_id == b))
        if exists:
            continue
        matched = [field for field, value in (("title", title_score), ("content", content_score)) if value >= 0.6]
        candidate = NoteDuplicateCandidate(note_a_id=a, note_b_id=b, similarity=score, matched_fields=matched, status="pending")
        db.add(candidate); created.append(candidate)
    return created
