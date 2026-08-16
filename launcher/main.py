"""启动器入口:PyWebView 窗口 + 进程管理 + 状态服务。

关联 spec: docs/superpowers/specs/2026-08-10-one-click-packaging-design.md § 2 + § 4
"""
from __future__ import annotations

import logging
import sys
import threading
import uvicorn
from pathlib import Path

from launcher.env_bootstrap import (
    ensure_env_file,
    force_local_host,
    set_cache_env_vars,
    update_env_value,
)
from launcher.port_finder import find_available_port
from launcher.process_manager import ProcessManager
from launcher.status_server import StatusServer

logger = logging.getLogger(__name__)


def get_project_root() -> Path:
    """获取项目根目录(启动器所在目录的父目录)。"""
    return Path(__file__).parent.parent.resolve()


def get_venv_python(project_root: Path) -> Path:
    """获取便携 Python 解释器路径。"""
    if sys.platform == "darwin":
        return project_root / "runtime" / "venv" / "bin" / "python"
    else:
        return project_root / "runtime" / "venv" / "Scripts" / "python.exe"


def bootstrap_env(project_root: Path) -> int:
    """初始化 .env + 找端口 + 设置环境变量。返回 API 端口。"""
    env_path = project_root / ".env"
    env_example_path = project_root / ".env.example"

    # 1. 确保 .env 存在
    ensure_env_file(env_path, env_example_path)

    # 2. 强制 API_HOST=127.0.0.1
    force_local_host(env_path)

    # 3. 设置缓存环境变量
    set_cache_env_vars(project_root)

    # 4. 找可用端口
    api_port = find_available_port(start=8001, end=8020)
    update_env_value(env_path, "API_PORT", str(api_port))

    return api_port


def main():
    """启动器主入口。"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    project_root = get_project_root()
    venv_python = get_venv_python(project_root)

    logger.info("启动器启动,项目根目录: %s", project_root)

    # 1. 初始化环境
    api_port = bootstrap_env(project_root)
    logger.info("API 端口: %d", api_port)

    # 2. 创建进程管理器
    pm = ProcessManager(project_root=project_root, venv_python=venv_python)

    # 3. 创建状态服务
    status_server = StatusServer(
        process_manager=pm,
        project_root=project_root,
        venv_python=venv_python,
        api_base_url=f"http://127.0.0.1:{api_port}",
    )

    # 4. 启动状态服务(在后台线程)
    status_port = find_available_port(start=9000, end=9020)
    status_thread = threading.Thread(
        target=lambda: uvicorn.run(status_server.app, host="127.0.0.1", port=status_port, log_level="warning"),
        daemon=True,
    )
    status_thread.start()
    logger.info("状态服务启动: http://127.0.0.1:%d", status_port)

    # 5. 启动后端服务
    pm.start_service("api")
    pm.start_service("worker")
    pm.start_service("beat")

    # 6. 启动 PyWebView 窗口
    try:
        import webview
        ui_dist = project_root / "launcher" / "ui" / "dist"
        if ui_dist.exists():
            # 同时传 statusPort(状态服务)和 apiPort(业务 API 端口)
            url = f"file://{ui_dist / 'index.html'}?statusPort={status_port}&apiPort={api_port}"
        else:
            # 开发模式:用占位 HTML
            url = f"data:text/html,<html><body><h1>启动器 UI 未构建</h1><p>请先 cd launcher/ui && npm run build</p><p>状态服务: http://127.0.0.1:{status_port}</p></body></html>"

        # 暴露给前端的 API:
        # - open_url(url):用系统默认浏览器打开 URL
        # - open_dir(path):在 Finder/Explorer 打开本地路径
        # - exit():退出启动器
        class Api:
            def __init__(self, project_root: Path):
                self._project_root = project_root

            def open_url(self, url: str) -> None:
                import webbrowser
                webbrowser.open(url)

            def open_dir(self, path: str) -> str:
                """在系统文件管理器(Finder/Explorer)中打开目录。返回绝对路径。"""
                import subprocess
                target = Path(path)
                if not target.is_absolute():
                    target = self._project_root / path
                target = target.resolve()
                if not target.exists():
                    raise FileNotFoundError(f"路径不存在: {target}")
                if sys.platform == "darwin":
                    subprocess.Popen(["open", str(target)])
                elif sys.platform.startswith("win"):
                    subprocess.Popen(["explorer", str(target)])
                else:
                    subprocess.Popen(["xdg-open", str(target)])
                return str(target)

            def exit(self) -> None:
                import webview as _wv
                if _wv.windows:
                    for w in _wv.windows:
                        w.destroy()

        api = Api(project_root=project_root)

        webview.create_window(
            "小红书活动信息抓取系统",
            url,
            width=900,
            height=700,
            min_size=(720, 600),
            js_api=api,
        )
        webview.start()
    finally:
        # 窗口关闭时清理
        logger.info("启动器退出,清理资源")
        pm.cleanup()


if __name__ == "__main__":
    main()
