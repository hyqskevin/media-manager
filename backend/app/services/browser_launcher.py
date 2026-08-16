import subprocess
import sys
from collections.abc import Callable
from typing import Any


class BrowserLaunchError(RuntimeError):
    pass


def open_xhs_login(
    settings,
    *,
    platform_name: str | None = None,
    run: Callable[..., Any] = subprocess.run,
) -> str:
    platform_name = platform_name or sys.platform
    url = settings.xhs_login_url
    browser = settings.xhs_login_browser
    if platform_name == "darwin":
        command = ["open", "-a", browser, url]
    elif platform_name.startswith("win"):
        command = ["cmd", "/c", "start", "", browser, url]
    else:
        executable = "google-chrome" if browser.lower() == "google chrome" else browser
        command = [executable, url]
    try:
        run(command, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BrowserLaunchError(f"无法打开 Chrome，请手动访问 {url}") from exc
    return url
