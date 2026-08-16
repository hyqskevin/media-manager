"""系统配置（.env 读写） + opencli 配置/测试/打开登录页。

端点（URL 不变）：
- GET  /settings/opencli/config
- POST /settings/opencli/test
- POST /settings/opencli/open-login
- GET  /settings/system-config
- PUT  /settings/system-config
"""
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.browser_launcher import BrowserLaunchError, open_xhs_login
from app.services.opencli_adapter import OpenCLIAdapter
from app.api.v1.settings._deps import Admin

router = APIRouter(tags=["settings"])


@router.get("/settings/opencli/config")
def opencli_config(_: Admin):
    # 关键：每次调用时从包级命名空间查找，兼容测试中
    # ``monkeypatch.setattr("app.api.v1.settings.get_settings", ...)`` 的写法。
    from app.api.v1.settings import get_settings
    settings = get_settings()
    return {
        "code": 200,
        "message": "success",
        "data": {
            "endpoint": settings.opencli_cdp_endpoint,
            "target_count": settings.xhs_search_target_count,
            "scroll_rounds": settings.xhs_search_scroll_max_rounds,
        },
    }


@router.post("/settings/opencli/test")
def opencli_test(_: Admin):
    from app.api.v1.settings import get_settings
    try:
        data = OpenCLIAdapter(get_settings()).check_login()
        return {"code": 200, "message": "连接正常", "data": data}
    except Exception as exc:
        raise HTTPException(503, str(exc)) from exc


@router.post("/settings/opencli/open-login")
def open_login(_: Admin):
    # 关键：每次调用时从包级命名空间查找，兼容测试中
    # ``monkeypatch.setattr("app.api.v1.settings.open_xhs_login", ...)`` 的写法。
    from app.api.v1.settings import get_settings, open_xhs_login
    settings = get_settings()
    try:
        url = open_xhs_login(settings)
        return {"code": 200, "message": "已打开 Chrome 小红书登录页", "data": {"url": url}}
    except BrowserLaunchError as exc:
        raise HTTPException(503, str(exc)) from exc


# ── 系统配置（.env 读写） ──

# env 字段名 → Settings 属性名映射
_ENV_KEY_MAP: dict[str, str] = {
    "minimax_api_key": "MINIMAX_API_KEY",
    "minimax_base_url": "MINIMAX_BASE_URL",
    "minimax_model": "MINIMAX_MODEL",
    "minimax_timeout_seconds": "MINIMAX_TIMEOUT_SECONDS",
    "minimax_concurrency": "MINIMAX_CONCURRENCY",
    "ocr_enabled": "OCR_ENABLED",
    "ocr_language": "OCR_LANGUAGE",
    "ocr_min_confidence": "OCR_MIN_CONFIDENCE",
    "ocr_parallel_workers": "OCR_PARALLEL_WORKERS",
    "pipeline_stage_max_retries": "PIPELINE_STAGE_MAX_RETRIES",
    "pipeline_stage_retry_delay_seconds": "PIPELINE_STAGE_RETRY_DELAY_SECONDS",
    "xhs_search_target_count": "XHS_SEARCH_TARGET_COUNT",
    "xhs_search_scroll_max_rounds": "XHS_SEARCH_SCROLL_MAX_ROUNDS",
    "xhs_scroll_pixels": "XHS_SCROLL_PIXELS",
    "xhs_scroll_stagnant_rounds": "XHS_SCROLL_STAGNANT_ROUNDS",
    "search_limit": "SEARCH_LIMIT",
    "weekly_search_limit": "WEEKLY_SEARCH_LIMIT",
    "consecutive_note_failure_limit": "CONSECUTIVE_NOTE_FAILURE_LIMIT",
    "activity_future_window_days": "ACTIVITY_FUTURE_WINDOW_DAYS",
    "account_rotation_notes": "ACCOUNT_ROTATION_NOTES",
    "chrome_bin": "CHROME_BIN",
    "chrome_user_data_dir": "CHROME_USER_DATA_DIR",
    "opencli_bin": "OPENCLI_BIN",
}


class SystemConfigIn(BaseModel):
    """系统配置更新请求，所有字段可选。"""

    minimax_api_key: str | None = None
    minimax_base_url: str | None = None
    minimax_model: str | None = None
    minimax_timeout_seconds: int | None = None
    minimax_concurrency: int | None = None
    ocr_enabled: bool | None = None
    ocr_language: str | None = None
    ocr_min_confidence: float | None = None
    ocr_parallel_workers: int | None = None
    pipeline_stage_max_retries: int | None = None
    pipeline_stage_retry_delay_seconds: float | None = None
    xhs_search_target_count: int | None = None
    xhs_search_scroll_max_rounds: int | None = None
    xhs_scroll_pixels: int | None = None
    xhs_scroll_stagnant_rounds: int | None = None
    search_limit: int | None = None
    weekly_search_limit: int | None = None
    consecutive_note_failure_limit: int | None = None
    activity_future_window_days: int | None = None
    account_rotation_notes: int | None = None
    chrome_bin: str | None = None
    chrome_user_data_dir: str | None = None
    opencli_bin: str | None = None


def _read_system_config(settings) -> dict[str, Any]:
    """从 Settings 实例读取所有可配置项。"""
    return {
        key: getattr(settings, key)
        for key in _ENV_KEY_MAP
    }


def _update_env_file(env_path: str, updates: dict[str, str]) -> None:
    """更新 .env 文件：已存在的 key 替换值，不存在的 key 追加到末尾。保留注释和空行。"""
    path = Path(env_path)
    lines: list[str] = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    updated_keys: set[str] = set()

    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                updated_keys.add(key)
                continue
        new_lines.append(line)

    # 追加未覆盖的新 key
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}")

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def _env_path_from_settings() -> str:
    """从 Settings 的 model_config 中获取 .env 文件路径。"""
    from app.api.v1.settings import get_settings
    settings = get_settings()
    env_file = settings.model_config.get("env_file", ".env")
    if isinstance(env_file, (str, Path)):
        return str(env_file)
    return ".env"


@router.get("/settings/system-config")
def get_system_config(_: Admin):
    """返回当前所有系统配置项。"""
    from app.api.v1.settings import get_settings
    settings = get_settings()
    return {"code": 200, "message": "success", "data": _read_system_config(settings)}


@router.put("/settings/system-config")
def update_system_config(payload: SystemConfigIn, _: Admin):
    """更新系统配置，写入 .env 文件。"""
    from app.api.v1.settings import get_settings
    updates: dict[str, str] = {}
    for field_name, env_key in _ENV_KEY_MAP.items():
        value = getattr(payload, field_name, None)
        if value is not None:
            updates[env_key] = str(value).lower() if isinstance(value, bool) else str(value)

    if not updates:
        raise HTTPException(422, "没有需要更新的字段")

    env_path = _env_path_from_settings()
    _update_env_file(env_path, updates)

    # 同步 os.environ：pydantic_settings 优先级 os.environ > .env，
    # 若不同步，uvicorn 启动时 source .env 注入的旧值会覆盖 .env 文件新值
    import os
    for env_key, raw_value in updates.items():
        os.environ[env_key] = raw_value

    # 重新加载 settings 以返回最新值
    from app.core.config import get_settings as _gs
    _gs.cache_clear()
    settings = get_settings()
    return {"code": 200, "message": "success", "data": _read_system_config(settings)}
