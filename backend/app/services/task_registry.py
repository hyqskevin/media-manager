"""任务子进程注册表：跨进程跟踪正在运行的爬虫子进程 PID。

后端 FastAPI 进程和 worker Celery 进程通过项目内 `data/run/task_registry.json` 共享状态：
- worker `run_crawl` 启动子进程时 register(task_id, pid)
- worker 子进程退出时 unregister(task_id)
- 用户点停止时，后端从 registry 找到 PID 发 SIGTERM

文件结构：
{
    "1": {"pid": 12345, "registered_at": 1700000000.0},
    "2": {"pid": 67890, "registered_at": 1700000001.5}
}

并发安全：使用 fcntl.flock 文件锁。

路径配置：通过 Settings.task_registry_path 配置，默认 `./data/run/task_registry.json`，
所有写操作限制在项目内，不污染 /tmp 等系统目录。模块加载时解析一次，
测试可通过 monkeypatch REGISTRY_PATH 隔离。
"""

from __future__ import annotations

import fcntl
import json
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.config import get_settings


def _resolve_registry_path() -> Path:
    """从 Settings 解析注册表路径（项目内绝对路径）。"""
    return get_settings().task_registry_file


# 模块加载时解析一次；测试可 monkeypatch 此变量隔离
REGISTRY_PATH: Path = _resolve_registry_path()


@contextmanager
def _file_lock(path: Path) -> Iterator[None]:
    """对 registry 文件加排他锁；跨进程安全。"""
    path.touch(exist_ok=True)
    fd = open(path, "r+")
    try:
        fcntl.flock(fd.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd.fileno(), fcntl.LOCK_UN)
        fd.close()


def _read() -> dict:
    if not REGISTRY_PATH.exists():
        return {}
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _write(data: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _key(task_id: int, run_token: str | None = None) -> str:
    return f"{task_id}:{run_token}" if run_token else str(task_id)


def register(task_id: int, pid: int, run_token: str | None = None) -> None:
    """注册任务的子进程 PID。

    多次 register 同一 task_id 会覆盖（保留最新 PID）。
    """
    with _file_lock(REGISTRY_PATH):
        data = _read()
        data[_key(task_id, run_token)] = {
            "pid": pid,
            "run_token": run_token,
            "registered_at": time.time(),
        }
        _write(data)


def unregister(task_id: int, run_token: str | None = None) -> None:
    """取消注册任务的子进程 PID。"""
    with _file_lock(REGISTRY_PATH):
        data = _read()
        data.pop(_key(task_id, run_token), None)
        _write(data)


def get(task_id: int, run_token: str | None = None) -> dict | None:
    """读取任务的子进程 PID 信息；不存在返回 None。"""
    with _file_lock(REGISTRY_PATH):
        return _read().get(_key(task_id, run_token))


def kill(task_id: int, *, run_token: str | None = None, timeout: float = 5.0) -> bool:
    """尝试 SIGTERM 终止任务子进程；立即发送 SIGKILL 确保进程快速退出。

    为了让 worker 在 opencli 阻塞时能及时响应停止信号，先发送 SIGTERM，
    然后立即发送 SIGKILL，不等待进程自然退出。

    Returns:
        True 如果进程被 kill 或已经不存在；False 如果杀不掉。
    """
    import os
    import signal

    info = get(task_id, run_token)
    if info is None:
        return True
    pid = info["pid"]
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        unregister(task_id, run_token)
        return True
    except PermissionError:
        unregister(task_id, run_token)
        return True

    # 立即发送 SIGKILL，不等待进程自然退出
    # 这是关键：opencli 子进程可能被 CDP 超时阻塞，无法响应 SIGTERM
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass

    # 等待进程真正退出
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            unregister(task_id, run_token)
            return True
        time.sleep(0.1)

    # The API process is not the OpenCLI process parent, so a successfully
    # killed child can remain visible as a zombie until the worker reaps it.
    # Keep the registry entry for the worker's token-aware unregister call.
    return True
