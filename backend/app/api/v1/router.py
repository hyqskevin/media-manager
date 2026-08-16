from fastapi import APIRouter

from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.activities import router as activities_router
from app.api.v1.poster_templates import router as poster_templates_router
from app.api.v1.poster_tasks import router as poster_tasks_router
from app.api.v1.settings import router as settings_router
from app.api.v1.xhs_accounts import router as xhs_accounts_router
from app.api.v1.schedules import router as schedules_router
from app.api.v1.reports import router as reports_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.duplicates import router as duplicates_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.notes import router as notes_router
from app.api.v1.diagnostics import router as diagnostics_router
from app.api.v1.users import router as users_router
from app.api.v1.groups import router as groups_router
from app.api.v1.permissions import router as permissions_router
from app.api.v1.audit_logs import router as audit_logs_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(activities_router)
api_router.include_router(poster_templates_router)  # before settings_router due to /{kind} collision
api_router.include_router(poster_tasks_router)
api_router.include_router(settings_router)
api_router.include_router(xhs_accounts_router)
api_router.include_router(schedules_router)
api_router.include_router(reports_router)
api_router.include_router(tasks_router)
api_router.include_router(duplicates_router)
api_router.include_router(dashboard_router)
api_router.include_router(notes_router)
api_router.include_router(diagnostics_router)
api_router.include_router(users_router)
api_router.include_router(groups_router)
api_router.include_router(permissions_router)
api_router.include_router(audit_logs_router)