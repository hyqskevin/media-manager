"""仪表盘连接检测路由。

关联 spec: docs/superpowers/specs/2026-08-03-diagnostics-panel-design.md
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.core.config import Settings
from app.core.security import require_admin
from app.services import diagnostics as svc
from app.services import diagnostics_ocr as ocr_svc


router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


def _raise_if_opencli_failure(payload: dict) -> None:
    """opencli bin 缺失/版本异常 → 503；业务态 logged_in=false 保持 200。"""
    if payload.get("ok") is False:
        reason = payload.get("reason") or "opencli 检测失败"
        raise HTTPException(503, reason)


@router.get("/snapshot")
def diagnostics_snapshot(_: dict = Depends(require_admin), settings: Settings = Depends(get_settings)) -> dict:
    return {"code": 200, "message": "success", "data": svc.probe_snapshot(settings)}


@router.get("/opencli")
def diagnostics_opencli(_: dict = Depends(require_admin), settings: Settings = Depends(get_settings)) -> dict:
    payload = svc.probe_opencli(settings)
    _raise_if_opencli_failure(payload)
    return {"code": 200, "message": "success", "data": payload}


@router.get("/xhs-login")
def diagnostics_xhs_login(_: dict = Depends(require_admin), settings: Settings = Depends(get_settings)) -> dict:
    payload = svc.probe_xhs_login(settings)
    return {"code": 200, "message": "success", "data": payload}


@router.get("/xhs-pool")
def diagnostics_xhs_pool(_: dict = Depends(require_admin), settings: Settings = Depends(get_settings)) -> dict:
    payload = svc.probe_xhs_pool(settings)
    return {"code": 200, "message": "success", "data": payload}


@router.post("/ocr")
def diagnostics_ocr(_: dict = Depends(require_admin), settings: Settings = Depends(get_settings)) -> dict:
    """测试 OCR 是否可用(启动器调用)。"""
    payload = ocr_svc.probe_ocr(settings)
    return {"code": 200, "message": "success", "data": payload}