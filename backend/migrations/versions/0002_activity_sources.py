"""Add activity source note and image indexes."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _cols(table: str) -> set:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _idx(table: str) -> set:
    return {i["name"] for i in sa.inspect(op.get_bind()).get_indexes(table)}


def upgrade():
    cols = _cols("activities")
    with op.batch_alter_table("activities") as batch:
        if "note_id" not in cols:
            batch.add_column(sa.Column("note_id", sa.Integer(), nullable=True))
        if "source_image_indexes" not in cols:
            batch.add_column(sa.Column("source_image_indexes", sa.JSON(), nullable=False, server_default="[]"))
    if "ix_activities_note_id" not in _idx("activities"):
        op.create_index("ix_activities_note_id", "activities", ["note_id"])


def downgrade():
    with op.batch_alter_table("activities") as batch:
        batch.drop_index("ix_activities_note_id")
        batch.drop_column("source_image_indexes")
        batch.drop_column("note_id")
