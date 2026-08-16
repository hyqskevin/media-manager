"""Task 22 (2026-08-13) 生产 DB 一次性数据修复：权限只来自组。

前置状态（已审计）：
- hanamaki  role=admin  enabled=0  groups=操作员    ← 角色与组脱钩
- editor_test role=admin enabled=1  groups=Administrators
- reviewer  role=editor enabled=0  groups=Viewers    ← 被误停用
- admin     role=admin enabled=1  groups=Administrators

修复后：
1. Administrators 组绑 '*' 通配（之前是 10 条具体码——加 '*' 让 require_admin / require_permission 统一放行）
2. builtin admin（username='admin'）保持 role=admin + Administrators 组
3. 所有非 builtin 用户的 enabled=0 → enabled=1（admin 在 UI 自行停用）
4. role 同步 group：Administrators 组外 + role=admin → role=editor；组内 + role=editor → role=admin

关联 spec: docs/superpowers/specs/2026-08-13-permission-only-from-groups-design.md

执行方式：
    cd backend && .venv/bin/python scripts/migrations/_fix_perm_data_2026_08_13.py

幂等：已符合条件的数据不会被改写。
"""
import sys
from pathlib import Path

# 把 backend 加进 sys.path，让脚本能 import app.*
BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.group import Group, GroupPermission, Permission, UserGroup
from app.models.user import User


def _ensure_star_permission_bound_to_admins(session) -> str:
    """确保 Administrators 组绑了 '*' 通配。返回状态（created/existed/bound_created）。"""
    star = session.scalar(select(Permission).where(Permission.code == "*"))
    if star is None:
        star = Permission(code="*", description="管理员通配（Administrators 组内置）", is_builtin=True)
        session.add(star)
        session.flush()
        perm_status = "created"
    else:
        perm_status = "existed"

    admins = session.scalar(select(Group).where(Group.name == "Administrators"))
    if admins is None:
        raise RuntimeError("Administrators 组不存在；先执行 alembic upgrade head")

    binding = session.scalar(
        select(GroupPermission)
        .where(GroupPermission.group_id == admins.id, GroupPermission.permission_id == star.id)
    )
    if binding is None:
        session.add(GroupPermission(group_id=admins.id, permission_id=star.id))
        session.flush()
        return f"perm_{perm_status}_bound"
    return f"perm_{perm_status}_already_bound"


def _ensure_builtin_admin_in_admins(session) -> str:
    """builtin admin 必须保留在 Administrators 组（防御性修复）。"""
    builtin = session.scalar(select(User).where(User.username == "admin"))
    if builtin is None:
        return "no_builtin_admin"
    admins = session.scalar(select(Group).where(Group.name == "Administrators"))
    link = session.scalar(
        select(UserGroup).where(UserGroup.user_id == builtin.id, UserGroup.group_id == admins.id)
    )
    if link is None:
        session.add(UserGroup(user_id=builtin.id, group_id=admins.id))
        session.flush()
        return "linked"
    return "already_linked"


def _re_enable_disabled_non_builtin(session) -> int:
    """所有 enabled=0 的非 builtin 用户 → enabled=1。"""
    users = session.scalars(select(User).where(User.enabled == False)).all()  # noqa: E712
    count = 0
    for u in users:
        if u.username == "admin":
            continue
        u.enabled = True
        count += 1
    return count


def _sync_role_to_group_membership(session) -> tuple[int, int]:
    """role 同步：Administrators 组外 + role=admin → editor；组内 + role=editor → admin。"""
    admins = session.scalar(select(Group).where(Group.name == "Administrators"))
    admins_user_ids = {
        uid for (uid,) in session.execute(
            select(UserGroup.user_id).where(UserGroup.group_id == admins.id)
        ).all()
    }
    promoted = 0
    demoted = 0
    for u in session.scalars(select(User)).all():
        if u.username == "admin":
            continue
        if u.id in admins_user_ids and u.role != "admin":
            u.role = "admin"
            promoted += 1
        elif u.id not in admins_user_ids and u.role == "admin":
            u.role = "editor"
            demoted += 1
    return promoted, demoted


def main() -> int:
    session = SessionLocal()
    try:
        print("=== Task 22 (2026-08-13) 生产数据修复 ===")

        perm_status = _ensure_star_permission_bound_to_admins(session)
        print(f"[1/4] Administrators 组 '*' 通配：{perm_status}")

        admin_link = _ensure_builtin_admin_in_admins(session)
        print(f"[2/4] builtin admin 与 Administrators 关联：{admin_link}")

        re_enabled = _re_enable_disabled_non_builtin(session)
        print(f"[3/4] 重新启用非 builtin 停用用户：{re_enabled} 个")

        promoted, demoted = _sync_role_to_group_membership(session)
        print(f"[4/4] role 同步组关系：升 admin {promoted} / 降 editor {demoted}")

        session.commit()
        print("\n提交成功。请用以下命令验证：")
        print("  sqlite3 ../data/app.db \"SELECT u.username, u.role, u.enabled, GROUP_CONCAT(g.name) FROM users u LEFT JOIN user_groups ug ON u.id=ug.user_id LEFT JOIN groups g ON ug.group_id=g.id GROUP BY u.id;\"")
        return 0
    except Exception as exc:
        session.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())