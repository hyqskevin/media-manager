"""一次性清理脚本：清空活动级 duplicate_candidates 死数据（TODO#5 方案 A）。

背景：去重已收敛推文维度（note_duplicate_candidates），活动级候选表无任何
API/UI 消费且已停写。本脚本清空存量，幂等可重复执行。

用法：
    python -m scripts.cleanup_duplicate_candidates --dry-run   # 只报计数
    python -m scripts.cleanup_duplicate_candidates             # 正式清理
"""
import argparse
import json

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.models.duplicate import DuplicateCandidate


def run_cleanup(db, *, dry_run: bool = False) -> dict:
    before = db.scalar(select(func.count()).select_from(DuplicateCandidate)) or 0
    if not dry_run and before:
        db.query(DuplicateCandidate).delete()
        db.commit()
    after = 0 if not dry_run else before
    if not dry_run:
        after = db.scalar(select(func.count()).select_from(DuplicateCandidate)) or 0
    return {"dry_run": dry_run, "before": before, "deleted": before if not dry_run else 0, "after": after}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="只报计数不删除")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        print(json.dumps(run_cleanup(db, dry_run=args.dry_run), ensure_ascii=False))
    finally:
        db.close()


if __name__ == "__main__":
    main()
