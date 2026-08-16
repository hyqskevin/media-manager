# media-manager v0.2 — API 契约

> 版本: v0.2.0  ·  状态: 草稿  ·  最后更新: 2026-08-16
> 适用范围: `backend/app/api/v1/*` 全部端点 + WebSocket 通道
> 读者: 前端工程师、QA、后端工程师、第三方接入方

本文档是 media-manager v0.2 后端 HTTP API 与 WebSocket 通道的**唯一权威契约**。任何后端实现改动都必须先更新本文件,再写代码;前端调用以前端对应章节为准。

---

## 目录

1. [通用规范](#1-通用规范)
2. [Auth 模块](#2-auth-模块)
3. [Operators 模块](#3-operators-模块)
4. [Platform Accounts 模块](#4-platform-accounts-模块)
5. [Platform Configs 模块](#5-platform-configs-模块)
6. [Nurture Tasks 模块](#6-nurture-tasks-模块)
7. [Nurture Schedules 模块](#7-nurture-schedules-模块)
8. [Nurture Action Sets 模块](#8-nurture-action-sets-模块)
9. [Favorites 模块](#9-favorites-模块)
10. [Dashboard 模块](#10-dashboard-模块)
11. [Risk Config 模块](#11-risk-config-模块)
12. [Notifications 模块](#12-notifications-模块)
13. [Audit Logs 模块](#13-audit-logs-模块)
14. [Browser Sessions 模块](#14-browser-sessions-模块)
15. [Health 模块](#15-health-模块)
16. [WebSocket](#16-websocket实时通知)

---

## 1. 通用规范

### 1.1 基础路径

所有业务端点统一挂载在:

```
/api/v1
```

平台/账号/养号类资源因为按平台分路径,前缀变成:

```
/api/v1/platforms/{platform}/...
```

完整域名示例:

| 环境 | Base URL |
|---|---|
| 本地开发 | `http://127.0.0.1:8000/api/v1` |
| 测试环境 | `https://test-mgr.example.com/api/v1` |
| 生产环境 | `https://mgr.example.com/api/v1` |

### 1.2 认证

除 `POST /auth/login`、`GET /health`、`GET /health/ready`、`GET /health/live` 外,所有端点必须携带:

```http
Authorization: Bearer <jwt>
```

JWT 解析后挂载到 FastAPI 的 `request.state.operator`,包含:

| 字段 | 类型 | 说明 |
|---|---|---|
| `operator_id` | int | 操作员 ID |
| `username` | string | 用户名 |
| `role` | string | 角色 key(参见 /roles 端点) |
| `permissions` | string[] | 显式授权的 permission 列表 |

每次请求会校验:

1. token 签名 + 过期(24h);
2. operator 是否被 `disable`;
3. operator 角色是否包含端点要求的 permission(参见 `operator_permissions` 表)。

Refresh token 通过 `POST /auth/refresh` 单独续期(7d 过期,绑定 fingerprint)。

### 1.3 请求格式

- `Content-Type: application/json; charset=utf-8`
- `Accept: application/json`
- 所有请求体均为 JSON,字段名使用 **snake_case**;返回体同样使用 snake_case。
- 路径参数也使用 snake_case,如 `{account_id}`。
- 二进制上传(暂未使用)走 `multipart/form-data`。

### 1.4 响应格式

成功响应:

```json
{
  "code": 0,
  "message": "ok",
  "data": { "...": "..." }
}
```

错误响应:

```json
{
  "code": 10001,
  "message": "operator not found",
  "data": null,
  "request_id": "0c1a2b3c-..."
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `code` | 是 | 业务码,`0` 表示成功,非 `0` 表示失败 |
| `message` | 是 | 人类可读信息,i18n key 或纯文本 |
| `data` | 否 | 业务负载;列表接口无数据时为 `[]`,分页接口为 `{items, page, page_size, total}` |
| `request_id` | 是(失败时) | 链路追踪 ID,前后端日志定位用 |

列表分页:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [ ... ],
    "page": 1,
    "page_size": 20,
    "total": 132
  }
}
```

### 1.5 分页参数

| 参数 | 默认 | 上限 | 说明 |
|---|---|---|---|
| `page` | 1 | — | 1-based |
| `page_size` | 20 | 200 | 超过 200 自动截断 |

排序参数(如 `sort=created_at`)可附 `order=desc|asc`,默认 `desc`。

### 1.6 时间格式

- 所有时间字段使用 **ISO 8601 + UTC**,形如 `2026-08-16T08:12:44.123Z`。
- 涉及日期过滤(无时间)使用 `YYYY-MM-DD`,按服务器时区(Asia/Shanghai)解析。
- 数值型时间戳(epoch ms)禁止出现在 API 层。

### 1.7 错误码表

业务错误码按域分段:

| 段位 | 域 | 范围 |
|---|---|---|
| 0 | 成功 | `0` |
| 1xxxx | 通用 / 鉴权 | `10000 - 10999` |
| 2xxxx | Auth | `20000 - 20999` |
| 3xxxx | Operators / Roles | `30000 - 30999` |
| 4xxxx | Platform Accounts | `40000 - 40999` |
| 5xxxx | Platform Configs | `50000 - 50999` |
| 6xxxx | Nurture Tasks | `60000 - 60999` |
| 7xxxx | Nurture Schedules / Action Sets | `70000 - 70999` |
| 8xxxx | Favorites | `80000 - 80999` |
| 9xxxx | Risk / Notifications / Audit | `90000 - 90999` |
| 10xxxx | Browser / Health | `100000 - 100999` |

常用错误码:

| HTTP | 业务 code | message | 含义 |
|---|---|---|---|
| 400 | 10000 | `bad request` | 请求参数不合法 |
| 401 | 10001 | `unauthenticated` | 缺 token / token 无效 |
| 401 | 10002 | `token expired` | access token 过期 |
| 403 | 10003 | `forbidden` | 无权限 |
| 404 | 10004 | `not found` | 资源不存在 |
| 409 | 10005 | `conflict` | 状态冲突(例如重复创建) |
| 422 | 10006 | `validation failed` | pydantic 校验失败 |
| 429 | 10007 | `rate limited` | 触发限流 |
| 500 | 10500 | `internal error` | 未捕获异常 |
| 502 | 10502 | `upstream error` | 上游(opencli / 平台)失败 |
| 503 | 10503 | `service unavailable` | 维护中 / 资源耗尽 |

前端处理建议:除 `10002` 外,所有 `code != 0` 都通过全局 toast 提示;`10002` 自动尝试一次 refresh,refresh 失败跳登录。

---

## 2. Auth 模块

基础路径:`/api/v1/auth`

| 端点 | 方法 | 鉴权 | 说明 |
|---|---|---|---|
| `/auth/login` | POST | 否 | 账号密码登录 |
| `/auth/logout` | POST | 是 | 注销当前 token |
| `/auth/refresh` | POST | 否(refresh token) | 续期 access token |
| `/auth/me` | GET | 是 | 当前操作员信息 |

### 2.1 POST /auth/login

**请求体**:

```json
{
  "username": "admin",
  "password": "s3cret-PW"
}
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "rt_8c1f...",
    "token_type": "Bearer",
    "expires_in": 86400,
    "operator": {
      "id": 1,
      "username": "admin",
      "display_name": "系统管理员",
      "role": "super_admin",
      "permissions": ["*"]
    }
  }
}
```

**错误**:

| HTTP | code | 触发条件 |
|---|---|---|
| 400 | 10000 | 缺字段 |
| 401 | 20001 | 账号或密码错误 |
| 403 | 20002 | 账号已 disable |
| 429 | 10007 | 5 分钟内同账号 5 次失败 |

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"s3cret-PW"}'
```

**TypeScript**:

```ts
export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'Bearer';
  expires_in: number;
  operator: OperatorInfo;
}

export interface OperatorInfo {
  id: number;
  username: string;
  display_name: string;
  role: string;
  permissions: string[];
}
```

### 2.2 POST /auth/logout

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "logged_out": true } }
```

服务端将当前 access token 加入黑名单(Redis,TTL=剩余有效期),同时撤销 refresh token。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/logout \
  -H "Authorization: Bearer $TOKEN"
```

### 2.3 POST /auth/refresh

**请求体**:

```json
{
  "refresh_token": "rt_8c1f..."
}
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "rt_8c1f...",
    "token_type": "Bearer",
    "expires_in": 86400
  }
}
```

**错误**:

| HTTP | code | 触发条件 |
|---|---|---|
| 401 | 20003 | refresh token 无效 / 已撤销 / 已过期 |
| 401 | 20004 | refresh token fingerprint 与当前请求不匹配(异常登录) |

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"rt_8c1f..."}'
```

### 2.4 GET /auth/me

**请求体**: 空

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 1,
    "username": "admin",
    "display_name": "系统管理员",
    "role": "super_admin",
    "permissions": ["*"],
    "last_login_at": "2026-08-15T09:00:00.000Z"
  }
}
```

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export interface AuthMe {
  id: number;
  username: string;
  display_name: string;
  role: string;
  permissions: string[];
  last_login_at: string;
}
```

---

## 3. Operators 模块

基础路径:`/api/v1`

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/operators` | GET | `operator.read` |
| `/operators` | POST | `operator.create` |
| `/operators/{id}` | GET | `operator.read` |
| `/operators/{id}` | PATCH | `operator.update` |
| `/operators/{id}` | DELETE | `operator.delete` |
| `/operators/{id}/reset-password` | POST | `operator.reset_password` |
| `/operators/{id}/enable` | POST | `operator.update` |
| `/operators/{id}/disable` | POST | `operator.update` |
| `/roles` | GET | `role.read` |
| `/roles/{role}/permissions` | PATCH | `role.update` |

### 3.1 GET /operators

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page` | int | 否 | 默认 1 |
| `page_size` | int | 否 | 默认 20,最大 200 |
| `keyword` | string | 否 | 模糊匹配 username / display_name |
| `role` | string | 否 | 角色 key |
| `status` | string | 否 | `active` / `disabled` |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 1,
        "username": "admin",
        "display_name": "系统管理员",
        "role": "super_admin",
        "status": "active",
        "created_at": "2026-06-01T03:11:00.000Z",
        "last_login_at": "2026-08-15T09:00:00.000Z"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/operators?page=1&page_size=20&status=active" \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export interface Operator {
  id: number;
  username: string;
  display_name: string;
  role: string;
  status: 'active' | 'disabled';
  created_at: string;
  last_login_at: string | null;
}
```

### 3.2 POST /operators

**请求体**:

```json
{
  "username": "ops_xhs",
  "display_name": "小红书运营",
  "role": "operator",
  "password": "initial-PW-1"
}
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 7,
    "username": "ops_xhs",
    "display_name": "小红书运营",
    "role": "operator",
    "status": "active",
    "created_at": "2026-08-16T03:11:00.000Z"
  }
}
```

**错误**:

| HTTP | code | 触发条件 |
|---|---|---|
| 409 | 30001 | username 重复 |
| 422 | 10006 | 密码长度 < 8 / 角色不存在 |

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/operators \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"ops_xhs","display_name":"小红书运营","role":"operator","password":"initial-PW-1"}'
```

### 3.3 GET /operators/{id}

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 7,
    "username": "ops_xhs",
    "display_name": "小红书运营",
    "role": "operator",
    "status": "active",
    "permissions": ["account.read", "nurture.read", "nurture.create"],
    "created_at": "2026-08-16T03:11:00.000Z",
    "last_login_at": null
  }
}
```

**错误**: 404 / 10004

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/operators/7 \
  -H "Authorization: Bearer $TOKEN"
```

### 3.4 PATCH /operators/{id}

**请求体**(全部可选,至少一个):

```json
{
  "display_name": "小红书运营(夜班)",
  "role": "operator_lead"
}
```

**响应 200**: 同 `GET /operators/{id}`。

**错误**: 404 / 10004, 422 / 10006。

**curl**:

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/operators/7 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"display_name":"小红书运营(夜班)"}'
```

### 3.5 DELETE /operators/{id}

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 7, "deleted": true } }
```

软删除(置 `status=disabled` + 撤销所有 refresh token)。不允许删除 `username="admin"` 或自己。

**错误**: 400 / 30002(试图删除自己/admin), 404 / 10004。

**curl**:

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/operators/7 \
  -H "Authorization: Bearer $TOKEN"
```

### 3.6 POST /operators/{id}/reset-password

**请求体**:

```json
{
  "new_password": "BrandNew-PW-1"
}
```

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 7, "password_reset_at": "2026-08-16T04:00:00.000Z" } }
```

操作完成后立即撤销该 operator 的所有 refresh token,强制下次登录走新密码。

**错误**: 422 / 10006(密码强度), 404 / 10004。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/operators/7/reset-password \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_password":"BrandNew-PW-1"}'
```

### 3.7 POST /operators/{id}/enable

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 7, "status": "active" } }
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/operators/7/enable \
  -H "Authorization: Bearer $TOKEN"
```

### 3.8 POST /operators/{id}/disable

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 7, "status": "disabled" } }
```

同时撤销该 operator 的所有 token。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/operators/7/disable \
  -H "Authorization: Bearer $TOKEN"
```

### 3.9 GET /roles

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "key": "super_admin",
      "display_name": "超级管理员",
      "permissions": ["*"],
      "builtin": true,
      "operator_count": 1
    },
    {
      "key": "operator",
      "display_name": "运营",
      "permissions": [
        "account.read",
        "nurture.read",
        "nurture.create",
        "nurture.update",
        "nurture.delete"
      ],
      "builtin": true,
      "operator_count": 3
    }
  ]
}
```

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/roles \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export interface Role {
  key: string;
  display_name: string;
  permissions: string[];
  builtin: boolean;
  operator_count: number;
}
```

### 3.10 PATCH /roles/{role}/permissions

**请求体**:

```json
{
  "permissions": [
    "account.read",
    "nurture.read",
    "nurture.create"
  ]
}
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "key": "operator",
    "permissions": ["account.read", "nurture.read", "nurture.create"]
  }
}
```

不允许修改 `super_admin`。`["*"]` 表示全权限。

**错误**: 400 / 30003(修改 super_admin), 404 / 10004。

**curl**:

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/roles/operator/permissions \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"permissions":["account.read","nurture.read","nurture.create"]}'
```

---

## 4. Platform Accounts 模块

> **核心约定**:账号资源按平台分路径,所有 `/platforms/{platform}/accounts` 下行为一致。
> 支持平台(共 8 个):`xhs` / `weibo` / `douyin` / `zhihu` / `twitter` / `bilibili` / `xiaoyuzhou` / `wechat_official`。
> v0.2 已实现:`xhs`;其余 7 个为 stub(返回 501,见错误码表 10504)。
> 文末 4.14 - 4.15 是 batch / activity 端点,本节用 `xhs` 完整列出,其他平台相同路径替换 `{platform}`。

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/platforms/{platform}/accounts` | GET | `account.read` |
| `/platforms/{platform}/accounts` | POST | `account.create` |
| `/platforms/{platform}/accounts/{id}` | GET | `account.read` |
| `/platforms/{platform}/accounts/{id}` | PATCH | `account.update` |
| `/platforms/{platform}/accounts/{id}` | DELETE | `account.delete` |
| `/platforms/{platform}/accounts/{id}/check-login` | POST | `account.read` |
| `/platforms/{platform}/accounts/{id}/login-qrcode` | POST | `account.login` |
| `/platforms/{platform}/accounts/{id}/login-qrcode` | GET | `account.read` |
| `/platforms/{platform}/accounts/{id}/login-qrcode` | DELETE | `account.login` |
| `/platforms/{platform}/accounts/{id}/export-cookies` | POST | `account.export` |
| `/platforms/{platform}/accounts/{id}/pause` | POST | `account.update` |
| `/platforms/{platform}/accounts/{id}/resume` | POST | `account.update` |
| `/platforms/{platform}/accounts/{id}/reset` | POST | `account.reset` |
| `/platforms/{platform}/accounts/batch/check-login` | POST | `account.read` |
| `/platforms/{platform}/accounts/batch/pause` | POST | `account.update` |
| `/platforms/{platform}/accounts/activity?days=7` | GET | `account.read` |

### 4.1 GET /platforms/xhs/accounts

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page` | int | 否 | 默认 1 |
| `page_size` | int | 否 | 默认 20,最大 200 |
| `keyword` | string | 否 | 模糊匹配 nickname / account_id |
| `status` | string | 否 | `active` / `paused` / `banned` / `logged_out` |
| `tag` | string | 否 | 业务标签,逗号分隔取交集 |
| `assigned_to` | int | 否 | 归属 operator_id |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 12,
        "platform": "xhs",
        "account_id": "xhs_01HABC...",
        "nickname": "栗子的小红书",
        "avatar_url": "https://...",
        "fans": 12034,
        "follows": 220,
        "notes": 89,
        "status": "active",
        "tags": ["主号", "美妆"],
        "assigned_to": 1,
        "last_login_at": "2026-08-15T22:00:00.000Z",
        "last_active_at": "2026-08-16T03:11:00.000Z",
        "risk_score": 0.12,
        "created_at": "2026-07-01T00:00:00.000Z"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 7
  }
}
```

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/platforms/xhs/accounts?status=active&page=1" \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export type XhsAccountStatus = 'active' | 'paused' | 'banned' | 'logged_out';

export interface XhsAccount {
  id: number;
  platform: 'xhs';
  account_id: string;
  nickname: string;
  avatar_url: string | null;
  fans: number;
  follows: number;
  notes: number;
  status: XhsAccountStatus;
  tags: string[];
  assigned_to: number | null;
  last_login_at: string | null;
  last_active_at: string | null;
  risk_score: number;
  created_at: string;
}
```

### 4.2 POST /platforms/xhs/accounts

**请求体**:

```json
{
  "account_id": "xhs_01HABC...",
  "nickname": "栗子的小红书",
  "tags": ["主号", "美妆"],
  "assigned_to": 1,
  "notes": "2026-08 创建"
}
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 12,
    "platform": "xhs",
    "account_id": "xhs_01HABC...",
    "status": "logged_out",
    "created_at": "2026-08-16T03:11:00.000Z"
  }
}
```

新账号默认 `logged_out`,需要先 `POST /login-qrcode` 扫码登录。

**错误**:

| HTTP | code | 触发条件 |
|---|---|---|
| 409 | 40001 | account_id 重复 |
| 422 | 10006 | 字段缺失 |
| 501 | 10504 | 平台 stub(非 xhs) |

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platforms/xhs/accounts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"account_id":"xhs_01HABC...","nickname":"栗子的小红书","tags":["主号"]}'
```

### 4.3 GET /platforms/xhs/accounts/{id}

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 12,
    "platform": "xhs",
    "account_id": "xhs_01HABC...",
    "nickname": "栗子的小红书",
    "avatar_url": "https://...",
    "bio": "美妆 / 探店",
    "fans": 12034,
    "follows": 220,
    "notes": 89,
    "status": "active",
    "tags": ["主号", "美妆"],
    "assigned_to": 1,
    "last_login_at": "2026-08-15T22:00:00.000Z",
    "last_active_at": "2026-08-16T03:11:00.000Z",
    "risk_score": 0.12,
    "login_qrcode": null,
    "created_at": "2026-07-01T00:00:00.000Z",
    "updated_at": "2026-08-16T03:11:00.000Z"
  }
}
```

**错误**: 404 / 10004。

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12 \
  -H "Authorization: Bearer $TOKEN"
```

### 4.4 PATCH /platforms/xhs/accounts/{id}

**请求体**(全可选,至少一个):

```json
{
  "nickname": "栗子的小红书(改名)",
  "tags": ["主号", "美妆", "夜班"],
  "assigned_to": 7,
  "notes": "调整归属"
}
```

**响应 200**: 同 `GET /platforms/xhs/accounts/{id}`。

**错误**: 404 / 10004, 422 / 10006。

**curl**:

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tags":["主号","美妆","夜班"]}'
```

### 4.5 DELETE /platforms/xhs/accounts/{id}

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 12, "deleted": true } }
```

软删除 + 清理 cookies 文件 + 撤销运行中 nurture tasks。**不级联** favorites,只标记 `account_id=NULL`。

**错误**: 404 / 10004, 409 / 40002(仍有 running 任务,需先 stop)。

**curl**:

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12 \
  -H "Authorization: Bearer $TOKEN"
```

### 4.6 POST /platforms/xhs/accounts/{id}/check-login

检查当前 cookie 是否还有效,会触发 opencli 调用平台 `/api/sns/web/v1/user/me` 这类轻量接口。

**请求体**: 空

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "logged_in": true,
    "checked_at": "2026-08-16T03:11:00.000Z",
    "latency_ms": 412,
    "user": {
      "nickname": "栗子的小红书",
      "user_id": "xhs_01HABC...",
      "fans": 12034
    }
  }
}
```

**响应 200(掉线)**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "logged_in": false,
    "checked_at": "2026-08-16T03:11:00.000Z",
    "latency_ms": 612,
    "reason": "cookie expired"
  }
}
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/check-login \
  -H "Authorization: Bearer $TOKEN"
```

### 4.7 POST /platforms/xhs/accounts/{id}/login-qrcode

启动扫码登录流程,通过 opencli 启动隔离 Chrome profile,生成二维码 base64。

**请求体**: 空

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "qrcode_id": "qrc_8c1f...",
    "qrcode_png_base64": "iVBORw0KGgo...",
    "expires_at": "2026-08-16T03:13:00.000Z",
    "cdp_port": 9222,
    "poll_url": "/api/v1/platforms/xhs/accounts/12/login-qrcode"
  }
}
```

**错误**:

| HTTP | code | 触发条件 |
|---|---|---|
| 409 | 40003 | 已有活跃 qrcode,需先 DELETE |
| 502 | 10502 | opencli 启动失败 |

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/login-qrcode \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export interface LoginQrcode {
  qrcode_id: string;
  qrcode_png_base64: string;
  expires_at: string;
  cdp_port: number;
  poll_url: string;
}
```

### 4.8 GET /platforms/xhs/accounts/{id}/login-qrcode

轮询扫码状态。前端通常每 2s 轮询一次,直到 `status` 变为 `confirmed` 或 `expired`。

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "qrcode_id": "qrc_8c1f...",
    "status": "waiting",   // waiting | scanned | confirmed | expired | failed
    "scanned_at": null,
    "confirmed_at": null,
    "expires_at": "2026-08-16T03:13:00.000Z"
  }
}
```

**响应 200(扫码成功)**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "qrcode_id": "qrc_8c1f...",
    "status": "confirmed",
    "scanned_at": "2026-08-16T03:11:30.000Z",
    "confirmed_at": "2026-08-16T03:11:45.000Z",
    "expires_at": "2026-08-16T03:13:00.000Z"
  }
}
```

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/login-qrcode \
  -H "Authorization: Bearer $TOKEN"
```

### 4.9 DELETE /platforms/xhs/accounts/{id}/login-qrcode

主动取消扫码流程,关闭隔离 Chrome profile。

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "qrcode_id": "qrc_8c1f...", "cancelled": true } }
```

**curl**:

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/login-qrcode \
  -H "Authorization: Bearer $TOKEN"
```

### 4.10 POST /platforms/xhs/accounts/{id}/export-cookies

**请求体**(可选):

```json
{
  "format": "json",   // json | netscape
  "include_session": true
}
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "filename": "xhs_12_2026-08-16.cookies.json",
    "content_type": "application/json",
    "content_base64": "eyJ...",  // base64 后的 cookies 文件
    "exported_at": "2026-08-16T03:11:00.000Z",
    "operator_id": 1
  }
}
```

此操作会写入 audit log(`action=account.cookies.export`)。

**错误**: 404 / 10004, 403 / 10003(无 `account.export`)。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/export-cookies \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"format":"json"}'
```

### 4.11 POST /platforms/xhs/accounts/{id}/pause

暂停账号参与 nurture 任务调度,但保留登录态。

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 12, "status": "paused" } }
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/pause \
  -H "Authorization: Bearer $TOKEN"
```

### 4.12 POST /platforms/xhs/accounts/{id}/resume

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 12, "status": "active" } }
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/resume \
  -H "Authorization: Bearer $TOKEN"
```

### 4.13 POST /platforms/xhs/accounts/{id}/reset

重置账号的所有 nurture 上下文(状态、风险分、最近动作时间),但**保留 cookies**。

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 12, "reset_at": "2026-08-16T03:11:00.000Z" } }
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/reset \
  -H "Authorization: Bearer $TOKEN"
```

### 4.14 POST /platforms/xhs/accounts/batch/check-login

**请求体**:

```json
{
  "account_ids": [12, 13, 14, 15]
}
```

**响应 200**(异步任务):

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "job_8c1f...",
    "total": 4,
    "status": "queued"
  }
}
```

任务结果通过 WebSocket `WS /ws/notifications` 推送,或通过 `GET /audit-logs?action_type=account.batch_check` 查询。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/batch/check-login \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"account_ids":[12,13,14,15]}'
```

### 4.15 POST /platforms/xhs/accounts/batch/pause

**请求体**:

```json
{
  "account_ids": [12, 13],
  "reason": "风控"
}
```

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "updated": 2 } }
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/batch/pause \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"account_ids":[12,13],"reason":"风控"}'
```

### 4.16 GET /platforms/xhs/accounts/activity?days=7

返回最近 N 天账号活跃度(用于 dashboard 时序图)。

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `days` | int | 否 | 默认 7,最大 90 |
| `account_ids` | int[] | 否 | 逗号分隔;空则返回所有 |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "range": { "from": "2026-08-09", "to": "2026-08-16" },
    "buckets": [
      {
        "date": "2026-08-16",
        "active_accounts": 7,
        "actions_total": 134,
        "actions_per_account": 19.1
      }
    ]
  }
}
```

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/activity?days=7" \
  -H "Authorization: Bearer $TOKEN"
```

### 4.17 其他平台

> `weibo` / `douyin` / `zhihu` / `twitter` / `bilibili` / `xiaoyuzhou` / `wechat_official` 七个平台复用 `4.1 - 4.16` 所有端点,只需将 `xhs` 替换为目标平台键值。
>
> v0.2 除 `xhs` 外其余平台均返回 `501 Not Implemented`,业务 code `10504`,message 形如 `platform "weibo" is not yet supported in v0.2`。
>
> 前端应在 dashboard / 列表页面对这些平台显示「即将上线」占位状态,不要发请求(避免 501 噪音)。

---

## 5. Platform Configs 模块

基础路径:`/api/v1/platform-configs`

每个平台的运行时配置(养号参数、限速、风险阈值),可在线调,改完实时生效。

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/platform-configs` | GET | `config.read` |
| `/platform-configs/{platform}` | GET | `config.read` |
| `/platform-configs/{platform}` | PATCH | `config.update` |
| `/platform-configs/{platform}/reset-default` | POST | `config.update` |
| `/platform-configs/{platform}/test` | POST | `config.update` |

### 5.1 GET /platform-configs

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": [
    {
      "platform": "xhs",
      "display_name": "小红书",
      "enabled": true,
      "actions_per_day_min": 8,
      "actions_per_day_max": 18,
      "active_hours": { "start": "08:00", "end": "23:00" },
      "max_concurrent_per_account": 1,
      "min_interval_seconds": 60,
      "max_interval_seconds": 600,
      "risk_threshold": 0.7,
      "updated_at": "2026-08-15T10:00:00.000Z",
      "updated_by": 1
    }
  ]
}
```

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/platform-configs \
  -H "Authorization: Bearer $TOKEN"
```

### 5.2 GET /platform-configs/{platform}

**响应 200**: 同 5.1 单元素。

**错误**: 404 / 10004, 501 / 10504(平台 stub)。

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/platform-configs/xhs \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export interface PlatformConfig {
  platform: string;
  display_name: string;
  enabled: boolean;
  actions_per_day_min: number;
  actions_per_day_max: number;
  active_hours: { start: string; end: string };
  max_concurrent_per_account: number;
  min_interval_seconds: number;
  max_interval_seconds: number;
  risk_threshold: number;
  updated_at: string;
  updated_by: number;
}
```

### 5.3 PATCH /platform-configs/{platform}

**请求体**(全可选,至少一个):

```json
{
  "actions_per_day_min": 10,
  "actions_per_day_max": 22,
  "min_interval_seconds": 90,
  "risk_threshold": 0.65
}
```

**响应 200**: 同 5.2。

**错误**: 422 / 10006(`min_interval > max_interval` 等), 501 / 10504。

**curl**:

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/platform-configs/xhs \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"actions_per_day_min":10,"actions_per_day_max":22}'
```

### 5.4 POST /platform-configs/{platform}/reset-default

恢复出厂配置,写 audit log。

**请求体**: 空

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "platform": "xhs",
    "reset_at": "2026-08-16T03:11:00.000Z",
    "snapshot_id": "snap_8c1f..."
  }
}
```

`snapshot_id` 可用于在 30 分钟内回滚(`PATCH {platform}` 传入该 id)。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platform-configs/xhs/reset-default \
  -H "Authorization: Bearer $TOKEN"
```

### 5.5 POST /platform-configs/{platform}/test

注入一段虚拟账号 id(0 表示不绑定真实账号),跑一次 5 分钟的"探针",验证当前参数是否会被平台风控。

**请求体**:

```json
{
  "account_id": 12,
  "duration_minutes": 5,
  "action_set_id": 3
}
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "probe_id": "probe_8c1f...",
    "estimated_actions": 4,
    "estimated_risk_score": 0.18,
    "warnings": []
  }
}
```

`warnings` 为空数组表示参数健康;非空会列出风险点(如 `actions_per_day_max 过高` 等)。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platform-configs/xhs/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"account_id":12,"duration_minutes":5,"action_set_id":3}'
```

---

## 6. Nurture Tasks 模块

基础路径:`/api/v1/nurture-tasks`

任务是一次性的"对一个或多个账号执行指定 action set",由 worker 拉取执行。

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/nurture-tasks` | GET | `nurture.read` |
| `/nurture-tasks` | POST | `nurture.create` |
| `/nurture-tasks/{id}` | GET | `nurture.read` |
| `/nurture-tasks/{id}/pause` | POST | `nurture.update` |
| `/nurture-tasks/{id}/stop` | POST | `nurture.update` |
| `/nurture-tasks/{id}/retry` | POST | `nurture.update` |
| `/nurture-tasks/{id}` | DELETE | `nurture.delete` |
| `/nurture-tasks/all/stop?platform=xhs` | POST | `nurture.update` |
| `/nurture-tasks/export` | GET | `nurture.read` |

### 6.1 GET /nurture-tasks

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page` | int | 否 | 默认 1 |
| `page_size` | int | 否 | 默认 20 |
| `status` | string | 否 | `queued` / `running` / `paused` / `stopped` / `succeeded` / `failed` |
| `platform` | string | 否 | 平台过滤 |
| `action_set_id` | int | 否 | 按 action set 过滤 |
| `schedule_id` | int | 否 | 由哪个 schedule 触发的任务 |
| `created_from` | date | 否 | `YYYY-MM-DD` |
| `created_to` | date | 否 | `YYYY-MM-DD` |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 88,
        "platform": "xhs",
        "action_set_id": 3,
        "action_set_name": "日常浏览+点赞",
        "account_ids": [12, 13],
        "status": "running",
        "progress": {
          "total_actions": 24,
          "done_actions": 11,
          "failed_actions": 1
        },
        "risk_score_avg": 0.18,
        "created_by": 1,
        "created_at": "2026-08-16T02:00:00.000Z",
        "started_at": "2026-08-16T02:01:00.000Z",
        "finished_at": null,
        "error_message": null
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 42
  }
}
```

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/nurture-tasks?status=running&platform=xhs" \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export type NurtureTaskStatus =
  | 'queued' | 'running' | 'paused' | 'stopped' | 'succeeded' | 'failed';

export interface NurtureTask {
  id: number;
  platform: string;
  action_set_id: number;
  action_set_name: string;
  account_ids: number[];
  status: NurtureTaskStatus;
  progress: {
    total_actions: number;
    done_actions: number;
    failed_actions: number;
  };
  risk_score_avg: number;
  created_by: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
}
```

### 6.2 POST /nurture-tasks

**请求体**:

```json
{
  "platform": "xhs",
  "action_set_id": 3,
  "account_ids": [12, 13],
  "schedule_id": null,
  "run_at": "2026-08-16T03:30:00.000Z",
  "priority": 5,
  "notes": "手动触发"
}
```

`run_at` 为可选,默认立即;`priority` 默认 5(0 最高,9 最低)。

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 89,
    "status": "queued",
    "created_at": "2026-08-16T03:11:00.000Z"
  }
}
```

**错误**: 422 / 10006, 404 / 10004(account_id 不存在), 409 / 60001(action set 已被删除)。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/nurture-tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"platform":"xhs","action_set_id":3,"account_ids":[12,13]}'
```

### 6.3 GET /nurture-tasks/{id}

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 88,
    "platform": "xhs",
    "action_set_id": 3,
    "action_set_name": "日常浏览+点赞",
    "account_ids": [12, 13],
    "status": "running",
    "progress": { "total_actions": 24, "done_actions": 11, "failed_actions": 1 },
    "actions": [
      {
        "seq": 1,
        "account_id": 12,
        "kind": "browse_feed",
        "params": { "duration_seconds": 45 },
        "status": "succeeded",
        "started_at": "2026-08-16T02:01:10.000Z",
        "finished_at": "2026-08-16T02:01:55.000Z",
        "latency_ms": 45000,
        "error_message": null
      }
    ],
    "risk_score_avg": 0.18,
    "created_by": 1,
    "created_at": "2026-08-16T02:00:00.000Z",
    "started_at": "2026-08-16T02:01:00.000Z",
    "finished_at": null,
    "error_message": null
  }
}
```

`actions` 数组在任务执行中持续增长,前端通过 WebSocket 订阅 `WS /ws/nurture-tasks/{id}/progress` 即可实时获得新增项,不必轮询本端点。

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/nurture-tasks/88 \
  -H "Authorization: Bearer $TOKEN"
```

### 6.4 POST /nurture-tasks/{id}/pause

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 88, "status": "paused" } }
```

worker 收到信号后,完成当前 action 后停步,资源不释放。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/nurture-tasks/88/pause \
  -H "Authorization: Bearer $TOKEN"
```

### 6.5 POST /nurture-tasks/{id}/stop

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 88, "status": "stopped" } }
```

与 pause 区别:`stopped` 状态后不可 resume,只能 `retry` 创建新任务。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/nurture-tasks/88/stop \
  -H "Authorization: Bearer $TOKEN"
```

### 6.6 POST /nurture-tasks/{id}/retry

**请求体**(可选):

```json
{
  "reset_progress": true,
  "reset_risk_score": false
}
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 90,
    "from_task_id": 88,
    "status": "queued"
  }
}
```

总是创建新任务(避免污染原任务历史)。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/nurture-tasks/88/retry \
  -H "Authorization: Bearer $TOKEN"
```

### 6.7 DELETE /nurture-tasks/{id}

仅删除 `queued` / `stopped` / `failed` / `succeeded` 状态的任务;`running` 必须先 stop。

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 88, "deleted": true } }
```

**错误**: 409 / 60002(任务 running)。

**curl**:

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/nurture-tasks/88 \
  -H "Authorization: Bearer $TOKEN"
```

### 6.8 POST /nurture-tasks/all/stop?platform=xhs

紧急停止某一平台下所有 running / paused 任务。

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `platform` | string | 否 | 不传则全部平台 |

**请求体**(可选):

```json
{ "reason": "风控升级" }
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": { "stopped_count": 12, "platform": "xhs" }
}
```

**curl**:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/nurture-tasks/all/stop?platform=xhs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason":"风控升级"}'
```

### 6.9 GET /nurture-tasks/export

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `format` | string | 否 | `csv` / `xlsx`,默认 `csv` |
| `date_from` | date | 否 | 默认 30 天前 |
| `date_to` | date | 否 | 默认今天 |
| `platform` | string | 否 | 过滤 |

**响应 200**: 流式下载,`Content-Disposition: attachment; filename=nurture-tasks_<from>_<to>.<ext>`。

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/nurture-tasks/export?format=csv&date_from=2026-07-01" \
  -H "Authorization: Bearer $TOKEN" \
  -o nurture-tasks.csv
```

---

## 7. Nurture Schedules 模块

基础路径:`/api/v1/nurture-schedules`

定时任务定义,由 Celery beat 周期触发。

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/nurture-schedules` | GET | `nurture.read` |
| `/nurture-schedules` | POST | `nurture.create` |
| `/nurture-schedules/{id}` | GET | `nurture.read` |
| `/nurture-schedules/{id}` | PATCH | `nurture.update` |
| `/nurture-schedules/{id}` | DELETE | `nurture.delete` |
| `/nurture-schedules/{id}/enable` | POST | `nurture.update` |
| `/nurture-schedules/{id}/disable` | POST | `nurture.update` |
| `/nurture-schedules/{id}/trigger` | POST | `nurture.create` |

### 7.1 GET /nurture-schedules

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page` | int | 否 | 默认 1 |
| `page_size` | int | 否 | 默认 20 |
| `platform` | string | 否 | 平台过滤 |
| `enabled` | bool | 否 | true / false |
| `keyword` | string | 否 | 模糊匹配 name |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 5,
        "name": "工作日上午养号",
        "platform": "xhs",
        "action_set_id": 3,
        "account_ids": [12, 13, 14],
        "cron": "0 10 * * 1-5",
        "timezone": "Asia/Shanghai",
        "enabled": true,
        "next_run_at": "2026-08-17T02:00:00.000Z",
        "last_run_at": "2026-08-16T02:00:00.000Z",
        "last_task_id": 88,
        "created_by": 1,
        "created_at": "2026-07-10T00:00:00.000Z"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 3
  }
}
```

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/nurture-schedules?platform=xhs" \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export interface NurtureSchedule {
  id: number;
  name: string;
  platform: string;
  action_set_id: number;
  account_ids: number[];
  cron: string;
  timezone: string;
  enabled: boolean;
  next_run_at: string | null;
  last_run_at: string | null;
  last_task_id: number | null;
  created_by: number;
  created_at: string;
}
```

### 7.2 POST /nurture-schedules

**请求体**:

```json
{
  "name": "工作日上午养号",
  "platform": "xhs",
  "action_set_id": 3,
  "account_ids": [12, 13, 14],
  "cron": "0 10 * * 1-5",
  "timezone": "Asia/Shanghai",
  "enabled": true
}
```

**响应 200**: 同 7.1 单元素。

**错误**: 422 / 10006(cron 格式错), 404 / 10004(action set / account 不存在)。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/nurture-schedules \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"工作日上午养号","platform":"xhs","action_set_id":3,
    "account_ids":[12,13,14],"cron":"0 10 * * 1-5",
    "timezone":"Asia/Shanghai","enabled":true
  }'
```

### 7.3 GET /nurture-schedules/{id}

**响应 200**: 同 7.1 单元素。

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/nurture-schedules/5 \
  -H "Authorization: Bearer $TOKEN"
```

### 7.4 PATCH /nurture-schedules/{id}

**请求体**(全可选,至少一个):

```json
{
  "cron": "0 11 * * 1-5",
  "account_ids": [12, 13, 14, 15]
}
```

修改 `cron` 后,`next_run_at` 立即重算。

**响应 200**: 同 7.1 单元素。

**curl**:

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/nurture-schedules/5 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cron":"0 11 * * 1-5"}'
```

### 7.5 DELETE /nurture-schedules/{id}

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 5, "deleted": true } }
```

不影响已生成的任务,只取消后续触发。

**curl**:

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/nurture-schedules/5 \
  -H "Authorization: Bearer $TOKEN"
```

### 7.6 POST /nurture-schedules/{id}/enable

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 5, "enabled": true, "next_run_at": "2026-08-17T02:00:00.000Z" } }
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/nurture-schedules/5/enable \
  -H "Authorization: Bearer $TOKEN"
```

### 7.7 POST /nurture-schedules/{id}/disable

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 5, "enabled": false, "next_run_at": null } }
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/nurture-schedules/5/disable \
  -H "Authorization: Bearer $TOKEN"
```

### 7.8 POST /nurture-schedules/{id}/trigger

立刻按当前配置创建一次 nurture task(不修改 schedule 本身)。

**请求体**(可选):

```json
{ "note": "手动触发(运维)" }
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": { "task_id": 91, "schedule_id": 5, "status": "queued" }
}
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/nurture-schedules/5/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"note":"手动触发"}'
```

---

## 8. Nurture Action Sets 模块

基础路径:`/api/v1/nurture-action-sets`

Action Set 是"养号动作的剧本",包含若干有序 action 步骤(浏览、点赞、评论、关注、发布、互动),可被 schedule / task 引用。

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/nurture-action-sets` | GET | `nurture.read` |
| `/nurture-action-sets` | POST | `nurture.create` |
| `/nurture-action-sets/{id}` | GET | `nurture.read` |
| `/nurture-action-sets/{id}` | PATCH | `nurture.update` |
| `/nurture-action-sets/{id}` | DELETE | `nurture.delete` |
| `/nurture-action-sets/{id}/clone` | POST | `nurture.create` |

### 8.1 GET /nurture-action-sets

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page` | int | 否 | 默认 1 |
| `page_size` | int | 否 | 默认 20 |
| `platform` | string | 否 | 平台过滤 |
| `keyword` | string | 否 | 模糊匹配 name |
| `tag` | string | 否 | 标签过滤 |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 3,
        "name": "日常浏览+点赞",
        "platform": "xhs",
        "description": "温和养号,每天 8-18 个动作",
        "action_count": 6,
        "estimated_duration_minutes": 25,
        "tags": ["温和", "日常"],
        "version": 4,
        "created_by": 1,
        "created_at": "2026-07-01T00:00:00.000Z",
        "updated_at": "2026-08-15T10:00:00.000Z"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 5
  }
}
```

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/nurture-action-sets?platform=xhs" \
  -H "Authorization: Bearer $TOKEN"
```

### 8.2 POST /nurture-action-sets

**请求体**:

```json
{
  "name": "激进互动模板",
  "platform": "xhs",
  "description": "高强度养号,慎用",
  "actions": [
    { "kind": "browse_feed", "params": { "duration_seconds": 60 }, "weight": 3 },
    { "kind": "like_note", "params": { "ratio": 0.4 }, "weight": 2 },
    { "kind": "comment_note", "params": { "ratio": 0.1, "min_chars": 6 }, "weight": 1 },
    { "kind": "follow_user", "params": { "ratio": 0.05 }, "weight": 1 },
    { "kind": "post_note", "params": { "ratio": 0.02 }, "weight": 1 },
    { "kind": "sleep", "params": { "min_seconds": 60, "max_seconds": 600 }, "weight": 1 }
  ],
  "tags": ["激进"]
}
```

`actions` 数组顺序即执行顺序;`weight` 决定单次任务中该 action 被抽样执行的概率权重(总和不必为 1,内部归一化)。

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 7,
    "name": "激进互动模板",
    "platform": "xhs",
    "version": 1,
    "action_count": 6,
    "created_at": "2026-08-16T03:11:00.000Z"
  }
}
```

**错误**: 422 / 10006(actions 为空 / kind 不支持), 501 / 10504(平台 stub)。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/nurture-action-sets \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @action-set.json
```

**TypeScript**:

```ts
export type ActionKind =
  | 'browse_feed' | 'like_note' | 'comment_note' | 'follow_user'
  | 'post_note' | 'sleep' | 'search_keyword' | 'view_profile';

export interface ActionStep {
  kind: ActionKind;
  params: Record<string, unknown>;
  weight: number;
}

export interface ActionSet {
  id: number;
  name: string;
  platform: string;
  description: string;
  actions: ActionStep[];
  tags: string[];
  version: number;
  created_by: number;
  created_at: string;
  updated_at: string;
}
```

### 8.3 GET /nurture-action-sets/{id}

**响应 200**: 同 8.1 单元素 + 完整 `actions` 数组。

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/nurture-action-sets/3 \
  -H "Authorization: Bearer $TOKEN"
```

### 8.4 PATCH /nurture-action-sets/{id}

**请求体**(全可选,至少一个):

```json
{
  "name": "日常浏览+点赞(加强版)",
  "actions": [
    { "kind": "browse_feed", "params": { "duration_seconds": 90 }, "weight": 3 },
    { "kind": "like_note", "params": { "ratio": 0.5 }, "weight": 2 }
  ]
}
```

每次 PATCH 会让 `version` 自增。被 schedule / task 引用时,旧版本会保留快照,不影响运行中任务。

**响应 200**: 同 8.3。

**curl**:

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/nurture-action-sets/3 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"日常浏览+点赞(加强版)"}'
```

### 8.5 DELETE /nurture-action-sets/{id}

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 3, "deleted": true } }
```

**错误**: 409 / 70001(被 schedule 引用), 404 / 10004。

**curl**:

```bash
curl -X DELETE http://127.0.0.1:8000/api/v1/nurture-action-sets/3 \
  -H "Authorization: Bearer $TOKEN"
```

### 8.6 POST /nurture-action-sets/{id}/clone

深拷贝一份,新版本号重置为 1。

**请求体**(可选):

```json
{ "new_name": "日常浏览+点赞 (副本)" }
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 8,
    "name": "日常浏览+点赞 (副本)",
    "from_id": 3,
    "version": 1,
    "created_at": "2026-08-16T03:11:00.000Z"
  }
}
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/nurture-action-sets/3/clone \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_name":"日常浏览+点赞 (副本)"}'
```

---

## 9. Favorites 模块

基础路径:`/api/v1/platforms/{platform}/accounts/{id}/favorites`

收藏数据来自养号过程中的浏览 / 点赞 / 评论,可用于内容复盘和素材库。

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/platforms/{platform}/accounts/{id}/favorites` | GET | `favorites.read` |
| `/platforms/{platform}/accounts/{id}/favorites/refresh` | POST | `favorites.refresh` |
| `/platforms/{platform}/accounts/{id}/favorites/{favorite_id}` | GET | `favorites.read` |
| `/platforms/{platform}/accounts/{id}/favorites/stats` | GET | `favorites.read` |
| `/platforms/{platform}/accounts/{id}/favorites/export` | GET | `favorites.read` |

> v0.2 仅小红书(`xhs`)实现,其他平台返回 `501 / 10504`。

### 9.1 GET /platforms/xhs/accounts/12/favorites

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `page` | int | 否 | 默认 1 |
| `page_size` | int | 否 | 默认 20 |
| `sort` | string | 否 | `captured_at` / `liked_at`,默认 `captured_at` |
| `order` | string | 否 | `asc` / `desc`,默认 `desc` |
| `kind` | string | 否 | `note` / `comment` / `user` |
| `tag` | string | 否 | 标签 |
| `keyword` | string | 否 | 模糊匹配 title / content |
| `captured_from` | date | 否 | 收藏日期起点 |
| `captured_to` | date | 否 | 收藏日期终点 |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 9001,
        "kind": "note",
        "platform_note_id": "xhs_note_64f...",
        "title": "上海小众咖啡店",
        "content": "静安区这家...",
        "cover_url": "https://...",
        "author": { "user_id": "xhs_8a...", "nickname": "咖啡控_Lynn" },
        "tags": ["咖啡", "探店"],
        "liked_at": "2026-08-15T13:00:00.000Z",
        "captured_at": "2026-08-15T13:01:10.000Z",
        "stats": { "likes": 234, "comments": 12, "collects": 88 }
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 312
  }
}
```

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/favorites?sort=captured_at&page=1" \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export type FavoriteKind = 'note' | 'comment' | 'user';

export interface FavoriteItem {
  id: number;
  kind: FavoriteKind;
  platform_note_id: string;
  title: string;
  content: string;
  cover_url: string | null;
  author: { user_id: string; nickname: string };
  tags: string[];
  liked_at: string;
  captured_at: string;
  stats: { likes: number; comments: number; collects: number };
}
```

### 9.2 POST /platforms/xhs/accounts/{id}/favorites/refresh

触发一次增量同步(最近 24h)。

**请求体**(可选):

```json
{ "lookback_hours": 24 }
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": "fav_job_8c1f...",
    "status": "queued",
    "estimated_seconds": 30
  }
}
```

完成时通过 `WS /ws/notifications` 推送 `event=favorites.refreshed`,payload 含 `{account_id, added_count, updated_count}`。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/favorites/refresh \
  -H "Authorization: Bearer $TOKEN"
```

### 9.3 GET /platforms/xhs/accounts/{id}/favorites/{favorite_id}

**响应 200**: 同 9.1 单元素(完整字段)。

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/favorites/9001 \
  -H "Authorization: Bearer $TOKEN"
```

### 9.4 GET /platforms/xhs/accounts/{id}/favorites/stats

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `days` | int | 否 | 默认 30,最大 365 |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "total": 312,
    "by_kind": { "note": 280, "comment": 20, "user": 12 },
    "by_day": [
      { "date": "2026-08-16", "count": 14 },
      { "date": "2026-08-15", "count": 22 }
    ],
    "top_tags": [
      { "tag": "咖啡", "count": 38 },
      { "tag": "美妆", "count": 31 }
    ],
    "top_authors": [
      { "user_id": "xhs_8a...", "nickname": "咖啡控_Lynn", "count": 12 }
    ]
  }
}
```

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/favorites/stats?days=30" \
  -H "Authorization: Bearer $TOKEN"
```

### 9.5 GET /platforms/xhs/accounts/{id}/favorites/export

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `format` | string | 否 | `csv` / `xlsx` / `json`,默认 `xlsx` |
| `captured_from` | date | 否 | 起点 |
| `captured_to` | date | 否 | 终点 |

**响应 200**: 流式下载,`Content-Disposition: attachment; filename=favorites_<account>_<from>_<to>.<ext>`。

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/platforms/xhs/accounts/12/favorites/export?format=xlsx" \
  -H "Authorization: Bearer $TOKEN" \
  -o favorites-12.xlsx
```

---

## 10. Dashboard 模块

基础路径:`/api/v1/dashboard`

仪表盘数据汇总,均要求鉴权。

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/dashboard/overview` | GET | `dashboard.read` |
| `/dashboard/pending-issues` | GET | `dashboard.read` |
| `/dashboard/chrome-status` | GET | `dashboard.read` |
| `/dashboard/daily-stats?days=7` | GET | `dashboard.read` |

### 10.1 GET /dashboard/overview

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "summary": {
      "total_accounts": 28,
      "active_accounts": 22,
      "logged_out_accounts": 4,
      "banned_accounts": 2,
      "running_tasks": 5,
      "queued_tasks": 3,
      "today_actions": 312,
      "today_risk_alerts": 1
    },
    "by_platform": [
      { "platform": "xhs", "active": 22, "total": 28 }
    ],
    "recent_alerts": [
      {
        "id": 901,
        "level": "warning",
        "title": "账号 xhs_12 风险分超过 0.6",
        "created_at": "2026-08-16T02:30:00.000Z"
      }
    ]
  }
}
```

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/dashboard/overview \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export interface DashboardOverview {
  summary: {
    total_accounts: number;
    active_accounts: number;
    logged_out_accounts: number;
    banned_accounts: number;
    running_tasks: number;
    queued_tasks: number;
    today_actions: number;
    today_risk_alerts: number;
  };
  by_platform: Array<{ platform: string; active: number; total: number }>;
  recent_alerts: Array<{
    id: number;
    level: 'info' | 'warning' | 'error';
    title: string;
    created_at: string;
  }>;
}
```

### 10.2 GET /dashboard/pending-issues

返回需要人工处理的事项清单(账号掉线、任务失败、风控告警、扫描二维码超时)。

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `level` | string | 否 | `warning` / `error` |
| `limit` | int | 否 | 默认 50 |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 901,
        "level": "warning",
        "category": "account",
        "title": "账号 xhs_12 风险分超过 0.6",
        "detail": "近 1h 点赞频率 0.18 > 阈值 0.15",
        "ref_id": 12,
        "ref_type": "platform_account",
        "action_url": "/accounts/12",
        "created_at": "2026-08-16T02:30:00.000Z"
      }
    ]
  }
}
```

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/dashboard/pending-issues \
  -H "Authorization: Bearer $TOKEN"
```

### 10.3 GET /dashboard/chrome-status

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "opencli": {
      "running": true,
      "version": "0.4.1",
      "uptime_seconds": 18342,
      "managed_sessions": 3
    },
    "sessions": [
      {
        "cdp_port": 9222,
        "account_id": 12,
        "platform": "xhs",
        "started_at": "2026-08-15T22:00:00.000Z",
        "last_active_at": "2026-08-16T03:11:00.000Z",
        "memory_mb": 412,
        "cpu_percent": 3.1
      }
    ]
  }
}
```

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/dashboard/chrome-status \
  -H "Authorization: Bearer $TOKEN"
```

### 10.4 GET /dashboard/daily-stats?days=7

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `days` | int | 否 | 默认 7,最大 90 |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "range": { "from": "2026-08-09", "to": "2026-08-16" },
    "series": [
      {
        "date": "2026-08-16",
        "actions": 312,
        "tasks_started": 5,
        "tasks_succeeded": 4,
        "tasks_failed": 1,
        "risk_alerts": 1
      }
    ]
  }
}
```

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/dashboard/daily-stats?days=7" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 11. Risk Config 模块

基础路径:`/api/v1/risk-config`

风险阈值、动作频率上限等参数。

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/risk-config` | GET | `risk.read` |
| `/risk-config` | PATCH | `risk.update` |
| `/risk-config/reset-default` | POST | `risk.update` |

### 11.1 GET /risk-config

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "global_risk_threshold": 0.7,
    "per_platform": {
      "xhs": {
        "risk_threshold": 0.7,
        "like_max_per_hour": 12,
        "comment_max_per_hour": 4,
        "follow_max_per_hour": 6,
        "post_max_per_day": 3,
        "min_dwell_seconds": 8,
        "max_dwell_seconds": 180,
        "concurrent_max_per_account": 1
      }
    },
    "ban_keywords": ["加微信", "代购", "拼多多"],
    "updated_at": "2026-08-15T10:00:00.000Z",
    "updated_by": 1
  }
}
```

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/risk-config \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export interface RiskConfig {
  global_risk_threshold: number;
  per_platform: Record<string, {
    risk_threshold: number;
    like_max_per_hour: number;
    comment_max_per_hour: number;
    follow_max_per_hour: number;
    post_max_per_day: number;
    min_dwell_seconds: number;
    max_dwell_seconds: number;
    concurrent_max_per_account: number;
  }>;
  ban_keywords: string[];
  updated_at: string;
  updated_by: number;
}
```

### 11.2 PATCH /risk-config

**请求体**(全可选,至少一个):

```json
{
  "global_risk_threshold": 0.65,
  "per_platform": {
    "xhs": {
      "like_max_per_hour": 10,
      "comment_max_per_hour": 3
    }
  },
  "ban_keywords": ["加微信", "代购", "拼多多", "私聊"]
}
```

**响应 200**: 同 11.1。

**错误**: 422 / 10006(数值越界,例如 `risk_threshold > 1.0`)。

**curl**:

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/risk-config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"global_risk_threshold":0.65}'
```

### 11.3 POST /risk-config/reset-default

**请求体**: 空

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "reset_at": "2026-08-16T03:11:00.000Z",
    "snapshot_id": "risk_snap_8c1f..."
  }
}
```

30 分钟内可通过 `snapshot_id` 复原(`PATCH /risk-config` 传 `from_snapshot`)。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/risk-config/reset-default \
  -H "Authorization: Bearer $TOKEN"
```

---

## 12. Notifications 模块

基础路径:`/api/v1`

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/notifications?status=unread` | GET | 任意已登录 |
| `/notifications/{id}` | GET | 任意已登录 |
| `/notifications/{id}/read` | POST | 任意已登录 |
| `/notifications/all/read` | POST | 任意已登录 |
| `/notification-config` | GET | `notification.read` |
| `/notification-config` | PATCH | `notification.update` |

### 12.1 GET /notifications

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `status` | string | 否 | `unread` / `read` / `archived` |
| `level` | string | 否 | `info` / `warning` / `error` |
| `category` | string | 否 | `account` / `task` / `risk` / `system` |
| `page` | int | 否 | 默认 1 |
| `page_size` | int | 否 | 默认 20 |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 5001,
        "category": "risk",
        "level": "warning",
        "title": "账号 xhs_12 风险分超过 0.6",
        "body": "近 1h 点赞频率 0.18 > 阈值 0.15",
        "ref_type": "platform_account",
        "ref_id": 12,
        "status": "unread",
        "created_at": "2026-08-16T02:30:00.000Z"
      }
    ],
    "unread_count": 3,
    "page": 1,
    "page_size": 20,
    "total": 18
  }
}
```

`unread_count` 同时出现在 `data` 顶层,方便前端红点展示。

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/notifications?status=unread" \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export type NotificationLevel = 'info' | 'warning' | 'error';
export type NotificationStatus = 'unread' | 'read' | 'archived';

export interface Notification {
  id: number;
  category: 'account' | 'task' | 'risk' | 'system';
  level: NotificationLevel;
  title: string;
  body: string;
  ref_type: string | null;
  ref_id: number | null;
  status: NotificationStatus;
  created_at: string;
}
```

### 12.2 GET /notifications/{id}

**响应 200**: 同 12.1 单元素。

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/notifications/5001 \
  -H "Authorization: Bearer $TOKEN"
```

### 12.3 POST /notifications/{id}/read

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "id": 5001, "status": "read" } }
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/notifications/5001/read \
  -H "Authorization: Bearer $TOKEN"
```

### 12.4 POST /notifications/all/read

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `category` | string | 否 | 不传则全部已读 |

**请求体**: 空

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "updated": 3 } }
```

**curl**:

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/notifications/all/read?category=risk" \
  -H "Authorization: Bearer $TOKEN"
```

### 12.5 GET /notification-config

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "channels": {
      "in_app": true,
      "email": false,
      "webhook": true
    },
    "webhook_url": "https://hooks.example.com/...",
    "rules": [
      { "level": "error", "enabled": true, "channels": ["in_app", "webhook"] },
      { "level": "warning", "enabled": true, "channels": ["in_app"] },
      { "level": "info", "enabled": false, "channels": [] }
    ],
    "quiet_hours": { "start": "23:00", "end": "08:00", "timezone": "Asia/Shanghai" }
  }
}
```

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/notification-config \
  -H "Authorization: Bearer $TOKEN"
```

### 12.6 PATCH /notification-config

**请求体**(全可选):

```json
{
  "channels": { "in_app": true, "email": true, "webhook": false },
  "rules": [
    { "level": "error", "enabled": true, "channels": ["in_app", "email"] }
  ]
}
```

**响应 200**: 同 12.5。

**curl**:

```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/notification-config \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channels":{"in_app":true,"email":true,"webhook":false}}'
```

---

## 13. Audit Logs 模块

基础路径:`/api/v1/audit-logs`

记录所有"危险"操作(登录、密码重置、账号删除、cookies 导出、配置修改、批量停止等),180 天保留。

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/audit-logs` | GET | `audit.read` |
| `/audit-logs/{id}` | GET | `audit.read` |
| `/audit-logs/export` | GET | `audit.read` |

### 13.1 GET /audit-logs

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `date` | string | 否 | `today` / `yesterday` / 任意 `YYYY-MM-DD` |
| `date_from` | date | 否 | 起点,优先级低于 `date` |
| `date_to` | date | 否 | 终点 |
| `actor_id` | int | 否 | 操作人 operator_id |
| `action_type` | string | 否 | 如 `auth.login` / `account.delete` / `config.update` |
| `ref_type` | string | 否 | `platform_account` / `operator` / `nurture_task` 等 |
| `ref_id` | int | 否 | 资源 id |
| `page` | int | 否 | 默认 1 |
| `page_size` | int | 否 | 默认 50,最大 200 |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "id": 12001,
        "actor": { "id": 1, "username": "admin" },
        "action_type": "account.cookies.export",
        "ref_type": "platform_account",
        "ref_id": 12,
        "ip": "10.0.0.7",
        "user_agent": "Mozilla/5.0 ...",
        "request_id": "0c1a2b3c-...",
        "payload": { "format": "json" },
        "created_at": "2026-08-16T03:11:00.000Z"
      }
    ],
    "page": 1,
    "page_size": 50,
    "total": 312
  }
}
```

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/audit-logs?date=today&actor_id=1&action_type=account.cookies.export&page=1" \
  -H "Authorization: Bearer $TOKEN"
```

**TypeScript**:

```ts
export interface AuditLog {
  id: number;
  actor: { id: number; username: string };
  action_type: string;
  ref_type: string | null;
  ref_id: number | null;
  ip: string;
  user_agent: string;
  request_id: string;
  payload: Record<string, unknown>;
  created_at: string;
}
```

### 13.2 GET /audit-logs/{id}

**响应 200**: 同 13.1 单元素。

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/audit-logs/12001 \
  -H "Authorization: Bearer $TOKEN"
```

### 13.3 GET /audit-logs/export

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `format` | string | 否 | `csv` / `xlsx`,默认 `xlsx` |
| `date_from` | date | 否 | 起点,默认 30 天前 |
| `date_to` | date | 否 | 终点,默认今天 |
| `action_type` | string | 否 | 过滤 |

**响应 200**: 流式下载,带 `Content-Disposition: attachment; filename=audit-logs_<from>_<to>.<ext>`。

**curl**:

```bash
curl "http://127.0.0.1:8000/api/v1/audit-logs/export?format=xlsx&date_from=2026-07-01" \
  -H "Authorization: Bearer $TOKEN" \
  -o audit-logs.xlsx
```

---

## 14. Browser Sessions 模块

基础路径:`/api/v1/browser-sessions`

管理隔离的 Chrome / opencli 会话。

| 端点 | 方法 | 鉴权(permission) |
|---|---|---|
| `/browser-sessions` | GET | `session.read` |
| `/browser-sessions/{cdp_port}/start` | POST | `session.manage` |
| `/browser-sessions/{cdp_port}/stop` | POST | `session.manage` |
| `/browser-sessions/all/cleanup-idle` | POST | `session.manage` |
| `/browser-sessions/opencli-status` | GET | `session.read` |
| `/browser-sessions/restart-opencli` | POST | `session.manage` |

### 14.1 GET /browser-sessions

**Query**:

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `status` | string | 否 | `running` / `idle` / `closed` |
| `account_id` | int | 否 | 过滤绑定的账号 |

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      {
        "cdp_port": 9222,
        "account_id": 12,
        "platform": "xhs",
        "status": "running",
        "started_at": "2026-08-15T22:00:00.000Z",
        "last_active_at": "2026-08-16T03:11:00.000Z",
        "memory_mb": 412,
        "cpu_percent": 3.1
      }
    ]
  }
}
```

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/browser-sessions \
  -H "Authorization: Bearer $TOKEN"
```

### 14.2 POST /browser-sessions/{cdp_port}/start

**请求体**:

```json
{ "account_id": 12, "platform": "xhs" }
```

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "cdp_port": 9222, "status": "running" } }
```

**错误**: 409 / 100005(端口已占用)。

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/browser-sessions/9222/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"account_id":12,"platform":"xhs"}'
```

### 14.3 POST /browser-sessions/{cdp_port}/stop

**请求体**(可选):

```json
{ "force": false, "reason": "手动停止" }
```

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "cdp_port": 9222, "status": "closed" } }
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/browser-sessions/9222/stop \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force":false}'
```

### 14.4 POST /browser-sessions/all/cleanup-idle

关闭 idle > 30 分钟的 session。

**请求体**(可选):

```json
{ "idle_threshold_minutes": 30 }
```

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "closed_count": 2 } }
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/browser-sessions/all/cleanup-idle \
  -H "Authorization: Bearer $TOKEN"
```

### 14.5 GET /browser-sessions/opencli-status

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "running": true,
    "version": "0.4.1",
    "uptime_seconds": 18342,
    "pid": 77821,
    "managed_sessions": 3
  }
}
```

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/browser-sessions/opencli-status \
  -H "Authorization: Bearer $TOKEN"
```

### 14.6 POST /browser-sessions/restart-opencli

**请求体**(可选):

```json
{ "preserve_sessions": false }
```

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "previous_pid": 77821,
    "new_pid": 78114,
    "restarted_at": "2026-08-16T03:11:00.000Z"
  }
}
```

**curl**:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/browser-sessions/restart-opencli \
  -H "Authorization: Bearer $TOKEN"
```

---

## 15. Health 模块

基础路径:`/api/v1/health`

无鉴权,供 LB / k8s 探针使用。

| 端点 | 方法 | 说明 |
|---|---|---|
| `/health` | GET | 综合健康 |
| `/health/ready` | GET | 就绪(依赖全部 OK) |
| `/health/live` | GET | 存活(进程未挂) |

### 15.1 GET /health

**响应 200**:

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "status": "ok",
    "components": {
      "database": "ok",
      "redis": "ok",
      "opencli": "ok",
      "celery": "ok"
    },
    "version": "0.2.0",
    "uptime_seconds": 18342
  }
}
```

任一关键组件 `!= ok` 时,HTTP 返回 503,`data.status = degraded`,`code = 10503`。

**curl**:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

### 15.2 GET /health/ready

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "ready": true } }
```

503 表示尚未就绪(例如正在迁移)。

**curl**:

```bash
curl -i http://127.0.0.1:8000/api/v1/health/ready
```

### 15.3 GET /health/live

**响应 200**:

```json
{ "code": 0, "message": "ok", "data": { "alive": true } }
```

进程能响应即返回 200,用于 k8s livenessProbe。

**curl**:

```bash
curl -i http://127.0.0.1:8000/api/v1/health/live
```

---

## 16. WebSocket(实时通知)

| 端点 | 鉴权 | 用途 |
|---|---|---|
| `WS /ws/notifications` | query `?token=<jwt>` | 全局通知通道(通知、任务进度、账号事件) |
| `WS /ws/nurture-tasks/{id}/progress` | query `?token=<jwt>` | 单个 nurture task 进度 |

### 16.1 连接约定

- WebSocket 路径前缀 `/api/v1/ws/...`,实际 nginx 转发到 uvicorn 时不携带 `/api/v1` 前缀(参见部署文档)。
- 鉴权通过 query 参数 `?token=<jwt>`(浏览器 EventSource/WebSocket 头限制);若 token 缺失或无效,服务端在握手阶段返回 401 并关闭。
- 客户端应在连接建立后立即发送 `{ "type": "ping" }` 心跳;服务端每 30s 主动发送 `{ "type": "pong" }`。
- 闲置 90s 未收到任何客户端消息,服务端主动关闭。

### 16.2 WS /ws/notifications

**客户端 → 服务端**(可选):

```json
{ "type": "subscribe", "topics": ["notifications", "nurture_tasks"] }
```

**服务端 → 客户端**(举例):

```json
{
  "type": "notification",
  "data": {
    "id": 5002,
    "category": "task",
    "level": "info",
    "title": "任务 #89 已开始",
    "ref_type": "nurture_task",
    "ref_id": 89,
    "created_at": "2026-08-16T03:12:00.000Z"
  }
}
```

任务进度事件:

```json
{
  "type": "nurture_task.action",
  "data": {
    "task_id": 88,
    "action_seq": 12,
    "kind": "like_note",
    "status": "succeeded",
    "latency_ms": 2340,
    "risk_score": 0.18
  }
}
```

### 16.3 WS /ws/nurture-tasks/{id}/progress

仅推送单个任务的动作增量,与 `WS /ws/notifications` 中 `nurture_task.action` payload 相同,但只包含 `task_id == {id}` 的事件。

**客户端示例(浏览器)**:

```ts
const ws = new WebSocket(
  `ws://127.0.0.1:8000/api/v1/ws/nurture-tasks/88/progress?token=${accessToken}`
);

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  if (msg.type === 'nurture_task.action') {
    // 更新进度条
  }
};
```

### 16.4 关闭与重连

- 客户端在网络抖动时使用指数退避(1s, 2s, 4s, 上限 30s)重连。
- 服务端不保证消息幂等;前端应根据 `action_seq` 去重。
- 服务端在心跳超时或 5xx 时主动关闭,客户端必须处理 `close` 事件。

### 16.5 错误码

WebSocket 握手错误通过 HTTP 状态码返回:

| HTTP | code | 含义 |
|---|---|---|
| 401 | 10001 | token 缺失 / 无效 |
| 403 | 10003 | 缺少 `dashboard.read` 等基础权限 |
| 404 | 10004 | task 不存在(仅 progress 通道) |
| 503 | 10503 | 服务端过载,稍后重连 |

连接建立后的运行期错误通过消息推送:

```json
{ "type": "error", "code": 10007, "message": "rate limited, slow down" }
```

---

## 附录 A: 端点速查表

| 模块 | 端点数 | 鉴权 |
|---|---|---|
| Auth | 4 | 大部分需 JWT |
| Operators | 10 | 角色级 |
| Platform Accounts | 16+ | permission |
| Platform Configs | 5 | permission |
| Nurture Tasks | 9 | permission |
| Nurture Schedules | 8 | permission |
| Nurture Action Sets | 6 | permission |
| Favorites | 5 | permission |
| Dashboard | 4 | 登录 |
| Risk Config | 3 | permission |
| Notifications | 6 | 登录 |
| Audit Logs | 3 | permission |
| Browser Sessions | 6 | permission |
| Health | 3 | 无 |
| WebSocket | 2 | JWT (query) |

合计约 **90 个端点** + **2 个 WebSocket 通道**。

## 附录 B: 错误响应示例合集

```json
// 401 10001
{ "code": 10001, "message": "unauthenticated", "data": null }

// 401 10002
{ "code": 10002, "message": "token expired", "data": null }

// 403 10003
{ "code": 10003, "message": "forbidden: missing permission nurture.create", "data": null }

// 404 10004
{ "code": 10004, "message": "platform account not found: id=999", "data": null }

// 409 40002
{ "code": 40002, "message": "account has running nurture tasks, stop them first", "data": { "running_task_ids": [88, 91] } }

// 422 10006
{ "code": 10006, "message": "validation failed", "data": { "errors": [{ "loc": ["body", "actions", 0, "weight"], "msg": "must be >= 0" }] } }

// 429 10007
{ "code": 10007, "message": "rate limited", "data": { "retry_after_seconds": 30 } }

// 500 10500
{ "code": 10500, "message": "internal error", "data": null, "request_id": "0c1a2b3c-..." }

// 501 10504
{ "code": 10504, "message": "platform \"weibo\" is not yet supported in v0.2", "data": null }

// 502 10502
{ "code": 10502, "message": "opencli not reachable", "data": { "endpoint": "http://127.0.0.1:7800/cdp/9222" } }

// 503 10503
{ "code": 10503, "message": "service unavailable", "data": null }
```

## 附录 C: 变更记录

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-08-16 | 0.2.0 | 初稿,覆盖 8 平台账号 + 15 个模块 + 2 个 WS |
