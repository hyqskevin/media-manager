"""微信公众号 platform adapter (v0.2 stub, not implemented)."""
from app.services.platforms.wechat_official.adapter import WechatOfficialAdapter
from app.services.platforms.registry import register

register(WechatOfficialAdapter())
