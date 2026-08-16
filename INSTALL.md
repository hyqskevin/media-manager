# Install & Run media-manager

> 本文档描述如何在本机（macOS / Linux）启动 **media-manager** 工程（多平台浏览器自动化养号管理台）。

## 1. 系统要求

| 工具 | 版本 | 用途 |
| --- | --- | --- |
| Python | ≥ 3.11 | backend (FastAPI + Celery) |
| Node.js | ≥ 18 LTS | frontend (Vue 3 + Vite) |
| npm | bundled with Node | frontend 依赖管理 |
| Git | any recent | 源码拉取 |
| macOS / Linux | OS | 主机 |
| Chrome | any recent | 平台账号登录 / 浏览器自动化 |
| Patchright | latest | 反检测浏览器驱动（v0.2 引入，详见 `reference/anti-detection-notes.md`） |
| (Optional) Make | any | 快捷启动 |

> Windows 用户请先安装 WSL2，再按 Linux 步骤操作。

## 2. 拉取代码

```bash
git clone https://github.com/hyqskevin/media-manager.git
cd media-manager
```

## 3. 后端 (FastAPI + Celery + SQLite)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
patchright install chromium
```

### 3.1 数据库初始化

```bash
export INITIAL_ADMIN_PASSWORD="ChangeMe123!"   # 可选：覆盖默认 admin 密码
alembic upgrade head                            # 应用全部迁移（含 v0.2 的 platform_accounts / favorite_snapshots）
```

### 3.2 环境变量（可选）

| 变量 | 默认值 | 用途 |
| --- | --- | --- |
| `MEDIA_BACKEND_HOST` | `0.0.0.0` | uvicorn bind |
| `MEDIA_BACKEND_PORT` | `8000` | uvicorn 端口 |
| `INITIAL_ADMIN_PASSWORD` | `Admin@123` | seed admin 密码（生产必须覆盖） |
| `NURTURE_GLOBAL_ENABLED` | `false` | **v0.2 养号总开关**（默认关闭，强制显式开启） |
| `OPENCLI_BROWSER_COMMAND_TIMEOUT` | `120` | 秒 |
| `CELERY_BROKER_URL` | `filesystem:///abs/path/celery_broker` | filesystem broker |
| `CELERY_RESULT_BACKEND` | `filesystem:///abs/path/celery_results` | filesystem result |

### 3.3 启动（三个终端）

```bash
# 终端 1 — API
cd backend && source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 终端 2 — Celery worker（含养号任务）
cd backend && source .venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=1

# 终端 3 — Celery beat（定时任务）
cd backend && source .venv/bin/activate
celery -A app.tasks.celery_app beat --loglevel=info
```

## 4. 前端 (Vue 3 + Vite)

```bash
cd frontend
npm ci
npm run dev          # http://localhost:5173 (dev with HMR)
# 或生产构建：
npm run build
npm run preview      # http://localhost:4173
```

前端 `.env` 或 `vite.config.ts` 需指向 backend，默认 `http://localhost:8000`。

## 5. 首次使用（v0.2 养号流程）

1. 打开 `http://localhost:5173`（dev）或 `http://localhost:4173`（preview）。
2. 用 admin / `Admin@123`（或你设置的密码）登录。
3. 「系统管理 → 系统配置」打开「**养号总开关**」（`NURTURE_GLOBAL_ENABLED=true`）。
4. 「系统管理 → 平台账号」新建账号（v0.2 仅小红书完整实现，其余 7 平台为 stub）。
5. 「系统管理 → 平台账号 → 启动养号」选动作 + 时长，提交后异步执行。
6. 「养号任务」页面查看执行进度与结果。

## 6. 测试（推荐 PR 前跑）

```bash
# 后端
cd backend && source .venv/bin/activate
pytest -q

# 前端
cd frontend
npm run test -- --run
npm run build
```

## 7. 故障排查

| 现象 | 修复 |
| --- | --- |
| `ModuleNotFoundError: app.xxx` | 确保在 `backend/` 目录并已激活 venv |
| Celery 任务不执行 | 检查 broker 目录可写 + `celery beat` 在跑 |
| `bot.sannysoft.com` 显示红色 | 检查 stealth.min.js 是否注入成功；详见 `reference/anti-detection-notes.md` |
| 前端访问不到后端 | 检查 CORS / `VITE_API_BASE` / proxy 配置 |

## 8. 相关文档

- `docs/TODO.md` — 当前迭代待办
- `AGENTS.md` — Agent 工作流程
- `docs/superpowers/specs/2026-08-16-v02-account-management-design.md` — v0.2 设计 spec（本地保留）
- `docs/superpowers/plans/2026-08-16-v02-account-management.md` — v0.2 实施计划（本地保留）
- `reference/anti-detection-notes.md` — 反检测配方