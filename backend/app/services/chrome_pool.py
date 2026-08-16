"""Chrome 实例池：为每个 XhsAccount 启动一个独立 Chrome 进程。

每个实例：
- 独立 --user-data-dir（隔离 cookie/历史/缓存）
- 独立 --remote-debugging-port（crawler 通过 OPENCLI_CDP_ENDPOINT 路由）
- 独立生命周期（release 时 SIGKILL）

绕开 opencli Browser Bridge 的多 profile 限制，真正实现账号级隔离。
关联 spec: docs/superpowers/specs/2026-08-12-chrome-pool-design.md
"""
from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# CDP 默认起始端口；如有冲突由 OS 分配，并回写到 instance.port
_CDP_PORT_START = 9223
_CDP_PORT_RANGE = 100  # 9223-9322 范围内分配
_CDP_READY_TIMEOUT_S = 10


class ChromeLaunchError(RuntimeError):
    """Chrome 实例启动失败（可恢复：用户可重试或排查 Chrome 路径）。"""


@dataclass
class ChromeInstance:
    """一个 Chrome 实例（一个 XhsAccount 对应一个）。"""

    session_name: str
    port: int
    user_data_dir: Path
    process: subprocess.Popen

    @property
    def cdp_endpoint(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def alive(self) -> bool:
        return self.process.poll() is None


class ChromePool:
    """管理 Chrome 实例的生命周期。

    用法：
        pool = ChromePool(chrome_bin=..., base_user_data_dir=Path('./data/chrome-pool'))
        a = pool.acquire('xhs-a')  # 启动 Chrome for 账号 A
        b = pool.acquire('xhs-b')  # 启动 Chrome for 账号 B
        ... # crawler 通过 a.cdp_endpoint 发请求
        pool.release_all()  # 全部 kill
    """

    def __init__(
        self,
        chrome_bin: str,
        base_user_data_dir: Path,
        cdp_port_start: int = _CDP_PORT_START,
    ) -> None:
        self._chrome_bin = chrome_bin
        self._base_user_data_dir = Path(base_user_data_dir)
        self._base_user_data_dir.mkdir(parents=True, exist_ok=True)
        self._cdp_port_start = cdp_port_start
        self._instances: dict[str, ChromeInstance] = {}
        self._next_port_offset = 0

    def acquire(self, session_name: str) -> ChromeInstance:
        """获取（或启动）该 session_name 对应的 Chrome 实例。已存在则直接复用。"""
        if session_name in self._instances:
            inst = self._instances[session_name]
            if inst.alive():
                return inst
            # 已死：清理 + 重新启动
            self._safe_kill(inst.process)
            self._instances.pop(session_name, None)

        if not Path(self._chrome_bin).exists():
            raise ChromeLaunchError(
                f"chrome 二进制不存在：{self._chrome_bin!r}"
                "（请确认 Chrome 已安装或更新 Settings.chrome_bin）"
            )

        port = self._next_port_offset % _CDP_PORT_RANGE + self._cdp_port_start
        self._next_port_offset += 1
        user_data_dir = self._base_user_data_dir / session_name
        user_data_dir.mkdir(parents=True, exist_ok=True)

        proc = self._launch(port=port, user_data_dir=user_data_dir)
        instance = ChromeInstance(
            session_name=session_name,
            port=port,
            user_data_dir=user_data_dir,
            process=proc,
        )
        self._instances[session_name] = instance
        self._wait_cdp_ready(instance)
        return instance

    def release(self, session_name: str) -> None:
        """释放指定 session_name 的 Chrome 实例（kill 子进程）。"""
        inst = self._instances.pop(session_name, None)
        if inst is None:
            return
        self._safe_kill(inst.process)

    def release_all(self) -> None:
        """释放所有 Chrome 实例。多次调用安全。"""
        for name in list(self._instances.keys()):
            self.release(name)

    def get(self, session_name: str) -> ChromeInstance | None:
        """已 acquire 的实例（不启动新实例）。"""
        return self._instances.get(session_name)

    def _launch(self, port: int, user_data_dir: Path) -> subprocess.Popen:
        cmd = [
            self._chrome_bin,
            "--headless=new=new",
            "--no-sandbox",
            "--disable-gpu",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "about:blank",
        ]
        try:
            return subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise ChromeLaunchError(f"无法启动 Chrome：{exc}") from exc

    def _wait_cdp_ready(self, instance: ChromeInstance, timeout: float = _CDP_READY_TIMEOUT_S) -> None:
        """轮询 CDP /json/version 直到就绪或超时。仅记录警告，不抛错（crawler 调 opencli 时仍会拿到错误）。"""
        import urllib.request
        import urllib.error

        # 允许测试桩短路：环境变量 OPENCLI_SKIP_CDP_READY=1 跳过 CDP 健康检查
        if os.environ.get("OPENCLI_SKIP_CDP_READY") == "1":
            return
        deadline = time.monotonic() + timeout
        url = f"{instance.cdp_endpoint}/json/version"
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=1) as resp:
                    if resp.status == 200:
                        return
            except (urllib.error.URLError, ConnectionError, OSError):
                time.sleep(0.2)
        logger.warning("Chrome 实例 %s 的 CDP 端点 %s 在 %ss 内未就绪", instance.session_name, instance.cdp_endpoint, timeout)

    @staticmethod
    def _safe_kill(proc: subprocess.Popen) -> None:
        if proc.poll() is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


# ── 全局单例（API 与 crawl_task 共享 ChromePool）──────────────────────────

_global_pool: ChromePool | None = None


def get_global_chrome_pool() -> ChromePool:
    """获取全局 ChromePool 单例（懒初始化）。

    用途：
    - API 端点（check-login）启动 Chrome 实例让用户扫码
    - crawl_task 任务启动时复用同池中的 Chrome

    何时释放：仅后端进程退出时（atexit）或显式调用 shutdown_global_chrome_pool()。
    """
    global _global_pool
    if _global_pool is None:
        from app.core.config import get_settings
        settings = get_settings()
        _global_pool = ChromePool(
            chrome_bin=settings.chrome_bin,
            base_user_data_dir=settings.resolve_project_path(settings.chrome_user_data_dir),
        )
    return _global_pool


def shutdown_global_chrome_pool() -> None:
    """释放全局 ChromePool（kill 所有 Chrome 进程）。"""
    global _global_pool
    if _global_pool is not None:
        _global_pool.release_all()
        _global_pool = None


import atexit as _atexit
_atexit.register(shutdown_global_chrome_pool)