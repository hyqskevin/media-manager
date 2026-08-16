"""add crawl task progress fields"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("crawl_tasks")}
    if "downloaded_notes" not in cols:
        op.add_column("crawl_tasks", sa.Column("downloaded_notes", sa.Integer(), nullable=False, server_default="0"))
    if "ocr_notes" not in cols:
        op.add_column("crawl_tasks", sa.Column("ocr_notes", sa.Integer(), nullable=False, server_default="0"))
    if "extracted_notes" not in cols:
        op.add_column("crawl_tasks", sa.Column("extracted_notes", sa.Integer(), nullable=False, server_default="0"))
    if "current_stage" not in cols:
        op.add_column("crawl_tasks", sa.Column("current_stage", sa.String(length=32), nullable=True))
    if "current_note" not in cols:
        op.add_column("crawl_tasks", sa.Column("current_note", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("crawl_tasks", "current_note")
    op.drop_column("crawl_tasks", "current_stage")
    op.drop_column("crawl_tasks", "extracted_notes")
    op.drop_column("crawl_tasks", "ocr_notes")
    op.drop_column("crawl_tasks", "downloaded_notes")
