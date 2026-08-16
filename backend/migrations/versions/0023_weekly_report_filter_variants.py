"""weekly_report_filter_variants: 周报按筛选组合区分

关联 TODO: 周报按 week+城市+关键词/博主组合区分
关联 spec: docs/superpowers/specs/2026-08-16-weekly-report-filter-variants-design.md

- weekly_reports.week 由 unique 改为普通索引（同一周允许多份）
- 新增 name / signature / keyword_group_ids / keywords / blogger_group_ids / blogger_ids
- 历史数据回填：name = 原 week，signature = week（保证旧数据可用）
"""

import json

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022_note_match_and_engagement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("weekly_reports")}

    if "name" not in cols:
        op.add_column("weekly_reports", sa.Column("name", sa.String(256), nullable=False, server_default=""))
    if "signature" not in cols:
        op.add_column("weekly_reports", sa.Column("signature", sa.String(512), nullable=False, server_default=""))
    if "keyword_group_ids" not in cols:
        op.add_column("weekly_reports", sa.Column("keyword_group_ids", sa.Text(), nullable=False, server_default="[]"))
    if "keywords" not in cols:
        op.add_column("weekly_reports", sa.Column("keywords", sa.Text(), nullable=False, server_default="[]"))
    if "blogger_group_ids" not in cols:
        op.add_column("weekly_reports", sa.Column("blogger_group_ids", sa.Text(), nullable=False, server_default="[]"))
    if "blogger_ids" not in cols:
        op.add_column("weekly_reports", sa.Column("blogger_ids", sa.Text(), nullable=False, server_default="[]"))

    # 历史数据：name = week，signature = week
    bind.execute(
        sa.text(
            "UPDATE weekly_reports SET name = week, signature = week "
            "WHERE name = '' OR signature = ''"
        )
    )

    # week 唯一索引 → 普通索引
    indexes = {ix["name"] for ix in sa.inspect(bind).get_indexes("weekly_reports")}
    if "ix_weekly_reports_week_unique" in indexes:
        op.drop_index("ix_weekly_reports_week_unique", table_name="weekly_reports")
    if "ix_weekly_reports_week" not in indexes:
        op.create_index("ix_weekly_reports_week", "weekly_reports", ["week"])
    if "ix_weekly_reports_signature" not in indexes:
        op.create_index("ix_weekly_reports_signature", "weekly_reports", ["signature"])


def downgrade() -> None:
    bind = op.get_bind()
    indexes = {ix["name"] for ix in sa.inspect(bind).get_indexes("weekly_reports")}
    if "ix_weekly_reports_signature" in indexes:
        op.drop_index("ix_weekly_reports_signature", table_name="weekly_reports")
    if "ix_weekly_reports_week" in indexes:
        op.drop_index("ix_weekly_reports_week", table_name="weekly_reports")
    if "ix_weekly_reports_week_unique" not in indexes:
        op.create_index("ix_weekly_reports_week_unique", "weekly_reports", ["week"], unique=True)
    for col in ("blogger_ids", "blogger_group_ids", "keywords", "keyword_group_ids", "signature", "name"):
        op.drop_column("weekly_reports", col)