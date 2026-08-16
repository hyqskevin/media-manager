"""add note review state and merge target"""

import sqlalchemy as sa
from alembic import op


revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    note_cols = {c["name"] for c in sa.inspect(bind).get_columns("notes")}
    if "review_status" not in note_cols:
        op.add_column("notes", sa.Column("review_status", sa.String(length=32), nullable=False, server_default="PENDING"))
    if "merged_into_note_id" not in note_cols:
        op.add_column("notes", sa.Column("merged_into_note_id", sa.Integer(), nullable=True))
    if "ix_notes_review_status" not in {i["name"] for i in sa.inspect(bind).get_indexes("notes")}:
        op.create_index("ix_notes_review_status", "notes", ["review_status"], unique=False)
    # 存量数据回填仅对 0011 之前的旧 schema（activities.status 仍存在）有意义；
    # 全新建库按当前模型建表、本无 status 列，跳过。
    activity_cols = {c["name"] for c in sa.inspect(bind).get_columns("activities")}
    if "status" in activity_cols:
        op.execute("UPDATE notes SET review_status='APPROVED' WHERE id NOT IN (SELECT DISTINCT note_id FROM activities WHERE status IN ('RAW','NEEDS_REVIEW'))")


def downgrade():
    op.drop_index("ix_notes_review_status", table_name="notes")
    op.drop_column("notes", "merged_into_note_id")
    op.drop_column("notes", "review_status")
