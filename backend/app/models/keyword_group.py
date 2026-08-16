"""关键词组模型。

设计要点：
- KeywordGroup 实体：id, name (unique), description, created_at
- 与城市一对多（多挂）：通过 KeywordGroupCity 中间表
- 与关键词一对多：通过 KeywordGroupWord 中间表
- 一个关键词组可挂多个城市，可包含多个关键词（many-to-many）

关联 spec: docs/superpowers/specs/2026-07-21-city-and-keyword-groups-design.md
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class KeywordGroup(Base):
    __tablename__ = "keyword_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    enabled: Mapped[bool] = mapped_column(default=True)
    # 排除词：抓取后命中任一关键词，但内容含任一排除词的笔记会被过滤（JSON list of str）
    excluded_words_json: Mapped[str | None] = mapped_column(Text, nullable=True, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class KeywordGroupCity(Base):
    """一个组挂在哪些城市（多对多）。"""
    __tablename__ = "keyword_group_cities"
    __table_args__ = (UniqueConstraint("keyword_group_id", "city_code", name="uq_kg_city"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    keyword_group_id: Mapped[int] = mapped_column(
        ForeignKey("keyword_groups.id", ondelete="CASCADE"), index=True
    )
    city_code: Mapped[str] = mapped_column(
        String(32), ForeignKey("cities.code", ondelete="CASCADE"), index=True
    )
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class KeywordGroupWord(Base):
    """一个组里包含哪些关键词（多对多）。"""
    __tablename__ = "keyword_group_words"
    __table_args__ = (UniqueConstraint("keyword_group_id", "word", name="uq_kg_word"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    keyword_group_id: Mapped[int] = mapped_column(
        ForeignKey("keyword_groups.id", ondelete="CASCADE"), index=True
    )
    word: Mapped[str] = mapped_column(String(128), index=True)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
