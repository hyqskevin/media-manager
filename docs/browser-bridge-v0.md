# media-manager — v0 浏览器自动化设计

> **版本:** v0.1.0 | **日期:** 2026-08-16
> **本文件定位:** 复用 xhs-info-crawl 的 opencli + chrome_pool，**不**自研 Chrome 扩展 / WS Bridge
> **继承基线:** [上级 Operate Browser Bridge 设计](../subsystems/operate/browser-bridge.md)（WS / 自研扩展架构，v1 才考虑）

---

## 一、为什么 v0 不自研 Chrome 扩展 / WS Bridge

- **成本高：** Manifest V3 + WS 双向 + Session Router + Token 鉴权 + 重连 + 心跳，要 3-4 周工程量
- **养号场景不需要：** 养号是**异步长任务**（单次 5-30 分钟），不是"实时双向指令"，不需要 WS 双向通信
- **opencli 已够用：** opencli browser eval + 原生命令 + chrome_pool 实例隔离，已经能跑通 8 平台养号
- **复用代码：** 直接 import [xhs-info-crawl chrome_pool.py](file:///Users/hanamaki_mac_mini/Documents/github/project/xhs-info-crawl/backend/app/services/chrome_pool.py) 和 [opencli_adapter.py](file:///Users/hanamaki_mac_mini/Documents/github/project/xhs-info-crawl/backend/app/services/opencli_adapter.py)

**v0 架构：** FastAPI 后端 → Celery worker → opencli CLI → 独立 Chrome 实例（每个账号独立 user-data-dir + CDP 端口）

---

## 二、chrome_pool 多账号独立实例

### 2.1 核心机制

```python
# 每个 media_account 分配独立的：
# 1. CDP 端口（9223-9322 范围）
# 2. Chrome user-data-dir（cookie 完全隔离）
# 3. opencli session 名
# → 多账号同时登录同一个平台不互相踢出
```

### 2.2 启动流程

```
[1] 用户新增账号 → POST /api/v1/manage/accounts
[2] 后端分配 cdp_port（9223-9322 范围，按 account_id hash）
[3] 创建 chrome_user_data_dir（data/chrome-pool/<account_id>/）
[4] 后台启动 Chrome（headless 或 headful 由 config 控制）：
    chrome --headless --user-data-dir=<dir> --remote-debugging-port=<cdp_port>
[5] opencli 客户端通过 OPENCLI_CDP_ENDPOINT=http://localhost:<cdp_port> 路由
```

### 2.3 复用代码示例

```python
# 直接 import xhs 的 chrome_pool
from xhs_info_crawl.backend.app.services.chrome_pool import ChromePool

# 改造点：把 XhsAccount 改成 MediaAccount（字段更多）
# xhs 的 chrome_pool 已经按 CDP 端口隔离实例，无需重写
```

---

## 三、opencli 适配策略

### 3.1 三类适配方式

| 平台 | 适配方式 | opencli 命令 |
|---|---|---|
| 小红书 / 微博 / 抖音 | opencli browser eval（点击 DOM） | `opencli browser eval '<JS 脚本>'` |
| 知乎 / Twitter / B站 / 小宇宙 | opencli 原生命令（API） | `opencli like <url>` / `opencli favorite <url>` |
| 公众号 | opencli browser 仅浏览 | `opencli browser eval '<滚动 JS>'` |

### 3.2 平台适配器接口

每个平台实现 `platforms/base.py` 抽象基类：

```python
from abc import ABC, abstractmethod
from typing import List, Optional

class PlatformAdapter(ABC):
    """8 平台统一接口（养号场景）"""

    @abstractmethod
    def platform_name(self) -> str:
        """返回平台标识：xhs / weibo / douyin / zhihu / twitter / bilibili / xiaoyuzhou / weixin"""

    @abstractmethod
    def supports_like(self) -> bool:
        """是否支持点赞"""

    @abstractmethod
    def supports_favorite(self) -> bool:
        """是否支持收藏"""

    @abstractmethod
    def supports_favorites_list(self) -> bool:
        """是否支持拉取收藏夹列表"""

    @abstractmethod
    async def whoami(self, cdp_endpoint: str) -> dict:
        """检查登录态，返回 {is_valid, platform_user_id, platform_user_name, avatar}"""

    @abstractmethod
    async def browse_feed(self, cdp_endpoint: str, count: int, dwell_range: tuple) -> List[dict]:
        """主动浏览 feed
        :param count: 浏览条数
        :param dwell_range: (min_sec, max_sec) 停留时长随机范围
        :return: 浏览的 item 列表 [{item_external_id, title, url, author, ...}]
        """

    @abstractmethod
    async def like(self, cdp_endpoint: str, item_url: str) -> bool:
        """点赞，返回是否成功"""

    @abstractmethod
    async def favorite(self, cdp_endpoint: str, item_url: str) -> bool:
        """收藏，返回是否成功"""

    @abstractmethod
    async def list_favorites(self, cdp_endpoint: str) -> List[dict]:
        """拉取收藏夹列表
        :return: [{item_external_id, title, url, author, thumbnail, favorited_at}, ...]
        """
```

### 3.3 适配器实现策略

| 平台 | whoami | browse_feed | like / favorite | list_favorites |
|---|---|---|---|---|
| 小红书 | opencli browser eval | 打开首页 + 滚动脚本 | DOM 点击 like/favorite 按钮 | 打开收藏页 + 解析 DOM |
| 微博 | 同上 | 同上 | 同上 | 同上 |
| 抖音 | 同上 | 同上 | 同上 | 同上 |
| 知乎 | opencli 原生命令 | opencli 原生命令 | `opencli like <url>` | opencli 原生命令 |
| Twitter | opencli 原生命令 | opencli 原生命令 | `opencli like <url>` | `opencli favorites list` |
| B站 | opencli 原生命令 | opencli 原生命令 | `opencli favorite <url>` | `opencli favorites list` |
| 小宇宙 | 仅浏览 | opencli browser eval | ❌（不支持） | opencli 原生命令 |
| 公众号 | 仅浏览 | opencli browser eval | ❌ | ❌ |

---

## 四、养号行为编排（nurture_service）

### 4.1 任务执行流程

```python
# nurture_tasks.py - Celery 任务
@celery.task(bind=True)
def execute_nurture_task(self, task_id: str):
    """执行一个养号任务"""
    task = db.query(NurtureTask).get(task_id)
    account = db.query(MediaAccount).get(task.account_id)
    
    # 1. 校验
    if not account.enabled or account.status != 'active':
        task.status = 'failed'
        task.error_message = '账号未启用或状态异常'
        return
    
    # 2. 启动 chrome 实例（如果未启动）
    chrome = chrome_pool.ensure_started(account)
    
    # 3. 选择适配器
    adapter = platform_registry.get(account.platform.name)
    
    # 4. 执行行为（按 action 类型）
    task.status = 'running'
    task.started_at = now()
    
    if task.action in ('browse', 'like', 'favorite', 'full'):
        items = await adapter.browse_feed(
            chrome.cdp_endpoint,
            count=task.config_snapshot['browse_count'],
            dwell_range=(5, 30)
        )
        task.browse_count = len(items)
        
        if task.action in ('like', 'full') and adapter.supports_like():
            like_n = int(len(items) * task.config_snapshot['like_probability'])
            for item in random.sample(items, like_n):
                if await adapter.like(chrome.cdp_endpoint, item['url']):
                    task.like_count += 1
                    db.add(BrowseLog(action='like', ...))
        
        if task.action in ('favorite', 'full') and adapter.supports_favorite():
            fav_n = int(len(items) * task.config_snapshot['favorite_probability'])
            for item in random.sample(items, fav_n):
                if await adapter.favorite(chrome.cdp_endpoint, item['url']):
                    task.favorite_count += 1
                    db.add(BrowseLog(action='favorite', ...))
    
    if task.action in ('snapshot', 'full') and adapter.supports_favorites_list():
        favorites = await adapter.list_favorites(chrome.cdp_endpoint)
        batch_id = str(uuid4())
        for fav in favorites:
            db.add(FavoriteSnapshot(
                account_id=account.id,
                platform=account.platform.name,
                snapshot_batch=batch_id,
                snapshot_at=now(),
                **fav
            ))
        task.snapshot_count = len(favorites)
    
    task.status = 'success'
    task.finished_at = now()
```

### 4.2 风控机制

| 机制 | 实现 | 触发后行为 |
|---|---|---|
| **验证码检测** | 监听每个 opencli 调用返回 + 页面 DOM 关键词（`captcha` / `verify` / `滑块`） | 自动暂停 + 标记 `account.status='relogin_required'` |
| **行为频率限制** | Redis 计数器，每账号每小时最多 N 次操作 | 超限跳过 |
| **随机化** | 每次浏览停留时长随机 + 点赞概率随机 + 浏览路径随机 | 防风控画像 |
| **失败重试** | Celery 任务失败自动重试 3 次（指数退避） | 持续失败则标记 `account.status='relogin_required'` |
| **静默时段** | `account.config.quiet_hours` 范围内不触发 | 定时任务扫描时跳过 |

### 4.3 并发与限流

- 单账号：**串行**（避免同账号并发触发风控）
- 多账号：**并行**（不同账号互不影响）
- 平台级：**可选限流**（同平台 N 个账号同时养号时排队）

---

## 五、与 xhs-info-crawl 的复用关系

| 模块 | 来源 | 改造点 |
|---|---|---|
| `opencli_adapter.py` | 复用 xhs | 无需改造 |
| `chrome_pool.py` | 复用 xhs | 1. 改 XhsAccount → MediaAccount 2. 增加 cdp_port 范围 9223-9322 |
| `crawler.py` | 复用 xhs | 抽取"通用浏览/收藏"逻辑，平台差异部分下沉到 PlatformAdapter |
| `platforms/xiaohongshu.py` | 复用 xhs | 实现新 PlatformAdapter 接口 |
| 其他 7 个平台 | 新增 | 参考小红书实现 |

**复用方式：** 通过 Python 包导入（[xhs-info-crawl](file:///Users/hanamaki_mac_mini/Documents/github/project/xhs-info-crawl) 的 backend/ 直接当模块用），或者把 `services/` 抽取到独立的 `media-common` 共享包（v1 抽取）。

---

## 六、v1 升级路径（什么时候做 WS Bridge）

需要自研 Chrome 扩展 + WS Bridge 的场景：
- v1 **发布模块**（Operate publish）需要实时双向通信（服务端下发指令 → 扩展执行 → 回传结果）
- v1 **多平台一键推送** 需要并发控制 + 重试 + 进度回传
- v1 **接入 media-matrix 体系** 后，Manager 网关要求所有子系统用统一 WS 通信规范

届时再开发：
- 自研 Chrome 扩展（Manifest V3 + Cookie 读取 + 平台 API 调用）
- `/ws/bridge` WebSocket 端点
- Session Router（token → Chrome Profile 映射）
- 离线任务暂存（Redis Sorted Set）

具体设计参考 [上级 Operate Browser Bridge 设计](../subsystems/operate/browser-bridge.md)。

---

## 七、关联文档

- [本仓库 SPEC.md](../SPEC.md)
- [v0 总览](./overview.md)
- [API 设计](./api.md)
- [数据库设计](./database.md)
- [UI 设计](./ui.md)
- [上级 Operate Browser Bridge 设计](../subsystems/operate/browser-bridge.md)（v1 升级参考）
- [继承基线 xhs-info-crawl chrome_pool](file:///Users/hanamaki_mac_mini/Documents/github/project/xhs-info-crawl/backend/app/services/chrome_pool.py)