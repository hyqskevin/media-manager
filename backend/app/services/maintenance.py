import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.security import hash_password
from app.models.user import User

def create_admin(db: Session, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        user = User(username=username, password_hash="", role="admin")
        db.add(user)
    user.password_hash = hash_password(password); user.role = "admin"
    db.commit(); db.refresh(user); return user

def backup_sqlite(database: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"app-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
    shutil.copy2(database, target); return target

def cleanup_runtime_files(directories: list[Path], older_than_days: int = 90) -> list[Path]:
    cutoff = datetime.now(timezone.utc).timestamp() - timedelta(days=older_than_days).total_seconds()
    removed=[]
    for directory in directories:
        for path in directory.rglob("*") if directory.exists() else []:
            if path.is_file() and path.stat().st_mtime <= cutoff:
                path.unlink(); removed.append(path)
    return removed
