"""XHS web adapter (v0.2 only fully implemented platform)."""
from app.services.platforms.xhs_web.adapter import XhsWebAdapter
from app.services.platforms.registry import register

register(XhsWebAdapter())