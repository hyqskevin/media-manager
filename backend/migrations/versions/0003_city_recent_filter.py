"""add per-city XHS recent filter"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    if "recent_filter" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("cities")}:
        op.add_column("cities", sa.Column("recent_filter", sa.String(length=16), nullable=False, server_default="一周内"))


def downgrade():
    op.drop_column("cities", "recent_filter")
