"""Twitter/X platform adapter (v0.2 stub, not implemented)."""
from app.services.platforms.twitter.adapter import TwitterAdapter
from app.services.platforms.registry import register

register(TwitterAdapter())
