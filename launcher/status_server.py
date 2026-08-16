"""本地状态 HTTP 服务:启动器 UI 通过这个服务查询和控制后端进程。

关联 spec: docs/superpowers/specs/2026-08-10-one-click-packaging-design.md § 2.2 + § 4.4
"""
from __future__ import annotations

import logging
import platform
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from launcher.opencli_checker import check_opencli, OPENCLI_DOWNLOAD_URL, OpenCLIResult
from launcher.ocr_installer import get_ocr_status, download_and_install, OcrInstallResult
from launcher.process_manager import ProcessManager

logger = logging.getLogger(__name__)


class StatusServer:
    """启动器本地状态服务。

    UI 通过 fetch 轮询这个服务来获取/控制状态。
    """

    def __init__(
        self,
        process_manager: ProcessManager,
        project_root: Path,
        venv_python: Path,
        api_base_url: str = "http://127.0.0.1:8000",
    ):
        self.process_manager = process_manager
        self.project_root = project_root
        self.venv_python = venv_python
        self.api_base_url = api_base_url
        self._install_thread: Optional[threading.Thread] = None
        self._install_progress: dict = {"active": False, "percent": 0, "message": ""}
        self.app = self._create_app()

    def _create_app(self) -> FastAPI:
        app = FastAPI(title="Launcher Status Server")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @app.get("/status")
        def get_status():
            return self.process_manager.get_status()

        @app.get("/api-port")
        def get_api_port():
            """返回后端 API 实际监听的端口(用于启动器 UI 打开业务前端)。"""
            # 从 api_base_url (如 http://127.0.0.1:8001) 解析端口
            from urllib.parse import urlparse
            parsed = urlparse(self.api_base_url)
            return {"port": parsed.port or 8000}

        @app.post("/service/{name}/restart")
        def restart_service(name: str):
            success = self.process_manager.restart_service(name)
            return {"ok": success}

        @app.post("/service/all/stop")
        def stop_all():
            self.process_manager.stop_all()
            return {"ok": True}

        @app.get("/opencli/test")
        def test_opencli():
            result: OpenCLIResult = check_opencli()
            return {
                "ok": result.ok,
                "version": result.version,
                "reason": result.reason,
                "message": result.message,
            }

        @app.get("/opencli/download-url")
        def opencli_download_url():
            return {"url": OPENCLI_DOWNLOAD_URL}

        @app.get("/ocr/status")
        def ocr_status():
            return get_ocr_status(self.project_root)

        @app.post("/ocr/install")
        def ocr_install():
            if self._install_progress.get("active"):
                return {"ok": False, "message": "已有安装任务在运行"}
            os_name = "macos" if platform.system() == "Darwin" else "windows"
            arch = "arm64" if platform.machine() in ("arm64", "aarch64") else "x64"
            version = "3.7.0"

            def run_install():
                self._install_progress = {"active": True, "percent": 0, "message": "下载中"}
                try:
                    result: OcrInstallResult = download_and_install(
                        project_root=self.project_root,
                        os_name=os_name,
                        arch=arch,
                        version=version,
                        venv_python=self.venv_python,
                    )
                    self._install_progress = {
                        "active": False,
                        "percent": 100 if result.ok else 0,
                        "message": result.message,
                        "ok": result.ok,
                    }
                except Exception as exc:
                    self._install_progress = {
                        "active": False,
                        "percent": 0,
                        "message": f"安装失败: {exc}",
                        "ok": False,
                    }

            self._install_thread = threading.Thread(target=run_install, daemon=True)
            self._install_thread.start()
            return {"ok": True, "message": "安装已启动"}

        @app.get("/ocr/install-progress")
        def ocr_install_progress():
            return self._install_progress

        @app.post("/ocr/test")
        def ocr_test():
            # 调后端 /api/v1/diagnostics/ocr
            import httpx
            try:
                resp = httpx.post(f"{self.api_base_url}/api/v1/diagnostics/ocr", timeout=30)
                if resp.status_code == 200:
                    return resp.json().get("data", {})
                return {"ok": False, "reason": "api_error", "message": f"API 返回 {resp.status_code}"}
            except Exception as exc:
                return {"ok": False, "reason": "api_unreachable", "message": str(exc)}

        @app.get("/logs/tail")
        def logs_tail(lines: int = 50):
            return {"lines": self.process_manager.get_logs_tail(lines)}

        return app
