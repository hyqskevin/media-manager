# media-manager · 多平台浏览器自动化养号管理台

> 媒体矩阵（media-matrix）账号运营管理台：基于 OpenCLI 浏览器自动化，跨平台（小红书/微博等）养号，支持主动浏览、点赞收藏、收藏夹管理。
> 本仓库从 `xhs-info-crawl` 继承而来，复用了其 OpenCLI 适配、Celery 任务、FastAPI + Vue3 管理台基建。

## 核心能力

- **多平台账号管理**：统一的平台/账号/登录态管理，支持小红书、微博等多平台扩展
- **自动养号行为**：模拟真人主动浏览平台页面（滚动 feed、停留时长随机化）
- **点赞 / 收藏**：按配置对推文执行点赞、收藏操作
- **收藏夹列表**：查看当前账号在各平台的收藏内容
- **定时任务**：Celery beat 按计划自动执行养号行为（继承自 xhs-info-crawl）

## 技术栈（继承自 xhs-info-crawl）

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy + Alembic + Celery + SQLite（一期） |
| 前端 | Vue 3 + Vite + Element Plus + Pinia |
| 浏览器自动化 | OpenCLI（`@jackwener/opencli`）+ Chrome（已登录态复用） |
| 任务 | Celery worker + beat（本地 filesystem broker） |

## 快速开始

需要本地装 `uv` + Node 22+ + Chrome + OpenCLI。

```bash
git clone https://github.com/hyqskevin/media-manager.git
cd media-manager
make init                     # 装依赖、建表、seed admin
```

四个终端分别跑：

```bash
make dev-api      # uvicorn → http://127.0.0.1:8000
make dev-worker   # celery worker (1 concurrency)
make dev-beat      # celery beat
make dev-web      # vite dev → http://127.0.0.1:5173
```

浏览器打开 <http://127.0.0.1:5173>，登录 `admin / Admin@123`。

> 详细安装、测试、迁移见 [`INSTALL.md`](INSTALL.md)。

## 仓库结构

```
media-manager/
├── README.md                ← 你正在读
├── INSTALL.md               ← 安装与初始化
├── AGENTS.md                ← AI 协作流程
├── Makefile                 ← 顶层快捷命令
├── .env.example             ← 环境变量样例
├── scripts/                 ← init / dev-* shims
├── backend/                 ← FastAPI + SQLAlchemy + Alembic + Celery
│   ├── app/
│   │   ├── api/v1/          ← HTTP endpoints
│   │   ├── models/          ← SQLAlchemy ORM
│   │   ├── services/        ← 业务服务（opencli 适配 / 养号行为 / 收藏夹等）
│   │   ├── tasks/           ← Celery 任务
│   │   └── core/            ← config / database / security
│   ├── migrations/          ← Alembic 版本
│   └── tests/               ← pytest
├── frontend/                ← Vue 3 + Vite + Element Plus + Pinia
│   ├── src/views/           ← 管理台视图
│   └── package.json
├── docs/                    ← 设计 / specs / 路线图
└── tests/                   ← E2E 测试案例（md）
```

## 常用命令

| 命令 | 作用 |
|---|---|
| `make init` | 安装依赖、建表、seed admin |
| `make dev-api` | 起 FastAPI (uvicorn) |
| `make dev-worker` | 起 Celery worker |
| `make dev-beat` | 起 Celery beat |
| `make dev-web` | 起 Vite dev server |
| `make migrate` | 升级 DB 到最新版本 |
| `make create-admin` | 手动创建/重置 admin |
| `make test` | 后端 + 前端测试 |
| `make build` | 前端生产构建 |

## 发版与 Release

- SemVer + git tag；每完成 `docs/TODO.md` 一项独立提交，稳定点打 tag。
- 详细开发约定见 [`AGENTS.md`](AGENTS.md)。

## License

Private phase-one prototype; licensing to be decided at a later stage.
