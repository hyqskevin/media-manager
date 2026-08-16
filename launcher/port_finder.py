"""端口探测:从指定范围找可用端口。"""
from __future__ import annotations

import socket


def find_available_port(start: int = 8000, end: int = 8020) -> int:
    """从 start 开始找可用端口,上限 end。

    Args:
        start: 起始端口(含)
        end: 结束端口(含)

    Returns:
        第一个可用端口

    Raises:
        RuntimeError: 所有端口都被占用
    """
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"端口 {start}-{end} 全部被占用,请手动在 .env 中配置 API_PORT")
