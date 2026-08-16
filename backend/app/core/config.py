import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "小红书本地活动信息抓取系统"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    web_host: str = "127.0.0.1"
    web_port: int = 5173
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    secret_key: str = "change-me-in-local-env"
    jwt_expire_hours: int = 24
    project_root: Path = Path(__file__).resolve().parents[3]
    database_url: str | None = None
    celery_broker_url: str = "filesystem://"
    celery_timezone: str = "Asia/Shanghai"
    celery_worker_pool: str = "solo"
    celery_worker_concurrency: int = 1
    celery_log_level: str = "INFO"
    weekly_crawl_day_of_week: int = 1
    weekly_crawl_hour: int = 2
    weekly_crawl_minute: int = 0
    opencli_cdp_endpoint: str = "http://localhost:9222"
    opencli_bin: str = "opencli"
    xhs_login_url: str = "https://www.xiaohongshu.com/explore"
    xhs_login_browser: str = "Google Chrome"
    search_interval_min: int = 10
    search_interval_max: int = 15
    search_limit: int = 50
    weekly_search_limit: int = 500
    consecutive_note_failure_limit: int = 3
    # 连续 N 篇 note.content 为空触发 PAUSED；默认 5（防小红书风控静默失败）
    crawl_empty_detail_threshold: int = 5
    # 每抓 N 条调一次 adapter.close_session() 重建 CDP 连接；0 表示禁用
    crawl_session_reset_interval: int = 30
    minimax_api_key: str = ""
    minimax_base_url: str = "https://api.minimaxi.com/v1"
    minimax_model: str = "MiniMax-M3"
    minimax_vision_model: str = "MiniMax-vision-01"
    minimax_chat_path: str = "/text/chatcompletion_v2"
    minimax_timeout_seconds: int = 180
    ocr_enabled: bool = False
    ocr_language: str = "ch"
    ocr_min_confidence: float = 0.5
    ocr_use_doc_orientation_classify: bool = False
    ocr_use_doc_unwarping: bool = False
    ocr_use_textline_orientation: bool = False
    # 笔记内图片并行 OCR 线程数（1-4，本地 PaddleOCR 模型，不占网络带宽）
    ocr_parallel_workers: int = 2
    # MiniMax API 并发调用数（1-4，默认 1 向后兼容，小范围并行避免 529 限流）
    minimax_concurrency: int = 1
    # PaddleOCR 3.x 模型缓存目录(通过环境变量 PADDLE_PDX_CACHE_HOME 生效)
    paddle_pdx_cache_home: Path = Field(
        Path("./data/paddlex"),
        validation_alias="PADDLE_PDX_CACHE_HOME",
    )
    # HuggingFace 缓存目录(paddlex 传递依赖,通过环境变量 HF_HOME 生效)
    huggingface_cache_home: Path = Field(
        Path("./data/huggingface"),
        validation_alias="HF_HOME",
    )
    # 前端构建产物目录(打包版用,开发模式不存在则跳过挂载)
    frontend_dist_path: Path = Field(
        Path("./frontend/dist"),
        validation_alias="FRONTEND_DIST_PATH",
    )
    xhs_search_target_count: int = 50
    xhs_search_scroll_max_rounds: int = 8
    xhs_detail_scroll_max_rounds: int = 8
    xhs_scroll_pixels: int = 800
    xhs_scroll_stagnant_rounds: int = 2
    pipeline_stage_max_retries: int = 2
    pipeline_stage_retry_delay_seconds: float = 2
    activity_future_window_days: int = 60
    # 多账号轮询：每个账号连续抓 N 篇后主动切换到下一个账号（避免触发频率限制）
    # 仅当配置了 ≥2 个已启用账号时生效；=1 时不切换
    account_rotation_notes: int = 25
    data_dir_setting: Path = Field(Path("./data"), validation_alias="DATA_DIR")
    image_dir_setting: Path = Field(Path("./data/images"), validation_alias="IMAGE_DIR")
    export_dir_setting: Path = Field(Path("./data/exports"), validation_alias="EXPORT_DIR")
    archive_dir_setting: Path = Field(Path("./data/archive"), validation_alias="ARCHIVE_DIR")
    celery_folder_setting: Path = Field(Path("./data/celery"), validation_alias="CELERY_FOLDER")
    # 任务子进程注册表路径（跨 API 与 worker 进程共享）
    task_registry_path: Path = Field(
        Path("./data/run/task_registry.json"), validation_alias="TASK_REGISTRY_PATH"
    )
    # 临时文件目录（如海报渲染的临时 HTML）
    tmp_dir_setting: Path = Field(Path("./data/tmp"), validation_alias="TMP_DIR")
    # ChromePool 启动的多 Chrome 实例的 user-data-dir 根目录
    chrome_user_data_dir: Path = Field(
        Path("./data/chrome-pool"), validation_alias="CHROME_USER_DATA_DIR"
    )
    # Chrome 二进制路径（ChromePool 启动用）
    chrome_bin: str = Field(
        "google-chrome",
        validation_alias="CHROME_BIN",
    )

    def resolve_project_path(self, path: Path) -> Path:
        return path if path.is_absolute() else self.project_root / path

    @computed_field
    @property
    def data_dir(self) -> Path:
        return self.resolve_project_path(self.data_dir_setting)

    @computed_field
    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "app.db"

    @computed_field
    @property
    def image_dir(self) -> Path:
        return self.resolve_project_path(self.image_dir_setting)

    @computed_field
    @property
    def export_dir(self) -> Path:
        return self.resolve_project_path(self.export_dir_setting)

    @computed_field
    @property
    def archive_dir(self) -> Path:
        return self.resolve_project_path(self.archive_dir_setting)

    @computed_field
    @property
    def celery_folder(self) -> Path:
        return self.resolve_project_path(self.celery_folder_setting)

    @computed_field
    @property
    def task_registry_file(self) -> Path:
        """解析后的任务注册表文件路径（绝对路径，在项目内）。"""
        return self.resolve_project_path(self.task_registry_path)

    @computed_field
    @property
    def tmp_dir(self) -> Path:
        """解析后的临时文件目录（绝对路径，在项目内）。"""
        return self.resolve_project_path(self.tmp_dir_setting)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def effective_database_url(self) -> str:
        if self.database_url and self.database_url.startswith("sqlite:///./"):
            relative_path = self.database_url.removeprefix("sqlite:///./")
            return f"sqlite:///{(self.project_root / relative_path).resolve()}"
        return self.database_url or f"sqlite:///{self.sqlite_path}"

    def ensure_runtime_directories(self) -> None:
        for path in (
            self.sqlite_path.parent,
            self.image_dir,
            self.export_dir,
            self.archive_dir,
            self.celery_folder / "queue",
            self.celery_folder / "processed",
            self.task_registry_file.parent,
            self.tmp_dir,
            self.resolve_project_path(self.paddle_pdx_cache_home),
            self.resolve_project_path(self.huggingface_cache_home),
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # 关键:在 Python 进程启动时设置环境变量,确保 paddleocr/huggingface 不污染用户 home
    # 之前只靠 scripts/dev-worker.sh 的 export,直接跑 uvicorn/celery 时会缺失
    cache_home = str(settings.paddle_pdx_cache_home.resolve())
    hf_home = str(settings.huggingface_cache_home.resolve())
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", cache_home)
    os.environ.setdefault("HF_HOME", hf_home)
    # 确保目录存在
    settings.paddle_pdx_cache_home.mkdir(parents=True, exist_ok=True)
    settings.huggingface_cache_home.mkdir(parents=True, exist_ok=True)
    return settings
