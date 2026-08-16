# 技术栈与工程架构

## 分阶段原则

项目采用“业务主体稳定、基础设施可替换”的两阶段架构。完整边界见 `phase-roadmap.md`。

## 共享技术栈

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus | 两阶段保持不变 |
| 后端 | Python 3.11 + FastAPI | 两阶段保持不变 |
| ORM/迁移 | SQLAlchemy + Alembic | 同一模型支持 SQLite 与 PostgreSQL |
| 任务队列 | Celery Worker + Celery Beat | Broker 按阶段替换 |
| 爬虫 | OpenCLI (Node.js) | 连接本机 Chrome CDP |
| OCR | PaddleOCR | 图片文字识别 |
| LLM | MiniMax-M3 API | 结合标题、正文与 PaddleOCR 文本进行字段提取 |
| 导出 | openpyxl + Markdown 模板 | 同时生成 `.xlsx` 与 `.md` |

## 阶段一架构

| 能力 | 实现 |
|------|------|
| 数据库 | SQLite，默认 `data/app.db` |
| Celery Broker | filesystem transport，默认 `data/celery/` |
| 图片存储 | 本地文件系统，默认 `data/images/` |
| 报告存储 | 本地文件系统，默认 `data/exports/` |
| 部署 | 本机多进程直接运行，不使用 Docker |

```text
Vue 3 管理端
       |
       v HTTP/JWT
FastAPI API ---- SQLAlchemy/Alembic ---- SQLite
       |
       v
Celery filesystem broker -> Worker/Beat
       |
       +-> OpenCLI/Chrome CDP
       +-> PaddleOCR
       +-> MiniMax API
       +-> LocalStorage(data/images, data/exports)
```

阶段一是可交付版本，不是一次性脚本。API、repository、storage 和任务派发接口必须保持清晰，以便阶段二替换实现。

## 阶段二架构

阶段二保持 Vue、FastAPI、Celery 以及业务服务不变，将 SQLite、filesystem broker 和本地文件存储分别替换为 PostgreSQL、Redis 和 MinIO，并通过 Docker Compose 编排。Flower、Nginx、HTTPS、备份和生产监控也在阶段二引入。

## 工程目录结构

```text
xhs-info-crawl/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   ├── core/             # 配置、认证、数据库、日志
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/     # 隔离数据库访问
│   │   ├── services/         # 抓取、OCR、提取、去重、导出
│   │   ├── storage/          # LocalStorage / MinIOStorage
│   │   ├── tasks/            # Celery app、任务、Beat 配置
│   │   └── main.py
│   ├── migrations/
│   └── tests/
├── frontend/
│   └── src/
│       ├── api/
│       ├── views/
│       ├── components/
│       ├── router/
│       └── stores/
├── data/                     # 阶段一运行数据，不提交 Git
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

## 可替换接口

- `repositories/` 隔离 SQLAlchemy 查询与事务，业务服务不得依赖 SQLite 专有 SQL。
- `storage/` 统一提供保存、读取、删除和生成访问地址能力；数据库只保存对象键或相对路径。
- `tasks/` 统一任务派发与 Celery 配置；业务服务不得感知 broker URL。
- 所有本地路径和连接信息都由环境变量或配置对象提供，不在业务代码中硬编码。
- 所有环境相关和可部署调整的变量统一定义在根目录 `.env`；`.env.example` 必须列出完整变量及安全示例值。前端仅通过 `VITE_*` 读取允许暴露到浏览器的变量。

## 并发约束

阶段一 SQLite 和 filesystem broker 面向单机低频批处理，Celery Worker 默认低并发运行，写事务保持短小，任务必须幂等。阶段二切换 PostgreSQL 与 Redis 后再提高 Worker 并发度。
