from datetime import datetime, timezone

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.activity_cleanup import cleanup_activity_dates


def main() -> None:
    db = SessionLocal()
    try:
        summary = cleanup_activity_dates(db, get_settings(), datetime.now(timezone.utc))
        print(
            f"scanned={summary.scanned} deleted={summary.deleted} "
            f"retained={summary.retained} task_ids={summary.task_ids}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
