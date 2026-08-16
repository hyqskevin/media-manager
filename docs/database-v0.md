# media-manager — v0 数据库设计

> **版本:** v0.1.0 | **日期:** 2026-08-16
> **数据库:** v0 一期 SQLite（文件 `data/media_manager.db`），v1 升级 PostgreSQL 16
> **继承基线:** [上级 Operate 数据库设计](../subsystems/operate/database.md)
> **精简原则:** v0 只保留平台账号 + 养号 + 收藏夹 6 张表，砍掉 publish/workflow/material/schedule 等 6 张

---

## 一、v0 数据表清单（6 张）

| # | 表名 | 说明 | 对应模块 |
|---|---|---|---|
| 1 | `platforms` | 平台字典（8 平台预置） | 平台账号 |
| 2 | `media_accounts` | 多平台媒体账号 | 平台账号 |
| 3 | `nurture_tasks` | 养号任务执行记录 | 养号 |
| 4 | `favorite_snapshots` | 收藏夹快照条目 | 收藏夹 / 养号 |
| 5 | `nurture_schedules` | 定时养号计划 | 养号 |
| 6 | `browse_logs` | 浏览行为日志（防风控审计） | 养号 |

> v0 砍掉的 6 张：workflow_tasks / publish_tasks / materials / content_schedule / workflow_rules / workflow_rule_logs / account_daily_stats / article_metrics / collections / collection_items（v0 改用 favorite_snapshots 单表）。

---

## 二、字段命名与主键约定

- 主键：UUID，迁移到 PG 后用 `gen_random_uuid()`；SQLite 用 `String(36)` + Python 端 uuid4
- 时间戳：DATETIME（带时区），UTC，`created_at` / `updated_at`
- 跨库引用：v0 单库，无跨库逻辑外键（Browse/Edit/Generate v1 才接）

---

## 三、完整 DDL（SQLite 一期）

### 3.1 platforms — 平台字典

```sql
CREATE TABLE platforms (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,           -- 平台标识：xhs / weibo / douyin / zhihu / twitter / bilibili / xiaoyuzhou / weixin
    display_name VARCHAR(100) NOT NULL,          -- 显示名：微博 / 知乎 / 小红书
    icon VARCHAR(50),                            -- 图标标识
    homepage VARCHAR(500),
    is_active BOOLEAN DEFAULT 1,
    adapter_type VARCHAR(20) NOT NULL,           -- browser / native / browse_only
    supports_like BOOLEAN DEFAULT 0,
    supports_favorite BOOLEAN DEFAULT 0,
    supports_favorites_list BOOLEAN DEFAULT 0,   -- 是否支持拉取收藏夹列表
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**预置数据（8 个平台）：**

| name | display_name | adapter_type | like | favorite | favorites_list |
|---|---|---|---|---|---|
| xhs | 小红书 | browser | 1 | 1 | 1 |
| weibo | 微博 | browser | 1 | 1 | 1 |
| douyin | 抖音 | browser | 1 | 1 | 1 |
| zhihu | 知乎 | native | 1 | 1 | 1 |
| twitter | Twitter | native | 1 | 1 | 1 |
| bilibili | B站 | native | 1 | 1 | 1 |
| xiaoyuzhou | 小宇宙 | browse_only | 0 | 1 | 1 |
| weixin | 公众号 | browse_only | 0 | 0 | 0 |

---

### 3.2 media_accounts — 多平台账号

```sql
CREATE TABLE media_accounts (
    id VARCHAR(36) PRIMARY KEY,
    platform_id VARCHAR(36) NOT NULL,            -- FK→platforms.id
    account_name VARCHAR(200) NOT NULL,          -- 显示名
    account_id VARCHAR(200),                     -- 平台原生账号 ID（whoami 拿到）
    account_avatar VARCHAR(500),
    status VARCHAR(20) DEFAULT 'active',         -- active / expired / banned / relogin_required / disabled
    login_status VARCHAR(20) DEFAULT 'unknown',  -- 缓存最近一次 whoami 结果
    cookies TEXT,                                -- JSON 字符串（应用层加密）
    session_name VARCHAR(100),                   -- opencli session 名
    cdp_port INTEGER,                            -- 独立 CDP 端口（chrome_pool 分配）
    chrome_user_data_dir VARCHAR(500),           -- Chrome user-data-dir 路径
    priority INTEGER DEFAULT 0,                  -- 调度优先级
    enabled BOOLEAN DEFAULT 1,
    config JSON,                                 -- 养号配置（browse_count / like_probability 等）
    last_login_at TIMESTAMP,
    last_whoami_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (platform_id) REFERENCES platforms(id)
);

CREATE INDEX idx_accounts_platform ON media_accounts(platform_id);
CREATE INDEX idx_accounts_status ON media_accounts(status);
CREATE INDEX idx_accounts_enabled ON media_accounts(enabled);
```

**字段说明：**

| 字段 | 说明 |
|---|---|
| `cdp_port` | 每个账号独立 CDP 端口（chrome_pool 自动分配 9223-9322 范围） |
| `chrome_user_data_dir` | 每个账号独立 user-data-dir（cookie 完全隔离） |
| `session_name` | opencli session 名（`opencli --session <name>`） |
| `login_status` | 缓存：`unknown`/`logged_in`/`logged_out`（whoami 实时结果） |
| `config` | 养号参数 JSON（详见 [overview.md §4.2](./overview.md#42-配置参数每账号独立)） |

---

### 3.3 nurture_tasks — 养号任务

```sql
CREATE TABLE nurture_tasks (
    id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,             -- FK→media_accounts.id
    action VARCHAR(20) NOT NULL,                 -- browse / like / favorite / snapshot / full（全套）
    status VARCHAR(20) DEFAULT 'pending',        -- pending / running / success / failed / stopped
    trigger VARCHAR(20) DEFAULT 'manual',        -- manual / schedule / retry
    schedule_id VARCHAR(36),                     -- FK→nurture_schedules.id（定时触发的来源）
    progress JSON,                               -- 进度 JSON {browsed: 5, liked: 1, favorited: 0}
    config_snapshot JSON,                        -- 任务执行时的 config 快照
    browse_count INTEGER DEFAULT 0,
    like_count INTEGER DEFAULT 0,
    favorite_count INTEGER DEFAULT 0,
    snapshot_count INTEGER DEFAULT 0,            -- 收藏夹快照拉取条数
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES media_accounts(id)
);

CREATE INDEX idx_nurture_tasks_account ON nurture_tasks(account_id);
CREATE INDEX idx_nurture_tasks_status ON nurture_tasks(status);
CREATE INDEX idx_nurture_tasks_created ON nurture_tasks(created_at);
CREATE INDEX idx_nurture_tasks_schedule ON nurture_tasks(schedule_id);
```

**字段说明：**

| 字段 | 说明 |
|---|---|
| `action` | 任务类型：`browse`（仅浏览）/ `like`（浏览+点赞）/ `favorite`（浏览+收藏）/ `snapshot`（仅拉收藏夹）/ `full`（全做） |
| `progress` | 实时进度 JSON，前端轮询展示 |
| `config_snapshot` | 任务执行时的 config 快照（防止后续修改 config 影响历史任务） |
| `trigger` | 触发方式：`manual`（手动按钮）/ `schedule`（定时）/ `retry`（自动重试） |

---

### 3.4 favorite_snapshots — 收藏夹快照

```sql
CREATE TABLE favorite_snapshots (
    id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,             -- FK→media_accounts.id
    platform VARCHAR(50) NOT NULL,               -- 平台名（冗余便于查询）
    item_external_id VARCHAR(500) NOT NULL,      -- 平台原生内容 ID（如小红书 note_id）
    item_type VARCHAR(20) DEFAULT 'note',         -- note / post / video / article
    title VARCHAR(1000),
    url VARCHAR(2000),
    author VARCHAR(200),
    thumbnail VARCHAR(2000),
    summary TEXT,
    snapshot_at TIMESTAMP NOT NULL,               -- 快照时间（按次任务批次）
    snapshot_batch VARCHAR(36) NOT NULL,          -- 同一批任务的 UUID（方便按批次对比）
    favorited_at TIMESTAMP,                       -- 平台记录的时间（如可获取）
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES media_accounts(id)
);

CREATE UNIQUE INDEX uq_fav_snapshot_unique
    ON favorite_snapshots(account_id, snapshot_batch, item_external_id);

CREATE INDEX idx_fav_snapshot_account ON favorite_snapshots(account_id);
CREATE INDEX idx_fav_snapshot_platform ON favorite_snapshots(platform);
CREATE INDEX idx_fav_snapshot_batch ON favorite_snapshots(snapshot_batch);
CREATE INDEX idx_fav_snapshot_at ON favorite_snapshots(snapshot_at);
```

**字段说明：**

| 字段 | 说明 |
|---|---|
| `snapshot_batch` | 同一批养号任务的 UUID，**对比两次快照的差异**（新增 / 移除 / 保留） |
| `item_external_id` | 平台原生 ID，配合 platform 唯一标识一条收藏 |
| `snapshot_at` | 快照时刻，便于按时间轴展示 |

**唯一约束：**(account_id, snapshot_batch, item_external_id) 防止同一批重复插入。

---

### 3.5 nurture_schedules — 定时养号计划

```sql
CREATE TABLE nurture_schedules (
    id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,             -- FK→media_accounts.id
    name VARCHAR(200),
    cron VARCHAR(50) NOT NULL,                   -- 标准 5 字段 cron "0 9 * * *"
    action VARCHAR(20) DEFAULT 'full',           -- browse / like / favorite / snapshot / full
    enabled BOOLEAN DEFAULT 1,
    quiet_hours VARCHAR(20),                     -- "00:00-07:00" 静默时段
    last_run_at TIMESTAMP,
    last_task_id VARCHAR(36),                    -- FK→nurture_tasks.id（最近一次执行）
    next_run_at TIMESTAMP,                       -- Celery beat 扫描用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES media_accounts(id)
);

CREATE INDEX idx_schedules_account ON nurture_schedules(account_id);
CREATE INDEX idx_schedules_enabled ON nurture_schedules(enabled);
CREATE INDEX idx_schedules_next_run ON nurture_schedules(next_run_at);
```

**字段说明：**

| 字段 | 说明 |
|---|---|
| `cron` | 标准 5 字段 cron 表达式 |
| `next_run_at` | Celery beat 每分钟扫描：到点触发 `execute_scheduled_nurture` |
| `quiet_hours` | 静默时段，到达时即使 cron 触发也跳过 |

---

### 3.6 browse_logs — 浏览行为日志（防风控审计）

```sql
CREATE TABLE browse_logs (
    id VARCHAR(36) PRIMARY KEY,
    account_id VARCHAR(36) NOT NULL,
    nurture_task_id VARCHAR(36),
    platform VARCHAR(50) NOT NULL,
    item_external_id VARCHAR(500),                -- 浏览的内容 ID
    item_url VARCHAR(2000),
    action VARCHAR(20) NOT NULL,                  -- view / like / favorite / unlike / unfavorite
    dwell_seconds INTEGER,                        -- 停留时长
    captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES media_accounts(id),
    FOREIGN KEY (nurture_task_id) REFERENCES nurture_tasks(id)
);

CREATE INDEX idx_browse_logs_account ON browse_logs(account_id);
CREATE INDEX idx_browse_logs_task ON browse_logs(nurture_task_id);
CREATE INDEX idx_browse_logs_action ON browse_logs(action);
CREATE INDEX idx_browse_logs_captured ON browse_logs(captured_at);
```

**字段说明：**

| 字段 | 说明 |
|---|---|
| `action` | 记录具体动作：`view`（仅浏览）/ `like`（点赞）/ `favorite`（收藏）/ `unlike`/`unfavorite`（如支持） |
| `dwell_seconds` | 停留时长，用于审计"是否像真人" |
| `item_external_id` + `platform` | 定位具体内容 |

**用途：**
1. 风控审计——异常行为告警（同一账号 1 小时内点赞 200 条）
2. 数据分析——养号效果（哪个时段养号转化率高）
3. v1 数据中心的基础数据

---

## 四、关系图

```
media_accounts ─┬─→ nurture_tasks ─→ browse_logs
                │       │
                │       └─→ favorite_snapshots (snapshot_batch)
                │
                └─→ nurture_schedules ─→ nurture_tasks (trigger='schedule')
                
platforms ─→ media_accounts
```

---

## 五、迁移到 PostgreSQL（v1 升级点）

迁移 Alembic 自动处理，关键差异：

| 差异点 | SQLite (v0) | PostgreSQL (v1) |
|---|---|---|
| 主键生成 | Python `uuid4()` | `DEFAULT gen_random_uuid()` |
| 时间戳 | `TIMESTAMP` | `TIMESTAMPTZ` |
| JSON 字段 | `JSON` (TEXT 存储) | `JSONB` + GIN 索引 |
| 触发器 | 无（应用层维护） | `set_updated_at()` 触发器 |
| 并发 | 单写 | WAL / 行锁 |

---

## 六、关联文档

- [本仓库 SPEC.md](../SPEC.md)
- [v0 总览](./overview.md)
- [API 设计](./api.md)
- [浏览器自动化](./browser-bridge.md)
- [上级 Operate 完整数据库设计](../subsystems/operate/database.md)（v1 恢复完整 12 张表）