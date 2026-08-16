"""共用依赖类型与批量删除 schema。

`app.api.v1.settings` 包下的各 router 共享：
- 鉴权依赖（``Admin``）
- DB 依赖（``DB``）
- 批量删除请求/响应 schema
"""
from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_admin

Admin = Annotated[dict[str, str], Depends(require_admin)]
DB = Annotated[Session, Depends(get_db)]


class BatchDeleteIdsIn(BaseModel):
    """5 个批量删除端点共用的请求体：1–500 个资源 id。"""

    ids: list[int] = Field(min_length=1, max_length=500)


class BatchDeleteOut(BaseModel):
    deleted_count: int
