"""add skipped crawl note progress"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    if "skipped_notes" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("crawl_tasks")}:
        op.add_column("crawl_tasks", sa.Column("skipped_notes", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("crawl_tasks", "skipped_notes")
