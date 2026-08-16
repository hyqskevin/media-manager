"""count notes in weekly reports"""

import sqlalchemy as sa
from alembic import op


revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    if "note_count" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("weekly_reports")}:
        op.add_column("weekly_reports", sa.Column("note_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("weekly_reports", "note_count")
