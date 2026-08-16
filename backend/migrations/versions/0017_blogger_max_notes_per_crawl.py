"""博主抓取数量上限

关联 TODO: 配置中心博主白名单支持每个博主抓取数量上限
关联 spec: docs/superpowers/specs/2026-08-03-blogger-max-notes-per-crawl-design.md

- 新增 bloggers.max_notes_per_crawl 列，默认 0 表示不限制。
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {col["name"] for col in sa.inspect(op.get_bind()).get_columns("bloggers")}
    if "max_notes_per_crawl" not in columns:
        op.add_column("bloggers", sa.Column("max_notes_per_crawl", sa.Integer, nullable=False, server_default="0"))


def downgrade() -> None:
    columns = {col["name"] for col in sa.inspect(op.get_bind()).get_columns("bloggers")}
    if "max_notes_per_crawl" in columns:
        op.drop_column("bloggers", "max_notes_per_crawl")