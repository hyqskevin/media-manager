from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def create_database_engine(settings: Settings) -> Engine:
    connect_args = {"check_same_thread": False} if settings.effective_database_url.startswith("sqlite") else {}
    return create_engine(settings.effective_database_url, connect_args=connect_args)


settings = get_settings()
engine = create_database_engine(settings)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_database(app_settings: Settings | None = None) -> None:
    from app.models import activity, audit, blogger_city, blogger_group, config, duplicate, group, keyword_group, note, poster, report, schedule, search_usage, task, user, xhs_account  # noqa: F401

    selected_settings = app_settings or settings
    selected_settings.ensure_runtime_directories()
    selected_engine = engine if app_settings is None else create_database_engine(selected_settings)
    with selected_engine.begin() as connection:
        connection.execute(text("SELECT 1"))
    Base.metadata.create_all(selected_engine)
    if app_settings is not None:
        selected_engine.dispose()


def get_db() -> Generator[Session, None, None]:
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
