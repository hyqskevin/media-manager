"""note: 落库抓取来源（matched_keywords / matched_blogger_*）+ 互动数（like/collect/comment_count）

关联 TODO: 活动管理按关键词组/博主组筛选
关联 spec: docs/superpowers/specs/2026-08-13-activities-filter-by-groups-design.md

- Note 表加 6 个 nullable 列；matched_blogger_id 加索引（Task 4 筛选 IN 用）
- 不回填历史数据（迁移前入库的推文这些列为 null，筛选时被自然忽略）
- 本迁移后至 ORM 字段落地前可暂不重启 worker；ORM 改动（app/models/note.py）
  与 crawl_task 写入新列落地后，**必须**重启 celery worker，否则 worker 持旧
  ORM 模型访问新列会触发 no such column
"""
import sqlalchemy as sa
from alembic import op


revision = "0022_note_match_and_engagement"
down_revision = "0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    note_cols = {c["name"] for c in inspector.get_columns("notes")}

    if "matched_keywords" not in note_cols:
        op.add_column("notes", sa.Column("matched_keywords", sa.JSON, nullable=True))
    if "matched_blogger_id" not in note_cols:
        op.add_column("notes", sa.Column("matched_blogger_id", sa.Integer, nullable=True))
    if "matched_blogger_username" not in note_cols:
        op.add_column("notes", sa.Column("matched_blogger_username", sa.String(64), nullable=True))
    if "like_count" not in note_cols:
        op.add_column("notes", sa.Column("like_count", sa.Integer, nullable=True))
    if "collect_count" not in note_cols:
        op.add_column("notes", sa.Column("collect_count", sa.Integer, nullable=True))
    if "comment_count" not in note_cols:
        op.add_column("notes", sa.Column("comment_count", sa.Integer, nullable=True))

    # matched_blogger_id 索引：Task 4 的 blogger_group_ids 筛选走 IN(...)，无索引会全表扫描
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("notes")}
    if "ix_notes_matched_blogger_id" not in existing_indexes:
        op.create_index("ix_notes_matched_blogger_id", "notes", ["matched_blogger_id"])


def downgrade() -> None:
    op.drop_index("ix_notes_matched_blogger_id", table_name="notes")
    op.drop_column("notes", "comment_count")
    op.drop_column("notes", "collect_count")
    op.drop_column("notes", "like_count")
    op.drop_column("notes", "matched_blogger_username")
    op.drop_column("notes", "matched_blogger_id")
    op.drop_column("notes", "matched_keywords")