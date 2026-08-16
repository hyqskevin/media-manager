"""定时抓取任务与博主分组表

关联 TODO: 定时任务调度 + 博主分组 + 仪表盘抓取统计
关联 spec: docs/superpowers/specs/2026-07-25-scheduled-crawls-and-dashboard-charts-design.md

- 新增 blogger_groups / blogger_group_members（白名单博主分组，成员多对多，级联删除）；
- 新增 scheduled_crawls（每周几 + 时间的定时抓取配置，JSON 存储关键词组/博主组 id 列表，
  last_fired_slot 用于 dispatcher 幂等）。
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "blogger_groups" not in existing_tables:
        op.create_table(
            "blogger_groups",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(128), nullable=False, unique=True),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_blogger_groups_name", "blogger_groups", ["name"], unique=True)

    if "blogger_group_members" not in existing_tables:
        op.create_table(
            "blogger_group_members",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("group_id", sa.Integer, sa.ForeignKey("blogger_groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("blogger_id", sa.Integer, sa.ForeignKey("bloggers.id", ondelete="CASCADE"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("group_id", "blogger_id", name="uq_bg_member"),
        )
        op.create_index("ix_blogger_group_members_group_id", "blogger_group_members", ["group_id"])
        op.create_index("ix_blogger_group_members_blogger_id", "blogger_group_members", ["blogger_id"])

    if "scheduled_crawls" not in existing_tables:
        op.create_table(
            "scheduled_crawls",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("day_of_week", sa.Integer, nullable=False),
            sa.Column("hour", sa.Integer, nullable=False),
            sa.Column("minute", sa.Integer, nullable=False),
            sa.Column("city_code", sa.String(32), nullable=False),
            sa.Column("keyword_group_ids", sa.JSON, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("blogger_group_ids", sa.JSON, nullable=False, server_default=sa.text("'[]'")),
            sa.Column("recent_filter", sa.String(16), nullable=True),
            sa.Column("last_fired_slot", sa.String(16), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_scheduled_crawls_city_code", "scheduled_crawls", ["city_code"])


def downgrade() -> None:
    op.drop_index("ix_scheduled_crawls_city_code", table_name="scheduled_crawls")
    op.drop_table("scheduled_crawls")
    op.drop_index("ix_blogger_group_members_blogger_id", table_name="blogger_group_members")
    op.drop_index("ix_blogger_group_members_group_id", table_name="blogger_group_members")
    op.drop_table("blogger_group_members")
    op.drop_index("ix_blogger_groups_name", table_name="blogger_groups")
    op.drop_table("blogger_groups")
