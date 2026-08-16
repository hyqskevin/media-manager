"""OCR 增强包下载安装器。

关联 spec: docs/superpowers/specs/2026-08-10-one-click-packaging-design.md § 5
"""
from __future__ import annotations

import datetime
import hashlib
import logging
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

GITHUB_RELEASE_BASE = "https://github.com/hyqskevin/xhs-info-crawl/releases/download"
MIN_DISK_BYTES = 3 * 1024 * 1024 * 1024  # 3 GB


@dataclass
class OcrInstallResult:
    """OCR 安装结果。"""
    ok: bool
    message: str = ""
    version: str = ""


def get_addon_url(os_name: str, arch: str, version: str) -> str:
    """获取对应平台/架构的 OCR 增强包下载 URL。"""
    return f"{GITHUB_RELEASE_BASE}/ocr-addon-{version}/paddleocr-addon-{version}-{os_name}-{arch}.zip"


def get_ocr_status(project_root: Path) -> dict:
    """获取 OCR 安装状态。

    Returns:
        {"status": "not_installed"|"installing"|"installed", "version": "..."}
    """
    paddlex_dir = project_root / "data" / "paddlex"
    installing_marker = paddlex_dir / ".installing"
    version_file = paddlex_dir / ".ocr_addon_version"
    models_dir = paddlex_dir / "official_models"

    if installing_marker.exists():
        return {"status": "installing", "version": ""}

    if version_file.exists() and models_dir.exists() and any(models_dir.iterdir()):
        version = ""
        for line in version_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("version:"):
                version = line.split(":", 1)[1].strip()
        return {"status": "installed", "version": version}

    return {"status": "not_installed", "version": ""}


def _get_disk_free_bytes(path: Path) -> int:
    """获取 path 所在磁盘的可用空间(字节)。"""
    usage = shutil.disk_usage(str(path))
    return usage.free


def _download_file(url: str, dest: Path, progress_callback: Optional[Callable[[int, int], None]] = None) -> bool:
    """下载文件,支持进度回调。返回 True 成功。"""
    import httpx
    with httpx.stream("GET", url, follow_redirects=True, timeout=300) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_bytes(chunk_size=1024 * 1024):
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    progress_callback(downloaded, total)
    return True


def _sha256(path: Path) -> str:
    """计算文件 SHA256。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _extract_zip(zip_path: Path, dest_dir: Path) -> bool:
    """解压 zip 到 dest_dir。"""
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dest_dir)
    return True


def _pip_install_wheels(wheels_dir: Path, venv_python: Path) -> bool:
    """用 venv 的 pip 安装 wheels 目录下的 wheel 文件。"""
    wheels = list(wheels_dir.glob("*.whl"))
    if not wheels:
        return False
    cmd = [str(venv_python), "-m", "pip", "install", "--no-deps", "--force-reinstall"]
    cmd.extend(str(w) for w in wheels)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return result.returncode == 0


def download_and_install(
    project_root: Path,
    os_name: str,
    arch: str,
    version: str,
    venv_python: Path,
    expected_sha256: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> OcrInstallResult:
    """下载并安装 OCR 增强包。

    流程:
    1. 检查磁盘空间(至少 3GB)
    2. 下载 zip 到 data/tmp/
    3. 校验 SHA256(如果提供)
    4. 解压:wheels 用 pip 装到 venv;模型放到 data/paddlex/official_models/
    5. 写 .ocr_addon_version
    """
    paddlex_dir = project_root / "data" / "paddlex"
    tmp_dir = project_root / "data" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    paddlex_dir.mkdir(parents=True, exist_ok=True)

    # 1. 磁盘空间检查
    free_bytes = _get_disk_free_bytes(project_root)
    if free_bytes < MIN_DISK_BYTES:
        free_gb = free_bytes / (1024 ** 3)
        return OcrInstallResult(
            ok=False,
            message=f"磁盘空间不足:需要至少 3 GB,当前可用 {free_gb:.1f} GB",
        )

    # 2. 下载
    url = get_addon_url(os_name, arch, version)
    zip_path = tmp_dir / f"paddleocr-addon-{version}-{os_name}-{arch}.zip"
    installing_marker = paddlex_dir / ".installing"
    installing_marker.touch()

    try:
        _download_file(url, zip_path, progress_callback)

        # 3. SHA256 校验
        if expected_sha256:
            actual_hash = _sha256(zip_path)
            if actual_hash != expected_sha256:
                zip_path.unlink(missing_ok=True)
                return OcrInstallResult(
                    ok=False,
                    message=f"SHA256 校验失败:期望 {expected_sha256},实际 {actual_hash}",
                )

        # 4. 解压
        extract_dir = tmp_dir / f"ocr-addon-extract-{version}"
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        _extract_zip(zip_path, extract_dir)

        # 5. 安装 wheels
        wheels_dir = extract_dir / "wheels"
        if wheels_dir.exists():
            _pip_install_wheels(wheels_dir, venv_python)

        # 6. 复制模型到 data/paddlex/official_models/
        models_src = extract_dir / "data" / "paddlex" / "official_models"
        if models_src.exists():
            models_dest = paddlex_dir / "official_models"
            models_dest.mkdir(parents=True, exist_ok=True)
            for item in models_src.iterdir():
                dest_item = models_dest / item.name
                if dest_item.exists():
                    if dest_item.is_dir():
                        shutil.rmtree(dest_item)
                    else:
                        dest_item.unlink()
                shutil.move(str(item), str(dest_item))

        # 7. 写版本文件
        version_file = paddlex_dir / ".ocr_addon_version"
        version_file.write_text(
            f"version: {version}\n"
            f"built_at: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n",
            encoding="utf-8",
        )

        # 8. 清理临时文件
        shutil.rmtree(extract_dir, ignore_errors=True)
        zip_path.unlink(missing_ok=True)

        return OcrInstallResult(ok=True, message="安装成功", version=version)

    except Exception as exc:
        logger.error("OCR 安装失败: %s", exc, exc_info=True)
        return OcrInstallResult(ok=False, message=f"安装失败: {exc}")
    finally:
        installing_marker.unlink(missing_ok=True)
