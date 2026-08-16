"""seed default admin user on fresh databases

关联 TODO: 一次性数据库迁移 seed_admin 启动后兜底管理员
关联 spec: docs/superpowers/specs/2026-07-21-migration-seed-admin-design.md

- 首次部署 / alembic upgrade head 之后 `users` 表为空时插入默认 admin 用户；
- 密码优先读取环境变量 `INITIAL_ADMIN_PASSWORD`；
- 未设置时使用默认 `Admin@123` 并 WARNING；
- 幂等：再次 upgrade 不会重复插入；
- `downgrade()` 删除 username='admin' 的用户。
"""

import logging
import os
from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from pwdlib import PasswordHash

logger = logging.getLogger("migration_0012")

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


_DEFAULT_PASSWORD = "Admin@123"
_ADMIN_USERNAME = "admin"


def _env_password() -> tuple[str, bool]:
    """返回 (密码, 是否是默认密码)。"""
    password = os.environ.get("INITIAL_ADMIN_PASSWORD")
    if password:
        return password, False
    return _DEFAULT_PASSWORD, True


def upgrade() -> None:
    bind = op.get_bind()
    existing = bind.scalar(sa.select(sa.func.count()).select_from(sa.table("users")))
    if existing and existing > 0:
        logger.info("seed_admin: users 表已存在 %s 行，跳过", existing)
        return

    password, is_default = _env_password()
    if is_default:
        logger.warning(
            "INITIAL_ADMIN_PASSWORD 未设置；admin 用户使用默认密码 Admin@123。" "生产环境必须通过 INITIAL_ADMIN_PASSWORD 覆盖。",
        )

    password_hash = PasswordHash.recommended().hash(password)
    bind.execute(
        sa.text(
            "INSERT INTO users (username, password_hash, role, created_at) "
            "VALUES (:username, :password_hash, :role, :created_at)"
        ),
        {
            "username": _ADMIN_USERNAME,
            "password_hash": password_hash,
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    logger.info("seed_admin: 插入默认 admin 用户")


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM users WHERE username = :u").bindparams(u=_ADMIN_USERNAME)
    )
    logger.info("seed_admin: 删除 admin 用户")
