"""删除 legacy keywords 表

关联 TODO: 废弃 legacy keywords 表，关键词统一由 keyword_groups 管理
关联 spec: docs/superpowers/specs/2026-08-10-keyword-group-cleanup-and-bugfix-design.md

- 关键词组表（keyword_groups/keyword_group_words/keyword_group_cities）已存完整数据
- legacy keywords 表与关键词组数据重复，直接 drop
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "keywords" in inspector.get_table_names():
        op.drop_table("keywords")


def downgrade() -> None:
    # 重建 legacy keywords 表（仅结构，数据不可恢复）
    op.create_table(
        "keywords",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("word", sa.String(128), nullable=False),
        sa.Column("city_code", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default="1"),
    )
    op.create_index("ix_keywords_city_code", "keywords", ["city_code"])
