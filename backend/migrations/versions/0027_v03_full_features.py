"""v0.3 full features: system_config + nurture_tasks + nurture_action_logs +
nurture_action_sets + nurture_schedules + notifications + audit_logs +
login_check_logs. Adds seed risk_config row.

Revision ID: 0027
Revises: 0026
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. system_config (key-value)
    op.create_table(
        "system_config",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.Text, nullable=False, server_default="{}"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.execute(
        sa.text(
            "INSERT INTO system_config (key, value) VALUES (:key, :value)"
        ).bindparams(
            key="risk_config",
            value=(
                '{"nurture_global_enabled":false,"silent_hour_start":0,'
                '"silent_hour_end":6,"max_daily_seconds":14400,'
                '"min_action_interval_s":3,"max_likes_per_hour":10,'
                '"max_likes_per_day":50}'
            ),
        )
    )

    # 2. nurture_tasks
    op.create_table(
        "nurture_tasks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("celery_task_id", sa.String(64), nullable=False, unique=True),
        sa.Column("account_id", sa.Integer, sa.ForeignKey("platform_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("actions_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("current_action", sa.String(32), nullable=True),
        sa.Column("progress_pct", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("items_collected", sa.Integer, nullable=False, server_default="0"),
        sa.Column("action_set_id", sa.Integer, nullable=True),
        sa.Column("triggered_by_schedule_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_nurture_tasks_celery_task_id", "nurture_tasks", ["celery_task_id"], unique=True)
    op.create_index("ix_nurture_tasks_account_id", "nurture_tasks", ["account_id"])
    op.create_index("ix_nurture_tasks_platform", "nurture_tasks", ["platform"])
    op.create_index("ix_nurture_tasks_status", "nurture_tasks", ["status"])
    op.create_index("ix_nurture_tasks_account_status", "nurture_tasks", ["account_id", "status"])
    op.create_index("ix_nurture_tasks_started", "nurture_tasks", ["started_at"])

    # 3. nurture_action_logs
    op.create_table(
        "nurture_action_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer, sa.ForeignKey("nurture_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("sequence", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("error", sa.Text, nullable=True),
    )
    op.create_index("ix_nurture_action_logs_task_id", "nurture_action_logs", ["task_id"])
    op.create_index("ix_nurture_action_logs_task_seq", "nurture_action_logs", ["task_id", "sequence"])

    # 4. nurture_action_sets
    op.create_table(
        "nurture_action_sets",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("actions_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("actions_order_json", sa.Text, nullable=False, server_default="[0,1,2,3]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_nurture_action_sets_platform", "nurture_action_sets", ["platform"])
    op.create_index("ix_nurture_action_sets_platform_name", "nurture_action_sets", ["platform", "name"], unique=True)

    # 5. nurture_schedules
    op.create_table(
        "nurture_schedules",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("account_id", sa.Integer, sa.ForeignKey("platform_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("cron", sa.String(64), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="30"),
        sa.Column("actions_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column("action_set_id", sa.Integer, nullable=True),
        sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_nurture_schedules_platform", "nurture_schedules", ["platform"])
    op.create_index("ix_nurture_schedules_enabled", "nurture_schedules", ["enabled"])
    op.create_index("ix_nurture_schedules_account_id", "nurture_schedules", ["account_id"])

    # 6. notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("severity", sa.String(16), nullable=False, server_default="info"),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("body", sa.Text, nullable=False, server_default=""),
        sa.Column("related_entity_type", sa.String(32), nullable=False, server_default=""),
        sa.Column("related_entity_id", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_notifications_severity", "notifications", ["severity"])
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"])

    # 7. audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("operator", sa.String(64), nullable=False, server_default="admin"),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False, server_default=""),
        sa.Column("entity_id", sa.Integer, nullable=True),
        sa.Column("changes_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("user_agent", sa.String(256), nullable=False, server_default=""),
    )
    op.create_index("ix_audit_logs_created", "audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_operator", "audit_logs", ["operator"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # 8. login_check_logs
    op.create_table(
        "login_check_logs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("account_id", sa.Integer, sa.ForeignKey("platform_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(16), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("logged_in", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("user_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("error", sa.String(256), nullable=True),
    )
    op.create_index("ix_login_check_logs_account_id", "login_check_logs", ["account_id"])
    op.create_index("ix_login_check_logs_account_checked", "login_check_logs", ["account_id", "checked_at"])
    op.create_index("ix_login_check_logs_platform", "login_check_logs", ["platform"])


def downgrade() -> None:
    op.drop_table("login_check_logs")
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("nurture_schedules")
    op.drop_table("nurture_action_sets")
    op.drop_table("nurture_action_logs")
    op.drop_table("nurture_tasks")
    op.drop_table("system_config")