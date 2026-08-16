"""add per-execution crawl run token"""

import sqlalchemy as sa
from alembic import op


revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "run_token" not in {c["name"] for c in sa.inspect(bind).get_columns("crawl_tasks")}:
        op.add_column("crawl_tasks", sa.Column("run_token", sa.String(length=36), nullable=True))
    if "ix_crawl_tasks_run_token" not in {i["name"] for i in sa.inspect(bind).get_indexes("crawl_tasks")}:
        op.create_index("ix_crawl_tasks_run_token", "crawl_tasks", ["run_token"], unique=False)


def downgrade():
    op.drop_index("ix_crawl_tasks_run_token", table_name="crawl_tasks")
    op.drop_column("crawl_tasks", "run_token")
