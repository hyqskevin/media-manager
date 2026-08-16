"""system admin: groups / permissions / audit_logs + users 扩列 + seed 内置组与权限码

关联 TODO: 系统管理 + 多账号 RBAC + 操作日志
关联 spec: docs/superpowers/specs/2026-08-12-system-admin-design.md

- 新建 5 张表：groups / permissions / group_permissions / user_groups / audit_logs
- 扩 users.display_name (nullable) / users.enabled (NOT NULL DEFAULT 1)
- 幂等 seed 9 条 permission 码 + Administrators（绑全部 9 条）+ Viewers（仅 users:read）
- 把 role='admin' 用户批量入 Administrators 组（INSERT OR IGNORE）
- 回填 display_name = username
- downgrade：drop 新表 + drop 新列
"""
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

revision = "0020_system_admin"
down_revision = "0019"
branch_labels = None
depends_on = None


PERMISSION_SEED = [
    ("users:manage", "账号管理（新增/删除/重置密码/分配分组）"),
    ("users:read", "查看账号列表"),
    ("settings:write", "配置中心写"),
    ("tasks:crawl", "发起/停止抓取任务"),
    ("notes:review", "单篇/批量审核推文"),
    ("reports:generate", "生成周报"),
    ("notes:edit", "编辑推文"),
    ("activities:edit", "编辑子活动"),
    ("duplicates:resolve", "merge/ignore 重复项"),
    ("notes:delete", "删除推文"),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # ---- 新建 5 张表（幂等：用 IF NOT EXISTS 风格的检查） ----
    if "groups" not in existing_tables:
        op.create_table(
            "groups",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(64), unique=True, nullable=False),
            sa.Column("description", sa.String(256), nullable=True),
            sa.Column("is_builtin", sa.Boolean, nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_groups_name", "groups", ["name"], unique=True)

    if "permissions" not in existing_tables:
        op.create_table(
            "permissions",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("code", sa.String(64), unique=True, nullable=False),
            sa.Column("description", sa.String(256), nullable=True),
            sa.Column("is_builtin", sa.Boolean, nullable=False, server_default=sa.text("0")),
        )
        op.create_index("ix_permissions_code", "permissions", ["code"], unique=True)

    if "group_permissions" not in existing_tables:
        op.create_table(
            "group_permissions",
            sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("permission_id", sa.Integer, sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
        )

    if "user_groups" not in existing_tables:
        op.create_table(
            "user_groups",
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("group_id", sa.Integer, sa.ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True),
        )

    if "audit_logs" not in existing_tables:
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("actor_user_id", sa.Integer, nullable=True),
            sa.Column("actor_username", sa.String(64), nullable=False),
            sa.Column("action", sa.String(64), nullable=False, index=True),
            sa.Column("resource_type", sa.String(32), nullable=True),
            sa.Column("resource_id", sa.Integer, nullable=True),
            sa.Column("target_label", sa.String(128), nullable=True),
            sa.Column("method", sa.String(8), nullable=False),
            sa.Column("path", sa.String(256), nullable=False),
            sa.Column("status_code", sa.Integer, nullable=False),
            sa.Column("client_ip", sa.String(45), nullable=False),
            sa.Column("user_agent", sa.String(256), nullable=True),
            sa.Column("extra", sa.Text, nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ---- 扩 users.display_name / users.enabled ----
    user_cols = {c["name"] for c in inspector.get_columns("users")}
    if "display_name" not in user_cols:
        op.add_column("users", sa.Column("display_name", sa.String(64), nullable=True))
    if "enabled" not in user_cols:
        op.add_column("users", sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("1")))

    # ---- seed 权限码（幂等：SELECT 后 INSERT） ----
    for code, desc in PERMISSION_SEED:
        exists = bind.execute(
            sa.text("SELECT 1 FROM permissions WHERE code = :code"), {"code": code}
        ).scalar()
        if not exists:
            bind.execute(
                sa.text(
                    "INSERT INTO permissions (code, description, is_builtin) VALUES (:c, :d, 1)"
                ),
                {"c": code, "d": desc},
            )

    # ---- seed Administrators 组（全权限） ----
    admins_gid = bind.execute(
        sa.text("SELECT id FROM groups WHERE name = 'Administrators'")
    ).scalar()
    if admins_gid is None:
        bind.execute(
            sa.text(
                "INSERT INTO groups (name, description, is_builtin, created_at) "
                "VALUES ('Administrators', '内置管理员组，拥有全部权限', 1, :ts)"
            ),
            {"ts": datetime.now(timezone.utc)},
        )
        admins_gid = bind.execute(
            sa.text("SELECT id FROM groups WHERE name = 'Administrators'")
        ).scalar()
        # 绑全部 9 条权限
        for code, _ in PERMISSION_SEED:
            pid = bind.execute(
                sa.text("SELECT id FROM permissions WHERE code = :c"), {"c": code}
            ).scalar()
            bind.execute(
                sa.text(
                    "INSERT OR IGNORE INTO group_permissions (group_id, permission_id) "
                    "VALUES (:g, :p)"
                ),
                {"g": admins_gid, "p": pid},
            )

    # ---- seed Viewers 组（仅 users:read） ----
    viewers_gid = bind.execute(
        sa.text("SELECT id FROM groups WHERE name = 'Viewers'")
    ).scalar()
    if viewers_gid is None:
        bind.execute(
            sa.text(
                "INSERT INTO groups (name, description, is_builtin, created_at) "
                "VALUES ('Viewers', '内置只读组，仅可查看账号列表', 1, :ts)"
            ),
            {"ts": datetime.now(timezone.utc)},
        )
        viewers_gid = bind.execute(
            sa.text("SELECT id FROM groups WHERE name = 'Viewers'")
        ).scalar()
        read_pid = bind.execute(
            sa.text("SELECT id FROM permissions WHERE code = 'users:read'")
        ).scalar()
        bind.execute(
            sa.text(
                "INSERT OR IGNORE INTO group_permissions (group_id, permission_id) "
                "VALUES (:g, :p)"
            ),
            {"g": viewers_gid, "p": read_pid},
        )

    # ---- 把 role='admin' 用户批量入 Administrators 组（幂等：INSERT OR IGNORE） ----
    bind.execute(
        sa.text(
            "INSERT OR IGNORE INTO user_groups (user_id, group_id) "
            "SELECT id, :g FROM users WHERE role = 'admin'"
        ),
        {"g": admins_gid},
    )

    # ---- 回填 display_name ----
    bind.execute(
        sa.text("UPDATE users SET display_name = username WHERE display_name IS NULL OR display_name = ''")
    )


def downgrade() -> None:
    op.drop_column("users", "enabled")
    op.drop_column("users", "display_name")
    op.drop_table("audit_logs")
    op.drop_table("user_groups")
    op.drop_table("group_permissions")
    op.drop_table("permissions")
    op.drop_table("groups")