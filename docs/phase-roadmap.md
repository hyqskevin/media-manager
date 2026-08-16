# 分阶段交付设计

## 设计目标

项目分两个阶段交付。第一阶段优先形成可在个人电脑直接运行的完整业务闭环；第二阶段在不重写前端、API 和核心业务服务的前提下，升级数据、队列、对象存储和部署基础设施。

## 阶段一：本地轻量版

### 范围

- 前端保持 Vue 3 + TypeScript + Vite + Element Plus。
- 后端使用 Python 3.11 + FastAPI。
- 异步任务与定时任务继续使用 Celery Worker + Celery Beat。
- Celery 使用 filesystem broker，不依赖 Redis；任务队列目录位于 `data/celery/queue/`，生产者与 Worker 共享该目录。
- 结构化数据使用 SQLite，数据库文件默认位于 `data/app.db`。
- 图片使用本地文件系统，默认保存到 `data/images/`。
- OCR 使用 PaddleOCR 提取原始文字；MiniMax-M3 结合标题、正文和 OCR 文本进行活动字段结构化提取。MiniMax 不替代基础 OCR。
- 导出文件保存到 `data/exports/`，每次周报同时生成 Excel（`.xlsx`）和 Markdown（`.md`）。
- 不使用 MinIO、PostgreSQL、Redis、Docker 或 Docker Compose。
- 提供统一的初始化和本地启动命令，可分别启动前端、API、Celery Worker 和 Celery Beat。

### 业务闭环

```text
Vue 管理端
  -> FastAPI 创建抓取任务并写入 SQLite
  -> Celery filesystem broker 投递任务
  -> Worker 调用 OpenCLI 获取公开笔记和图片
  -> 图片写入 data/images/
  -> OCR、字段提取和活动去重
  -> 活动写入 SQLite
  -> 运营人员在 Vue 管理端审核和编辑
  -> 导出 data/exports/*.xlsx 和 data/exports/*.md
```

### 运行进程

| 进程 | 职责 | 本地依赖 |
|------|------|----------|
| Vue/Vite | 管理页面 | Node.js |
| FastAPI/Uvicorn | REST API、静态文件访问、导出下载 | Python 3.11 |
| Celery Worker | 抓取、OCR、提取、去重、导出 | filesystem broker |
| Celery Beat | 每周一 02:00 定时调度 | filesystem broker |
| Chrome + OpenCLI | 复用登录态抓取公开笔记 | 本机 Chrome CDP |

### 阶段一验收边界

- 能在不安装 Docker、PostgreSQL、Redis 和 MinIO 的电脑上完成初始化并启动。
- 管理端页面和 `/api/v1` 接口可用。
- 支持后台手动触发及 Celery Beat 定时触发抓取任务。
- SQLite 能持久化配置、笔记、活动、任务和报告记录。
- 图片可写入本地目录并通过受控 API 访问。
- 审核通过的活动可同时导出 Excel 与 Markdown。
- 外部依赖不可用时，任务状态和错误信息可在管理端查看。

## 阶段二：完整技术栈版

### 升级范围

- SQLite 替换为 PostgreSQL 15。
- Celery filesystem broker 替换为 Redis broker/result backend。
- 本地图片目录替换为 MinIO 对象存储。
- 增加 Docker Compose，统一编排前端、后端、Worker、Beat、Flower、PostgreSQL、Redis 和 MinIO。
- 增加生产环境反向代理、HTTPS、备份、监控与访问控制。

### 保持不变

- Vue 页面、路由和用户操作流程。
- FastAPI 的 `/api/v1` 契约。
- SQLAlchemy 模型的业务字段与 Alembic 迁移方式。
- 抓取、OCR、字段提取、去重和报表服务的公开接口。
- Excel 与 Markdown 导出格式。

## 可替换边界

| 能力 | 阶段一实现 | 阶段二实现 | 约束 |
|------|------------|------------|------|
| 数据库 | SQLite | PostgreSQL 15 | 业务层只依赖 repository/session 接口 |
| 任务消息 | Celery filesystem broker | Redis | 业务层只调用任务派发接口 |
| 图片存储 | 本地文件系统 | MinIO | 业务层只依赖 storage 接口和对象键 |
| 部署 | 本机多进程 | Docker Compose | 环境变量名称尽量保持一致 |

阶段一禁止在业务服务中硬编码 SQLite 文件路径、本地图片绝对路径或 filesystem broker 目录。相关差异必须集中在配置、数据库、storage 和 task-dispatcher 边界中。

根目录 `.env` 是两阶段统一配置入口，`.env.example` 必须覆盖全部环境相关和可部署调整的变量。前端只能使用 `VITE_*` 变量，服务端密钥不得进入前端构建产物。

## 工程目录

```text
xhs-info-crawl/
├── frontend/
│   └── src/
│       ├── api/
│       ├── views/
│       ├── components/
│       ├── router/
│       └── stores/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── storage/
│   │   └── tasks/
│   ├── migrations/
│   └── tests/
├── data/
│   ├── app.db
│   ├── images/
│   ├── exports/
│   └── celery/
├── scripts/
├── docs/
├── .env.example
├── Makefile
└── README.md
```

`data/` 中的运行数据不得提交到 Git；仅保留必要的 `.gitkeep` 和示例文件。
