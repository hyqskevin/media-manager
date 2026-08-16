# 项目工作流程（Agent 工作约定）

> 本文件记录 AI 协作流程的硬约束。每次会话开始时必须先读本文件再行动。

## 核心规则

### 1. 先写 spec，再按 TDD 开发

每条 TODO 必须按以下顺序：

```
TODO 提出
    ↓
先解答问题（如果用户问"为什么"）
    ↓
写 spec（docs/superpowers/specs/<日期>-<slug>-design.md）
   含：目标、设计、验收
    ↓
记录 spec 审核状态（当前已有持续授权，可自动进入开发）
    ↓
写 TDD 测试（先写测试，让它失败）
   - 后端：backend/tests/test_*.py
   - 前端：frontend/src/**/*.spec.ts
   - E2E：tests/test-*.md
    ↓
实现代码（让测试通过）
    ↓
更新 docs/TODO.md（完成的标 [x]，然后移入"已完成"区）
```

**任何代码改动前必须有 spec。** 用户已授权 Agent 按 `docs/TODO.md` 顺序持续执行，spec 写完后默认视为已审核，无需逐条等待确认；用户可随时撤回或暂停该授权。

以下情况仍必须暂停并询问：
- 需要新的外部系统权限、登录、验证码或敏感信息；
- 涉及删除重要数据、生产部署、付费、对外发送或其他不可逆操作；
- TODO 存在会实质改变产品方向的歧义，且无法从现有 spec、代码或文档确定。

### 2. TDD 是测试驱动的开发

- 测试**先写**，先看到失败（红）
- 再写实现，看到通过（绿）
- 再重构
- 单元测试和 E2E 测试都要写
- 不写测试不算完成

### 3. 提问与回答

如果用户问"为什么"或质疑"问题原因"：
- **先排查证据**（看代码、看日志、看 DB）
- **找到真正根因**（不止表面现象）
- **给方案**（不止"延长超时"等 workaround）
- 按持续授权进入 spec + TDD；若会改变既定需求边界则暂停询问

### 4. TODO 流程

每条 TODO 必须出现在 `docs/TODO.md`：
- 当前待办：`- [ ]` 描述 + 目标 + 验收
- 完成后：移入"已完成"区，标 `[x]`，保留目标/验收描述
- 不直接删除，便于追踪

### 5. 撤销不符合规则的代码

任何**缺少 spec、未完成 TDD**的代码：
- 立即撤掉实现
- 用户否决 spec 时撤掉对应实现和 spec
- 不偷偷保留

## 文件约定

| 文件 | 用途 |
|---|---|
| `docs/TODO.md` | 唯一待办入口 |
| `docs/superpowers/specs/<日期>-<slug>-design.md` | 每条 TODO 的 spec |
| `docs/api-doc.md` | API 文档 |
| `docs/database-design.md` | 数据库设计 |
| `docs/ui-design.md` | UI 设计 |
| `docs/crawler-design.md` | 爬虫设计 |
| `docs/architecture.md` | 架构 |
| `backend/tests/test_*.py` | 后端单元/集成测试 |
| `frontend/src/**/*.spec.ts` | 前端组件测试 |
| `frontend/e2e/*.spec.ts` | 前端 E2E |
| `tests/test-*.md` | 测试案例文档 |

## 测试命令

```bash
make test                           # 全量
cd backend && pytest -q             # 后端
cd frontend && npm run test -- --run  # 前端
```

## 项目内写操作规范

**所有写操作（文件下载、缓存、临时文件、日志、数据库）必须限制在项目根目录内，不得污染项目外部目录（`/tmp`、`~/.paddlex`、`~/.cache`、`$HOME` 等）。**

### 硬约束

- 生产代码禁止硬编码 `/tmp/`、`Path.home()`、`expanduser('~')`、`tempfile.gettempdir()`
- 第三方库缓存目录必须通过环境变量重定向到项目内：
  - `PADDLE_PDX_CACHE_HOME=$ROOT_DIR/data/paddlex`（PaddleOCR）
  - `HF_HOME=$ROOT_DIR/data/huggingface`（huggingface_hub）
- 临时文件用 `Settings.tmp_dir`（默认 `./data/tmp`），不用 `tempfile.mkdtemp()`
- 跨进程共享文件用 `Settings.task_registry_path`（默认 `./data/run/task_registry.json`）
- 测试代码用 pytest `tmp_path` fixture，不直接写 `/tmp`
- 测试脚本用 `$ROOT_DIR/data/tmp/`，不硬编码 `/tmp`

### 验证

`backend/tests/test_project_internal_writes.py` 静态扫描生产代码，确保无硬编码外部路径。新增服务代码后跑该测试确认合规。

## 服务进程管理

`uvicorn` 在本地通常带 `--reload` 启动，源码改动后会自动重载。但 **celery worker、Celery beat、定时任务、消费消息队列的后台进程不会自动重载**：

- 修改 ORM 模型（增删列、改 nullable、改外键）后：**必须**手动重启 worker，否则 worker 持旧模型访问新 schema 会触发 `no such column`、`OperationalError` 等错误，并将 traceback 写到 `error_message` 字段让前端看到的"任务报错"。
- 修改依赖 SQL 的服务代码（`app/services/*.py`、`app/tasks/*.py`）后：**必须**重启 worker。
- 仅修改 API 层代码（`app/api/v1/*.py`）和 pydantic schema：uvicorn reload 已生效，不必动 worker。
- 修改前端代码：仅 dev server 自动刷新，无后端进程需要重启。

**凡涉及模型/迁移/schema 的 TODO，验收项必须包含"重启 worker"**。Agent 完成迁移后应提示用户重启 worker，而不是默认用户会处理。

## 提交约定

- 改动经过 spec + TDD + 测试通过后才能提交；持续授权不降低这些质量门槛
- 不提交无 spec 的代码
- 每个 commit 关联一条 TODO 项
