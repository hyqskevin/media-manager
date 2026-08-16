"""API v1 router aggregation (v0.2 + v0.3 full features)."""
from fastapi import APIRouter

from app.api.v1.platforms import router as platforms_router
from app.api.v1.platform_accounts import router as platform_accounts_router
from app.api.v1.risk_config import router as risk_config_router
from app.api.v1.nurture import router as nurture_router
from app.api.v1.action_sets import router as action_sets_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.operators import router as operators_router
from app.api.v1.activity import router as activity_router

api_router = APIRouter()
api_router.include_router(platforms_router)
api_router.include_router(platform_accounts_router)
api_router.include_router(risk_config_router)
api_router.include_router(nurture_router)
api_router.include_router(action_sets_router)
api_router.include_router(schedules_router)
api_router.include_router(notifications_router)
api_router.include_router(audit_logs_router)
api_router.include_router(operators_router)
api_router.include_router(activity_router)