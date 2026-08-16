from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.core.config import get_settings
from app.core.database import Base
from app.models import activity, audit, blogger_city, blogger_group, config, duplicate, group, keyword_group, note, poster, report, schedule, search_usage, task, user, xhs_account  # noqa: F401

configuration = context.config
if configuration.config_file_name: fileConfig(configuration.config_file_name)
configuration.set_main_option("sqlalchemy.url", get_settings().effective_database_url)
target_metadata = Base.metadata

def run_migrations_offline():
    context.configure(url=configuration.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction(): context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(configuration.get_section(configuration.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction(): context.run_migrations()

run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
