"""一次性 CLI：把指向已不可见 note 的 pending 去重候选标为 superseded。"""
from app.core.database import SessionLocal
from app.services.prune_orphan_duplicates import prune_orphan_duplicates


def main() -> None:
    db = SessionLocal()
    try:
        result = prune_orphan_duplicates(db)
        print(f"scanned={result['scanned']} pruned={result['pruned']} kept={result['kept']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()