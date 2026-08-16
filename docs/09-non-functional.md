# media-manager v0.2 — 非功能性与质量规范

> 版本: v0.2.0  ·  状态: 草稿  ·  最后更新: 2026-08-16
> 适用范围: media-manager 全栈(后端 / 前端 / Worker / 部署)
> 读者: 全员(研发、测试、运维、PM)

本文档定义 v0.2 的**非功能性需求(NFR)**与**质量红线**。所有 PR 必须满足本文档中的硬指标,否则 CI 会拒绝合并。

---

## 目录

1. [性能要求](#1-性能要求)
2. [可用性要求](#2-可用性要求)
3. [安全要求](#3-安全要求)
4. [可扩展性](#4-可扩展性)
5. [可观测性](#5-可观测性)
6. [兼容性](#6-兼容性)
7. [数据合规](#7-数据合规)
8. [开发流程](#8-开发流程)
9. [风险与限制](#9-风险与限制)

---

## 1. 性能要求

### 1.1 页面加载

| 指标 | 目标 | 测量方法 |
|---|---|---|
| 首屏 FCP | < 1.5s (P95) | Lighthouse / WebPageTest |
| 首屏 LCP | < 2.0s (P95) | Web Vitals |
| TTI(可交互) | < 2.5s (P95) | Lighthouse |
| 路由切换(已加载 SPA) | < 200ms (P95) | Vue Router 性能埋点 |

**实现约束**:

- 路由级 `defineAsyncComponent` 懒加载,非首屏页面单独 chunk。
- 列表页首屏只请求 `page=1&page_size=20`,滚到底再请求下一页。
- 关键 CSS 内联到 `<head>`,非关键 CSS 通过 `<link rel="preload">` 异步加载。

### 1.2 API 响应

| 类别 | P95 目标 | P99 上限 | 例子 |
|---|---|---|---|
| 简单 CRUD(单条) | < 200ms | < 500ms | `GET /operators/{id}` |
| 列表查询(分页) | < 500ms | < 1500ms | `GET /platforms/xhs/accounts?page=1` |
| 复杂查询(聚合 / 跨表) | < 2000ms | < 5000ms | `GET /dashboard/pending-issues` |
| 写操作(创建任务 / 启动浏览器) | < 1500ms | < 4000ms | `POST /nurture-tasks` |
| 导出(异步触发) | < 3000ms(返回 job_id) | < 8000ms | `GET /audit-logs/export` |

**实现约束**:

- 单条 SQL 必加索引,慢查询(> 200ms)在 review 阶段拦截。
- 列表查询上限 `page_size=200`;超过报错 422,不允许"分页兜底"。
- 涉及跨表 JOIN 超过 3 张时,必须走预先物化的 `mv_*` 视图或汇总表,不允许临时 JOIN。

### 1.3 实时数据刷新

| 通道 | 频率 | 触发 |
|---|---|---|
| `WS /ws/notifications` | 服务端推送(无心跳) | 事件驱动 |
| `WS` 心跳 | 30s 一次(`pong`) | 服务端定时 |
| 客户端轮询降级 | 5s | WS 断线超过 10s |
| 仪表盘时序图 | 5s 心跳 | `GET /dashboard/overview` 客户端拉取 |

**降级策略**:

- WS 连接断开 → 退避 1s / 2s / 4s / 8s / 上限 30s 重连;
- 连续 3 次失败 → 切换到 5s 轮询(可配置 `VITE_POLL_INTERVAL_MS`);
- 轮询也失败 → 仪表盘展示"连接断开"占位,不抛错。

### 1.4 并发养号任务

- **单 worker 同时执行 nurture 任务数 ≤ 3**(硬上限,可调 `WORKER_CONCURRENCY`)。
- **单账号同时 nurture 任务数 ≤ 1**(由 `platform_accounts.status` 保证,被 nurture 引用时不允许 pause 之外的并发启动)。
- **单 worker 持有 Chrome sessions ≤ 8**(`MAX_SESSIONS_PER_WORKER`)。
- **单账号 risk_score 连续 3 天 > 0.7** → 自动 `paused`,24h 后才能由人工 `resume`。

### 1.5 数据库查询

| 类别 | 目标 |
|---|---|
| 单表主键 / 索引查询 | < 50ms (P95) |
| 单表复杂条件查询 | < 100ms (P95) |
| 单次事务 | < 200ms |
| 跨表 JOIN(2-3 张) | < 300ms (P95) |
| 跨表聚合(预物化) | < 500ms (P95) |
| 慢查询阈值(超过即告警) | > 1000ms |

**强制**:

- 所有写操作必须在 200ms 内提交;超过 500ms 必须引入 background task,不阻塞 HTTP。
- `EXPLAIN` 必须出现在 PR 中涉及新 SQL 的 reviewer 评语里;type=ALL 或 Extra=Using filesort 必拒绝。

### 1.6 前端包大小

| 资源 | 预算 |
|---|---|
| main bundle (gzip) | < 500KB |
| 单个路由 chunk (gzip) | < 200KB |
| 第三方依赖总大小 (gzip) | < 1.5MB |
| 单页字体文件 | < 200KB(中文字体按需子集化) |
| 首次加载总资源 | < 2MB |

**强制**:

- `vite build` 报告超过预算时,CI 直接 fail,需拆 chunk 或优化依赖。
- 引入新依赖前,必须说明引入原因和替代方案;≥ 100KB 的依赖需要 reviewer 二次确认。

---

## 2. 可用性要求

### 2.1 系统可用性

| 环境 | 目标 | 测量窗口 |
|---|---|---|
| 生产环境 | ≥ 99% 月度可用性 | 30 天滚动 |
| 测试环境 | ≥ 95% 月度可用性 | 30 天滚动 |
| 开发环境(本机) | 不承诺 | — |

"可用" = `/api/v1/health` 返回 200 且 `dashboard.overview` 关键指标非 0。

### 2.2 故障恢复

| 故障 | RTO(恢复时间目标) | RPO(数据丢失上限) |
|---|---|---|
| API 进程崩溃 | < 10s(uvicorn 自动重启) | 0(无状态) |
| Worker 进程崩溃 | < 30s(Celery 自动重启 + 任务重派) | 0(任务可重试) |
| Chrome / opencli 崩溃 | < 30s(自动重启) | 当前任务 action 失败,已完成的 action 已持久化 |
| Redis 不可用 | < 5min(降级到内存缓存 + 限流关闭) | 通知 / WS 推送丢失(可重建) |
| 数据库连接断开 | < 1min(连接池重连) | 0(无写入丢失) |
| 整库灾难 | < 4h(从全量备份恢复) | < 24h(增量 binlog 恢复) |

**自动恢复策略**:

- Chrome 进程退出码 ≠ 0 → `supervisord` 自动拉起;3 次/5 分钟失败 → 触发 notification(level=error)。
- Worker 任务失败 → 指数退避 1s / 4s / 16s,3 次后置 `failed` 状态;非致命错误可由用户 `POST /retry` 恢复。
- opencli 不可达 → heartbeat 检查 3 次失败后,自动 `POST /restart-opencli`,失败再升级到运维。

### 2.3 任务失败重试

- 退避策略:指数 + 抖动,base=1s, max=60s。
- 重试上限:3 次(可由 `risk_config.task_max_retry` 调整,范围 0-10)。
- 重试范围:仅 retryable 错误(网络超时、5xx、上游 502);业务错误(400/404/422)不重试。
- 重试不影响原始 `error_message`,而是写到 `actions[*].retry_count` 与 `actions[*].last_error`。

### 2.4 数据备份

| 备份类型 | 频率 | 保留 | 存储 |
|---|---|---|---|
| 数据库全量 | 每天 1 次(02:00) | 30 天 | `data/backups/db/yyyymmdd.sqlite3.gz`(本地)+ S3 冷存(异地) |
| 数据库增量(WAL) | 实时 | 7 天 | S3 |
| 配置文件 | 每次变更 1 次 | 90 天 | git + S3 |
| audit logs | 每天 1 次(03:00) | 180 天 | S3(合规保留) |
| cookies 文件 | 每天 1 次 | 30 天 | 加密 + S3 |

**强制**:

- 备份脚本必须含校验和(`sha256`),恢复时先校验完整性。
- 每月 1 号做一次"恢复演练",自动起容器从备份恢复并跑 5 个 smoke test。

### 2.5 日志保留

| 日志类型 | 保留 | 清理策略 |
|---|---|---|
| 应用日志(结构化 JSON) | 180 天 | 按日切割,180 天前自动删除 |
| 访问日志(Nginx) | 90 天 | 滚动删除 |
| 错误日志 / traceback | 365 天 | 单独存储,带 request_id 索引 |
| audit logs | 180 天(合规) | 数据库保留 180 天,离线归档永久 |
| Celery 任务日志 | 90 天 | Redis 24h 过期,落盘 90 天 |

---

## 3. 安全要求

### 3.1 鉴权

| 项 | 值 |
|---|---|
| 算法 | HS256(v0.2);RS256 列入 v0.3 路线图 |
| access token 有效期 | 24h(86400s) |
| refresh token 有效期 | 7d(604800s) |
| refresh token 绑定 | 设备 fingerprint(IP + User-Agent hash) |
| 密码哈希 | bcrypt(cost=12) |
| token 黑名单 | Redis,TTL=剩余有效期 |
| 登录失败限流 | 5 次 / 5min / IP+username |
| token 泄露响应 | revoke refresh + 全设备 logout |

### 3.2 密码

- 长度 ≥ 8 位,必须包含大小写字母 + 数字(可由 `password_policy` 调整)。
- 不允许与最近 5 次密码重复(可选,默认关闭)。
- 不允许与 username / 邮箱 / 真实姓名相似(可选,默认关闭)。
- 临时密码(初始化 / 重置)有效期 24h,首次登录强制修改。
- 存储格式:`$2b$12$...`(bcrypt)。

### 3.3 CSRF

- 所有非 GET 请求必须校验 `X-CSRF-Token` 头(由 cookie 自动写入,前端 axios 拦截器注入)。
- Cookie 强制 `SameSite=Strict` + `Secure`(生产) + `HttpOnly`。
- 跨域请求预检通过 CORS 白名单(在 `Settings.cors_origins`),不允许 `*`。

### 3.4 XSS

- Vue 3 默认自动转义,禁止使用 `v-html`;必须使用时需在 PR 描述中说明转义来源。
- 用户输入的富文本(评论模板)后端用 `bleach` 白名单清洗,白名单仅含基础标签。
- 响应头强制 `Content-Security-Policy: default-src 'self'`,禁止 inline script(开发模式除外)。

### 3.5 SQL 注入

- 禁止原生 SQL 字符串拼接;统一使用 SQLAlchemy ORM 参数化。
- 必须使用原生 SQL 时,必须用 `text("... :param ...")`,参数通过 `session.execute(text, params)` 绑定。
- PR 中出现 `f"SELECT ..."` 字符串,reviewer 直接拒绝。

### 3.6 操作日志(audit_logs)

- 所有"危险"操作必记录,包括但不限于:登录 / 登出 / 密码重置 / 账号删除 / cookies 导出 / 配置修改 / 批量停止 / 角色变更。
- 必含字段:`actor_id`, `action_type`, `ref_type`, `ref_id`, `ip`, `user_agent`, `request_id`, `payload`(JSON), `created_at`。
- 不可由普通 operator 删除,仅超管可配置 180 天前的归档导出。

### 3.7 权限校验

- 每个 API endpoint 必须显式声明 `permission`(`@require_permission("nurture.create")`)。
- 缺声明 = 拒绝合入(由 CI 静态扫描 `app/api/v1/` 校验)。
- `super_admin` 角色默认全权限(`["*"]`),但不允许修改 `super_admin` 自身。

### 3.8 Cookie 文件权限

- `platform_accounts.session_name` 对应目录权限 **700**(仅 owner 可读写执行)。
- 加密:AES-256-GCM,密钥从 `MEDIA_MGR_COOKIE_KEY`(env)派生,不进 git。
- 进程退出后 24h 内未使用的 cookies 文件,自动清理(后台 task)。

---

## 4. 可扩展性

### 4.1 平台扩展

- 新增 1 个平台,工作量上限 **1 张表 + 1 个 adapter + 1 个 platform_config**。
- adapter 必须继承 `PlatformAdapter` 抽象基类(参见 `app/services/platforms/base.py`)。
- platform_config 通过 `GET /platform-configs/{platform}` 自动暴露,无需改 API 代码。
- v0.2 平台清单:`xhs`(已实现)、`weibo` / `douyin` / `zhihu` / `twitter` / `bilibili` / `xiaoyuzhou` / `wechat_official`(stub)。

### 4.2 数据库

- 支持 SQLite(开发)与 PostgreSQL(生产)无缝切换,通过 `DATABASE_URL` 决定。
- ORM 使用 SQLAlchemy 2.x 异步 API,迁移工具 Alembic。
- v0.2 默认 SQLite,生产部署允许切到 PostgreSQL 14+。
- 不允许在生产环境使用 SQLite(并发写能力不足)。

### 4.3 Worker 横向扩展

- Celery worker 可部署多实例,通过 Redis 共享任务队列。
- 单实例默认 `WORKER_CONCURRENCY=3`,可由环境变量调整。
- 任务路由:`nurture_task` 走 `nurture` 队列,`favorites_refresh` 走 `favorites` 队列,可独立伸缩。
- Beat 单实例部署(避免重复触发 schedule),用 `celery beat -s /var/lib/celerybeat-schedule`。

### 4.4 前端扩展

- 路由级 `defineAsyncComponent`,按需加载。
- Pinia store 拆分:`useAccountStore` / `useTaskStore` / `useNotificationStore` 等,避免单一大 store。
- 通用组件放 `src/components/common/`,业务组件放 `src/components/<feature>/`。

---

## 5. 可观测性

### 5.1 日志

**格式**:所有日志必须为结构化 JSON,字段:

```json
{
  "ts": "2026-08-16T03:11:00.123Z",
  "level": "info",
  "logger": "app.api.v1.platforms",
  "msg": "account created",
  "request_id": "0c1a2b3c-...",
  "operator_id": 1,
  "platform": "xhs",
  "account_id": 12,
  "latency_ms": 142
}
```

**禁止**:打印明文密码 / token / cookies / 个人手机号。脱敏在 logger filter 统一处理。

**关联**:每个 HTTP 请求分配 `request_id`(由 `X-Request-Id` 头或自动生成),贯穿到下游调用、DB 日志、worker 任务。

### 5.2 指标(Prometheus)

必暴露(`/metrics`):

| 指标 | 类型 | 说明 |
|---|---|---|
| `http_requests_total{method,path,status}` | counter | API 调用量 |
| `http_request_duration_seconds{method,path}` | histogram | 延迟分布 |
| `nurture_task_success_total{platform}` | counter | 养号成功数 |
| `nurture_task_failure_total{platform,kind}` | counter | 养号失败数 |
| `nurture_action_duration_seconds{platform,kind}` | histogram | action 耗时 |
| `opencli_session_memory_mb{cdp_port}` | gauge | Chrome 内存 |
| `platform_account_status_count{platform,status}` | gauge | 各状态账号数 |
| `celery_task_queue_length{queue}` | gauge | 任务积压 |
| `error_total{kind}` | counter | 错误计数(分类) |

### 5.3 告警

| 触发 | 级别 | 通道 |
|---|---|---|
| API P95 > 1s 持续 5min | warning | in-app + webhook |
| 养号任务失败率 > 20% / 1h | warning | in-app |
| 任意账号被风控 | error | in-app + webhook + email |
| Chrome session 全部 idle > 1h | warning | in-app |
| 数据库连接池耗尽 | error | in-app + webhook |
| 备份失败 | error | in-app + email |
| audit log 写入失败 | critical | 立即人工介入 |

---

## 6. 兼容性

### 6.1 浏览器 / 运行环境

- **opencli 后端**:Chrome ≥ 100(实测 124+ 稳定)。
- **管理后台(前端)**:Chrome ≥ 100、Edge ≥ 100、Safari ≥ 15。不支持 IE。
- 不强制适配移动端浏览器(后台以桌面端为主)。

### 6.2 运行时

- Python ≥ 3.11(项目 `.python-version` 已锁 3.11.x)。
- Node ≥ 20(项目 `package.json` engines 已锁 20+)。
- 操作系统:macOS 12+(开发)、Ubuntu 22.04+(生产),理论兼容 Debian 12 / Rocky 9。

### 6.3 数据库

- 开发:SQLite 3.40+。
- 生产:PostgreSQL 14+ / 15 / 16(MySQL 暂不支持,因 JSONB / partial index 用得多)。

### 6.4 API 兼容

- v0.2 一旦发布,`/api/v1/*` 接口的 path / method / 响应字段**只增不破坏**。
- 不再使用的字段先 `deprecated` 标记,6 个月后再删除,删除时在 CHANGELOG 注明。
- 破坏性变更只允许出现在 `/api/v2/`。

---

## 7. 数据合规

### 7.1 敏感字段加密

| 字段 | 加密方式 |
|---|---|
| `operators.password_hash` | bcrypt |
| `platform_accounts.session_cookies` | AES-256-GCM(本地密钥 + env master key) |
| `audit_logs.payload` 中含 cookies | AES-256-GCM |
| 通知 `body` 包含手机号 / 邮箱 | 脱敏(显示 `138****1234`) |

加密密钥从 `MEDIA_MGR_MASTER_KEY` 派生(env 注入),不进 git,不进日志。密钥每 90 天轮换,旧密钥保留 30 天以解密历史数据。

### 7.2 数据导出

- 所有"批量导出"必须经 audit log(actor + 时间 + 范围 + 数量)。
- 大于 10000 行的导出走异步 job,完成后通过通知中心交付下载链接(24h 有效)。
- 导出文件不包含密码 / cookies / token;包含明文手机号 / 邮箱时,需二次确认。

### 7.3 数据删除

- 删除 operator:`status=disabled` + 撤销 token + 清空姓名 / 邮箱 / 手机号(保留 username 用于审计追溯,加盐 hash)。
- 删除 platform_account:软删除 + 清理 cookies 文件 + 撤销未完成任务 + 标记关联 favorites `account_id=NULL`。
- 删除 platform_account 的 cookies 文件 **必须** 物理删除,不允许"逻辑删除留作恢复"。

---

## 8. 开发流程

### 8.1 TDD 与覆盖率

- 关键模块单测覆盖率 ≥ 80%(`platforms/*` adapter、`tasks/*`、`core/security.py` 必须 100%)。
- 整体覆盖率 ≥ 60%。
- CI 上 coverage 下降 ≥ 1% 拒绝合入。
- 不写测试的 PR = 拒绝合入。

### 8.2 Code Review

- 所有 PR 至少 1 名 reviewer 通过,涉及数据库 / 安全 / worker 代码需 2 名。
- 涉及 spec 的代码改动必须先有对应 `docs/superpowers/specs/<日期>-<slug>-design.md`。
- 涉及模型 / 迁移 / schema 的 TODO,验收项必须含"重启 worker"。

### 8.3 CI/CD

GitHub Actions 流水线:

1. `lint` — ruff(后端) / eslint(前端)
2. `type-check` — mypy(后端) / tsc --noEmit(前端)
3. `test` — pytest(后端) / vitest(前端) / playwright(前端 E2E)
4. `build` — docker build + 镜像扫描(trivy 高危 CVE 阻断)
5. `coverage` — coverage report,下降阻断
6. `migration-check` — alembic upgrade head 干跑 + downgrade 回滚
7. `docs-lint` — markdown 链接检查(可选)

合并到 `main` 后自动:

- 构建多架构镜像(`linux/amd64`、`linux/arm64`);
- 推送到 GHCR;
- 部署到测试环境(自动);
- 生产环境需手动确认。

### 8.4 提交规范

- commit message 格式:`<type>(<scope>): <subject>`,如 `feat(xhs): add account reset endpoint`。
- type 限定:`feat` / `fix` / `refactor` / `test` / `docs` / `chore` / `perf` / `revert`。
- 每个 commit 关联一条 TODO 项;TODO 完成时同步更新 `docs/TODO.md`。
- 不允许 commit:`.env` / `*.sqlite3` / `data/` / `node_modules/` / `__pycache__/`。

### 8.5 分支策略

- `main` — 受保护,只接受 PR,不允许直推。
- `feat/*` / `fix/*` / `chore/*` — 功能 / 修复 / 杂项,从最新 `main` 拉。
- 长期分支需 PM 批准。
- 版本 tag:`v0.2.0`,由 release-drafter 自动生成 draft。

---

## 9. 风险与限制

### 9.1 v0.2 平台范围

- **仅小红书(`xhs`)可用**。其他 7 个平台(weibo / douyin / zhihu / twitter / bilibili / xiaoyuzhou / wechat_official)的 API 路径已预留,但请求会返回 `501 / code=10504`。
- 前端 UI 上对这些平台显示「即将上线」,禁止用户对 stub 平台做任何"成功"假设。
- v0.3 起按平台逐个实现,预计优先级:weibo > douyin > zhihu > bilibili > twitter > xiaoyuzhou > wechat_official。

### 9.2 单机部署

- 当前架构**仅支持单机部署**,不支持 HA(高可用)集群。
- 不支持多实例 API(无 sticky session,WS 跨实例无法保证状态)。
- 不支持多实例 Worker + 共享 CDP(CDP 端口绑定物理机)。
- 升级 v0.4 才考虑引入 Redis Pub/Sub + 跨实例 WS 路由。

### 9.3 微信公众平台限制

- 微信公众号(wechat_official)调用官方 API **必须** 申请 `appid` / `appsecret` + IP 白名单,流程不在本项目范围。
- 没有 appid 的运营无法使用该平台。
- 微信平台不在 v0.2 / v0.3 实施计划内,仅占位。

### 9.4 平台风控不确定性

- 小红书风控规则不公开,本项目采用"保守动作 + 风险评分"策略,无法承诺 0 封号。
- 一旦平台升级反爬,可能需要紧急更新 adapter,响应时间 SLA:**4 小时内** 给出 mitigation,24 小时内发布修复版本。
- 客户须知:使用本工具产生的账号风险由客户自行承担,本项目仅提供技术能力,不做合规背书。

### 9.5 数据丢失风险

- SQLite 单文件存储,**生产环境强烈建议切换 PostgreSQL**。
- 单机磁盘故障 → RPO 最长 24h(下次全量备份前)。
- 启用 PostgreSQL + WAL 归档后,RPO 缩短到 5min。

### 9.6 性能上限

- 仪表盘聚合查询(`pending-issues` / `daily-stats`)在账号数 > 5000 时可能超过 2s P95。
- nurture task 并发 > 100 时,Chrome 内存占用可能超过 32GB,需要拆分 worker。
- favorites 数据量 > 100 万条时,导出 / 搜索体验下降,需引入归档表。

### 9.7 法律与合规边界

- 本项目不内置"绕过平台风控"功能,所有动作通过浏览器正常交互完成。
- 自动化操作需遵守各平台《用户协议》《社区规范》,违规使用风险由用户承担。
- cookies / 账号数据属用户资产,本项目不收集、不上传、不分析,仅本地保存。
- 团队开发不接入任何第三方"养号云控"服务。

### 9.8 不承诺项

- v0.2 不承诺:多租户、移动端、SSO(LDAP/OAuth)、i18n 多语言、暗色主题(路线图 v0.3+)。
- 不承诺:小红书以外的平台在 v0.2 内的可用性。
- 不承诺:7×24 客服(issue tracker + 文档为主,响应时间 1 个工作日)。

---

## 附录:指标速查表

| 维度 | 指标 | 数值 |
|---|---|---|
| 性能 | API P95 (CRUD) | < 500ms |
| 性能 | API P95 (复杂查询) | < 2000ms |
| 性能 | 首屏 LCP | < 2.0s |
| 性能 | 前端 main bundle | < 500KB gzip |
| 可用性 | 月度可用性 | ≥ 99% |
| 可用性 | Chrome 崩溃恢复 | < 30s |
| 可用性 | 任务失败重试 | 3 次指数退避 |
| 可用性 | 全量备份 | 每天 1 次,30 天保留 |
| 可用性 | 日志保留 | 180 天 |
| 安全 | access token | 24h |
| 安全 | refresh token | 7d |
| 安全 | 密码 | bcrypt cost=12, ≥ 8 位 |
| 安全 | 失败登录限流 | 5 / 5min / IP+username |
| 可扩展 | 加 1 平台工作量 | 1 表 + 1 adapter + 1 config |
| 可扩展 | Worker 并发 | ≤ 3 / 实例 |
| 可扩展 | 单账号并发 | ≤ 1 nurture task |
| 合规 | 备份保留 | 30 天(可扩 90) |
| 合规 | audit log 保留 | 180 天 |
| 合规 | cookies 文件权限 | 700 |

---

## 变更记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-08-16 | 0.2.0 | 初稿,覆盖 9 大维度,含硬指标与风险清单 |
