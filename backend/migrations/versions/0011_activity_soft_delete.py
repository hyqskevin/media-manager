"""replace activities.status with activities.deleted_at

关联 TODO: 移除推文内子活动审核状态
关联 spec: docs/superpowers/specs/2026-07-21-remove-activity-approval-status-design.md

- 删除 activities.status 列与索引。
- 新增 activities.deleted_at 列（nullable + 索引）。
- 历史脏数据全部迁移为不存在（deleted_at = NULL）。
"""

import sqlalchemy as sa
from alembic import op


revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("activities")}
    existing_columns = {column["name"] for column in inspector.get_columns("activities")}

    if "deleted_at" not in existing_columns:
        op.add_column(
            "activities",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "ix_activities_deleted_at" not in existing_indexes:
        op.create_index("ix_activities_deleted_at", "activities", ["deleted_at"], unique=False)

    # 历史脏数据迁移：所有 status 都视为存在；deleted_at 留 NULL。
    # upgraded DB 不需要 UPDATE（默认 NULL）。

    if "ix_activities_status" in existing_indexes:
        op.drop_index("ix_activities_status", table_name="activities")
    # 全新建库按当前模型建表、本无 status 列，仅旧库需要删除。
    if "status" in existing_columns:
        op.drop_column("activities", "status")


def downgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
    )
    op.create_index("ix_activities_status", "activities", ["status"], unique=False)
    # 已软删除的行回填 DELETED
    op.execute("UPDATE activities SET status='DELETED' WHERE deleted_at IS NOT NULL")
    op.drop_index("ix_activities_deleted_at", table_name="activities")
    op.drop_column("activities", "deleted_at")
