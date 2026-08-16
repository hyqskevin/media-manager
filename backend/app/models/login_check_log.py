"""LoginCheckLog model — login check history (activity data source)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LoginCheckLog(Base):
    """One login-check invocation for an account."""
    __tablename__ = "login_check_logs"
    __table_args__ = (
        Index("ix_login_check_logs_account_checked", "account_id", "checked_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("platform_accounts.id", ondelete="CASCADE"), index=True
    )
    platform: Mapped[str] = mapped_column(String(16), index=True)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    logged_in: Mapped[bool] = mapped_column(default=False)
    user_id: Mapped[str] = mapped_column(String(64), default="")
    error: Mapped[str | None] = mapped_column(String(256), default=None)