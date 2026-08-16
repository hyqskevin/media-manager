"""xhs_accounts 加 cdp_port 列（ChromePool 分配的 CDP 端口）

关联 spec: docs/superpowers/specs/2026-08-12-chrome-pool-design.md

- 每个 Xhs_account 可独立绑定到 ChromePool 启动的独立 Chrome 实例
- cdp_port 为该 Chrome 实例的 --remote-debugging-port
- crawler 通过 OPENCLI_CDP_ENDPOINT=http://127.0.0.1:<cdp_port> 路由到对应实例
- cdp_port 为 None 表示走默认 Chrome Browser Bridge（向后兼容）
- 唯一约束避免端口冲突
"""

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020_system_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    existing_cols = {c["name"] for c in inspector.get_columns("xhs_accounts")}
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("xhs_accounts")}
    if "cdp_port" not in existing_cols:
        with op.batch_alter_table("xhs_accounts") as batch:
            batch.add_column(sa.Column("cdp_port", sa.Integer, nullable=True))
        if "ix_xhs_accounts_cdp_port" not in existing_indexes:
            op.create_index(
                "ix_xhs_accounts_cdp_port",
                "xhs_accounts",
                ["cdp_port"],
                unique=True,
            )


def downgrade() -> None:
    op.drop_index("ix_xhs_accounts_cdp_port", table_name="xhs_accounts")
    with op.batch_alter_table("xhs_accounts") as batch:
        batch.drop_column("cdp_port")