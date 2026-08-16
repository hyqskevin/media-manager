"""博主（白名单）分组模型。

设计要点：
- BloggerGroup 实体：id, name (unique), description, enabled, created_at
- 组成员通过 BloggerGroupMember 中间表（多对多），删除组时级联删除成员
- 组不直接绑城市：触发抓取时按任务城市过滤（博主须在该城市 blogger_cities.enabled=true）

关联 spec: docs/superpowers/specs/2026-07-25-scheduled-crawls-and-dashboard-charts-design.md
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BloggerGroup(Base):
    __tablename__ = "blogger_groups"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class BloggerGroupMember(Base):
    """组里包含哪些博主（多对多）。"""
    __tablename__ = "blogger_group_members"
    __table_args__ = (UniqueConstraint("group_id", "blogger_id", name="uq_bg_member"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("blogger_groups.id", ondelete="CASCADE"), index=True
    )
    blogger_id: Mapped[int] = mapped_column(
        ForeignKey("bloggers.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
