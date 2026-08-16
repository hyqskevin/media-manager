"""多小红书账号配置模型。

每个 XhsAccount 对应一个独立的 opencli session（Chrome profile），
run_crawl 按 priority 升序选账号，某账号失效时切换到下一个。

关联 spec:
- docs/superpowers/specs/2026-08-10-multi-xhs-account-design.md
- docs/superpowers/specs/2026-08-12-xhs-account-registration.md
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class XhsAccount(Base):
    __tablename__ = "xhs_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    remark: Mapped[str] = mapped_column(String(256), default="")
    session_name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # 小红书用户 ID；可手动填也可由 whoami 自动覆盖
    platform_user_id: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    # ChromePool 为该账号分配的 CDP 端口；crawler 据此构造 OPENCLI_CDP_ENDPOINT 路由到对应 Chrome 实例
    # None 表示回退到默认 Chrome Browser Bridge（向后兼容）
    cdp_port: Mapped[int | None] = mapped_column(Integer, default=None, unique=True, index=True)
    login_status: Mapped[str] = mapped_column(String(16), default="unknown")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
