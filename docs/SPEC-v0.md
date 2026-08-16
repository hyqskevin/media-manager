# SPEC — media-manager（养号 + 平台账号 + 收藏夹）

> **版本:** v0.1.0 | **日期:** 2026-08-16
> **本仓库定位:** 媒体矩阵 Operate 子系统工程，**v0 范围** = 平台账号管理 + 自动养号 + 收藏夹
> **依赖服务:** xhs-info-crawl / ai-info-crawl (Browse)、ai-article-edit (Edit)、ai-poster-generate (Generate)
> **继承基线:** [上级 Operate 设计](../superpowers/plans/2026-08-03-media-manager-design.md) + [subsystems/operate](../subsystems/operate/overview.md)

---

## 1. 一句话定位

**多平台账号管理台 + 自动养号 + 收藏夹**，v0 不做"内容发布"（保留为后续 v1）。

## 2. v0 三大模块

| 模块 | 做什么 | 核心数据表 |
|------|------|-----------|
| **平台账号管理** | 8 个平台的账号 CRUD + 登录态 + 浏览器实例隔离 | `platforms`、`media_accounts` |
| **自动养号** | 主动浏览 feed + 点赞 + 收藏 + 收藏夹拉取（手动/定时触发） | `nurture_tasks`、`favorite_snapshots`、`nurture_schedules` |
| **收藏夹** | 各平台收藏夹列表入库快照 + 历史对比 | `favorite_snapshots`（同上表） |

## 3. 不在 v0 范围（v1 再做）

- ❌ 工作流看板 / 内容日历 / 数据中心 / 推送模块 / 素材库 / 规则引擎
- ❌ 多平台一键发布（这是 publish 模块，本次只做"看 / 赞 / 收"）
- ❌ 自研 Chrome 扩展 / WS Bridge（v0 复用 xhs-info-crawl 的 opencli + chrome_pool 跑通养号，v1 再考虑独立扩展）

## 4. 8 个平台与适配策略

| 平台 | 浏览 | 点赞 | 收藏 | 收藏夹列表 | 适配方式 |
|---|---|---|---|---|---|
| 小红书 xhs | ✅ | ✅ | ✅ | ✅ | opencli browser eval（继承 xhs-info-crawl） |
| 微博 weibo | ✅ | ✅ | ✅ | ✅ | opencli browser eval |
| 抖音 douyin | ✅ | ✅ | ✅ | ✅ | opencli browser eval |
| 知乎 zhihu | ✅ | ✅ (原生 API) | ✅ (原生 API) | ✅ (原生 API) | opencli 原生命令 |
| Twitter / X | ✅ | ✅ (原生 API) | ✅ (原生 API) | ✅ (原生 API) | opencli 原生命令 |
| B站 bilibili | ✅ | ✅ (原生 API) | ✅ (原生 API) | ✅ (原生 API) | opencli 原生命令 |
| 小宇宙 xiaoyuzhou | ✅ | ❌ | ✅ (原生 API) | ✅ | opencli browser + 原生 |
| 公众号 weixin | ✅ (浏览订阅号) | ❌ | ❌ | ❌ | opencli browser 仅浏览 |

## 5. 养号行为（防风控）

- **主动浏览**：打开平台 feed → 随机滚动 → 随机停留 5-30s → 记录浏览行为
- **点赞**：按配置概率（默认 5%）随机点赞 feed 内容
- **收藏**：按配置概率（默认 2%）随机收藏
- **收藏夹快照**：每次养号任务完成后拉取收藏夹列表入库，可查历史
- **风控**：复用 xhs 的验证码检测 + 自动暂停 + 安全停止

## 6. 技术栈（v0）

- 后端：FastAPI + SQLAlchemy + Celery + Redis（与 xhs-info-crawl 完全对齐）
- 数据库：SQLite（一期本地）+ PostgreSQL（v1 生产），Alembic 迁移
- 前端：Vue3 + Vite + Element Plus + Pinia（与 xhs-info-crawl 完全对齐）
- 浏览器：opencli + chrome_pool（直接复用 xhs 模块）
- 任务：Celery beat 定时扫描 `nurture_schedules`

## 7. 与其他子系统关系

```
┌──────────────┐
│   Browse     │ ← AI 推文所需热点（养号不需要，仅依赖）
│ (ai-info-    │
│  crawl)      │
└──────────────┘
        ▲
        │ （v1 才需要）
        │
┌───────┴──────────────────────────────────┐
│            media-manager (本仓库)        │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│   │ 平台账号 │ │  养号    │ │ 收藏夹   │ │
│   │ +Chrome  │ │  任务    │ │  快照    │ │
│   │ 池       │ │ +定时    │ │ +历史    │ │
│   └──────────┘ └──────────┘ └──────────┘ │
│        │              │             │    │
│        └──────────────┴─────────────┘    │
│                  ↓                        │
│            opencli + ChromePool (复用)    │
└───────────────────────────────────────────┘
```

v0 **不调用** Browse / Edit / Generate 的 HTTP 接口——养号纯靠浏览器操作，独立闭环。

## 8. 触发方式

- **手动**：前端按钮"开始养号" → 触发 Celery 任务 → 立即执行
- **定时**：Celery beat 每分钟扫描 `nurture_schedules` 表 → 到点触发
- **自动重试**：任务失败自动重试 3 次（指数退避）

## 9. 仓库目录（v0 精简）

```
media-manager/
├── backend/
│   ├── app/
│   │   ├── api/v1/accounts.py
│   │   ├── api/v1/nurture.py          ← 养号任务
│   │   ├── api/v1/favorites.py        ← 收藏夹
│   │   ├── api/v1/schedules.py        ← 定时计划
│   │   ├── core/                      ← config / database / security
│   │   ├── models/                    ← SQLAlchemy ORM
│   │   ├── services/
│   │   │   ├── platforms/             ← 8 个平台适配器（继承 xhs base）
│   │   │   ├── opencli_adapter.py     ← 复用
│   │   │   ├── chrome_pool.py         ← 复用
│   │   │   └── crawler.py             ← 复用（养号行为编排）
│   │   └── tasks/                     ← Celery 任务
│   ├── alembic/                       ← 迁移
│   └── tests/
├── frontend/
│   └── src/views/
│       ├── AccountsView.vue           ← 账号管理
│       ├── NurtureView.vue            ← 养号任务
│       ├── FavoritesView.vue          ← 收藏夹
│       └── SchedulesView.vue          ← 定时计划
└── scripts/ + Makefile
```

## 10. 不做事项（v0 明确排除）

- ❌ 多租户 / RBAC / Manager 网关接入（v1 接入 media-matrix 体系时再补）
- ❌ 审计日志（v1 接 media-common 的 `@audit_log`）
- ❌ 推送通知 / Webhook（v1 接 notify-service）
- ❌ 工作流 / 看板（v1 单独设计）
- ❌ 数据中心 / 图表（v1 单独设计）

## 11. 关联文档（本仓库 docs/）

- [docs/overview-v0.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/overview-v0.md) — v0 总览
- [docs/api-v0.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/api-v0.md) — v0 API
- [docs/database-v0.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/database-v0.md) — v0 数据表
- [docs/browser-bridge-v0.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/browser-bridge-v0.md) — v0 浏览器自动化
- [docs/ui-v0.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/ui-v0.md) — v0 UI

> **完整基线（继承自 xhs-info-crawl + 上级 Operate 设计）：**
> - [docs/overview.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/overview.md) — 完整 13 维度设计（继承基线）
> - [docs/api.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/api.md) — 完整 API 设计（继承基线）
> - [docs/database.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/database.md) — 完整数据库设计（继承基线）
> - [docs/browser-bridge.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/browser-bridge.md) — 完整浏览器桥接设计（继承基线）
> - [docs/ui.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/ui.md) — 完整 UI 设计（继承基线）