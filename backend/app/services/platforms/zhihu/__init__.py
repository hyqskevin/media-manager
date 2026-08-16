"""知乎 platform adapter (v0.2 stub, not implemented)."""
from app.services.platforms.zhihu.adapter import ZhihuAdapter
from app.services.platforms.registry import register

register(ZhihuAdapter())
