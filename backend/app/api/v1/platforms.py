"""GET /api/v1/platforms - list all 8 platforms metadata."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.security import require_admin
from app.schemas.platform_account import PlatformMetaOut
from app.services.platforms import registry

router = APIRouter(prefix="/platforms", tags=["platforms"])


@router.get("", response_model=list[PlatformMetaOut])
async def list_platforms(_: Annotated[dict, Depends(require_admin)]) -> list[PlatformMetaOut]:
    """List all supported platforms (xhs implemented, 7 are stubs)."""
    registry.load_all()
    return [
        PlatformMetaOut(
            id=a.platform.value,
            display_name=a.display_name,
            icon=a.icon,
            status=a.status,
        )
        for a in registry.all_implemented()
    ]