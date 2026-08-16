"""introduce keyword_groups many-to-many + cities.name unique

关联 TODO: 城市复用 + 关键词组一对多
关联 spec: docs/superpowers/specs/2026-07-21-city-and-keyword-groups-design.md

- 新增 keyword_groups / keyword_group_cities / keyword_group_words 三表；
- 从现有 keywords (city_code, word) 自动按"城市名-默认"命名规则生成 KeywordGroup，
  让旧调用方在 migration 之后仍有默认组可用；
- cities.name 加 unique 约束（重复行由 scripts/dedupe_cities.py 先清理）。
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(sa.inspect(bind).get_table_names())
    created_groups = False

    # 1. 新增 keyword_groups 表
    if "keyword_groups" not in existing_tables:
        created_groups = True
        op.create_table(
            "keyword_groups",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("name", sa.String(128), nullable=False, unique=True),
            sa.Column("description", sa.Text, nullable=True),
            sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_keyword_groups_name", "keyword_groups", ["name"], unique=True)

    # 2. 中间表：keyword_group_cities
    if "keyword_group_cities" not in existing_tables:
        op.create_table(
            "keyword_group_cities",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("keyword_group_id", sa.Integer, sa.ForeignKey("keyword_groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("city_code", sa.String(32), sa.ForeignKey("cities.code", ondelete="CASCADE"), nullable=False),
            sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("keyword_group_id", "city_code", name="uq_kg_city"),
        )
        op.create_index("ix_keyword_group_cities_keyword_group_id", "keyword_group_cities", ["keyword_group_id"])
        op.create_index("ix_keyword_group_cities_city_code", "keyword_group_cities", ["city_code"])

    # 3. 中间表：keyword_group_words
    if "keyword_group_words" not in existing_tables:
        op.create_table(
            "keyword_group_words",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("keyword_group_id", sa.Integer, sa.ForeignKey("keyword_groups.id", ondelete="CASCADE"), nullable=False),
            sa.Column("word", sa.String(128), nullable=False),
            sa.Column("enabled", sa.Boolean, nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("keyword_group_id", "word", name="uq_kg_word"),
        )
        op.create_index("ix_keyword_group_words_keyword_group_id", "keyword_group_words", ["keyword_group_id"])
        op.create_index("ix_keyword_group_words_word", "keyword_group_words", ["word"])

    # 4. 数据迁移：从老 keywords (city_code, word) 每城市建一个 default 组。
    #    仅在三表由本次迁移创建（旧库升级路径）时执行；全新建库 keywords 为空且无意义。
    if created_groups:
        rows = bind.execute(
            sa.text(
                "SELECT k.city_code, c.name, k.word "
                "FROM keywords k JOIN cities c ON c.code = k.city_code "
                "WHERE k.enabled = 1 "
                "ORDER BY k.city_code, k.id"
            )
        ).fetchall()
        by_city: dict[str, dict] = {}  # code -> {name, words[]}
        for code, name, word in rows:
            slot = by_city.setdefault(code, {"name": name, "words": []})
            if word not in slot["words"]:
                slot["words"].append(word)

        for code, slot in by_city.items():
            default_name = f"{slot['name']}-默认"
            # 插入组
            kg_id = bind.execute(
                sa.text(
                    "INSERT INTO keyword_groups (name, description, enabled) VALUES (:n, :d, 1)"
                ),
                {"n": default_name, "d": f"由 0013 migration 从 keywords 历史数据生成"},
            ).lastrowid
            # 挂城市
            bind.execute(
                sa.text(
                    "INSERT INTO keyword_group_cities (keyword_group_id, city_code, enabled) "
                    "VALUES (:g, :c, 1)"
                ),
                {"g": kg_id, "c": code},
            )
            # 挂关键词
            for word in slot["words"]:
                bind.execute(
                    sa.text(
                        "INSERT INTO keyword_group_words (keyword_group_id, word, enabled) "
                        "VALUES (:g, :w, 1)"
                    ),
                    {"g": kg_id, "w": word},
                )

    # 5. cities.name 加 unique 约束（依赖 dedupe_cities.py 先清理）
    # SQLite + alembic 在 unique 索引实现上等价；用 create_index
    city_indexes = {i["name"] for i in sa.inspect(bind).get_indexes("cities")}
    if "ix_cities_name_unique" not in city_indexes:
        with op.batch_alter_table("cities") as batch_op:
            batch_op.create_index("ix_cities_name_unique", ["name"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("cities") as batch_op:
        batch_op.drop_index("ix_cities_name_unique")
    op.drop_index("ix_keyword_group_words_word", table_name="keyword_group_words")
    op.drop_index("ix_keyword_group_words_keyword_group_id", table_name="keyword_group_words")
    op.drop_table("keyword_group_words")
    op.drop_index("ix_keyword_group_cities_city_code", table_name="keyword_group_cities")
    op.drop_index("ix_keyword_group_cities_keyword_group_id", table_name="keyword_group_cities")
    op.drop_table("keyword_group_cities")
    op.drop_index("ix_keyword_groups_name", table_name="keyword_groups")
    op.drop_table("keyword_groups")
