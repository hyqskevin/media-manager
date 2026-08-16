# media-manager — v0 总览（养号 + 平台账号 + 收藏夹）

> **版本:** v0.1.0 | **日期:** 2026-08-16
> **本文件定位:** media-manager 仓库的精简总览，仅覆盖 v0 三块：平台账号管理、自动养号、收藏夹。
> **继承基线:** [上级 Operate 总体设计](../subsystems/operate/overview.md)（v0 已大幅精简）
> **依赖基线:** xhs-info-crawl（chrome_pool + opencli_adapter）

---

## 一、系统定位

media-manager 是 Operate 子系统的 v0 工程落地，专注于"**账号 + 养号 + 收藏**"三件事：

| 模块 | 做什么 | v1 何时做 |
|---|---|---|
| **平台账号管理** | 多平台账号 CRUD + 登录态校验 + Chrome 实例隔离 | ✅ v0 |
| **自动养号** | 主动浏览 feed / 点赞 / 收藏（手动+定时） | ✅ v0 |
| **收藏夹** | 各平台收藏夹列表入库 + 快照历史 | ✅ v0 |
| ~~工作流~~ | ~~看板 / 6 阶段状态机~~ | ❌ v1 |
| ~~推送模块~~ | ~~多平台一键发布~~ | ❌ v1 |
| ~~数据中心~~ | ~~粉丝/阅读/互动统计图~~ | ❌ v1 |
| ~~素材库 / 日历 / 规则~~ | | ❌ v1+ |

> **说明：** v0 不发布内容，只做"看 + 赞 + 收"，让账号活跃。v1 再加 publish（发布）。

---

## 二、v0 三大模块关系

```
┌──────────────────────────────────────────────────────────┐
│                  media-manager (v0)                       │
│                                                          │
│  ┌──────────────┐   触发养号    ┌──────────────┐         │
│  │ 平台账号管理  │ ───────────→ │  自动养号     │         │
│  │              │              │              │         │
│  │ • 8 平台账号  │   上传快照    │ • 主动浏览    │         │
│  │ • 登录态      │ ───────────→ │ • 点赞        │         │
│  │ • ChromePool │              │ • 收藏        │         │
│  │   隔离       │              │ • 拉收藏夹    │         │
│  └──────┬───────┘              └──────┬───────┘         │
│         │                              │                  │
│         │                              ▼                  │
│         │                       ┌──────────────┐         │
│         │    拉收藏夹列表       │  收藏夹       │         │
│         └────────────────────→ │              │         │
│                                 │ • 快照入库    │         │
│                                 │ • 历史对比    │         │
│                                 └──────────────┘         │
└──────────────────────────────────────────────────────────┘
```

---

## 三、8 平台适配策略（详细表见 SPEC §4）

| 平台 | 浏览 | 点赞 | 收藏 | 收藏夹 | 适配层 |
|---|---|---|---|---|---|
| 小红书 | ✅ opencli browser | ✅ opencli browser | ✅ opencli browser | ✅ opencli browser | 复用 xhs 适配器 |
| 微博 / 抖音 | opencli browser | opencli browser | opencli browser | opencli browser | 新增 |
| 知乎 / Twitter / B站 | opencli 原生命令 | opencli 原生命令 | opencli 原生命令 | opencli 原生命令 | 新增 |
| 小宇宙 / 公众号 | opencli browser | - | 小宇宙 opencli 原生 / 公众号无 | 小宇宙 opencli 原生 / 公众号无 | 新增 |

> 复用层：[opencli_adapter.py](../opencli_adapter.py) + [chrome_pool.py](../chrome_pool.py)（直接 import）

---

## 四、养号行为设计（v0）

### 4.1 行为步骤（每个养号任务）

```
[1] 选账号 → 取该账号的平台 chrome_pool 实例（独立 CDP port）
[2] 登录态校验 → check_auth() 失败 → 标记 relogin_required，跳过
[3] 打开平台首页 → 等待加载
[4] 滚动 feed 随机 5-15 次 → 每次随机停留 5-30s
[5] 按概率点赞 / 收藏 → 调用对应适配器
[6] 拉取收藏夹列表 → 写入 favorite_snapshots
[7] 关闭浏览器 / 归还实例
```

### 4.2 配置参数（每账号独立）

```json
{
  "browse_count": 10,            // 一次任务浏览多少条
  "browse_min_dwell_sec": 5,
  "browse_max_dwell_sec": 30,
  "like_probability": 0.05,       // 点赞概率 0-1
  "favorite_probability": 0.02,   // 收藏概率 0-1
  "snapshot_favorites": true,    // 任务完成后是否拉收藏夹
  "daily_max_tasks": 3,           // 每天最多自动触发几次
  "quiet_hours": "00:00-07:00"    // 静默时段不触发
}
```

### 4.3 风控（继承 xhs）

- 检测到验证码 → 自动暂停 → 标记 `account.status='relogin_required'`
- 行为频率限制（每天 / 每小时最多 N 次操作）
- 行为随机化（避免固定模式触发风控）

---

## 五、技术栈（v0）

| 层 | 技术 | 说明 |
|---|---|---|
| 后端 | FastAPI 0.110+ | REST API |
| ORM | SQLAlchemy 2.0+ | 异步 |
| DB | SQLite（一期）/ PostgreSQL 16（v1） | Alembic 迁移 |
| 任务 | Celery 5.3+ | 异步养号任务 |
| Broker | Redis 7.0+ | Celery broker + beat 调度 |
| 浏览器 | opencli + chrome_pool | 复用 xhs |
| 前端 | Vue3 + Vite + Element Plus | 与 xhs-info-crawl 对齐 |

> **关键决策：** 不引入 Postgres/Redis/Docker 等生产栈到 v0，本地 SQLite + filesystem broker 即可跑通。v1 再升级。

---

## 六、工程目录（v0 精简）

```
media-manager/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── accounts.py          # 账号管理 API
│   │   │   ├── nurture.py           # 养号任务 API
│   │   │   ├── favorites.py         # 收藏夹 API
│   │   │   └── schedules.py         # 定时计划 API
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/
│   │   │   ├── platform.py
│   │   │   ├── media_account.py
│   │   │   ├── nurture_task.py
│   │   │   ├── favorite_snapshot.py
│   │   │   └── nurture_schedule.py
│   │   ├── services/
│   │   │   ├── platforms/           # 8 个平台适配器
│   │   │   │   ├── base.py
│   │   │   │   ├── xiaohongshu.py   # 复用 xhs
│   │   │   │   ├── weibo.py
│   │   │   │   ├── douyin.py
│   │   │   │   ├── zhihu.py
│   │   │   │   ├── twitter.py
│   │   │   │   ├── bilibili.py
│   │   │   │   ├── xiaoyuzhou.py
│   │   │   │   └── weixin.py
│   │   │   ├── nurture_service.py   # 养号行为编排
│   │   │   ├── favorite_service.py  # 收藏夹快照入库
│   │   │   ├── opencli_adapter.py   # 复用 xhs
│   │   │   └── chrome_pool.py       # 复用 xhs
│   │   └── tasks/
│   │       ├── nurture_tasks.py     # Celery 养号
│   │       └── schedule_tasks.py    # Celery beat 定时扫描
│   ├── alembic/
│   └── tests/
├── frontend/
│   └── src/views/
│       ├── AccountsView.vue
│       ├── NurtureView.vue
│       ├── FavoritesView.vue
│       └── SchedulesView.vue
├── data/                            # chrome-pool user-data + sqlite
├── docs/
├── scripts/ + Makefile
└── SPEC.md
```

---

## 七、v0 阶段路线

| 阶段 | 交付 | 周期 |
|---|---|---|
| v0.1 | 仓库初始化 + Spec 文档 + 继承 xhs 模块 | ✅ 当前 |
| v0.2 | `media_accounts` + `platforms` 数据表 + 账号 CRUD API | 1 周 |
| v0.3 | `chrome_pool` 改造为多账号独立端口 + 8 平台适配器 | 1.5 周 |
| v0.4 | `nurture_tasks` + 主动浏览/点赞/收藏 + 前端触发 | 1.5 周 |
| v0.5 | `favorite_snapshots` + 收藏夹列表入库 + 历史对比 UI | 1 周 |
| v0.6 | `nurture_schedules` + Celery beat 定时触发 | 0.5 周 |

---

## 八、关联文档

- [本仓库 SPEC.md](../SPEC.md)
- [API 设计](./api.md)
- [数据库设计](./database.md)
- [浏览器自动化（opencli + chrome_pool）](./browser-bridge.md)
- [UI 设计](./ui.md)
- [上级 Operate 总体设计](../subsystems/operate/overview.md)（完整 8 模块基线）
- [继承基线 xhs-info-crawl](https://github.com/hyamaki_macmini/xhs-info-crawl)