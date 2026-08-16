"""搜索周配额用量表

关联 TODO: 抓取频率控制落地（SPEC P1）
关联 spec: docs/superpowers/specs/2026-07-25-crawl-rate-limit-design.md

- 新增 search_usage：按 ISO 周（week_key，如 "2026-W30"）全局累计关键词搜索次数；
- 配合 settings.weekly_search_limit（默认 500/周）在 run_crawl 中超限跳过。
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "search_usage" not in set(sa.inspect(op.get_bind()).get_table_names()):
        op.create_table(
            "search_usage",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("week_key", sa.String(8), nullable=False, unique=True),
            sa.Column("count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_search_usage_week_key", "search_usage", ["week_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_search_usage_week_key", table_name="search_usage")
    op.drop_table("search_usage")
