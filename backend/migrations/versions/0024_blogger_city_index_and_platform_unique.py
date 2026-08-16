"""blogger_city_index_and_platform_unique: 补齐 bloggers 模型声明的索引与唯一约束

关联当次巡检：模型声明了 bloggers.city_code 索引与 platform_user_id 唯一约束，
但未生成迁移，alembic check 检测到数据库缺失。

- 新增 ix_bloggers_city_code 普通索引（city_code 允许 NULL，SQLite 索引允许 NULL）
- 新增 platform_user_id 唯一约束（已确认数据无 NULL、无重复）
"""

import sqlalchemy as sa
from alembic import op

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    indexes = {ix["name"] for ix in sa.inspect(bind).get_indexes("bloggers")}
    if "ix_bloggers_city_code" not in indexes:
        op.create_index("ix_bloggers_city_code", "bloggers", ["city_code"])
    uniques = {c["name"] for c in sa.inspect(bind).get_unique_constraints("bloggers")}
    if "uq_bloggers_platform_user_id" not in uniques:
        with op.batch_alter_table("bloggers") as batch:
            batch.create_unique_constraint("uq_bloggers_platform_user_id", ["platform_user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    indexes = {ix["name"] for ix in sa.inspect(bind).get_indexes("bloggers")}
    if "ix_bloggers_city_code" in indexes:
        op.drop_index("ix_bloggers_city_code", table_name="bloggers")
    uniques = {c["name"] for c in sa.inspect(bind).get_unique_constraints("bloggers")}
    if "uq_bloggers_platform_user_id" in uniques:
        with op.batch_alter_table("bloggers") as batch:
            batch.drop_constraint("uq_bloggers_platform_user_id", type_="unique")