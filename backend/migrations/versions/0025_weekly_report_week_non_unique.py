"""weekly_report_week_non_unique: 修正 weekly_reports.week 为普通索引

0023 想把 week 由 unique 改为普通索引以支持「同周多份」，但实际在 SQLite 上
创建成了唯一索引，导致插入同 week 的第二份周报报 UNIQUE constraint failed。

- 将 ix_weekly_reports_week 重建为非唯一索引
"""

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    indices = {ix["name"]: ix for ix in sa.inspect(bind).get_indexes("weekly_reports")}
    current = indices.get("ix_weekly_reports_week")
    if current is not None and current.get("unique"):
        op.drop_index("ix_weekly_reports_week", table_name="weekly_reports")
        op.create_index("ix_weekly_reports_week", "weekly_reports", ["week"])


def downgrade() -> None:
    bind = op.get_bind()
    indices = {ix["name"]: ix for ix in sa.inspect(bind).get_indexes("weekly_reports")}
    current = indices.get("ix_weekly_reports_week")
    if current is not None and not current.get("unique"):
        op.drop_index("ix_weekly_reports_week", table_name="weekly_reports")
        op.create_index("ix_weekly_reports_week", "weekly_reports", ["week"], unique=True)