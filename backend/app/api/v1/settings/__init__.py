"""聚合 settings 下各子 router，并对外暴露 ``router``。

子模块：
- ``cities``         城市 CRUD + 批量删除
- ``keyword_groups`` 关键词组 CRUD + 批量删除
- ``blogger_groups`` 博主组 CRUD + 批量删除
- ``system_config``  系统配置（.env）+ opencli 配置/测试/打开登录页
- ``bloggers``       博主 CRUD + 批量删除 + 导入/补充 + 通用 ``/{kind}``

xhs-accounts 端点在 ``app/api/v1/xhs_accounts.py``（独立 router），不在本包内。

为兼容测试中 ``monkeypatch.setattr("app.api.v1.settings.get_settings", ...)``
和 ``monkeypatch.setattr("app.api.v1.settings.open_xhs_login", ...)`` 的写法，
``__init__`` 把这两个名字提升到包级；endpoint 通过延迟 import
（``from app.api.v1.settings import get_settings``）查找，monkeypatch 后能正确看到新值。
"""
from fastapi import APIRouter

# 在 ``include_router`` 之前先 import 子模块，确保它们的 handler 已绑定。
from app.api.v1.settings import bloggers, blogger_groups, cities, keyword_groups, system_config
from app.api.v1.settings.bloggers import get_settings
from app.api.v1.settings.system_config import open_xhs_login  # noqa: F401  (re-export for tests)

router = APIRouter()

# 注册顺序：具体路径先于 ``/{kind}`` 通用路径；``bloggers`` 含通用路由，放最后。
# 注意：FastAPI 在 ``include_router`` 阶段只收集路由，真正的匹配发生在请求时。
# 由于每个子 router 已各自使用 ``/settings/...`` 完整路径，``include_router`` 之间
# 不会发生 catch-all 误吞。子 router 内部的 ``/{kind}`` 与其自身具体路径的匹配
# 顺序由各子 router 内的注册顺序决定（具体路径在 catch-all 之前注册）。
router.include_router(cities.router)
router.include_router(keyword_groups.router)
router.include_router(blogger_groups.router)
router.include_router(system_config.router)
router.include_router(bloggers.router)


__all__ = [
    "router",
    "get_settings",
    "open_xhs_login",
]
