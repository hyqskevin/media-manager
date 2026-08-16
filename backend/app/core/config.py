"""应用配置（pydantic-settings，从环境变量 + .env 加载）。"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """media-manager 全局配置。"""

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 服务 ──
    media_backend_host: str = "0.0.0.0"
    media_backend_port: int = 8000

    # ── 数据库（SQLite 一期）──
    database_url: str = f"sqlite:///{ROOT_DIR / 'data' / 'media.db'}"

    # ── 安全 ──
    initial_admin_password: str = "Admin@123"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expires_hours: int = 12

    # ── v0.2 养号 ──
    nurture_global_enabled: bool = False  # 默认关闭,强制显式开启

    # ── Celery ──
    celery_broker_url: str = "memory://"
    celery_result_backend: str = "cache+memory://"


_settings: Settings | None = None


def get_settings() -> Settings:
    """单例获取 settings。"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings