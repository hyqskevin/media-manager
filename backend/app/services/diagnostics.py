"""仪表盘连接检测：opencli 二进制 / 小红书 whoami / Chrome CDP。

关联 spec: docs/superpowers/specs/2026-08-03-diagnostics-panel-design.md

每个 probe 是独立的轻量探测，失败原因分类可读。供 ``app.api.v1.diagnostics`` 路由调用。
"""
from __future__ import annotations

import json
import logging
import re
import shutil
import socket
import subprocess
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from app.core.config import Settings
from app.services.crawler import AuthenticationRequired, OpenCLIError, OpenCLITimeout
from app.services.opencli_adapter import OpenCLIAdapter


logger = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _safe_version(bin_path: str, timeout: float = 5.0) -> str | None:
    """尝试 ``opencli --version``；失败返回 None，不抛。"""
    try:
        proc = subprocess.run(
            [bin_path, "--version"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = (proc.stdout or proc.stderr or "").strip()
    return out or None


# ≥此版本走 daemon+扩展模式检测；<此版本走 CDP 端口检测。
DAEMON_MODE_MIN_VERSION: tuple[int, int, int] = (1, 8, 5)

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _parse_opencli_version(text: str | None) -> tuple[int, int, int] | None:
    """从 ``opencli --version`` 输出提取语义化版本。

    支持 ``v1.8.5`` / ``1.8.5`` / ``opencli v1.8.5`` 等格式。
    返回 ``(major, minor, patch)`` 或 None（无法解析）。
    """
    if not text:
        return None
    match = _VERSION_RE.search(text)
    if not match:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _parse_daemon_status(text: str) -> dict[str, Any]:
    """解析 ``opencli daemon status`` 输出。"""
    result: dict[str, Any] = {
        "daemon_running": None,
        "extension_connected": None,
        "profiles": [],
        "daemon_port": None,
    }
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("Daemon: running"):
            result["daemon_running"] = True
        elif line.startswith("Daemon: stopped") or line.startswith("Daemon: not running"):
            result["daemon_running"] = False
        elif line.startswith("Extension: connected"):
            result["extension_connected"] = True
        elif line.startswith("Extension: disconnected"):
            result["extension_connected"] = False
        elif line.startswith("Profiles:"):
            profiles_part = line.split(":", 1)[1].strip()
            if profiles_part:
                # 每个形如 "jjm94buu v1.0.22"，取首个 token 作为 profile id
                result["profiles"] = [p.split()[0] for p in profiles_part.split(",") if p.split()]
        elif line.startswith("Port:"):
            try:
                result["daemon_port"] = int(line.split(":", 1)[1].strip())
            except (IndexError, ValueError):
                pass
    return result


def _probe_daemon(bin_path: str, timeout: float = 5.0) -> dict[str, Any]:
    """运行 ``opencli daemon status``，返回 ``{success, output}``。"""
    try:
        proc = subprocess.run(
            [bin_path, "daemon", "status"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"success": False, "output": None}
    return {"success": proc.returncode == 0, "output": proc.stdout}


def probe_opencli(settings: Settings) -> dict[str, Any]:
    """探测 opencli 二进制是否在 PATH。

    返回 ``{ok, bin, resolved, reason, version}``。
    """
    bin_name = (settings.opencli_bin or "opencli").strip() or "opencli"
    resolved = shutil.which(bin_name)
    if not resolved:
        return {
            "ok": False,
            "bin": bin_name,
            "resolved": None,
            "reason": f"opencli 不在 PATH，请设置 OPENCLI_BIN 环境变量指向 {bin_name} 的绝对路径",
            "version": None,
        }
    version = _safe_version(resolved)
    return {
        "ok": True,
        "bin": bin_name,
        "resolved": resolved,
        "reason": None,
        "version": version,
    }


def probe_xhs_login(settings: Settings) -> dict[str, Any]:
    """探测当前 Chrome 是否登录小红书。

    返回 ``{logged_in, username, user_id, reason}``；``reason`` 取值
    ``auth_required / timeout / other / None``。
    """
    try:
        payload = OpenCLIAdapter(settings).check_login()
    except AuthenticationRequired:
        return {"logged_in": False, "username": None, "user_id": None, "reason": "auth_required"}
    except OpenCLITimeout:
        return {"logged_in": False, "username": None, "user_id": None, "reason": "timeout"}
    except OpenCLIError as exc:
        return {"logged_in": False, "username": None, "user_id": None, "reason": "other", "error": str(exc)}
    except Exception as exc:  # pragma: no cover - 兜底
        logger.warning("probe_xhs_login unexpected error: %s", exc)
        return {"logged_in": False, "username": None, "user_id": None, "reason": "other", "error": str(exc)}

    if isinstance(payload, dict):
        username = payload.get("username") or payload.get("nickname") or payload.get("name")
        user_id = (
            payload.get("user_id")
            or payload.get("id")
            or payload.get("platform_user_id")
        )
    else:
        username = None
        user_id = None
    return {
        "logged_in": True,
        "username": username,
        "user_id": user_id,
        "reason": None,
    }


def _cdp_host_port(endpoint: str) -> tuple[str, int] | None:
    parsed = urlparse(endpoint)
    host = parsed.hostname
    port = parsed.port
    if not host or not port:
        return None
    return host, port


def _probe_cdp(endpoint: str, timeout: float = 2.0) -> tuple[bool, str | None]:
    addr = _cdp_host_port(endpoint)
    if not addr:
        return False, f"CDP 端点格式无效：{endpoint}"
    host, port = addr
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, None
    except OSError as exc:
        return False, f"CDP 端点 {endpoint} 连接失败：{exc}"


def probe_xhs_pool(settings: Settings) -> dict[str, Any]:
    """探测浏览器连接：按 opencli 版本路由到 daemon 或 CDP 检测。

    版本 ≥(1,8,5) → daemon+扩展模式检测；
    版本 <(1,8,5) → CDP 端口检测；
    版本解析失败 → 能力探测兜底（先 daemon，失败再 CDP）。

    返回 ``{mode, version, version_tuple, daemon_running, extension_connected,
    profiles, daemon_port, cdp_endpoint, cdp_reachable, sessions, reason}``。
    """
    bin_name = (settings.opencli_bin or "opencli").strip() or "opencli"
    resolved = shutil.which(bin_name)

    base: dict[str, Any] = {
        "mode": "unknown",
        "version": None,
        "version_tuple": None,
        "daemon_running": None,
        "extension_connected": None,
        "profiles": [],
        "daemon_port": None,
        "cdp_endpoint": None,
        "cdp_reachable": None,
        "sessions": [],
        "reason": None,
    }

    if not resolved:
        base["reason"] = f"opencli 不在 PATH，请设置 OPENCLI_BIN 环境变量指向 {bin_name} 的绝对路径"
        return base

    version_raw = _safe_version(resolved)
    version_tuple = _parse_opencli_version(version_raw)
    base["version"] = version_raw
    base["version_tuple"] = list(version_tuple) if version_tuple else None

    # 确定模式：版本驱动为主，版本解析失败时能力探测兜底
    daemon_output: str | None = None
    if version_tuple is not None:
        use_daemon = version_tuple >= DAEMON_MODE_MIN_VERSION
    else:
        # 版本解析失败 → 先试 daemon status
        daemon_result = _probe_daemon(resolved)
        daemon_output = daemon_result["output"] if daemon_result["success"] else None
        use_daemon = daemon_output is not None

    if use_daemon:
        base["mode"] = "daemon"
        output = daemon_output
        if output is None:  # 版本路由路径需主动获取
            daemon_result = _probe_daemon(resolved)
            if not daemon_result["success"] or not daemon_result["output"]:
                base["reason"] = "opencli daemon status 命令失败"
                return base
            output = daemon_result["output"]
        parsed = _parse_daemon_status(output)
        base["daemon_running"] = parsed["daemon_running"]
        base["extension_connected"] = parsed["extension_connected"]
        base["profiles"] = parsed["profiles"]
        base["daemon_port"] = parsed["daemon_port"]
        if not parsed["daemon_running"]:
            base["reason"] = "daemon 未运行"
        elif not parsed["extension_connected"]:
            base["reason"] = "浏览器扩展未连接"
        elif not parsed["profiles"]:
            base["reason"] = "未找到已连接的浏览器 profile"
        return base

    # CDP 模式（版本 <1.8.5 或兜底路径 daemon 失败）
    endpoint = settings.opencli_cdp_endpoint
    base["cdp_endpoint"] = endpoint
    reachable, reason = _probe_cdp(endpoint)
    base["cdp_reachable"] = reachable
    sessions: list[dict[str, Any]] = []
    if reachable:
        try:
            proc = subprocess.run(
                [resolved, "browser", "list", "--format", "json"],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
            )
            out = (proc.stdout or "").strip()
            if out:
                parsed_json = json.loads(out)
                if isinstance(parsed_json, list):
                    sessions = [row for row in parsed_json if isinstance(row, dict)]
                elif isinstance(parsed_json, dict) and "sessions" in parsed_json and isinstance(parsed_json["sessions"], list):
                    sessions = [row for row in parsed_json["sessions"] if isinstance(row, dict)]
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            logger.info("probe_xhs_pool browser list 解析失败：%s", exc)
    base["sessions"] = sessions
    base["reason"] = reason
    # 兜底路径下 CDP 也不可达 → mode=unknown
    if version_tuple is None and not reachable:
        base["mode"] = "unknown"
    else:
        base["mode"] = "cdp"
    return base


def probe_snapshot(settings: Settings) -> dict[str, Any]:
    """三合一聚合，任一 probe 异常都被隔离不影响其它段。"""
    sections: dict[str, dict[str, Any]] = {}
    for name, fn in (
        ("opencli", probe_opencli),
        ("xhs_login", probe_xhs_login),
        ("xhs_pool", probe_xhs_pool),
    ):
        try:
            sections[name] = fn(settings)
        except Exception as exc:  # pragma: no cover - 防御
            logger.warning("probe_snapshot %s unexpected error: %s", name, exc)
            sections[name] = {"ok": False, "reason": str(exc)}
    sections["checked_at"] = _iso_now()
    return sections