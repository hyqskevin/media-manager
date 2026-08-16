from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ActivityCreate(BaseModel):
    name: str
    city_code: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str = ""
    price: str = ""
    type: str
    source_url: str = ""
    summary: str = ""
    confidence: float = 1.0


class ActivityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    city_code: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    location: str | None = None
    price: str | None = None
    type: str | None = None
    source_url: str | None = None
    summary: str | None = None


class ActivityRead(ActivityCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    note_id: int | None = None
    source_image_indexes: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
