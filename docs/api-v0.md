# media-manager — v0 API 设计

> **版本:** v0.1.0 | **日期:** 2026-08-16
> **路径前缀:** `/api/v1/manage/*`（v0 自定义前缀，避免与 Operate 体系撞）
> **继承基线:** [上级 Operate API 设计](../subsystems/operate/api.md)
> **v0 砍掉:** 工作流 / 发布 / 素材 / 日历 / 数据中心 / 规则 6 大模块 API

---

## 一、通用规范

### 1.1 响应格式

**成功：**
```json
{
  "code": 0,
  "data": {...},
  "message": "ok"
}
```

**失败：**
```json
{
  "code": <error_code>,
  "data": null,
  "message": "错误描述",
  "details": {}
}
```

### 1.2 分页规范

列表接口统一 `page` + `size`，`page` 从 1 开始，`size` 默认 20，最大 100：

```json
{
  "code": 0,
  "data": {
    "items": [...],
    "total": 156,
    "page": 1,
    "size": 20
  },
  "message": "ok"
}
```

### 1.3 错误码

| 范围 | 模块 |
|---|---|
| 1001-1099 | 账号模块 |
| 2001-2099 | 养号模块 |
| 3001-3099 | 收藏夹模块 |
| 4001-4099 | 定时模块 |
| 9001-9099 | 系统错误 |

---

## 二、平台账号 API（`/api/v1/manage/accounts`）

### 2.1 GET /accounts — 账号列表

**查询参数：**

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `platform` | string | - | 平台标识（xhs / weibo / douyin ...） |
| `status` | string | - | active / expired / banned / relogin_required / disabled |
| `enabled` | bool | - | 是否启用 |
| `page` | int | 1 | |
| `size` | int | 20 | |

**响应 items 字段：**
```json
{
  "id": "acc-uuid",
  "platform_id": "plat-uuid-xhs",
  "platform_name": "xhs",
  "platform_display_name": "小红书",
  "account_name": "我的小红书号",
  "account_id": "xhs-12345",
  "account_avatar": "https://...",
  "status": "active",
  "login_status": "logged_in",
  "cdp_port": 9223,
  "enabled": true,
  "last_login_at": "2026-08-15T10:00:00Z",
  "last_whoami_at": "2026-08-16T09:00:00Z",
  "created_at": "2026-08-10T08:00:00Z"
}
```

> 响应**不返回** `cookies` 字段（脱敏）

### 2.2 POST /accounts — 新增账号

**请求体：**
```json
{
  "platform_id": "plat-uuid-xhs",
  "account_name": "我的小红书号",
  "account_id": "xhs-12345",
  "account_avatar": "https://...",
  "cookies": {"cookie_data": "..."},
  "config": {
    "browse_count": 10,
    "like_probability": 0.05,
    "favorite_probability": 0.02,
    "daily_max_tasks": 3,
    "quiet_hours": "00:00-07:00"
  }
}
```

### 2.3 GET /accounts/{id} — 账号详情

### 2.4 PUT /accounts/{id} — 更新账号

允许更新：`account_name`、`account_avatar`、`cookies`、`config`、`enabled`、`priority`

### 2.5 DELETE /accounts/{id} — 删除账号

> 软删除（设置 `status='disabled'`），不物理删除

### 2.6 POST /accounts/{id}/whoami — 检查登录态

调用 chrome_pool 中该账号的 Chrome 实例，调对应平台适配器的 `whoami()` 方法。

**响应：**
```json
{
  "code": 0,
  "data": {
    "is_valid": true,
    "platform_user_id": "xhs-12345",
    "platform_user_name": "我的小红书号",
    "avatar": "https://...",
    "checked_at": "2026-08-16T10:00:00Z"
  }
}
```

**失败：**
- 账号离线（CDP 无连接）→ 错误码 `1001`（Account chrome offline）
- Cookie 已失效 → `data.is_valid=false`，自动更新 `status='relogin_required'`，错误码 `1002`

### 2.7 POST /accounts/{id}/relogin — 触发重新登录

> v0 暂不实现自研登录流程，调用平台适配器的 `launch_login_window()`，让用户在浏览器窗口手动登录，登录完成后自动捕获 cookies。

**响应：**
```json
{
  "code": 0,
  "data": {
    "login_url": "https://www.xiaohongshu.com/login",
    "cdp_port": 9223,
    "expires_at": "2026-08-16T10:05:00Z",
    "message": "请在 5 分钟内完成登录"
  }
}
```

### 2.8 GET /accounts/{id}/config — 获取养号配置

返回该账号的 `config` JSON。

### 2.9 PUT /accounts/{id}/config — 更新养号配置

**请求体：**
```json
{
  "browse_count": 15,
  "like_probability": 0.03,
  "favorite_probability": 0.01,
  "daily_max_tasks": 2,
  "quiet_hours": "01:00-08:00",
  "snapshot_favorites": true
}
```

---

## 三、养号任务 API（`/api/v1/manage/nurture`）

### 3.1 POST /nurture/tasks — 立即触发养号任务

**请求体：**
```json
{
  "account_id": "acc-uuid",
  "action": "full",
  "config_override": null
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `account_id` | 是 | 目标账号 |
| `action` | 是 | browse / like / favorite / snapshot / full |
| `config_override` | 否 | 临时覆盖账号 config（如不覆盖用 account.config） |

**响应：**
```json
{
  "code": 0,
  "data": {
    "task_id": "task-uuid",
    "status": "pending",
    "created_at": "2026-08-16T10:00:00Z"
  }
}
```

后台异步执行，Celery 任务 `execute_nurture_task` 立即派发。

### 3.2 GET /nurture/tasks — 任务列表

**查询参数：**

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `account_id` | UUID | - | 按账号筛选 |
| `status` | string | - | pending / running / success / failed / stopped |
| `trigger` | string | - | manual / schedule / retry |
| `date_from` | ISO 8601 | - | |
| `date_to` | ISO 8601 | - | |
| `page` | int | 1 | |
| `size` | int | 20 | |

**响应 items 字段：**
```json
{
  "id": "task-uuid",
  "account_id": "acc-uuid",
  "account_name": "我的小红书号",
  "platform": "xhs",
  "action": "full",
  "status": "running",
  "trigger": "manual",
  "browse_count": 8,
  "like_count": 1,
  "favorite_count": 0,
  "snapshot_count": 23,
  "progress": {
    "current_step": "scrolling",
    "scrolled_count": 5,
    "liked_count": 1
  },
  "started_at": "2026-08-16T10:00:00Z",
  "finished_at": null,
  "error_message": null
}
```

### 3.3 GET /nurture/tasks/{id} — 任务详情

返回完整记录 + 实时 `progress`。

### 3.4 POST /nurture/tasks/{id}/stop — 停止任务

只能停止 `status='running'` 的任务，设置 `status='stopped'`。

**响应：**
```json
{
  "code": 0,
  "data": {
    "id": "task-uuid",
    "status": "stopped",
    "stopped_at": "2026-08-16T10:05:00Z"
  }
}
```

### 3.5 POST /nurture/tasks/{id}/retry — 重试失败任务

重置 `retry_count=0`，立即重新执行。

### 3.6 GET /nurture/tasks/{id}/logs — 任务关联浏览日志

返回该任务的 `browse_logs` 列表（按时间倒序）。

### 3.7 GET /nurture/stats — 养号统计

**响应：**
```json
{
  "code": 0,
  "data": {
    "total_tasks": 156,
    "success_tasks": 142,
    "failed_tasks": 8,
    "stopped_tasks": 6,
    "total_browsed": 1560,
    "total_liked": 78,
    "total_favorited": 31,
    "today_tasks": 5,
    "today_liked": 2
  }
}
```

---

## 四、收藏夹 API（`/api/v1/manage/favorites`）

### 4.1 GET /favorites/snapshots — 收藏夹快照列表

**查询参数：**

| 参数 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `account_id` | UUID | - | |
| `platform` | string | - | |
| `batch` | UUID | - | 指定批次（对比用） |
| `date_from` | ISO 8601 | - | |
| `date_to` | ISO 8601 | - | |
| `page` | int | 1 | |
| `size` | int | 20 | |

**响应 items：**
```json
{
  "id": "snap-uuid",
  "account_id": "acc-uuid",
  "platform": "xhs",
  "item_external_id": "xhs-note-123",
  "item_type": "note",
  "title": "AI 趋势观察",
  "url": "https://www.xiaohongshu.com/explore/...",
  "author": "技术博主",
  "thumbnail": "https://...",
  "snapshot_at": "2026-08-16T10:00:00Z",
  "snapshot_batch": "batch-uuid",
  "favorited_at": "2026-08-15T08:00:00Z"
}
```

### 4.2 GET /favorites/diff — 对比两次快照

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `account_id` | UUID | 是 | |
| `batch_from` | UUID | 是 | 起始批次 |
| `batch_to` | UUID | 是 | 目标批次 |

**响应：**
```json
{
  "code": 0,
  "data": {
    "batch_from": "batch-uuid-1",
    "batch_to": "batch-uuid-2",
    "added": [
      {"item_external_id": "xhs-note-200", "title": "新增收藏", ...}
    ],
    "removed": [
      {"item_external_id": "xhs-note-100", "title": "已移除收藏", ...}
    ],
    "kept": [
      {"item_external_id": "xhs-note-123", "title": "保留收藏", ...}
    ],
    "stats": {
      "from_count": 25,
      "to_count": 30,
      "added_count": 8,
      "removed_count": 3,
      "kept_count": 22
    }
  }
}
```

### 4.3 GET /favorites/batches — 列出所有批次

按账号分组的所有 `snapshot_batch`，用于前端选择对比。

### 4.4 POST /favorites/snapshot — 手动触发快照

立即拉取指定账号的收藏夹并入库（不执行浏览/点赞/收藏行为）。

**请求体：**
```json
{
  "account_id": "acc-uuid"
}
```

**响应：**
```json
{
  "code": 0,
  "data": {
    "snapshot_batch": "batch-uuid",
    "item_count": 25,
    "started_at": "2026-08-16T10:00:00Z"
  }
}
```

---

## 五、定时计划 API（`/api/v1/manage/schedules`）

### 5.1 GET /schedules — 计划列表

**查询参数：** `account_id`、`enabled`

**响应 items：**
```json
{
  "id": "sched-uuid",
  "account_id": "acc-uuid",
  "account_name": "我的小红书号",
  "name": "每日早晚养号",
  "cron": "0 9,21 * * *",
  "action": "full",
  "enabled": true,
  "quiet_hours": "00:00-07:00",
  "last_run_at": "2026-08-16T09:00:00Z",
  "next_run_at": "2026-08-16T21:00:00Z"
}
```

### 5.2 POST /schedules — 创建计划

**请求体：**
```json
{
  "account_id": "acc-uuid",
  "name": "每日早晚养号",
  "cron": "0 9,21 * * *",
  "action": "full",
  "quiet_hours": "00:00-07:00",
  "enabled": true
}
```

### 5.3 PUT /schedules/{id} — 更新计划

### 5.4 DELETE /schedules/{id} — 删除计划

### 5.5 POST /schedules/{id}/enable — 启用

### 5.6 POST /schedules/{id}/disable — 停用

---

## 六、平台字典 API（`/api/v1/manage/platforms`）

### 6.1 GET /platforms — 平台列表

返回所有 `platforms`（含能力字段：supports_like / supports_favorite / adapter_type），前端用于：
- 账号创建时下拉选择
- 按钮可用性判断（如公众号不支持点赞，按钮灰掉）

---

## 七、关联文档

- [本仓库 SPEC.md](../SPEC.md)
- [v0 总览](./overview.md)
- [数据库设计](./database.md)
- [浏览器自动化](./browser-bridge.md)
- [上级 Operate 完整 API 设计](../subsystems/operate/api.md)（v1 恢复完整 8 模块 API）