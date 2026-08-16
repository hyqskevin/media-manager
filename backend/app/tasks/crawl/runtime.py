"""任务运行时辅助：守卫、日志、进度、调度常量、异常类。

- ``assert_execution_active`` / ``finish_stop_if_requested``：run_token + 状态守卫；
- ``log`` / ``set_progress``：TaskLog 写入 + CrawlTask 进度更新；
- ``rate_limit_sleep``：可被 stop 守卫打断的 sleep；
- ``find_opencli``：shutil.which 的薄封装，便于测试 monkeypatch；
- ``ExecutionStopped`` / ``ExecutionSuperseded``：run_crawl 内部终止信号。
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import logging
import shutil
import time

from sqlalchemy import func, select, update

from app.models.schedule import ScheduledCrawl
from app.models.task import CrawlTask, TaskLog


logger = logging.getLogger(__name__)

_DISPATCH_TZ = ZoneInfo("Asia/Shanghai")
_BUSY_STATUSES = ("PENDING", "RUNNING", "STOP_REQUESTED")


class ExecutionStopped(Exception):
    pass


class ExecutionSuperseded(Exception):
    pass


def find_opencli(bin_name: str) -> str | None:
    """解析 opencli 可执行文件路径（shutil.which 的薄封装，测试可 patch）。"""
    return shutil.which(bin_name)


def rate_limit_sleep(seconds: float, guard: Callable[[], None] | None = None) -> None:
    """可中断的频率控制 sleep：0.5s 分片，每片执行 guard（执行栅栏），stop 请求 0.5s 内响应。"""
    deadline = time.monotonic() + max(0.0, seconds)
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(0.5, remaining))
        if guard:
            guard()


def assert_execution_active(db, task_id: int, run_token: str) -> None:
    row = db.execute(
        select(CrawlTask.status, CrawlTask.run_token).where(CrawlTask.id == task_id)
    ).one_or_none()
    if row is None or row.run_token != run_token:
        raise ExecutionSuperseded()
    if row.status in {"STOP_REQUESTED", "STOPPED"}:
        raise ExecutionStopped()
    if row.status != "RUNNING":
        raise ExecutionSuperseded()


def log(db, task_id: int, level: str, message: str) -> None:
    db.add(TaskLog(task_id=task_id, level=level, message=message))
    db.commit()


def set_progress(db, task: CrawlTask, run_token: str, stage: str, current_note: str | None = None) -> None:
    changed = db.execute(
        update(CrawlTask)
        .where(
            CrawlTask.id == task.id,
            CrawlTask.run_token == run_token,
            CrawlTask.status == "RUNNING",
        )
        .values(current_stage=stage, current_note=current_note)
    )
    db.commit()
    if changed.rowcount != 1:
        assert_execution_active(db, task.id, run_token)
    db.refresh(task)


def finish_stop_if_requested(db, task_id: int, run_token: str) -> bool:
    current = db.get(CrawlTask, task_id)
    db.refresh(current)
    if current.run_token != run_token:
        raise ExecutionSuperseded()
    if current.status not in ("STOP_REQUESTED", "STOPPED"):
        return False
    if current.status != "STOPPED":
        current.status = "STOPPED"
        current.current_stage = None
        current.current_note = None
        current.finished_at = datetime.now(timezone.utc)
        db.commit()
        log(db, current.id, "INFO", "任务已安全停止")
    return True
