# 02 · 信息架构（Information Architecture）

> 适用版本：**media-manager v0.2**
> 撰写日期：2026-08-16
> 关联文档：[`01-product-overview.md`](01-product-overview.md) · [`08-business-flows.md`](08-business-flows.md)

---

## 1. Navbar 整体结构

media-manager v0.2 的整体页面框架由"**侧边栏主菜单** + **顶部平台 Tab**"两层组成。侧边栏管"做什么业务"，顶部 Tab 管"在哪 1 个平台做"，二者正交。

### 1.1 视觉结构（ASCII art）

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  media-manager                                           🔔  admin ▾  退出  │  ← 顶栏（用户 / 通知 / 退出）
├──────────┬───────────────────────────────────────────────────────────────────┤
│          │  [🔴小红书] [🧣微博] [🎵抖音] [💡知乎] [🐦Twitter] [📺B站] [🎙️小宇宙] [📰公众号] │  ← 顶部 Tab（平台过滤）
│          ├───────────────────────────────────────────────────────────────────┤
│  📊 账号总览  │                                                                │
│  ─────────────  │                                                                │
│  📋 媒体账号  │                                                                │
│   ├─ 📱账号列表 │                                                                │
│   ├─ 🔐登录态  │                       <当前路由对应的页面内容>                    │
│   ├─ 📈活跃度  │                                                                │
│   └─ 🛡️风控配置 │                                                                │
│  ─────────────  │                                                                │
│  ⚡ 养号任务  │                                                                │
│   ├─ 🟢执行中  │                                                                │
│   ├─ 📜历史    │                                                                │
│   ├─ ⏰定时任务│                                                                │
│   ├─ 📑动作集  │                                                                │
│   └─ ⭐我的收藏│                                                                │
│  ─────────────  │                                                                │
│  ⚙️ 管理台    │                                                                │
│   ├─ ⚙️平台配置│                                                                │
│   ├─ 🔔通知    │                                                                │
│   ├─ 📊操作日志│                                                                │
│   └─ 👥操作员  │                                                                │
│          │                                                                │
│  [<折叠/展开>]│                                                                │
└──────────┴───────────────────────────────────────────────────────────────────┘
```

### 1.2 结构组成

| 区域 | 位置 | 数量 | 作用 | 是否受 Tab 影响 |
|------|------|------|------|-----------------|
| 顶栏 | 最上方 | 3 元素 | 用户名 / 通知中心入口 / 退出登录 | 否 |
| **顶部 Tab** | 顶栏之下、内容之上 | **8 个**（小红书 + 7 平台） | 当前选中的平台；过滤页面内"账号"维度 | **是**（影响下方内容） |
| 侧边栏主菜单 | 左侧 220px（可折叠到 64px） | 4 顶级 + 13 子级 = 17 项 | 业务域导航 | 否（菜单本身不受 Tab 影响） |
| 内容区 | 右侧 | — | 当前路由对应页面 | **是**（页面内数据按 Tab 过滤） |

### 1.3 关键设计原则

- **菜单与平台正交**：菜单管"业务域"（账号 / 养号 / 管理），Tab 管"平台"（xhs / weibo / ...），互不耦合。任何"账号"相关页面都不会因为 Tab 切换而消失，只会过滤数据。
- **最多 2 层**：侧边栏顶级 + 子级，不再有 3 层。避免"汉堡包套娃"。
- **Tab 默认平台**：刷新页面后 Tab 持久化到 `localStorage.media_manager_active_platform`，默认 `xhs`。
- **Tab 切换 = URL query 变化**：例如 `?platform=xhs`；不进入路由表。

---

## 2. 完整菜单树

下面是从上到下、点击可达的完整菜单树。**17 个菜单项**（4 顶级 + 13 子级）覆盖 v0.2 全部业务域。

```
media-manager v0.2 菜单树
─────────────────────────

👤 账号总览                                  ← 默认路由 /accounts
   │  📊 全平台账号健康度一屏（按平台分组卡片：账号数 / 启用数 / 异常数 / 今日配额占用）
   │  🎯 进入即看到所有账号的"今天是否需要养号"
   │
📋 媒体账号管理
   │
   ├─ 📱 账号列表           /accounts/list
   │    │  CRUD 账号；启停；查看 CDP 端口
   │    │  表格列：账号名 / 平台(emoji) / 状态 / 端口 / 优先级 / 启用 / 操作
   │    │  操作：检查登录 / 启动养号 / 收藏夹 / 编辑 / 删除
   │    │
   ├─ 🔐 登录态管理         /accounts/sessions
   │    │  按平台分组显示 cookie 状态：✅valid / ⚠️cookie_invalid / 🚫banned / ❓unknown
   │    │  一键触发 check-login；显示最近一次检查时间
   │    │
   ├─ 📈 账号活跃度         /accounts/activity
   │    │  30 天活跃度折线图：每账号每天被养号次数 / 浏览时长 / 点赞数 / 收藏数
   │    │  支持按平台过滤（受 Tab 影响）
   │    │
   └─ 🛡️ 风控配置           /accounts/risk
        │  风控阈值配置：MAX_LIKES_PER_HOUR / MAX_LIKES_PER_DAY / SILENT_HOURS
        │  当前生效值与建议值的对比；保存后写入 system_settings
        │
⚡ 养号任务
   │
   ├─ 🟢 执行中             /nurture/running
   │    │  实时表格：task_id / 账号 / 开始 / 持续 / 状态(⏳/✅/❌) / 进度 / 结果
   │    │  5 秒轮询；点击行看动作详情
   │    │
   ├─ 📜 历史               /nurture/history
   │    │  分页表格 + 过滤器（账号 / 平台 / 时间 / 状态）
   │    │  点击看完整 action log + 截图（如有）
   │    │
   ├─ ⏰ 定时任务           /nurture/schedules
   │    │  cron 表达式 + 绑定账号集 + 绑定动作集 + 启停
   │    │  下次触发时间预览
   │    │
   ├─ 📑 动作集             /nurture/actions
   │    │  动作模板 CRUD：浏览 / 点赞 / 收藏 的组合
   │    │  示例："轻度日养" = 浏览 30 min + 点赞 5 + 收藏 3
   │    │
   └─ ⭐ 我的收藏夹         /nurture/favorites
        │  收藏夹快照网格（按账号分组）
        │  支持历史对比（今天 vs 7 天前 / 30 天前）
        │
⚙️ 管理台配置
   │
   ├─ ⚙️ 平台配置           /admin/platforms
   │    │  8 平台元数据：icon / display_name / status(implemented/stub) / 备注
   │    │  全局开关 nurture_global_enabled
   │    │
   ├─ 🔔 通知中心           /admin/notifications
   │    │  事件订阅配置：哪些事件通知谁（站内 / 邮件 / webhook）
   │    │  历史通知列表
   │    │
   ├─ 📊 操作日志           /admin/audit
   │    │  完整 audit_logs：谁 / 何时 / 做了什么 / 结果
   │    │  按操作员 / 类型 / 时间过滤
   │    │
   └─ 👥 操作员管理         /admin/operators
        │  users 表 CRUD + 角色分配（admin/operator/viewer）
        │  重置密码 / 启停账号

─────────────────────────
顶部 Tab（始终在内容区上方）：
  [🔴小红书] [🧣微博] [🎵抖音] [💡知乎] [🐦Twitter] [📺B站] [🎙️小宇宙] [📰公众号]
```

> 顶级菜单的图标：👤 账号总览 / 📋 媒体账号管理 / ⚡ 养号任务 / ⚙️ 管理台配置。侧边栏在折叠态下只显示图标，hover 弹出 tooltip。

---

## 3. 路由表

v0.2 共 **14 条**业务路由 + 1 条登录路由 + 1 条默认重定向。每条路由标注是否受顶部平台 Tab 影响。

> **"受 Tab 影响"** 定义：页面渲染时是否读取 `?platform=xhs` 或 store 里的 `activePlatform` 来过滤数据。**菜单本身不受 Tab 影响**——你切到微博 Tab 后，"养号任务 / 执行中"菜单还在，只是内容只显示微博平台的运行中任务。

| # | 路由 | 页面名 | 顶级菜单 | 子菜单 | 受 Tab 影响 | 备注 |
|---|------|--------|----------|--------|-------------|------|
| 1 | `/login` | 登录页 | — | — | ❌ | `meta.public = true` |
| 2 | `/` | （重定向） | — | — | ❌ | redirect → `/accounts` |
| 3 | `/accounts` | 账号总览 | 👤 账号总览 | — | ✅ | 默认平台 Tab 数据；首屏 |
| 4 | `/accounts/list` | 账号列表 | 📋 媒体账号管理 | 📱 账号列表 | ✅ | CRUD；最常用 |
| 5 | `/accounts/sessions` | 登录态管理 | 📋 媒体账号管理 | 🔐 登录态管理 | ✅ | 一键 check-login |
| 6 | `/accounts/activity` | 账号活跃度 | 📋 媒体账号管理 | 📈 账号活跃度 | ✅ | 30 天折线图 |
| 7 | `/accounts/risk` | 风控配置 | 📋 媒体账号管理 | 🛡️ 风控配置 | ❌ | 写 system_settings，与平台无关 |
| 8 | `/nurture/running` | 执行中 | ⚡ 养号任务 | 🟢 执行中 | ✅ | 5s 轮询 |
| 9 | `/nurture/history` | 历史 | ⚡ 养号任务 | 📜 历史 | ✅ | 分页 + 多维过滤 |
| 10 | `/nurture/schedules` | 定时任务 | ⚡ 养号任务 | ⏰ 定时任务 | ✅ | cron + 账号集 + 动作集 |
| 11 | `/nurture/actions` | 动作集 | ⚡ 养号任务 | 📑 动作集 | ❌ | 动作模板是平台无关的元数据 |
| 12 | `/nurture/favorites` | 我的收藏夹 | ⚡ 养号任务 | ⭐ 我的收藏夹 | ✅ | 网格 + 历史对比 |
| 13 | `/admin/platforms` | 平台配置 | ⚙️ 管理台配置 | ⚙️ 平台配置 | ❌ | 8 平台元数据；展示所有平台 |
| 14 | `/admin/notifications` | 通知中心 | ⚙️ 管理台配置 | 🔔 通知中心 | ❌ | 事件订阅配置 |
| 15 | `/admin/audit` | 操作日志 | ⚙️ 管理台配置 | 📊 操作日志 | ❌ | 全量审计 |
| 16 | `/admin/operators` | 操作员管理 | ⚙️ 管理台配置 | 👥 操作员管理 | ❌ | users CRUD |

**统计：14 业务路由，其中 9 条受 Tab 影响，5 条不受。**

### 3.1 路由参数约定

- **平台过滤**通过 query string `?platform=xhs`（或 store `activePlatform`）；不在 path 里。
- **资源 ID** 通过 path 段：`/accounts/list/:id/edit`（v0.3 计划，本期不用）。
- **状态过滤** 通过 query string：`/nurture/history?status=failed&platform=xhs&date=2026-08-16`。

### 3.2 路由守卫

| 守卫点 | 行为 |
|--------|------|
| 未登录访问 `meta.public=false` 路由 | 重定向 `/login` |
| 已登录访问 `/login` | 重定向 `/accounts` |
| Token 过期（401） | 弹 toast + 重定向 `/login`（保留 `redirect` query） |
| 无权限访问 | 页面级 403（Element Plus `ElEmpty`） |

---

## 4. 受 Tab 影响的页面矩阵

只有"读账号数据"的页面才受 Tab 影响；"写配置 / 看元数据 / 看审计"的页面不受影响。

| 页面 | 路由 | 读 platform_accounts | 读 nurture_tasks | 读 favorite_snapshots | 写 system_settings | 受 Tab 影响 |
|------|------|----------------------|-------------------|------------------------|----------------------|---------------|
| 账号总览 | `/accounts` | ✅（按平台聚合） | — | — | — | ✅ |
| 账号列表 | `/accounts/list` | ✅（按平台过滤） | — | — | — | ✅ |
| 登录态管理 | `/accounts/sessions` | ✅（按平台分组） | — | — | — | ✅ |
| 账号活跃度 | `/accounts/activity` | ✅（按平台过滤） | ✅（关联） | — | — | ✅ |
| 风控配置 | `/accounts/risk` | — | — | — | ✅ | ❌ |
| 执行中 | `/nurture/running` | ✅ | ✅（按平台过滤） | — | — | ✅ |
| 历史 | `/nurture/history` | ✅ | ✅（按平台过滤） | — | — | ✅ |
| 定时任务 | `/nurture/schedules` | ✅（按平台过滤） | — | — | — | ✅ |
| 动作集 | `/nurture/actions` | — | — | — | — | ❌（动作模板本身是平台无关元数据，但展开后浏览/点赞参数按平台区分） |
| 我的收藏夹 | `/nurture/favorites` | ✅ | — | ✅（按平台过滤） | — | ✅ |
| 平台配置 | `/admin/platforms` | — | — | — | — | ❌（展示 8 平台全部） |
| 通知中心 | `/admin/notifications` | — | — | — | — | ❌ |
| 操作日志 | `/admin/audit` | — | — | — | — | ❌ |
| 操作员管理 | `/admin/operators` | — | — | — | — | ❌ |

**直观规律：凡是"看具体账号"或"看具体任务"的页面都受 Tab 影响；凡是"配置 / 审计 / 元数据"的页面都不受影响。**

### 4.1 Tab 切换的行为契约

```
用户点击顶部 Tab [🧣微博]
  ↓
1. 写 localStorage.media_manager_active_platform = 'weibo'
2. 写 store.activePlatform = 'weibo'
3. 当前页面 watcher 触发 → 重新发请求携带 ?platform=weibo
4. 页面内容刷新
5. URL 不变（platform 仅作 query，不进 path）
6. 菜单不重渲染（菜单项不变）
```

如果当前页面**不**受 Tab 影响（例如 `/accounts/risk`），Tab 切换**仅**改写 store 不触发任何请求；视觉上 Tab 仍高亮在新平台，下次进入受影响的页面才生效。

---

## 5. 导航层级深度

v0.2 严格遵守 **最多 2 层**深度（顶级菜单 + 子菜单），不再有第三层。

```
深度 0:  业务域（4 顶级）
         ├─ 👤 账号总览
         ├─ 📋 媒体账号管理
         ├─ ⚡ 养号任务
         └─ ⚙️ 管理台配置

深度 1:  业务子项（13 子级）
         📋 媒体账号管理 下：
           ├─ 📱 账号列表
           ├─ 🔐 登录态管理
           ├─ 📈 账号活跃度
           └─ 🛡️ 风控配置
         ⚡ 养号任务 下：
           ├─ 🟢 执行中
           ├─ 📜 历史
           ├─ ⏰ 定时任务
           ├─ 📑 动作集
           └─ ⭐ 我的收藏夹
         ⚙️ 管理台配置 下：
           ├─ ⚙️ 平台配置
           ├─ 🔔 通知中心
           ├─ 📊 操作日志
           └─ 👥 操作员管理

深度 2:  ❌ 不存在
```

### 5.1 为什么不做第 3 层

| 反对第 3 层的理由 | 解释 |
|-------------------|------|
| 侧边栏宽度有限 | 220px 折叠到 64px 后，最多显示 2 级文字 |
| Element Plus ElMenu 模型 | 嵌套 ElSubMenu × 2 视觉噪音陡增 |
| 操作员认知负担 | 养号相关只有 5 个子项，再分层无意义 |
| 替代方案 | 复杂场景用页面内 Tab（参考 `/accounts/sessions` 内按平台 Tab） |

### 5.2 页面内二级导航（Tab）的允许位置

虽然**菜单**严格 2 层，但**页面内**允许出现二级 Tab 来组织内容，常见位置：

| 页面 | 二级 Tab | 用途 |
|------|----------|------|
| `/accounts/sessions` | 按平台 Tab | 切小红书/微博/抖音 查看登录态 |
| `/nurture/history` | 按状态 Tab | 全部 / 进行中 / 成功 / 失败 |
| `/nurture/favorites` | 按账号 Tab | 多账号收藏夹切换 |
| `/admin/audit` | 按类型 Tab | 登录 / 养号 / 配置 / 账号 |

---

## 6. 权限到菜单的映射

> 详细权限矩阵见 [`01-product-overview.md`](01-product-overview.md) §3。这里只列"哪个角色能看到哪些菜单项"。

| 菜单项 | admin | operator | viewer |
|--------|:-----:|:--------:|:------:|
| 👤 账号总览 | ✅ | ✅ | ✅ |
| 📋 / 📱 账号列表 | ✅ | ⚠️ 只读 | ✅ 只读 |
| 📋 / 🔐 登录态管理 | ✅ | ⚠️ 仅 check-login | ✅ 只读 |
| 📋 / 📈 账号活跃度 | ✅ | ✅ | ✅ |
| 📋 / 🛡️ 风控配置 | ✅ | ❌ | ❌ |
| ⚡ / 🟢 执行中 | ✅ | ✅ | ✅ 只读 |
| ⚡ / 📜 历史 | ✅ | ✅ | ✅ 只读 |
| ⚡ / ⏰ 定时任务 | ✅ | ❌ | ❌ |
| ⚡ / 📑 动作集 | ✅ | ⚠️ 仅使用 | ✅ 只读 |
| ⚡ / ⭐ 我的收藏夹 | ✅ | ✅ | ✅ |
| ⚙️ / ⚙️ 平台配置 | ✅ | ❌ | ❌ |
| ⚙️ / 🔔 通知中心 | ✅ | ❌ | ❌ |
| ⚙️ / 📊 操作日志 | ✅ | ⚠️ 仅自己 | ⚠️ 仅自己 |
| ⚙️ / 👥 操作员管理 | ✅ | ❌ | ❌ |

> 说明：✅ = 完全可访问；⚠️ = 受限访问（按钮置灰或过滤数据）；❌ = 完全不可见（菜单项不渲染）。

实现机制：
- 前端：`navPermissions.ts` 中 `TopItem.topLevelPermission` / `SubItem.permission` 控制菜单可见性。
- 后端：`Depends(require_permission("perm.code"))` 控制 API 可调用性；前端绕过时返回 403。

---

## 7. 路由 → 数据源 → API 全景图

| 路由 | 页面 | 主要数据源 | 主要 API |
|------|------|------------|----------|
| `/accounts` | 账号总览 | `platform_accounts` 聚合 | `GET /api/v1/platform-accounts?platform=xhs` + `GET /api/v1/platforms` |
| `/accounts/list` | 账号列表 | `platform_accounts` | `GET/POST/PUT/DELETE /api/v1/platform-accounts`、`POST .../check-login`、`POST .../nurture` |
| `/accounts/sessions` | 登录态管理 | `platform_accounts.login_status` | 同上 + `POST /api/v1/platform-accounts/{id}/check-login` |
| `/accounts/activity` | 账号活跃度 | `nurture_tasks`（聚合） | `GET /api/v1/nurture-tasks?platform=xhs&days=30` |
| `/accounts/risk` | 风控配置 | `system_settings` | `GET/PUT /api/v1/system-settings` |
| `/nurture/running` | 执行中 | `nurture_tasks`（status=running/pending） | `GET /api/v1/nurture-tasks?status=running`（5s 轮询） |
| `/nurture/history` | 历史 | `nurture_tasks` | `GET /api/v1/nurture-tasks?status=...&page=...` |
| `/nurture/schedules` | 定时任务 | `nurture_schedules` | `CRUD /api/v1/nurture-schedules` |
| `/nurture/actions` | 动作集 | `action_sets` | `CRUD /api/v1/action-sets` |
| `/nurture/favorites` | 我的收藏夹 | `favorite_snapshots` | `GET /api/v1/platform-accounts/{id}/favorites`、`GET .../favorites/history` |
| `/admin/platforms` | 平台配置 | `platforms` + `system_settings` | `GET /api/v1/platforms`、`PUT /api/v1/system-settings` |
| `/admin/notifications` | 通知中心 | `system_settings` + `notifications` | `GET/PUT /api/v1/system-settings`、`GET /api/v1/notifications` |
| `/admin/audit` | 操作日志 | `audit_logs` | `GET /api/v1/audit-logs` |
| `/admin/operators` | 操作员管理 | `users` + `permissions` | `CRUD /api/v1/users`、`GET /api/v1/permissions` |

---

## 8. 后续演进（v0.3+ 预览）

| 演进点 | 何时做 | 备注 |
|--------|--------|------|
| `/accounts/list/:id/edit` 详情页 | v0.3 | 账号单独详情/历史养号时间线 |
| `/nurture/schedules/:id/log` | v0.3 | 定时任务触发历史 |
| `/admin/platforms/:platform/adapter` | v0.3+ | 进入单个平台适配器配置（每个平台一份） |
| `/nurture/favorites/compare` | v0.3 | 收藏夹历史 diff 视图 |
| 顶栏搜索 | v1+ | 全局搜账号 / 任务 / 收藏 |

> 本节仅作规划参考，不在 v0.2 范围。
