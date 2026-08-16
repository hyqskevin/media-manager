# 部署与运行方案

## 阶段一：本地直接运行

阶段一不使用 Docker、PostgreSQL、Redis 或 MinIO。开发者只需安装 Python 3.11、Node.js、OpenCLI 和 Chrome。

预期统一命令如下，具体命令由脚手架实施时落地：

```bash
make init       # 创建 Python 环境、安装前后端依赖、初始化 SQLite
make dev-api    # FastAPI
make dev-worker # Celery Worker + filesystem broker
make dev-beat   # Celery Beat
make dev-web    # Vue/Vite
make test       # 后端与前端测试
```

运行数据默认位于：

```text
data/app.db
data/images/
data/exports/
data/celery/queue/
```

启动 Chrome CDP 并登录小红书后，设置 `OPENCLI_CDP_ENDPOINT`。API、Worker 与 Beat 是独立本机进程，filesystem broker 目录必须使用相同配置。

### 阶段一环境变量

根目录 `.env` 是阶段一唯一运行配置入口。API、Celery、前端和启动脚本均加载该文件；新增可配置项时必须同步更新 `.env.example`，不得在代码或脚本中新增环境相关硬编码。

完整变量清单以仓库根目录 `.env.example` 为准，包括应用、API/前端端口、CORS、数据库、本地目录、Celery、定时任务、抓取限制和外部服务配置。`make init` 会在保留 `.env` 已有值的前提下补充后来新增的变量。

## 阶段二：完整技术栈部署

阶段二增加 Docker Compose，并部署 PostgreSQL 15、Redis、MinIO、FastAPI、Celery Worker、Celery Beat、Flower 和前端。生产环境再增加 Nginx、HTTPS、备份与访问控制。

阶段二通过配置替换完成升级：

- `DATABASE_URL` 从 SQLite 改为 PostgreSQL。
- `CELERY_BROKER_URL` 和 result backend 改为 Redis。
- `STORAGE_BACKEND` 从 `local` 改为 `minio`，并配置 MinIO 凭据。
- 使用 Alembic 将阶段一数据结构迁移到 PostgreSQL，并提供 SQLite 数据导入工具。

OpenCLI 与 Chrome 初期仍可运行在本地电脑，通过 CDP 与后端连接；服务器化 Chrome 属于阶段二后续部署优化，不是阶段一验收条件。

## 打包版部署（2026-08-10 新增）

打包版面向非开发者用户,通过 GitHub Actions 自动构建,推 tag 触发。spec:`docs/superpowers/specs/2026-08-10-one-click-packaging-design.md`。

### 打包版架构

```
xhs-info-crawl/
├── runtime/                       # 便携运行时(平台相关)
│   ├── python/                    # python-build-standalone cpython-3.11.9
│   └── venv/                      # 已装好 fastapi/celery/uvicorn/pywebview/...
├── app/                           # 应用代码
│   ├── backend/                   # Python 后端源码
│   ├── frontend/dist/             # 前端已构建静态产物
│   └── migrations/
├── launcher/                      # PyWebView 启动器
│   ├── main.py                    # 入口,管理 3 个子进程 + 状态服务 + PyWebView 窗口
│   ├── status_server.py           # 本地 HTTP 状态服务(端口 = API_PORT + 1)
│   ├── process_manager.py         # API/Worker/Beat 子进程管理
│   ├── ocr_installer.py           # OCR 增强包一键安装
│   ├── opencli_checker.py         # OpenCLI 连接测试
│   ├── port_finder.py             # 端口冲突自动探测(8000-8020)
│   ├── env_bootstrap.py           # .env 初始化 + 敏感配置生成
│   ├── requirements.txt
│   └── ui/dist/                   # 启动器 UI 构建产物
├── data/                          # 运行数据(首次启动初始化)
│   ├── logs/                      # 服务日志
│   ├── paddlex/official_models/   # PaddleOCR 模型(OCR 增强包安装后填充)
│   ├── huggingface/               # HuggingFace 缓存
│   └── tmp/                       # 临时文件
├── .env                           # 首次启动由 launcher 从 .env.example 生成
├── .env.example
└── README-USER.md                 # 用户使用说明
```

### GitHub Actions 构建流程

两个独立工作流:

1. **主程序**(`release.yml`):推 `v*.*.*` tag 触发
   - `build-macos` job:macos-latest,构建 `xhs-info-crawl-<version>-macos.zip`
   - `build-windows` job:windows-latest,构建 `xhs-info-crawl-<version>-windows.zip`
   - `release` job:ubuntu-latest,下载两个 zip + 生成源码 zip + 创建 GitHub Release

2. **OCR 增强包**(`release-ocr-addon.yml`):推 `ocr-addon-*` tag 触发
   - `build-macos-arm64` job:macos-latest
   - `build-macos-x86_64` job:macos-13
   - `build-windows-x64` job:windows-latest
   - `release` job:汇总 3 个 zip 到 OCR Addon Release

### 本地复现打包

```bash
# macOS(需先构建 frontend/dist 和 launcher/ui/dist)
./scripts/package-macos.sh <version>

# Windows
.\scripts\package-windows.ps1 -Version <version>

# OCR 增强包(3 平台)
./scripts/package-ocr-addon.sh macos arm64 <paddleocr_version>
./scripts/package-ocr-addon.sh macos x86_64 <paddleocr_version>
./scripts/package-ocr-addon.sh windows x64 <paddleocr_version>
```

### OCR 增强包分发

OCR 增强包与主程序版本独立,采用 `paddleocr-<paddleocr_version>` 格式(如 `ocr-addon-3.7.0`)。

- 用户在启动器内点"下载安装 OCR" → 启动器根据平台选择对应 zip
- wheels 安装到 `runtime/venv/`(pip install)
- 模型文件解压到 `data/paddlex/official_models/`
- 自动设 `OCR_ENABLED=true`
- 与项目 `PADDLE_PDX_CACHE_HOME=./data/paddlex` 配置对齐,无路径冲突

### 数据目录布局

| 目录 | 用途 | 备份优先级 |
|---|---|---|
| `data/app.db` | SQLite 数据库(所有抓取数据) | 高 |
| `data/images/` | 下载的笔记图片 | 中 |
| `data/exports/` | Excel/Markdown 导出文件 | 中 |
| `data/archive/` | 按日期归档的图片和 Markdown | 中 |
| `data/backups/` | 数据库备份 | 高 |
| `data/paddlex/` | PaddleOCR 模型(可重新下载) | 低 |
| `data/huggingface/` | HuggingFace 缓存(可重新下载) | 低 |
| `data/celery/` | Celery 消息队列(临时) | 不备份 |
| `data/tmp/` | 临时文件 | 不备份 |
| `data/logs/` | 服务日志 | 不备份 |
| `data/run/` | 进程注册表(临时) | 不备份 |

### 升级与迁移策略

- **小版本升级**:下载新版 zip,替换除 `data/` 外的所有文件,保留 `data/` 和 `.env`
- **大版本升级**:先备份数据,按 release notes 执行迁移(如 `alembic upgrade head`)
- **跨平台迁移**:复制 `data/` 目录到新平台的解压目录,首次启动自动检测并适配
- **回滚**:用旧版 zip 替换,保留 `data/`(注意大版本回滚可能需要数据库降级)

### 启动器进程管理

启动器(Python 主进程)管理 3 个子进程:

| 子进程 | 启动命令 | 健康检查 | 日志 |
|---|---|---|---|
| API | `runtime/venv/bin/python -m uvicorn app.main:app` | `GET /api/v1/health` 返回 200 | `data/logs/api.log` |
| Worker | `runtime/venv/bin/python -m celery -A app.tasks.crawl_task worker` | 进程存活 | `data/logs/worker.log` |
| Beat | `runtime/venv/bin/python -m celery -A app.tasks.crawl_task beat` | 进程存活 | `data/logs/beat.log` |

启动顺序:API → (健康检查通过) → Worker → Beat。退出时反向停止:Beat → Worker → API,先 SIGTERM 5 秒后 SIGKILL。

## 系统管理 + 多账号 RBAC 部署（2026-08-13 新增）

系统管理 + 多账号 RBAC 功能涉及 5 张新表 + users 扩列 + `require_permission` 工厂替换部分 `require_admin` 端点。spec:`docs/superpowers/specs/2026-08-12-system-admin-design.md`。

### 标准部署路径（干净的 alembic 链）

按规格执行的全新 / 重置环境应走：

```bash
cd backend
alembic upgrade head                                  # 0020_system_admin + 0021_xhs_account_cdp_port 都自动应用
```

`0020_system_admin` migration 是**幂等**的：

- 建表用 `if "groups" not in existing_tables` 检查
- 建权限用 `SELECT 1 FROM permissions WHERE code = :c` 检测
- 建组用 `SELECT id FROM groups WHERE name = 'Administrators'` 检测
- 加权限绑用 `INSERT OR IGNORE INTO group_permissions`
- 加用户组用 `INSERT OR IGNORE INTO user_groups SELECT id, :g FROM users WHERE role = 'admin'`

所以即使重跑 0020（理论上 alembic 不会），也不会破坏数据。

### 非标准部署路径：生产 DB 已被手工干预

⚠️ **2026-08-13 真实生产环境发生过这种情况**：

> 生产 `data/app.db` 的 `alembic_version=0021`（声称已经 head），但 0020 的内容**根本没跑过**——5 张新表存在但全空，`users` 表缺 `display_name / enabled` 两列。推测路径：有人手工创建了 5 张表 → 跑了 0021（cdp_port）→ **手动塞 `alembic_version='0021'` 跳过 0020 的 ALTER + seed**。

如果不处理，worker 进程加载新 ORM 访问 `users.enabled` 会抛 `OperationalError: no such column: enabled`，前端"系统管理"页也会因空 `groups` 表报错。

**应对脚本**：`backend/migrations/_manual_finish_0020.py`

脚本本质是 0020 的 `upgrade()` 函数的子集：

1. **users 扩列**：`PRAGMA table_info(users)` 检测后 `ADD COLUMN display_name / enabled`（SQLite 不支持 `ADD COLUMN IF NOT EXISTS`，所以脚本走 PRAGMA 检测）
2. **seed 10 条权限码**：`SELECT code FROM permissions` 检测已存在则跳过
3. **seed Administrators 组**（绑全 10 条权限）+ **seed Viewers 组**（仅绑 `users:read`）
4. **批量入组**：`INSERT OR IGNORE INTO user_groups SELECT id, :g FROM users WHERE role = 'admin'`
5. **回填 display_name**：`UPDATE users SET display_name = username WHERE display_name IS NULL`

### 部署步骤（标准 + 非标准共用）

```bash
# 0. 确认当前 alembic 状态
cd backend && .venv/bin/alembic current
# 期望: 0021 (head)（非标准场景）或 0020（标准场景）

# 1. 备份生产 DB（不可逆操作的第一步）
BACKUP_FILE="../data/backups/app-pre-system-admin-$(date +%Y%m%d-%H%M%S).db"
cp ../data/app.db "$BACKUP_FILE"
ls -la "$BACKUP_FILE"   # 确认文件 size > 0

# 2a. 标准路径：跑 alembic upgrade head
.venv/bin/alembic upgrade head

# 2b. 非标准路径：先跑 alembic upgrade head（应是 no-op，因 DB 已 0021）
.venv/bin/alembic upgrade head
# 然后跑手工补 seed 脚本
.venv/bin/python migrations/_manual_finish_0020.py
# 输出会按行打印 + users.display_name / + users.enabled / + permission <code> / + group / 等
# 末行 "Administrators 组现有 N 个成员" 必须 > 0

# 3. 校验 seed 数据（确认种子落地）
sqlite3 ../data/app.db "SELECT name, is_builtin FROM groups;"
sqlite3 ../data/app.db "SELECT COUNT(*) FROM permissions;"
sqlite3 ../data/app.db "SELECT u.username, g.name FROM user_groups ug JOIN users u ON u.id=ug.user_id JOIN groups g ON g.id=ug.group_id;"
# 期望: Administrators + Viewers + 10 条权限 + 所有 role='admin' 用户在 Administrators 组

# 4. 重启服务进程
# uvicorn --reload 通常已自动加载；如未自动 reload，停掉 + 起 ./scripts/dev-api.sh
# celery worker 必须重启（改动了 models）: pkill -f "celery.*worker" && ./scripts/dev-worker.sh &
# celery beat 必须重启（同上 models 改动）: pkill -f "celery.*beat" && ./scripts/dev-beat.sh &
# 注意：重启次序应是 beat 先停 → worker 停 → uvicorn 停 → 起 uvicorn → 起 worker → 起 beat

# 5. 冒烟测试（确认新端点工作）
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['access_token'])")
curl -s http://127.0.0.1:8000/api/v1/permissions -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; print('permissions:', len(json.load(sys.stdin)))"
curl -s http://127.0.0.1:8000/api/v1/groups -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; print('groups:', [g['name'] for g in json.load(sys.stdin)])"
curl -s "http://127.0.0.1:8000/api/v1/audit-logs?size=1" -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('audit total:', d['total'], 'latest:', d['items'][0]['action'] if d['items'] else None)"
# 期望: permissions=10, groups=['Administrators','Viewers'], audit total>=1, latest=login_success
```

### 进程重启顺序的注意事项

| 场景 | 是否需要重启 |
|---|---|
| 仅改 `app/api/v1/*.py`（API 层） | 否，uvicorn `--reload` 自动加载 |
| 改 `app/services/*.py` 或 `app/models/*.py` | **worker 必须重启**，beat 必须重启 |
| 改 `app/tasks/*.py` 或 `app/services/crawl_task.py` | **worker 必须重启** |
| 改 `migrations/versions/*.py` + `alembic upgrade` | API 层自动 reload；worker/beat 因 ORM 缓存必须重启 |

**Worker/beat 重启命令**（项目脚本风格）：

```bash
# 停
pkill -f "celery.*worker"   # 仅 worker
pkill -f "celery.*beat"     # 仅 beat
# 起
nohup ./scripts/dev-worker.sh > data/logs/celery-worker.log 2>&1 &
nohup ./scripts/dev-beat.sh   > data/logs/celery-beat.log   2>&1 &
```

⚠️ macOS 没有 `setsid`；用 `nohup` 后必须确认子进程没被父 shell 关闭信号带走（运行后会话断开时仍可能退出）。更可靠的方式是用 `launchd` 或独立窗口。

### 回滚

```bash
# 1. 停所有进程
pkill -f "celery.*worker" && pkill -f "celery.*beat" && pkill -f "uvicorn"

# 2. 还原 DB
cp data/backups/app-pre-system-admin-YYYYMMDD-HHMMSS.db data/app.db

# 3. 还原代码（git 回滚 12 个 commit）
git checkout HEAD~12 -- backend/app/api/v1/ backend/app/models/ backend/migrations/versions/0020_system_admin.py backend/migrations/versions/0021_xhs_account_cdp_port.py backend/app/core/security.py backend/app/services/audit.py
git checkout HEAD~12 -- frontend/src/api/client.ts frontend/src/views/LoginView.vue frontend/src/stores/user.ts frontend/src/components/SystemAdminGuard.vue frontend/src/views/SystemAdminView.vue frontend/src/views/admin/ frontend/src/router/index.ts frontend/src/layouts/AppLayout.vue

# 4. 重启进程（uvicorn --reload 自动加载回滚后的代码）
nohup ./scripts/dev-api.sh   > data/logs/uvicorn.log         2>&1 &
nohup ./scripts/dev-worker.sh > data/logs/celery-worker.log 2>&1 &
nohup ./scripts/dev-beat.sh   > data/logs/celery-beat.log   2>&1 &
```

`_manual_finish_0020.py` 是部署一次性脚本，不入 git；它本身幂等，重跑不会破坏数据。

### 为什么 `_manual_finish_0020.py` 不入 git

1. 它是**应急部署脚本**，处理"生产 DB 已被手工干预"这种异常情况；正常 `alembic upgrade head` 不需要它
2. 把它放进 migrations 目录会**污染 alembic 自动发现机制**（虽然 `_` 前缀按 alembic 约定通常会被忽略，但要小心）
3. 它依赖 0020 的内部 seed 数据（PERMISSION_SEED），如果未来 0020 改了 seed，需要同步这份脚本——维护成本大于价值
4. 项目已有 SRE-friendly 的备份+回滚流程（见上方"回滚"小节），遇到类似情况应先备份+排查根因，不应无脑重跑此脚本

