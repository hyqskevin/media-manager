"""v0.3 full-features Pydantic schemas (risk config / nurture / action sets /
schedules / notifications / audit logs / operators / activity)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RiskConfigOut(BaseModel):
    nurture_global_enabled: bool = False
    silent_hour_start: int = 0
    silent_hour_end: int = 6
    max_daily_seconds: int = 14400
    min_action_interval_s: int = 3
    max_likes_per_hour: int = 10
    max_likes_per_day: int = 50


class RiskConfigUpdate(BaseModel):
    nurture_global_enabled: bool | None = None
    silent_hour_start: int | None = Field(default=None, ge=0, le=23)
    silent_hour_end: int | None = Field(default=None, ge=0, le=23)
    max_daily_seconds: int | None = Field(default=None, ge=3600, le=28800)
    min_action_interval_s: int | None = Field(default=None, ge=1, le=30)
    max_likes_per_hour: int | None = Field(default=None, ge=1, le=50)
    max_likes_per_day: int | None = Field(default=None, ge=1, le=500)


class NurtureActionLogOut(BaseModel):
    id: int
    task_id: int
    action: str
    status: str
    sequence: int
    started_at: datetime | None
    finished_at: datetime | None
    result: dict[str, Any]
    error: str | None


class NurtureTaskOut(BaseModel):
    id: int
    celery_task_id: str
    account_id: int
    platform: str
    actions: list[str]
    duration_minutes: int
    status: str
    current_action: str | None
    progress_pct: int
    started_at: datetime | None
    finished_at: datetime | None
    error: str | None
    items_collected: int
    created_at: datetime


class NurtureTaskPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[NurtureTaskOut]


class ActionSetCreate(BaseModel):
    platform: str
    name: str = Field(min_length=1, max_length=64)
    duration_minutes: int = Field(default=30, ge=5, le=240)
    actions: list[str] = Field(default_factory=list)
    actions_order: list[int] | None = None


class ActionSetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    duration_minutes: int | None = Field(default=None, ge=5, le=240)
    actions: list[str] | None = None
    actions_order: list[int] | None = None


class ActionSetOut(BaseModel):
    id: int
    platform: str
    name: str
    duration_minutes: int
    actions: list[str]
    actions_order: list[int]
    created_at: datetime
    updated_at: datetime


class ScheduleCreate(BaseModel):
    platform: str
    account_id: int
    name: str = Field(min_length=1, max_length=64)
    cron: str = Field(min_length=1, max_length=64)
    duration_minutes: int = Field(default=30, ge=5, le=240)
    actions: list[str] = Field(default_factory=list)
    action_set_id: int | None = None
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    cron: str | None = Field(default=None, min_length=1, max_length=64)
    duration_minutes: int | None = Field(default=None, ge=5, le=240)
    actions: list[str] | None = None
    action_set_id: int | None = None
    enabled: bool | None = None


class ScheduleOut(BaseModel):
    id: int
    platform: str
    account_id: int
    name: str
    cron: str
    duration_minutes: int
    actions: list[str]
    action_set_id: int | None
    enabled: bool
    next_run_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SchedulePage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ScheduleOut]


class NotificationOut(BaseModel):
    id: int
    severity: str
    title: str
    body: str
    related_entity_type: str
    related_entity_id: int | None
    created_at: datetime
    read_at: datetime | None
    is_read: bool


class NotificationPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[NotificationOut]


class UnreadCountOut(BaseModel):
    unread: int


class AuditLogOut(BaseModel):
    id: int
    created_at: datetime
    operator: str
    action: str
    entity_type: str
    entity_id: int | None
    changes: dict[str, Any]
    ip: str
    user_agent: str


class AuditLogPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[AuditLogOut]


class OperatorMeOut(BaseModel):
    id: int
    username: str
    is_admin: bool


class PasswordChange(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6)


class ActivityKpiOut(BaseModel):
    login_count: int
    nurture_seconds: int
    like_count: int
    favorite_count: int
    nurture_task_count: int


class HeatmapCell(BaseModel):
    account_id: int
    date: str
    intensity: int


class ActionCount(BaseModel):
    action_type: str
    count: int


class PlatformCount(BaseModel):
    platform: str
    count: int


class TaskCreatedOut(BaseModel):
    task_id: str