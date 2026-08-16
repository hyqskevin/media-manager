"""海报模板与海报任务表

关联 TODO: 海报生成（按 docs/海报制作.md）
关联 spec: docs/superpowers/specs/2026-07-21-poster-generation-design.md

- 新增 poster_templates / poster_tasks 两张表；
- poster_templates.id -> poster_tasks.template_id (FK ON DELETE RESTRICT)；
- poster_tasks.items 是 JSON 列表，每条形如
  {"type": "note"|"activity", "id": int, "title": str,
   "fields": {time_range, location, fee, content},
   "image_url": str}。
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "poster_templates" not in existing_tables:
        op.create_table(
            "poster_templates",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(128), nullable=False, unique=True),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("html_template", sa.Text, nullable=False),
            sa.Column("css_text", sa.Text, nullable=True),
            sa.Column("thumbnail_path", sa.String(512), nullable=True),
            sa.Column("parsed_meta", sa.JSON, nullable=True),
            sa.Column("source", sa.String(32), nullable=False, server_default="manual"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_poster_templates_name", "poster_templates", ["name"], unique=True)

    if "poster_tasks" not in existing_tables:
        op.create_table(
            "poster_tasks",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
            sa.Column("template_id", sa.Integer, sa.ForeignKey("poster_templates.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("items", sa.JSON, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("override_html", sa.Text, nullable=True),
            sa.Column("output_path", sa.String(512), nullable=True),
            sa.Column("output_format", sa.String(16), nullable=False, server_default="png"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_poster_tasks_status", "poster_tasks", ["status"])
        op.create_index("ix_poster_tasks_template_id", "poster_tasks", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_poster_tasks_template_id", table_name="poster_tasks")
    op.drop_index("ix_poster_tasks_status", table_name="poster_tasks")
    op.drop_table("poster_tasks")
    op.drop_index("ix_poster_templates_name", table_name="poster_templates")
    op.drop_table("poster_templates")
