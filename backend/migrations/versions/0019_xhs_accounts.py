"""新增 xhs_accounts 表（多小红书账号配置）

关联 TODO: 多小红书账号配置 + 抓取失效自动切换
关联 spec: docs/superpowers/specs/2026-08-10-multi-xhs-account-design.md

- 每行对应一个 opencli session（Chrome profile），按 priority 升序选用
- run_crawl 中某账号 AuthenticationRequired/VerificationRequired 时切换到下一个
"""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "xhs_accounts" not in existing_tables:
        op.create_table(
            "xhs_accounts",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("remark", sa.String(256), nullable=False, server_default=""),
            sa.Column("session_name", sa.String(64), nullable=False, unique=True),
            sa.Column("login_status", sa.String(16), nullable=False, server_default="unknown"),
            sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.true()),
            sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_xhs_accounts_session_name", "xhs_accounts", ["session_name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_xhs_accounts_session_name", table_name="xhs_accounts")
    op.drop_table("xhs_accounts")
