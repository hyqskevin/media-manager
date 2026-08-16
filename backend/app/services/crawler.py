class OpenCLIError(RuntimeError):
    pass


class OpenCLITimeout(OpenCLIError):
    pass


class AuthenticationRequired(OpenCLIError):
    pass


class VerificationRequired(AuthenticationRequired):
    pass


class CrawlHalted(Exception):
    """连续笔记处理失败达到阈值，任务应 PAUSED 等待用户决策（扫码/验证/结束）。"""
    pass


_VERIFICATION_SIGNALS = (
    "captcha",
    "安全验证",
    "请完成验证",
    "扫码验证",
    "异常访问验证",
    "risk verification",
)


def is_verification_required(message: str) -> bool:
    normalized = (message or "").strip().lower()
    return any(signal in normalized for signal in _VERIFICATION_SIGNALS)
