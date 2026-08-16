"""deduplicate at note level"""

import sqlalchemy as sa
from alembic import op


revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "note_duplicate_candidates" not in inspector.get_table_names():
        op.create_table(
            "note_duplicate_candidates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("note_a_id", sa.Integer(), nullable=False),
            sa.Column("note_b_id", sa.Integer(), nullable=False),
            sa.Column("similarity", sa.Float(), nullable=False),
            sa.Column("matched_fields", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
            sa.Column("resolution", sa.String(length=32), nullable=True),
            sa.Column("kept_note_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("note_a_id", "note_b_id", name="uq_note_duplicate_pair"),
        )
        op.create_index("ix_note_duplicate_candidates_note_a_id", "note_duplicate_candidates", ["note_a_id"])
        op.create_index("ix_note_duplicate_candidates_note_b_id", "note_duplicate_candidates", ["note_b_id"])
        op.create_index("ix_note_duplicate_candidates_status", "note_duplicate_candidates", ["status"])
    elif not inspector.get_unique_constraints("note_duplicate_candidates"):
        with op.batch_alter_table("note_duplicate_candidates") as batch:
            batch.create_unique_constraint("uq_note_duplicate_pair", ["note_a_id", "note_b_id"])
    op.execute("UPDATE duplicate_candidates SET status='superseded' WHERE status='pending'")


def downgrade():
    op.drop_table("note_duplicate_candidates")
