"""FastAPI 入口（v0.2 最小骨架）。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="media-manager API",
    version="0.2.0",
    description="多平台浏览器自动化养号管理台",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"service": "media-manager", "version": "0.2.0", "nurture_enabled": settings.nurture_global_enabled}