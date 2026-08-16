"""allow unknown activity dates and count skipped activities"""

import sqlalchemy as sa
from alembic import op


revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("activities") as batch:
        batch.alter_column("start_time", existing_type=sa.DateTime(), nullable=True)
    if "skipped_activities" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("crawl_tasks")}:
        op.add_column(
            "crawl_tasks",
            sa.Column("skipped_activities", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade():
    op.drop_column("crawl_tasks", "skipped_activities")
    with op.batch_alter_table("activities") as batch:
        batch.alter_column("start_time", existing_type=sa.DateTime(), nullable=False)
