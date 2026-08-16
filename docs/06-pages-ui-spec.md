# 06 · 页面 UI 详细规范（media-manager v0.2）

> 本文档列出 v0.2 全部 **17 项 UI 入口**（14 个子页面 + 1 个默认入口 + 2 个隐含视图）的视觉布局、字段、交互、API、异常状态。
> 设计规范来源：[Google Material Design 3](https://m3.material.io/)。
> 组件实现层：[Element Plus 2.9](https://element-plus.org/zh-CN/component/overview.html)。
> 详细设计 token 见 `docs/05-ui-design-system.md`。
> 详细 API 见 `docs/api-doc.md`（继承自 v0.1）；v0.2 新增端点以本文档为准。

---

## 0. 全局布局

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ☰  活动采集系统 / [页面标题]            [本地轻量版]  [👤 admin  ⏏退出]   │  ← AppBar (64dp, Elevation 0)
├────────┬───────────────────────────────────────────────────────────────────┤
│        │  [🔴小红书] [🧣微博] [🎵抖音] [💡知乎] [🐦Twitter] [📺B站] [🎙️...]│  ← 顶部 Tab (48dp, sticky)
│  👤    │  ┌────────────────────────────────────────────────────────────┐  │
│  📱    │  │                                                            │  │
│  🔐    │  │                                                            │  │
│  📈    │  │                  页面内容区 (24dp padding)                  │  │
│  🛡️    │  │                                                            │  │
│  ──    │  │                                                            │  │
│  🟢    │  │                                                            │  │
│  📜    │  │                                                            │  │
│  ⏰    │  │                                                            │  │
│  📑    │  │                                                            │  │
│  ⭐    │  │                                                            │  │
│  ──    │  │                                                            │  │
│  ⚙️    │  │                                                            │  │
│  🔔    │  │                                                            │  │
│  📊    │  │                                                            │  │
│  👥    │  │                                                            │  │
│ NavRail│  └────────────────────────────────────────────────────────────┘  │
│ 240dp  │                                                                   │
└────────┴───────────────────────────────────────────────────────────────────┘
```

- **AppBar**：高 64dp，背景 `surface`，底边 1dp `outline-variant`。
- **NavRail**：宽 240dp（可折叠 80dp），背景 `surface-container`。
- **顶部 Tab**：高 48dp，指示器 3dp `primary`，未选中 `on-surface-variant`。
- **页面内容区**：最大宽 1440dp，居中，24dp 内边距。

---

## 块 1 · 总览

### 1. 👤 账号总览（默认入口 `/`）

> 路由：`/` → 重定向到 `/?tab=dashboard`
> 角色：所有登录用户
> 用途：聚合视图，看 8 个平台的账号健康度、养号进度、最近 7 天活跃度趋势

#### 1.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 账号总览                                          │
│                                                                    │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                   │
│ │ 账号总数 │ │ 今日活跃 │ │ 养号任务 │ │ 异常账号 │   ← 4 KPI 卡片  │
│ │   24    │ │   18    │ │   3     │ │   2     │                   │
│ │ ──────── │ │ ──────── │ │ ──────── │ │ ──────── │                  │
│ │ ↑ 2 本周 │ │ ↑ 3 昨日 │ │ 2 失败   │ │ 需关注    │                 │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘                   │
│                                                                    │
│ 活跃度趋势 (近 7 天)                                               │
│ ┌────────────────────────────────────────────────────────────┐    │
│ │  20 ┤                                          ╱╲           │    │
│ │  15 ┤                              ╱╲    ╱╲╱  ╱  ╲         │    │
│ │  10 ┤           ╱╲    ╱╲     ╱╲╱  ╲╱  ╲╱                  │    │
│ │   5 ┤    ╱╲╱╲╱╲╱  ╲╱  ╲╱╲╱╲╱                          │    │
│ │   0 ┴──────────────────────────────────────────────         │    │
│ │      Mon  Tue  Wed  Thu  Fri  Sat  Sun                    │    │
│ └────────────────────────────────────────────────────────────┘    │
│                                                                    │
│ 平台分布                                       最近异常 ↓        │
│ ┌──────────────────────────┐   ┌──────────────────────────────┐  │
│ │ [xhs] ████████ 12        │   │ ⚠ #18 小红书·夜猫号          │  │
│ │ [wb]  ██████ 6           │   │   登录已过期 5 分钟前         │  │
│ │ [dy]  ███ 3              │   │ ────────────                  │  │
│ │ [zh]  █ 1                │   │ ❌ #22 微博·八卦号           │  │
│ │ [tw]  █ 1                │   │   养号失败 1 小时前           │  │
│ │ [bili]█ 1                │   │ ────────────                  │  │
│ └──────────────────────────┘   └──────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

#### 1.2 字段说明表

| 区块 | 字段 | 类型 | 来源 | 备注 |
|---|---|---|---|---|
| KPI | 账号总数 | int | `COUNT(platform_accounts WHERE enabled=true)` | 跨所有平台 |
| KPI | 今日活跃 | int | `COUNT(accounts WHERE last_login_check_at::date = today)` | — |
| KPI | 养号任务 | int | `COUNT(nurture_tasks WHERE status IN (pending, running))` | — |
| KPI | 异常账号 | int | `COUNT(accounts WHERE login_status IN (expired, logged_out))` | — |
| KPI | 周环比 | str | (this_week - last_week) / last_week | ↑/↓ + 百分比 |
| 趋势 | date[7] | date | GROUP BY date | 折线图 |
| 趋势 | active_count[7] | int | — | Y 轴 |
| 分布 | platform | enum | GROUP BY platform | 横向 bar |
| 分布 | count | int | — | — |
| 异常 | account_id, name, error, time | — | 最近 10 条 | — |

#### 1.3 交互行为

- KPI 卡片可点击 → 跳转到对应子页面（账号总数 → `/accounts`、今日活跃 → `/account-activity`、养号任务 → `/nurture/running`、异常账号 → `/login-status?status=abnormal`）。
- 趋势图悬停 → Tooltip 显示当日数据明细。
- 异常列表点击行 → 跳到 `/accounts/:id` 详情。
- 平台分布 bar 点击 → 切到对应平台 Tab + 跳到 `/accounts?platform=xhs`。

#### 1.4 涉及 API

```
GET  /api/v1/accounts/summary          → { total, today_active, running_tasks, abnormal }
GET  /api/v1/accounts/activity-trend   → { dates: [], counts: [] }
GET  /api/v1/accounts/distribution     → [{ platform, count }]
GET  /api/v1/accounts/recent-abnormal → [10 条]
```

#### 1.5 异常状态

**Loading**：
```
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ ◐...    │ │ ◐...    │ │ ◐...    │ │ ◐...    │  ← 4 张骨架卡（el-skeleton）
└─────────┘ └─────────┘ └─────────┘ └─────────┘
[趋势图占位高度 320px, 显示旋转加载]
```

**Empty**（全新账号无数据）：
```
┌────────────────────────────────────┐
│           🐣                        │
│    还没有任何账号，从这里开始       │
│     [+ 新建账号]  ← Filled Button  │
└────────────────────────────────────┘
```

**Error**：
```
┌────────────────────────────────────┐
│ ❌ 加载失败：网络错误              │
│ [重试]  ← Text Button              │
└────────────────────────────────────┘
```

#### 1.6 Material 3 组件映射

| 区域 | M3 组件 | Element Plus |
|---|---|---|
| 页面标题 | Headline Medium | `<h1 class="md-typescale-headline-medium">` |
| KPI 卡片 | Card (Elevated) | `el-card` |
| 趋势图 | — | ECharts Line |
| 平台分布 | Card | `el-card` + 自绘 bar |
| 异常列表 | List | `el-table` 或 `el-list` |
| 新建按钮 | Filled Button | `el-button type="primary"` |

---

## 块 2 · 媒体账号管理

### 2. 📱 账号列表 `/accounts`

> 路由：`/accounts`
> 角色：admin
> 用途：CRUD 平台账号、启停、优先级、配额

#### 2.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 账号列表                            [+ 新建账号] │
│ Body Medium: 共 24 个账号 · 启用 21 · 禁用 3                       │
│                                                                    │
│ [搜索账号名_______]  [平台▼ xhs]  [状态▼ 全部]  [⚙ 列]  [↻ 刷新] │
│                                                                    │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ ID │ 名称        │ 平台 │ 会话名      │ 登录态 │ 优先级 │ ⚙ │  │
│ ├────┼─────────────┼──────┼─────────────┼────────┼────────┼───┤  │
│ │ 12 │ 种草号-蓝    │ 🔴xhs│ xhs_12      │ ✓ 已登 │ P2     │⋯│  │
│ │ 13 │ 测评号-红    │ 🔴xhs│ xhs_13      │ ⚠ 过期 │ P1     │⋯│  │
│ │ 22 │ 八卦号       │ 🧣wb │ weibo_22    │ ✗ 未登 │ P3     │⋯│  │
│ │ ...                                                          │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ 共 24 条  [<] 1 2 3 [>]   每页 [20▼]   跳转 [_]                    │
└────────────────────────────────────────────────────────────────────┘
```

#### 2.2 字段说明表

| 字段 | 类型 | 必填 | 来源 | 校验 | 备注 |
|---|---|---|---|---|---|
| `id` | int | — | DB | — | 主键，禁用编辑 |
| `name` | str(64) | ✓ | 用户输入 | 1-64 字符、全局唯一 | 友好名 |
| `platform` | enum | ✓ | 下拉 | 8 选 1 | xhs / weibo / douyin / zhihu / twitter / bilibili / xiaoyuzhou / wechat-official |
| `session_name` | str(64) | auto | 后端生成 | 唯一 | `xhs_12`、`wb_22` |
| `login_status` | enum | — | 系统检测 | — | logged_in / logged_out / expired / unknown |
| `enabled` | bool | ✓ | Switch | — | 默认 true |
| `priority` | int | — | 滑块 | 0-100 | 默认 0，数值越大越优先 |
| `daily_quota_seconds` | int | — | 数字输入 | 600-28800 | 默认 14400（4 小时） |
| `last_login_check_at` | datetime | — | 系统 | — | 只读 |
| `created_at` | datetime | — | DB | — | 只读 |

#### 2.3 交互行为

- 行 hover → 背景 `surface-container-low`。
- 行点击 → 打开账号详情侧拉（Side Sheet，宽 480dp）。
- 行的 ⋯ 菜单：编辑、禁用/启用、复制 ID、查看养号历史、删除。
- 启用 Switch 直接切换，**无需弹窗**（乐观更新）。
- 删除前必弹确认 Dialog（Material Dialog），文案："确认删除账号「{name}」？该账号的所有收藏快照将一并删除。"
- 平台筛选为多选下拉（v0.2 简化为单选）。
- 列设置（⚙ 列）：可隐藏 `session_name` / `priority` / `daily_quota_seconds`。
- 排序：点击列头切换 asc/desc，可排序列：id / name / priority / last_login_check_at。

#### 2.4 涉及 API

```
GET    /api/v1/accounts?platform=&status=&q=&page=&page_size=  → Page<PlatformAccountOut>
POST   /api/v1/accounts                                          → 201 PlatformAccountOut
GET    /api/v1/accounts/{id}                                     → PlatformAccountOut
PATCH  /api/v1/accounts/{id}                                     → PlatformAccountOut
DELETE /api/v1/accounts/{id}                                     → 204
POST   /api/v1/accounts/{id}/check-login                         → CheckLoginResultOut
```

#### 2.5 异常状态

**Loading**：`el-skeleton` 占位 5 行 × 8 列。
**Empty**（筛选后无结果）：
```
┌────────────────────────────────────┐
│           🔍                        │
│     没有符合条件的账号              │
│     [清除筛选]  ← Text Button       │
└────────────────────────────────────┘
```
**Error**：Snackbar `❌ 加载失败：{msg} [重试]`。

#### 2.6 Material 3 组件映射

| 元素 | M3 组件 | Element Plus |
|---|---|---|
| 搜索框 | SearchBar | `el-input` + `prefix="search"` |
| 筛选 | Filter Chip | `el-select` |
| 表格 | Data Table | `el-table` + `el-table-column` |
| 状态徽章 | Badge | `el-tag`（按 §3.2.1 颜色） |
| 启用 Switch | Switch | `el-switch` |
| 分页 | — | `el-pagination` |
| 新建按钮 | Filled Button | `el-button type="primary"` |
| ⋯ 菜单 | Icon Menu | `el-dropdown` |
| 删除确认 | Dialog | `el-dialog` |
| 详情 | Side Sheet | `el-drawer direction="rtl"` |

---

### 3. 🔐 登录态管理 `/login-status`

> 路由：`/login-status`
> 角色：admin
> 用途：批量检查 8 平台账号的登录态、查看异常、批量触发重新登录

#### 3.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 登录态管理                                         │
│ Body Medium: 24 个账号 · 4 项异常 · 上次检查 5 分钟前                │
│                                                                    │
│ [平台▼ 全部]  [状态▼ 异常]  [↻ 全部检查登录态]  [🔐 批量重新登录] │
│                                                                    │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ ⚠ 异常账号 (4)                                                │  │
│ ├────┬───────────┬──────┬──────────┬───────────┬─────────────┤  │
│ │ ID │ 名称      │ 平台 │ 状态     │ 上次检查  │ 操作        │  │
│ ├────┼───────────┼──────┼──────────┼───────────┼─────────────┤  │
│ │ 13 │ 测评号-红  │ 🔴xhs│ ⚠ 已过期 │ 5 分钟前  │ [重新登录] │  │
│ │ 18 │ 夜猫号    │ 🔴xhs│ ✗ 未登录 │ 1 小时前  │ [重新登录] │  │
│ │ 22 │ 八卦号    │ 🧣wb │ ✗ 未登录 │ 2 小时前  │ [重新登录] │  │
│ │ 24 │ 旅行号    │ 🎵dy │ ⚠ 已过期 │ 1 天前   │ [重新登录] │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ ✓ 正常账号 (20)                                    [展开]          │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ 12 │ 种草号-蓝 │ 🔴xhs│ ✓ 已登录 │ 1 分钟前 │ [检查] [编辑]│  │
│ │ ...                                                          │  │
│ └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

#### 3.2 字段说明表

| 字段 | 类型 | 枚举 | 显示色 |
|---|---|---|---|
| `login_status` | enum | `logged_in` | Success 绿 |
| `login_status` | enum | `logged_out` | Error 红 |
| `login_status` | enum | `expired` | Warning 橙 |
| `login_status` | enum | `unknown` | Info 蓝 |
| `last_login_check_at` | datetime | — | 相对时间："5 分钟前" |

#### 3.3 交互行为

- 顶部 [↻ 全部检查登录态] → 触发 `POST /api/v1/accounts/check-all` → 按钮转 Progress → 完成后 Snackbar。
- [🔐 批量重新登录] → 弹 Dialog 选账号（多选）→ 启动 Celery 任务队列。
- 单行 [重新登录] → 立即触发 `POST /api/v1/accounts/{id}/login` → 进入"重新登录中"过渡态（Spinner overlay）。
- 状态变化通过 polling（5s 一次）或 SSE 推送（v0.3 规划）。
- 异常区域始终在最上，自动展开；正常账号默认折叠。

#### 3.4 涉及 API

```
POST  /api/v1/accounts/check-all             → 202 { task_id }
POST  /api/v1/accounts/{id}/check-login      → CheckLoginResultOut
POST  /api/v1/accounts/{id}/login            → 202 { task_id }
GET   /api/v1/accounts?status=abnormal       → 异常列表
GET   /api/v1/accounts?status=normal         → 正常列表
GET   /api/v1/tasks/{task_id}                → 轮询任务状态
```

#### 3.5 异常状态

**Loading**：表格骨架屏 + 顶部 Progress Linear。
**Empty**（无异常）：绿色 Banner "🎉 所有账号登录态正常"。
**Error**（检查失败）：行内 Error Container "❌ 检查失败：[重试]"。

#### 3.6 Material 3 组件映射

| 元素 | M3 组件 | Element Plus |
|---|---|---|
| 状态徽章 | Status Badge | `el-tag type="success/warning/danger/info"` |
| 重新登录按钮 | Filled Button | `el-button type="primary"` |
| 批量操作按钮 | Tonal Button | `el-button type="primary" plain` |
| 进度覆盖层 | Loading Indicator | `el-loading` |

---

### 4. 📈 账号活跃度 `/account-activity`

> 路由：`/account-activity`
> 角色：admin
> 用途：可视化账号登录频次、养号时长、动作分布

#### 4.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 账号活跃度                                         │
│                                                                    │
│ [时间范围▼ 近 7 天]  [平台▼ 全部]  [账号▼ 全部]  [↻ 刷新]          │
│                                                                    │
│ ┌──────────────┬──────────────┬──────────────┬──────────────┐    │
│ │ 总登录次数     │ 总养号时长    │ 点赞数       │ 收藏数        │   │
│ │   142         │  36h 12m     │   89         │   156         │   │
│ │ ↑ 12% 本周    │ ↑ 8% 本周    │ ↓ 3% 本周    │ ↑ 20% 本周   │   │
│ └──────────────┴──────────────┴──────────────┴──────────────┘    │
│                                                                    │
│ 登录活跃度热力图 (账号 × 日期)                                       │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ 账号  \  日期  │ Mon │ Tue │ Wed │ Thu │ Fri │ Sat │ Sun     │  │
│ │ #12 种草号-蓝   │  ▓  │  ▓  │  ░  │  ▓  │  █  │  █  │  █    │  │
│ │ #13 测评号-红   │  ░  │  ░  │  ░  │  ░  │  ░  │  ░  │  ░    │  │
│ │ #18 夜猫号     │  █  │  █  │  █  │  █  │  █  │  █  │  █    │  │
│ │ ...                                                          │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ 动作分布                       平台占比                            │
│ ┌─────────────────────┐       ┌─────────────────────┐             │
│ │  浏览首页  45%       │       │   ╭─────╮            │            │
│ │  点赞     20%       │       │   │xhs  │ 50%        │            │
│ │  收藏     25%       │       │   ╰─────╯            │            │
│ │  其他     10%       │       │   ╭─╮                │            │
│ └─────────────────────┘       │   │wb│ 25%           │            │
│                                │   ╰─╯                │            │
│                                │   [dy 17%]           │            │
│                                └─────────────────────┘             │
└────────────────────────────────────────────────────────────────────┘
```

#### 4.2 字段说明表

| 区块 | 字段 | 类型 | 来源 |
|---|---|---|---|
| KPI | login_count | int | COUNT(login_check_logs) |
| KPI | nurture_seconds | int | SUM(nurture_tasks.duration) |
| KPI | like_count | int | COUNT(nurture_actions WHERE action=like) |
| KPI | favorite_count | int | COUNT(nurture_actions WHERE action=favorite) |
| 热力图 | account_id | int | — |
| 热力图 | date | date | — |
| 热力图 | intensity | int (0-3) | 0=无 / 1=低 / 2=中 / 3=高 |
| 饼图 1 | action_type | enum | browse/like/favorite/other |
| 饼图 2 | platform | enum | — |

#### 4.3 交互行为

- 时间范围可选：今日 / 近 7 天 / 近 30 天 / 自定义。
- 热力图单元格 hover → Tooltip 显示"账号 X 于 YYYY-MM-DD 登录 N 次，养号 M 分钟"。
- 热力图单元格点击 → 跳到该账号的养号历史 `/nurture/history?account_id=X`。
- 图表与 KPI 支持导出 PNG（顶部 [📷 截图] 按钮，ECharts 自带 `getDataURL`）。
- 平台/账号筛选切换 → 图表重新加载（带 Loading 蒙层 200ms 过渡）。

#### 4.4 涉及 API

```
GET /api/v1/accounts/activity/kpi?from=&to=&platform=&account_id=
GET /api/v1/accounts/activity/heatmap?from=&to=
GET /api/v1/accounts/activity/actions?from=&to=
GET /api/v1/accounts/activity/platforms?from=&to=
```

#### 4.5 异常状态

**Loading**：图表位置显示 ECharts Loading 动画。
**Empty**（无活动数据）：
```
┌────────────────────────────────────┐
│           📊                        │
│   该时间范围内没有活跃度数据         │
│   [去新建养号任务 →]                │
└────────────────────────────────────┘
```
**Error**：Snackbar + 图表位置 Error Container。

#### 4.6 Material 3 组件映射

| 元素 | M3 组件 | Element Plus |
|---|---|---|
| 时间选择 | Segmented Button | `el-radio-group button` |
| 平台/账号选择 | Filter Chip | `el-select` |
| KPI 卡片 | Card (Elevated) | `el-card` |
| 热力图 | — | ECharts Heatmap |
| 饼图 | — | ECharts Pie |
| 导出 | IconButton | `el-button` + icon |

---

### 5. 🛡️ 风控配置 `/risk-config`

> 路由：`/risk-config`
> 角色：admin
> 用途：配置全局养号风控守则（静默时段、单日时长上限、操作间隔）

#### 5.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 风控配置                                           │
│ Body Small: 修改后立即生效 · Celery Worker 需重启以重读            │
│                                                                    │
│ ┌─ 全局养号开关 ─────────────────────────────────────────────────┐ │
│ │ [●━━○] 已启用（nurture_global_enabled = true）                │ │
│ │ Body Small: 关闭后所有养号任务会立即进入 skipped 状态          │ │
│ └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│ ┌─ 静默时段 ───────────────────────────────────────────────────┐  │
│ │ 静默开始 [00▼] : [00▼]  静默结束 [06▼] : [00▼]                │  │
│ │ Body Small: 静默时段内养号任务自动跳过（人类睡觉时间）         │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ ┌─ 单日时长上限 ────────────────────────────────────────────────┐  │
│ │ [4 ▼] 小时 (14400 秒)                                          │  │
│ │ Body Small: 超过上限后当日不再执行养号任务                      │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ ┌─ 操作间隔 ────────────────────────────────────────────────────┐  │
│ │ 最小操作间隔 [3 ▼] 秒                                          │  │
│ │ Body Small: 每次操作之间的最小等待时间                          │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ ┌─ 点赞上限 ───────────────────────────────────────────────────┐  │
│ │ 每小时最多 [10 ▼] 次   每日最多 [50 ▼] 次                     │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│                                            [取消]  [保存]         │
└────────────────────────────────────────────────────────────────────┘
```

#### 5.2 字段说明表

| 字段 | 类型 | 默认 | 范围 | 约束 |
|---|---|---|---|---|
| `nurture_global_enabled` | bool | false | — | 全局开关 |
| `silent_hour_start` | int | 0 | 0-23 | < `silent_hour_end` |
| `silent_hour_end` | int | 6 | 0-23 | > `silent_hour_start` |
| `max_daily_seconds` | int | 14400 | 3600-28800 | 单账号每日上限 |
| `min_action_interval_s` | int | 3 | 1-30 | 每次操作最小间隔 |
| `max_likes_per_hour` | int | 10 | 1-50 | 点赞速率限制 |
| `max_likes_per_day` | int | 50 | 1-500 | 点赞日上限 |

> 实际值存储在 `Settings`（pydantic-settings），但 v0.2 通过数据库 `system_config` 表持久化（参考 v0.3 计划）。

#### 5.3 交互行为

- 任何字段修改 → [保存] 按钮启用；未修改时禁用。
- [保存] → `PUT /api/v1/risk-config` → Snackbar "保存成功，Worker 已收到新配置"。
- 静默时段可视化：显示为 24 小时环形图，深色区域即静默时段。
- 字段说明均带 Tooltip 解释。
- 切换全局开关时弹确认 Dialog（防误触）。

#### 5.4 涉及 API

```
GET   /api/v1/risk-config    → RiskConfigOut
PUT   /api/v1/risk-config    → RiskConfigOut
POST  /api/v1/risk-config/reload  → 通知 Worker 重读
```

#### 5.5 异常状态

**Loading**：表单骨架屏。
**Error**（保存失败）：字段下方 Helper Text 变红 + Snackbar。

#### 5.6 Material 3 组件映射

| 元素 | M3 组件 | Element Plus |
|---|---|---|
| 开关 | Switch | `el-switch` |
| 时间选择 | Time Picker | `el-time-select` |
| 数字输入 | TextField | `el-input-number` |
| 保存按钮 | Filled Button | `el-button type="primary"` |
| 取消按钮 | Text Button | `el-button text` |

---

## 块 3 · 养号任务

### 6. 🟢 执行中 `/nurture/running`

> 路由：`/nurture/running`
> 角色：admin
> 用途：实时显示运行中/排队中的养号任务，可手动取消

#### 6.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 执行中任务                       [+ 新建养号任务] │
│ Body Medium: 运行中 2 · 排队 1 · 今日完成 12 · 失败 1              │
│                                                                    │
│ [平台▼ 全部]  [账号▼ 全部]  [↻ 自动刷新 5s]                        │
│                                                                    │
│ ┌─ 运行中 (2) ─────────────────────────────────────────────────┐  │
│ │ #T-3401  #12 种草号-蓝  🔴xhs                                 │  │
│ │ 进度 60%  [████████████░░░░░░░░]  已运行 18 分钟 / 30 分钟     │  │
│ │ 当前动作: 点赞 (3/10)                                          │  │
│ │ [详情] [取消]                                                  │  │
│ ├──────────────────────────────────────────────────────────────┤  │
│ │ #T-3402  #15 萌宠号   🔴xhs                                   │  │
│ │ 进度 25%  [█████░░░░░░░░░░░░░░░]  已运行 7 分钟 / 30 分钟      │  │
│ │ 当前动作: 浏览首页                                              │  │
│ │ [详情] [取消]                                                  │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ ┌─ 排队中 (1) ─────────────────────────────────────────────────┐  │
│ │ #T-3403  #22 八卦号  🧣wb  预计开始 2 分钟后                  │  │
│ │ 动作: 浏览首页 → 收藏                                          │  │
│ │ [提前启动] [取消排队]                                          │  │
│ └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

#### 6.2 字段说明表

| 字段 | 类型 | 说明 |
|---|---|---|
| `task_id` | str | Celery task UUID |
| `account_id` | int | 关联 PlatformAccount |
| `account_name` | str | 友好显示 |
| `platform` | enum | 平台 |
| `actions` | list[str] | browse_home / like_post / favorite_post / fetch_favorites |
| `duration_minutes` | int | 总时长（5-240） |
| `elapsed_seconds` | int | 已运行时长 |
| `progress_pct` | int | 0-100 |
| `current_action` | str | 当前动作 |
| `status` | enum | pending / running / completed / failed / skipped / cancelled |
| `started_at` | datetime | 开始时间 |
| `error` | str | 错误信息（如有） |

#### 6.3 交互行为

- 每 5s 自动轮询 `GET /api/v1/nurture/running`。
- 进度条用 LinearProgress + 动画。
- [取消] → 二次确认 Dialog "确认取消任务 #T-3401？" → `POST /api/v1/nurture/{task_id}/cancel` → 任务进入 cancelled 状态。
- [详情] → 打开 Side Sheet 显示完整动作日志（每个动作的执行时间、结果）。
- [+ 新建养号任务] → 弹 Dialog 选择账号、动作、时长、目标 URL。

#### 6.4 涉及 API

```
GET    /api/v1/nurture/running                          → [NurtureTaskOut]
POST   /api/v1/nurture                                  → 202 { task_id }
POST   /api/v1/nurture/{task_id}/cancel                 → 204
GET    /api/v1/nurture/{task_id}                        → NurtureTaskOut（带动作日志）
GET    /api/v1/nurture/{task_id}/logs                   → [ActionLog]
```

#### 6.5 异常状态

**Loading**：任务卡片骨架屏。
**Empty**（无任务）：
```
┌────────────────────────────────────┐
│           🌱                        │
│     当前没有运行中的养号任务         │
│     [+ 新建养号任务]                │
└────────────────────────────────────┘
```
**Error**（轮询失败）：顶部 Error Banner "⚠ 连接中断，正在重试..."。

#### 6.6 Material 3 组件映射

| 元素 | M3 组件 | Element Plus |
|---|---|---|
| 进度条 | Linear Progress | `el-progress` (line) |
| 任务卡 | Card (Outlined) | `el-card shadow="hover"` |
| 状态徽章 | Status Badge | `el-tag` |
| 取消按钮 | Outlined Button | `el-button` |

---

### 7. 📜 历史 `/nurture/history`

> 路由：`/nurture/history`
> 角色：admin
> 用途：查询历史养号任务，可重跑、查看动作日志

#### 7.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 养号历史                       [📥 导出 CSV]       │
│                                                                    │
│ [日期范围📅 近 7 天]  [平台▼ 全部]  [账号▼ 全部]  [状态▼ 全部]     │
│ [搜索任务ID/名称________]                          [🔍 搜索]        │
│                                                                    │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ 任务ID   │ 账号       │ 平台 │ 动作     │ 时长  │ 状态   │ ⚙ │  │
│ ├──────────┼────────────┼──────┼──────────┼───────┼────────┼───┤  │
│ │ T-3400   │ 种草号-蓝   │ 🔴xhs│ 4 项     │ 28m   │ ✓ 完成 │⋯│  │
│ │ T-3399   │ 萌宠号     │ 🔴xhs│ 3 项     │ 15m   │ ⚠ 跳过 │⋯│  │
│ │ T-3398   │ 夜猫号     │ 🔴xhs│ 4 项     │ 0m    │ ✗ 失败 │⋯│  │
│ │ T-3397   │ 测评号-红   │ 🔴xhs│ 4 项     │ 30m   │ ✓ 完成 │⋯│  │
│ │ ...                                                          │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ 共 142 条  [<] 1 2 3 ... 8 [>]   每页 [20▼]   跳转 [_]            │
└────────────────────────────────────────────────────────────────────┘
```

#### 7.2 字段说明表

| 字段 | 类型 | 说明 |
|---|---|---|
| `task_id` | str | — |
| `account.name` | str | — |
| `platform` | enum | — |
| `actions` | list[str] | 显示为 "4 项" |
| `duration_minutes` | int | — |
| `started_at` | datetime | — |
| `status` | enum | 6 种状态按 §3.2.2 配色 |
| `items_collected` | int | 收藏快照条目数 |
| `error` | str | 失败原因 |

#### 7.3 交互行为

- 行的 ⋯ 菜单：[查看详情] / [查看动作日志] / [重跑] / [删除]。
- [重跑] → 弹 Dialog 确认 → `POST /api/v1/nurture/{task_id}/rerun` → 跳到 `/nurture/running`。
- [查看动作日志] → 弹 Dialog 展示时间线（每步开始/结束/结果）。
- [📥 导出 CSV] → 触发下载，包含当前筛选条件下的所有任务。
- 列头点击排序（task_id / started_at / duration）。

#### 7.4 涉及 API

```
GET    /api/v1/nurture/history?from=&to=&platform=&account_id=&status=&q=&page=&page_size=
POST   /api/v1/nurture/{task_id}/rerun
DELETE /api/v1/nurture/{task_id}
GET    /api/v1/nurture/{task_id}/logs
GET    /api/v1/nurture/export?from=&to=  → CSV
```

#### 7.5 异常状态

**Loading**：表格骨架。
**Empty**（无历史）：
```
┌────────────────────────────────────┐
│           📜                        │
│     暂无养号历史                    │
└────────────────────────────────────┘
```
**Error**：Snackbar "❌ 加载失败 [重试]"。

#### 7.6 Material 3 组件映射

| 元素 | M3 组件 | Element Plus |
|---|---|---|
| 日期范围 | Date Range Picker | `el-date-picker type="daterange"` |
| 表格 | Data Table | `el-table` |
| 导出按钮 | Tonal Button | `el-button plain` |
| 状态徽章 | Status Badge | `el-tag` |

---

### 8. ⏰ 定时任务 `/nurture/schedules`

> 路由：`/nurture/schedules`
> 角色：admin
> 用途：配置 Cron 定时养号计划（v0.6 上线，v0.2 标记为"规划中"）

#### 8.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 定时任务                       [+ 新建定时计划]    │
│ Body Small: 🚧 v0.6 计划 · 当前 UI 仅占位                          │
│                                                                    │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ 🚧 定时养号计划将在 v0.6 引入 Celery Beat 后上线。            │  │
│ │   v0.2 当前支持：手动触发（/nurture/running）                 │  │
│ │   v0.3 计划：每个账号可配置"每天 X 点自动开始养号"            │  │
│ │   进度：⏳⏳⏳░░░░░░░░                                          │  │
│ └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

> **v0.2 占位页**。不实现具体功能，仅 Roadmap 占位。v0.6 落地。

#### 8.2 ~ 8.6 占位

- 字段、交互、API、异常状态、组件映射 全部 v0.6 补充。

---

### 9. 📑 动作集 `/nurture/action-sets`

> 路由：`/nurture/action-sets`
> 角色：admin
> 用途：保存常用动作组合（"浏览+点赞"），供养号任务复用

#### 9.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 动作集                          [+ 新建动作集]     │
│                                                                    │
│ ┌─ 我的动作集 (3) ──────────────────────────────────────────────┐ │
│ │  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐    │ │
│ │  │ 标准养号        │ │ 仅浏览          │ │ 深度互动        │    │ │
│ │  │ 4 项动作        │ │ 1 项动作        │ │ 3 项动作        │    │ │
│ │  │ 30 分钟         │ │ 15 分钟         │ │ 45 分钟         │    │ │
│ │  │ [浏览][点赞]    │ │ [浏览]          │ │ [浏览][点赞]    │    │ │
│ │  │ [收藏][抓收藏]  │ │                 │ │ [收藏]          │    │ │
│ │  │                │ │                 │ │                │    │ │
│ │  │ [使用] [编辑]   │ │ [使用] [编辑]   │ │ [使用] [编辑]   │    │ │
│ │  └────────────────┘ └────────────────┘ └────────────────┘    │ │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  弹窗编辑：                                                         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 名称: [标准养号____________]                                   │  │
│  │ 默认时长: [30 ▼] 分钟                                          │  │
│  │ 动作:                                                          │  │
│  │   [☑] 浏览首页 (browse_home)                                  │  │
│  │   [☑] 点赞 (like_post)        需要 post_url                   │  │
│  │   [☑] 收藏 (favorite_post)    需要 post_url                   │  │
│  │   [☑] 抓取收藏 (fetch_favorites)                              │  │
│  │ 排序: [↑↓] 拖拽调整顺序                                       │  │
│  │                                            [取消]  [保存]     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

#### 9.2 字段说明表

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | int | — |
| `name` | str(64) | 唯一 |
| `duration_minutes` | int | 5-240 |
| `actions` | list[str] | 子集：`browse_home` / `like_post` / `favorite_post` / `fetch_favorites` |
| `actions_order` | list[int] | 动作顺序（默认 0/1/2/3） |
| `created_at` | datetime | — |

#### 9.3 交互行为

- [使用] → 跳到 `/nurture/running` 并预填表单（动作 + 时长）。
- [编辑] / [+ 新建] → 弹 Dialog，拖拽排序动作。
- 勾选 like_post / favorite_post 时 Helper Text 提示 "需要提供 post_url"。
- 删除前弹确认 Dialog（动作集被引用时不阻止删除，但提示"已用于 N 个历史任务"）。

#### 9.4 涉及 API

```
GET    /api/v1/action-sets                  → [ActionSetOut]
POST   /api/v1/action-sets                  → 201
PATCH  /api/v1/action-sets/{id}             → 200
DELETE /api/v1/action-sets/{id}             → 204
```

#### 9.5 异常状态

**Loading**：卡片骨架（3 个）。
**Empty**：
```
┌────────────────────────────────────┐
│           📑                        │
│   创建你的第一个动作集               │
│   [+ 新建动作集]                    │
└────────────────────────────────────┘
```
**Error**：Snackbar。

#### 9.6 Material 3 组件映射

| 元素 | M3 组件 | Element Plus |
|---|---|---|
| 卡片 | Card (Elevated) | `el-card` |
| 多选 | Checkbox | `el-checkbox` |
| 拖拽 | — | `el-draggable` / `vuedraggable` |
| 数字输入 | TextField | `el-input-number` |

---

### 10. ⭐ 我的收藏夹 `/favorites`

> 路由：`/favorites`
> 角色：admin
> 用途：跨平台聚合收藏夹，支持搜索、对比

#### 10.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 我的收藏夹                                         │
│                                                                    │
│ [账号▼ 全部]  [平台▼ 全部]  [📅 最近一次]  [排序▼ 收藏时间↓]      │
│ [🔍 搜索标题/作者______]                                            │
│                                                                    │
│ ┌─────────┬─────────┬─────────┬─────────┬─────────┐              │
│ │ 12,456  │ 892     │ 156     │ 24      │ 8       │  ← 顶部 KPI  │
│ │ 总条目  │ 账号数  │ 今日新增│ 平台数  │ 快照数   │              │
│ └─────────┴─────────┴─────────┴─────────┴─────────┘              │
│                                                                    │
│ ┌─ 收藏列表 (3 列卡片网格) ─────────────────────────────────────┐  │
│ │ ┌────────┐ ┌────────┐ ┌────────┐                              │  │
│ │ │ [cover]│ │ [cover]│ │ [cover]│                              │  │
│ │ │ Title  │ │ Title  │ │ Title  │                              │  │
│ │ │ @author│ │ @author│ │ @author│                              │  │
│ │ │ 🔴xhs  │ │ 🧣wb   │ │ 🎵dy   │                              │  │
│ │ │ 2天前  │ │ 5天前  │ │ 1周前  │                              │  │
│ │ └────────┘ └────────┘ └────────┘                              │  │
│ │ ...                                                          │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ 加载更多 [↓]                                                       │
└────────────────────────────────────────────────────────────────────┘
```

#### 10.2 字段说明表

| 字段 | 类型 | 来源 |
|---|---|---|
| `note_id` | str | FavoriteSnapshot.items_json[].note_id |
| `title` | str | — |
| `author` | str | — |
| `url` | str | 原帖链接（点击新窗口打开） |
| `cover_url` | str | 缩略图（懒加载） |
| `liked_at` | datetime | 收藏时间 |
| `platform` | enum | 来自 snapshot |
| `account_id` | int | 哪个账号收藏的 |
| `account_name` | str | — |

#### 10.3 交互行为

- 卡片 hover → 提升 Elevation 1→2 + 阴影过渡。
- 卡片点击 → 弹 Bottom Sheet 显示详情 + 完整摘要 + [打开原帖]。
- 懒加载：滚动到底部 → 触发加载下一页（IntersectionObserver）。
- 排序：收藏时间↓/↑、作者、平台。
- 多选（Shift+点击 或 checkbox）→ 顶部出现 Action Bar [对比] [导出] [取消]。

#### 10.4 涉及 API

```
GET /api/v1/favorites?account_id=&platform=&q=&sort=&page=&page_size=
    → { items: [FavoriteItemOut], total, has_more }
GET /api/v1/favorites/compare?ids=1,2,3  → 对比视图数据
GET /api/v1/favorites/snapshots?account_id=&from=&to=
    → [FavoriteSnapshotOut]
```

#### 10.5 异常状态

**Loading**：首次加载显示 6 个骨架卡 + 顶部 Progress。
**Empty**：
```
┌────────────────────────────────────┐
│           ⭐                        │
│   收藏夹还是空的                    │
│   启动一次养号任务来抓取收藏         │
│   [去新建养号 →]                    │
└────────────────────────────────────┘
```
**Error**：Snackbar + 卡片位置错误占位。

#### 10.6 Material 3 组件映射

| 元素 | M3 组件 | Element Plus |
|---|---|---|
| 卡片 | Card (Elevated) | `el-card` |
| 网格 | Grid List | CSS Grid + `el-row` |
| 懒加载 | — | `el-scrollbar` + IntersectionObserver |
| 详情 | Bottom Sheet | `el-drawer direction="btt"` |
| 图片 | — | `<img loading="lazy">` |

---

## 块 4 · 管理台配置

### 11. ⚙️ 平台配置 `/platform-configs`

> 路由：`/platform-configs`
> 角色：admin
> 用途：查看 8 个平台的元数据、启用/禁用、查看适配器健康度

#### 11.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 平台配置                                           │
│ Body Small: 8 个平台 · 1 已实现 · 7 规划中                          │
│                                                                    │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ 平台          │ 显示名  │ 状态      │ 账号数 │ 适配器版本  │⚙│  │
│ ├───────────────┼─────────┼───────────┼────────┼────────────┼─┤  │
│ │ 🔴 小红书      │ xhs     │ ✓ 已实现   │  12    │ v0.2.0     │⋯│  │
│ │ 🧣 微博        │ weibo   │ ⏳ 规划中  │  6     │ v0.3.0     │⋯│  │
│ │ 🎵 抖音        │ douyin  │ ⏳ 规划中  │  3     │ v0.3.0     │⋯│  │
│ │ 💡 知乎        │ zhihu   │ ⏳ 规划中  │  1     │ v0.3.0     │⋯│  │
│ │ 🐦 Twitter     │ twitter │ ⏳ 规划中  │  1     │ v0.3.0     │⋯│  │
│ │ 📺 B 站        │ bilibili│ ⏳ 规划中  │  1     │ v0.3.0     │⋯│  │
│ │ 🎙️ 小宇宙      │ xiaoyuzhou│ ⏳ 规划中│  0    │ v0.3.0     │⋯│  │
│ │ 📰 公众号      │ wechat-official│ ⏳ 规划中│  0 │ v0.3.0     │⋯│  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ ┌─ 单平台详情 (展开 #1 小红书) ──────────────────────────────────┐  │
│ │ 适配器:  app.services.platforms.xhs_web.XhsWebAdapter         │  │
│ │ 实现方法: check_login / browse_home / like_post /              │  │
│ │          favorite_post / fetch_favorites                       │  │
│ │ 浏览器:  Chrome 124+ (CDP 协议)                                │  │
│ │ 反检测:  stealth.min.js + human-like 延迟                      │  │
│ │ 最近一次健康检查: 5 分钟前 ✓                                   │  │
│ │ 最近一次养号: T-3401 · 18 分钟前 · ✓ 成功                      │  │
│ │ [查看文档] [测试适配器]                                        │  │
│ └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

#### 11.2 字段说明表

| 字段 | 类型 | 来源 |
|---|---|---|
| `platform.id` | enum | PlatformType |
| `platform.display_name` | str | adapter.display_name |
| `platform.icon` | str | adapter.icon (emoji) |
| `platform.status` | enum | `implemented` / `stub` |
| `account_count` | int | COUNT(platform_accounts) |
| `adapter_version` | str | adapter.__version__ |
| `last_health_check_at` | datetime | — |
| `last_nurture_at` | datetime | — |

#### 11.3 交互行为

- 行点击 → 展开/折叠详情。
- ⋯ 菜单：[测试适配器] / [查看代码] / [禁用平台]（v0.3）。
- [测试适配器] → 弹 Dialog 显示 6 个方法的健康度（每个方法独立测试）。
- 平台状态用 Status Badge 配色：已实现=Success、规划中=Info、禁用=Warn。

#### 11.4 涉及 API

```
GET   /api/v1/platforms                    → [PlatformMetaOut]
GET   /api/v1/platforms/{id}/health        → { check_login, browse_home, like_post, favorite_post, fetch_favorites }
POST  /api/v1/platforms/{id}/test-method   → 单方法测试
```

#### 11.5 异常状态

**Loading**：表格骨架。
**Empty**：不会出现（始终有 8 个平台）。
**Error**：Snackbar。

#### 11.6 Material 3 组件映射

| 元素 | M3 组件 | Element Plus |
|---|---|---|
| 表格 | Data Table | `el-table` |
| 展开行 | Expandable Row | `el-table type="expand"` |
| 状态徽章 | Status Badge | `el-tag` |

---

### 12. 🔔 通知中心 `/notifications`

> 路由：`/notifications`
> 角色：admin
> 用途：聚合系统通知（登录态异常、养号失败、配额将满）

#### 12.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 通知中心       [全部已读] [⚙ 通知设置]            │
│ Body Small: 8 条未读 · 共 142 条                                   │
│                                                                    │
│ [全部] [未读 8] [严重] [警告]                                      │
│                                                                    │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ ❗ [严重] #18 夜猫号 登录已过期 1 小时                          │  │
│ │   🔴xhs  ·  5 分钟前  ·  [→ 去查看]              [○未读]     │  │
│ ├──────────────────────────────────────────────────────────────┤  │
│ │ ❗ [严重] 养号任务 T-3398 失败                                  │  │
│ │   原因: Chrome 连接超时  ·  1 小时前  ·  [→ 去查看]  [○未读] │  │
│ ├──────────────────────────────────────────────────────────────┤  │
│ │ ⚠ [警告] 配额将满：#13 今日已用 3h 45m / 4h                    │  │
│ │   🔴xhs  ·  2 小时前  ·  [→ 去查看]                [○未读]   │  │
│ ├──────────────────────────────────────────────────────────────┤  │
│ │ ℹ [提示] 收藏夹快照 #T-3400 已保存 156 条                      │  │
│ │   🔴xhs  ·  3 小时前  ·  [→ 去查看]                [○已读]   │  │
│ │ ...                                                          │  │
│ └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

#### 12.2 字段说明表

| 字段 | 类型 | 枚举 |
|---|---|---|
| `id` | int | — |
| `severity` | enum | critical / warning / info |
| `title` | str | 短描述 |
| `body` | str | 详情 |
| `related_entity_type` | enum | account / task / snapshot / config |
| `related_entity_id` | int | — |
| `created_at` | datetime | — |
| `read_at` | datetime \| null | — |
| `is_read` | bool | — |

#### 12.3 交互行为

- 点击通知行 → 标记已读 + 跳到关联实体。
- Tab 切换：[全部] / [未读] / [严重] / [警告]。
- [全部已读] → 批量更新所有未读。
- 顶部铃铛角标（NavBar 通知入口）显示未读数。
- 浏览器原生通知（Notification API，需用户授权）。

#### 12.4 涉及 API

```
GET    /api/v1/notifications?severity=&is_read=&page=&page_size=
PATCH  /api/v1/notifications/{id}/read
POST   /api/v1/notifications/read-all
GET    /api/v1/notifications/unread-count
```

#### 12.5 异常状态

**Loading**：通知卡骨架。
**Empty**（无通知）：
```
┌────────────────────────────────────┐
│           🔔                        │
│   暂无通知                          │
└────────────────────────────────────┘
```
**Error**：Snackbar。

#### 12.6 Material 3 组件映射

| 元素 | M3 组件 | Element Plus |
|---|---|---|
| Tab | Primary Tab | `el-tabs` |
| 通知卡 | List Item | `el-card` + 列表布局 |
| 严重度图标 | — | Material Symbols |

---

### 13. 📊 操作日志 `/audit-logs`

> 路由：`/audit-logs`
> 角色：admin
> 用途：审计所有 admin 操作（CRUD、配置修改）

#### 13.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 操作日志                       [📥 导出 CSV]       │
│                                                                    │
│ [日期范围📅 近 7 天]  [操作员▼ 全部]  [动作类型▼ 全部]  [🔍 搜索] │
│                                                                    │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ 时间                │ 操作员 │ 动作    │ 目标       │ IP    │  │
│ ├─────────────────────┼────────┼─────────┼────────────┼───────┤  │
│ │ 2026-08-16 14:32:01 │ admin  │ 新建账号│ 账号 #24   │ ::1   │  │
│ │ 2026-08-16 14:30:00 │ admin  │ 更新配额│ 账号 #12   │ ::1   │  │
│ │ 2026-08-16 14:25:00 │ admin  │ 启动养号│ 任务 T-3400│ ::1   │  │
│ │ 2026-08-16 14:00:00 │ admin  │ 修改风控│ silent_hour│ ::1   │  │
│ │ 2026-08-16 13:50:00 │ admin  │ 登录   │ -          │ ::1   │  │
│ │ ...                                                          │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ 共 1,234 条  [<] 1 2 3 ... 62 [>]   每页 [20▼]                    │
└────────────────────────────────────────────────────────────────────┘
```

#### 13.2 字段说明表

| 字段 | 类型 | 枚举 |
|---|---|---|
| `id` | int | — |
| `created_at` | datetime | — |
| `operator` | str | username |
| `action` | enum | create_account / update_account / delete_account / start_nurture / cancel_nurture / update_config / login / logout / ... |
| `entity_type` | str | account / task / config / user |
| `entity_id` | int | — |
| `changes` | json | 变更前 → 变更后 |
| `ip` | str | — |
| `user_agent` | str | — |

#### 13.3 交互行为

- 点击行 → 弹 Side Sheet 显示完整 `changes`（diff 视图）。
- [📥 导出 CSV] 导出当前筛选结果。
- 动作类型多选筛选（v0.2 简化为下拉单选）。
- 排序：时间↓/↑。
- 只读，不可编辑/删除（合规要求）。

#### 13.4 涉及 API

```
GET  /api/v1/audit-logs?from=&to=&operator=&action=&q=&page=&page_size=
GET  /api/v1/audit-logs/{id}              → 含完整 changes
GET  /api/v1/audit-logs/export?from=&to=  → CSV
```

#### 13.5 异常状态

**Loading**：表格骨架。
**Empty**：
```
┌────────────────────────────────────┐
│           📊                        │
│   没有符合条件的日志                │
└────────────────────────────────────┘
```
**Error**：Snackbar。

#### 13.6 Material 3 组件映射

| 元素 | M3 组件 | Element Plus |
|---|---|---|
| 表格 | Data Table | `el-table` |
| 详情 | Side Sheet | `el-drawer direction="rtl"` |
| 导出 | Tonal Button | `el-button plain` |

---

### 14. 👥 操作员管理 `/operators`

> 路由：`/operators`
> 角色：admin
> 用途：CRUD 操作员账号（v0.2 简化为单 admin，v0.3 引入多用户）

#### 14.1 视觉布局

```
┌────────────────────────────────────────────────────────────────────┐
│ Headline Medium: 操作员管理        🚧 v0.2 仅 admin 账号           │
│                                                                    │
│ ┌──────────────────────────────────────────────────────────────┐  │
│ │ 名称    │ 状态      │ 角色    │ 最后登录         │ 操作      │  │
│ ├─────────┼───────────┼─────────┼──────────────────┼──────────┤  │
│ │ admin   │ ● 在岗    │ Admin   │ 2026-08-16 09:00 │ [改密码] │  │
│ └──────────────────────────────────────────────────────────────┘  │
│                                                                    │
│ v0.3 规划：                                                        │
│ - 邀请新操作员（邮箱）                                              │
│ - 角色：Admin / Operator / Viewer                                  │
│ - 操作员活跃度报表                                                  │
└────────────────────────────────────────────────────────────────────┘
```

#### 14.2 ~ 14.6 占位

> v0.2 仅展示当前 admin 账号。CRUD 在 v0.3 落地。
> 字段、交互、API、异常状态、组件映射见 v0.3 spec。

---

## 附录 A · API 端点汇总（v0.2 全量）

```
# —— 账号 ——
GET    /api/v1/accounts
POST   /api/v1/accounts
GET    /api/v1/accounts/{id}
PATCH  /api/v1/accounts/{id}
DELETE /api/v1/accounts/{id}
POST   /api/v1/accounts/{id}/check-login
POST   /api/v1/accounts/{id}/login
POST   /api/v1/accounts/check-all
GET    /api/v1/accounts/summary
GET    /api/v1/accounts/activity-trend
GET    /api/v1/accounts/distribution
GET    /api/v1/accounts/recent-abnormal
GET    /api/v1/accounts/activity/kpi
GET    /api/v1/accounts/activity/heatmap
GET    /api/v1/accounts/activity/actions
GET    /api/v1/accounts/activity/platforms

# —— 平台 ——
GET    /api/v1/platforms
GET    /api/v1/platforms/{id}/health
POST   /api/v1/platforms/{id}/test-method

# —— 养号任务 ——
POST   /api/v1/nurture
GET    /api/v1/nurture/running
GET    /api/v1/nurture/history
GET    /api/v1/nurture/{task_id}
POST   /api/v1/nurture/{task_id}/cancel
POST   /api/v1/nurture/{task_id}/rerun
DELETE /api/v1/nurture/{task_id}
GET    /api/v1/nurture/{task_id}/logs
GET    /api/v1/nurture/export

# —— 动作集 ——
GET    /api/v1/action-sets
POST   /api/v1/action-sets
PATCH  /api/v1/action-sets/{id}
DELETE /api/v1/action-sets/{id}

# —— 收藏夹 ——
GET    /api/v1/favorites
GET    /api/v1/favorites/compare
GET    /api/v1/favorites/snapshots

# —— 风控配置 ——
GET    /api/v1/risk-config
PUT    /api/v1/risk-config
POST   /api/v1/risk-config/reload

# —— 通知 ——
GET    /api/v1/notifications
PATCH  /api/v1/notifications/{id}/read
POST   /api/v1/notifications/read-all
GET    /api/v1/notifications/unread-count

# —— 操作日志 ——
GET    /api/v1/audit-logs
GET    /api/v1/audit-logs/{id}
GET    /api/v1/audit-logs/export

# —— 操作员（v0.2 仅 admin）——
GET    /api/v1/operators/me
PATCH  /api/v1/operators/me/password

# —— 任务通用 ——
GET    /api/v1/tasks/{task_id}
```

---

## 附录 B · 顶部 Tab（平台切换）

> 全局平台 Tab，位于 AppBar 下方、高度 48dp。点击切换后，**当前页面 query 追加 `?platform=xxx`**。

```
[🔴小红书] [🧣微博] [🎵抖音] [💡知乎] [🐦Twitter] [📺B站] [🎙️小宇宙] [📰公众号]
```

| 状态 | 视觉 |
|---|---|
| 默认未选中 | Title Small (14/600) + On Surface Variant |
| Hover | 背景 Surface Variant |
| 选中 | 文字 Primary + 底部 3dp Primary 指示器 |
| 已实现（仅 xhs） | 图标可点击 + 实心 |
| 规划中（其他 7 个） | 图标半透明 + Tooltip "v0.3 规划中" |

> 跨页面保持选中态：URL `?platform=` 参数 → Pinia store `usePlatformStore`。

---

## 附录 C · 设计资源链接

- Material 3 概览：https://m3.material.io/
- Material 3 Color：https://m3.material.io/styles/color/the-color-system/key-colors-tones
- Material 3 Type Scale：https://m3.material.io/styles/typography/type-scale-tokens
- Material 3 Elevation：https://m3.material.io/styles/elevation/elevation-tokens
- Material 3 Shape：https://m3.material.io/styles/shape/shape-scale-tokens
- Material 3 States：https://m3.material.io/styles/interaction/state-layer-tokens
- Material 3 Accessibility：https://m3.material.io/foundations/accessible-design/accessibility-basics
- Material Symbols：https://fonts.google.com/icons
- Element Plus：https://element-plus.org/zh-CN/component/overview.html
- ECharts：https://echarts.apache.org/zh/index.html

---

> **维护说明**：本规范是 v0.2 UI 实现的"合同"。任何字段、API、交互调整必须先更新本文档，再写代码。
> v0.3 计划新增页面（动作编辑器、收藏对比视图）将在 `docs/06-pages-ui-spec.md` 同文件追加。
