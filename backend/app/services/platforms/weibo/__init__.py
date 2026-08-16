"""Weibo platform adapter (v0.2 stub, not implemented)."""
from app.services.platforms.weibo.adapter import WeiboAdapter
from app.services.platforms.registry import register

register(WeiboAdapter())