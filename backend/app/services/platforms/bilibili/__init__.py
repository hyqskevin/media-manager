"""B站 platform adapter (v0.2 stub, not implemented)."""
from app.services.platforms.bilibili.adapter import BilibiliAdapter
from app.services.platforms.registry import register

register(BilibiliAdapter())
