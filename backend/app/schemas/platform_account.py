"""v0.2 platform account / favorite snapshot Pydantic schemas."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.models.platform_account import PlatformType


class PlatformAccountOut(BaseModel):
    id: int
    name: str
    platform: PlatformType
    session_name: str
    platform_user_id: str | None
    cdp_port: int | None
    login_status: str
    last_login_check_at: datetime | None
    enabled: bool
    priority: int
    daily_quota_seconds: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PlatformAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    platform: PlatformType
    enabled: bool = True
    priority: int = Field(default=0, ge=0, le=100)
    daily_quota_seconds: int = Field(default=14400, ge=600, le=28800)


class PlatformAccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    daily_quota_seconds: int | None = Field(default=None, ge=600, le=28800)


class CheckLoginResultOut(BaseModel):
    logged_in: bool
    user_id: str = ""
    nickname: str = ""
    error: str = ""


class NurtureAction(str, Enum):
    BROWSE_HOME = "browse_home"
    LIKE_POST = "like_post"
    FAVORITE_POST = "favorite_post"
    FETCH_FAVORITES = "fetch_favorites"


class NurtureRequest(BaseModel):
    actions: list[NurtureAction] = [
        NurtureAction.BROWSE_HOME,
        NurtureAction.FETCH_FAVORITES,
    ]
    duration_minutes: int = Field(default=30, ge=5, le=240)
    post_url: str | None = None


class NurtureTaskCreated(BaseModel):
    task_id: str


class FavoriteSnapshotOut(BaseModel):
    id: int
    account_id: int
    platform: PlatformType
    captured_at: datetime
    item_count: int
    items: list[dict[str, Any]]
    error: str | None

    class Config:
        from_attributes = True


class PlatformMetaOut(BaseModel):
    id: str
    display_name: str
    icon: str
    status: str