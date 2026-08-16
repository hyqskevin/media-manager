"""v0.2 platform account + favorite snapshot data models.

See: docs/superpowers/specs/2026-08-16-v02-account-management-design.md §2
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PlatformType(str, enum.Enum):
    """8 platforms supported by v0.2 (xhs fully implemented, rest are stubs)."""
    XHS = "xhs"
    WEIBO = "weibo"
    DOUYIN = "douyin"
    ZHIHU = "zhihu"
    TWITTER = "twitter"
    BILIBILI = "bilibili"
    XIAOYUZHOU = "xiaoyuzhou"
    WECHAT_OFFICIAL = "wechat-official"


# v0.2 only implements xhs; the other 7 are stubs.
IMPLEMENTED_PLATFORMS: frozenset[PlatformType] = frozenset({PlatformType.XHS})


class PlatformAccount(Base):
    """v0.2 multi-platform account model.

    Replaces v0.1's single-platform xhs_accounts. xhs accounts migrated in.
    """
    __tablename__ = "platform_accounts"
    __table_args__ = (
        Index("ix_platform_accounts_platform", "platform"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    platform: Mapped[PlatformType] = mapped_column(
        SAEnum(PlatformType, native_enum=False, length=16)
    )
    session_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    platform_user_id: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    cdp_port: Mapped[int | None] = mapped_column(Integer, default=None, unique=True, index=True)
    login_status: Mapped[str] = mapped_column(String(16), default="unknown")
    last_login_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    daily_quota_seconds: Mapped[int] = mapped_column(Integer, default=14400)  # 4 hours
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    snapshots: Mapped[list["FavoriteSnapshot"]] = relationship(
        "FavoriteSnapshot", back_populates="account", cascade="all, delete-orphan"
    )


class FavoriteSnapshot(Base):
    """Favorite snapshot (captured periodically by nurture task)."""
    __tablename__ = "favorite_snapshots"
    __table_args__ = (
        Index("ix_favorite_snapshots_account_captured", "account_id", "captured_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("platform_accounts.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(16))  # denormalized for query convenience
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    items_json: Mapped[str] = mapped_column(Text, default="[]")
    error: Mapped[str | None] = mapped_column(Text, default=None)

    account: Mapped["PlatformAccount"] = relationship(
        "PlatformAccount", back_populates="snapshots"
    )