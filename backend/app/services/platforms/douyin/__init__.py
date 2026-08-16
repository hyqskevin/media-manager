"""抖音 platform adapter (v0.2 stub, not implemented)."""
from app.services.platforms.douyin.adapter import DouyinAdapter
from app.services.platforms.registry import register

register(DouyinAdapter())
