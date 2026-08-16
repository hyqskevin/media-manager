"""子进程管理:启动/停止/重启 API/Worker/Beat 进程。

关联 spec: docs/superpowers/specs/2026-08-10-one-click-packaging-design.md § 2.1-2.2
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SERVICE_NAMES = ("api", "worker", "beat")


class ProcessManager:
    """管理 API/Worker/Beat 三个子进程。"""

    def __init__(self, project_root: Path, venv_python: Path):
        self.project_root = project_root
        self.venv_python = venv_python
        self._processes: dict[str, subprocess.Popen] = {}
        self._logs_dir = project_root / "data" / "logs"
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        # 默认命令模板(可被 _commands 覆盖,用于测试)
        self._commands = self._build_default_commands()

    def _build_default_commands(self) -> dict[str, list[str]]:
        """构建默认的服务启动命令。"""
        python = str(self.venv_python)
        backend_dir = self.project_root / "app" / "backend"
        # 从 .env 读 API_PORT(launcher.bootstrap_env 会写入),
        # 默认 8000 防止 .env 不存在时崩
        api_port = self._read_api_port(default=8000)
        return {
            "api": [python, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(api_port)],
            "worker": [python, "-m", "celery", "-A", "app.tasks.crawl_task", "worker", "--loglevel=info"],
            "beat": [python, "-m", "celery", "-A", "app.tasks.crawl_task", "beat", "--loglevel=info"],
        }

    def _read_api_port(self, default: int = 8000) -> int:
        """从 .env 读 API_PORT,找不到则用 default。"""
        env_path = self.project_root / ".env"
        if not env_path.exists():
            return default
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            if key.strip() == "API_PORT":
                try:
                    return int(value.strip())
                except ValueError:
                    return default
        return default

    def start_service(self, name: str) -> bool:
        """启动指定服务。"""
        if name not in SERVICE_NAMES:
            return False

        # 如果已在运行,直接返回成功
        if name in self._processes:
            proc = self._processes[name]
            if proc.poll() is None:
                return True
            del self._processes[name]

        cmd = self._commands.get(name)
        if not cmd:
            return False

        log_file = self._logs_dir / f"{name}.log"
        log_handle = open(log_file, "ab")

        env = {
            **os.environ,
            "PYTHONPATH": str(self.project_root / "app" / "backend"),
            # 强制无缓冲输出,确保日志实时写入文件
            "PYTHONUNBUFFERED": "1",
        }
        proc = subprocess.Popen(
            cmd,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            cwd=str(self.project_root),
            env=env,
        )
        self._processes[name] = proc
        logger.info("启动服务 %s (PID %d)", name, proc.pid)
        return True

    def stop_service(self, name: str, timeout: float = 5.0) -> bool:
        """停止指定服务。"""
        if name not in self._processes:
            return True

        proc = self._processes[name]
        if proc.poll() is not None:
            del self._processes[name]
            return True

        # 先 SIGTERM
        proc.terminate()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        del self._processes[name]
        logger.info("停止服务 %s", name)
        return True

    def restart_service(self, name: str) -> bool:
        """重启指定服务。"""
        self.stop_service(name)
        time.sleep(0.3)
        return self.start_service(name)

    def stop_all(self) -> None:
        """停止所有服务。"""
        for name in SERVICE_NAMES:
            self.stop_service(name)

    def get_status(self) -> dict:
        """获取所有服务状态。"""
        result = {}
        for name in SERVICE_NAMES:
            if name not in self._processes:
                result[name] = {"state": "stopped", "pid": None}
                continue

            proc = self._processes[name]
            if proc.poll() is None:
                result[name] = {"state": "running", "pid": proc.pid}
            else:
                result[name] = {"state": "crashed" if proc.returncode != 0 else "stopped", "pid": None}
                del self._processes[name]
        return result

    def get_logs_tail(self, lines: int = 50) -> list[str]:
        """获取最近日志(三个服务合并)。"""
        all_lines = []
        for name in SERVICE_NAMES:
            log_file = self._logs_dir / f"{name}.log"
            if not log_file.exists():
                continue
            try:
                content = log_file.read_text(encoding="utf-8", errors="ignore")
                file_lines = content.splitlines()[-lines:]
                all_lines.extend(file_lines)
            except Exception:
                continue
        return all_lines[-lines:]

    def cleanup(self) -> None:
        """清理资源(退出时调用)。"""
        self.stop_all()
