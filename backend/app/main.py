from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import init_database
from app.core.json_response import UtcJsonResponse


settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.ensure_runtime_directories()
    init_database()
    mount_static_frontend_if_exists(app, settings.frontend_dist_path)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
    default_response_class=UtcJsonResponse,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> UtcJsonResponse:
    return UtcJsonResponse(status_code=exc.status_code, content={"code": exc.status_code, "message": str(exc.detail), "data": {}})


def mount_static_frontend_if_exists(app: FastAPI, dist_path: Path) -> None:
    """挂载前端静态文件;dist 不存在则跳过(开发模式)。

    打包版需要:后端直接服务前端构建产物,不用单独跑 vite dev server。
    """
    if not dist_path.exists() or not dist_path.is_dir():
        return

    index_html = dist_path / "index.html"
    if not index_html.exists():
        return

    # 挂载 assets 等静态资源
    assets_dir = dist_path / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # SPA fallback:未匹配的路由回退到 index.html(让前端路由处理)
    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str):
        # 优先返回对应的静态文件
        file_path = dist_path / full_path
        if full_path and file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # 否则回退到 index.html
        return FileResponse(index_html)
