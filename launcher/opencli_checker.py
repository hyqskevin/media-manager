"""OpenCLI 连接测试:调用 opencli doctor 检测连接状态。

关联 spec: docs/superpowers/specs/2026-08-10-one-click-packaging-design.md § 2.5
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

OPENCLI_DOWNLOAD_URL = "https://opencli.info/download"


@dataclass
class OpenCLIResult:
    """OpenCLI 测试结果。"""
    ok: bool
    version: str = ""
    reason: str = ""
    message: str = ""


def _find_opencli() -> str | None:
    """查找 opencli 可执行文件。

    优先级:
    1. 系统 PATH(用户终端装的位置)
    2. ~/.local/bin/opencli(OpenCLIApp 默认安装位置)
    3. /usr/local/bin/opencli
    4. ~/Library/Application Support/opencli/bin/opencli
    """
    # 1. shutil.which 已经在 PATH 中查找
    found = shutil.which("opencli")
    if found:
        return found

    # 2. 显式检查常见 GUI 安装路径(macOS 上 .app 启动时 PATH 不完整)
    candidates = [
        Path.home() / ".local" / "bin" / "opencli",
        Path.home() / "Library" / "Application Support" / "opencli" / "bin" / "opencli",
        Path("/usr/local/bin/opencli"),
        Path("/opt/homebrew/bin/opencli"),
    ]
    for c in candidates:
        if c.exists() and os.access(c, os.X_OK):
            logger.info("在 %s 找到 opencli", c)
            return str(c)
    return None


def check_opencli(timeout: float = 10.0) -> OpenCLIResult:
    """测试 OpenCLI 连接。

    调用 `opencli doctor`,解析输出判断连接状态。
    """
    bin_path = _find_opencli()
    if not bin_path:
        return OpenCLIResult(
            ok=False,
            reason="not_installed",
            message="未安装 OpenCLI,请点 [下载 OpenCLI] 安装",
        )

    try:
        proc = subprocess.run(
            [bin_path, "doctor"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return OpenCLIResult(
            ok=False,
            reason="not_installed",
            message="未安装 OpenCLI,请点 [下载 OpenCLI] 安装",
        )
    except subprocess.TimeoutExpired:
        return OpenCLIResult(
            ok=False,
            reason="timeout",
            message=f"opencli doctor 超时({timeout}s),请检查 OpenCLIApp 是否正常运行",
        )

    output = (proc.stdout or "") + (proc.stderr or "")
    # 兼容两种 opencli doctor 输出格式:
    # 老版本: "daemon: ok" / "extension: connected"
    # 新版本(>=1.8.5): "[OK] Daemon: running on port ..." / "[OK] Extension: connected"
    daemon_ok = (
        "daemon: ok" in output.lower()
        or "[ok] daemon" in output.lower()
        or "everything looks good" in output.lower()
    )
    extension_ok = (
        "extension: connected" in output.lower()
        or "[ok] extension" in output.lower()
    )
    if proc.returncode == 0 and (daemon_ok or extension_ok):
        # 从 opencli v1.8.5 doctor (node v24.16.0) 提取版本
        version_match = re.search(r"opencli\s+v?([\d.]+)", output, re.IGNORECASE)
        version = version_match.group(1) if version_match else ""
        return OpenCLIResult(ok=True, version=version, message="连接正常")

    stderr = proc.stderr or ""
    stdout = proc.stdout or ""
    if "daemon not running" in stderr or "daemon not running" in stdout:
        return OpenCLIResult(
            ok=False,
            reason="daemon_not_running",
            message="OpenCLIApp 未启动,请打开 OpenCLIApp 应用",
        )
    if "extension not connected" in stderr or "extension not connected" in stdout:
        return OpenCLIResult(
            ok=False,
            reason="extension_not_connected",
            message="未装 Chrome 扩展,在 OpenCLIApp 里点 [安装扩展]",
        )

    return OpenCLIResult(
        ok=False,
        reason="unknown_error",
        message=stderr.strip() or stdout.strip() or "未知错误",
    )
