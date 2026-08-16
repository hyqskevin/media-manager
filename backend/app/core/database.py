"""SQLAlchemy 数据库引擎 + Session 工厂。"""
from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

# 确保 SQLite data 目录存在
if settings.database_url.startswith("sqlite:///"):
    db_path = Path(settings.database_url.replace("sqlite:///", ""))
    db_path.parent.mkdir(parents=True, exist_ok=True)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base。所有模型继承自此类。"""


engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI 依赖注入：提供 Session 并自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()