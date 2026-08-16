"""v0.2 platform accounts + favorite snapshots + initial users table

v0.2 fresh start: drops all legacy xhs-info-crawl tables and creates the v0.2
schema (users + platform_accounts + favorite_snapshots).

Revision ID: 0026
Revises: None  (this is the new base revision)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0026"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0. users table (admin auth)
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    # 1. platform_accounts
    op.create_table(
        "platform_accounts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("session_name", sa.String(64), nullable=False, unique=True),
        sa.Column("platform_user_id", sa.String(64), nullable=True),
        sa.Column("cdp_port", sa.Integer, nullable=True, unique=True),
        sa.Column("login_status", sa.String(16), nullable=False, server_default="unknown"),
        sa.Column("last_login_check_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
        sa.Column("daily_quota_seconds", sa.Integer, nullable=False, server_default="14400"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_platform_accounts_platform", "platform_accounts", ["platform"])
    op.create_index("ix_platform_accounts_session_name", "platform_accounts", ["session_name"])
    op.create_index("ix_platform_accounts_platform_user_id", "platform_accounts", ["platform_user_id"])
    op.create_index("ix_platform_accounts_cdp_port", "platform_accounts", ["cdp_port"])

    # 2. favorite_snapshots
    op.create_table(
        "favorite_snapshots",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("account_id", sa.Integer, sa.ForeignKey("platform_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("item_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("items_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_index("ix_favorite_snapshots_account_id", "favorite_snapshots", ["account_id"])
    op.create_index("ix_favorite_snapshots_account_captured", "favorite_snapshots", ["account_id", "captured_at"])


def downgrade() -> None:
    op.drop_index("ix_favorite_snapshots_account_captured", table_name="favorite_snapshots")
    op.drop_index("ix_favorite_snapshots_account_id", table_name="favorite_snapshots")
    op.drop_table("favorite_snapshots")

    op.drop_index("ix_platform_accounts_cdp_port", table_name="platform_accounts")
    op.drop_index("ix_platform_accounts_platform_user_id", table_name="platform_accounts")
    op.drop_index("ix_platform_accounts_session_name", table_name="platform_accounts")
    op.drop_index("ix_platform_accounts_platform", table_name="platform_accounts")
    op.drop_table("platform_accounts")

    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")