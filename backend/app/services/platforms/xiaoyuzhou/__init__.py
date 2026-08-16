"""小宇宙 platform adapter (v0.2 stub, not implemented)."""
from app.services.platforms.xiaoyuzhou.adapter import XiaoyuzhouAdapter
from app.services.platforms.registry import register

register(XiaoyuzhouAdapter())
