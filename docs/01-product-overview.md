# 01 · 产品定位与概览（Product Overview）

> 适用版本：**media-manager v0.2**
> 撰写日期：2026-08-16
> 维护者：media-manager 需求组
> 关联 spec：[`docs/superpowers/specs/2026-08-16-v02-account-management-design.md`](superpowers/specs/2026-08-16-v02-account-management-design.md)

---

## 1. 一句话定位

**media-manager v0.2 是一个面向"媒体矩阵"运营场景的多平台账号管理与自动化养号中台。**

它把 xhs-info-crawl 中沉淀下来的"OpenCLI + Chrome 池 + 浏览器自动化"基建，升级为 **8 平台 × N 账号** 的统一抽象，并通过 Patchright + stealth + 真人行为三件套，把"养号"这一高频但高风险的运营动作，变成可配置、可观察、可回滚的流水线。

v0.2 **不是**内容生产工具、**不是**数据洞察 BI、**不是**多平台发布器；它只做一件事——**让你以"管理员"视角，可靠地把一批社交媒体账号养起来，并随时知道每只账号的健康度**。

---

## 2. 核心使用场景

| # | 场景 | 角色 | 关键动作 |
|---|------|------|----------|
| S1 | 接入新账号 | operator | 创建账号 → 二维码扫码登录 → 自动校验登录态 → 启用 |
| S2 | 单次养号 | operator | 选账号 → 选动作（浏览/点赞/收藏）→ 提交 → 看实时进度 → 查看结果 |
| S3 | 定时养号 | admin | 配 cron 表达式 → 绑定账号集 + 动作集 → 启用 → 让 beat 自动跑 |
| S4 | 收藏夹抓取 | operator / admin | 养号结束自动触发 / 手动触发 → 写入 favorite_snapshots → 对比历史 |
| S5 | 健康巡检 | admin | 看账号活跃度 / 登录态 / 风控状态 → 处理掉线、被风控的账号 |
| S6 | 审计追溯 | admin | 看操作员登录、操作日志、养号结果 → 定位异常 |

所有场景都围绕"养"和"看"两个动词：**养**账号、**看**结果。**生产内容**和**发布内容**不在 v0.2 范畴内。

---

## 3. 用户角色与权限矩阵

v0.2 沿用 v0.1 的三角色模型（`user.role` 字段），按权限码（`permission.code`）控制页面可见性与 API 可调用性。

| 角色 | code | 典型职责 | 能做的事 | 不能做的事 |
|------|------|----------|----------|------------|
| **admin** 超管 | `role.admin` | 平台配置、账号管理、定时任务、操作员管理 | 全部功能 | — |
| **operator** 运营 | `role.operator` | 日常养号、查看收藏夹 | 单次养号、查看账号状态、查看自己的任务历史、收藏夹抓取 | 创建/删除账号、配 cron、配置平台、增删操作员 |
| **viewer** 只读 | `role.viewer` | 看 dashboard / 进度 | 查看所有只读页面（账号总览 / 活跃度 / 收藏夹） | 任何写操作、任何启动/触发动作 |

> 权限码注册在 `permissions` 表；具体页面/按钮是否可见由前端 `navPermissions.ts` 中的 `TopItem.topLevelPermission` / `SubItem.permission` 控制；后端 API 通过 `Depends(require_permission("..."))` 二次校验。

---

## 4. 核心能力矩阵

下表把 v0.2 的能力按"业务域"切分，每个能力关联到具体页面 / API / 数据表。

| 能力域 | 关键能力 | 前端页面 | 后端 API | 核心表 |
|--------|----------|----------|----------|--------|
| **账号总览** | 全平台账号健康度一屏看 | `/accounts`（默认页） | `GET /api/v1/platform-accounts` | `platform_accounts` |
| **媒体账号管理** | 账号 CRUD、登录态校验、活跃度、风控 | `/accounts/list`、`/accounts/sessions`、`/accounts/activity`、`/accounts/risk` | `GET/POST/PUT/DELETE /api/v1/platform-accounts`、`POST .../check-login` | `platform_accounts`、`risk_events` |
| **养号任务** | 单次 / 定时 / 动作集 / 我的收藏 | `/nurture/running`、`/nurture/history`、`/nurture/schedules`、`/nurture/actions`、`/nurture/favorites` | `POST .../nurture`、`GET /api/v1/nurture-tasks`、`CRUD /nurture-schedules` | `nurture_tasks`、`nurture_schedules`、`action_sets` |
| **配置管理** | 平台元数据、养号总开关、通知配置 | `/admin/platforms`、`/admin/notifications` | `GET /api/v1/platforms`、`GET/PUT /api/v1/system-settings` | `platforms`、`system_settings` |
| **权限管理** | 操作员、权限码、审计 | `/admin/operators`、`/admin/audit` | `CRUD /api/v1/users`、`GET /api/v1/audit-logs` | `users`、`permissions`、`audit_logs` |
| **反检测** | Patchright + stealth + 真人行为 | （无页面，后台生效） | `backend/app/anti_detection/` | — |

> 表中 `/accounts` 等路径为 v0.2 设计目标；当前 v0.2 实现通过 `/system-admin?tab=platform-accounts` 进入账号管理，未来按本页 IA 演进。

---

## 5. v0.2 vs v0.3 范围对比

> **关键约束**：v0.2 不是"全平台全部养号功能齐活"，而只是"账号管理体系齐活 + 小红书养号跑通 + 其他 7 平台占位"。下面这张表是产品边界**最重要**的一张表。

| 平台 | 平台元数据 | PlatformAdapter 注册 | 6 个方法实现 | 前端可选 | 养号可跑 |
|------|-----------|----------------------|--------------|----------|----------|
| 🔴 **小红书 xhs** | ✅ | ✅ `xhs_web` | ✅ 完整（check_login / browse_home / like / favorite / fetch_favorites） | ✅ | ✅ |
| 🧣 **微博 weibo** | ✅ | ✅ stub | ❌ 全部 `raise NotImplementedError` | ✅（仅占位） | ❌ |
| 🎵 **抖音 douyin** | ✅ | ✅ stub | ❌ | ✅ | ❌ |
| 💡 **知乎 zhihu** | ✅ | ✅ stub | ❌ | ✅ | ❌ |
| 🐦 **Twitter** | ✅ | ✅ stub | ❌ | ✅ | ❌ |
| 📺 **B 站 bilibili** | ✅ | ✅ stub | ❌ | ✅ | ❌ |
| 🎙️ **小宇宙 xiaoyuzhou** | ✅ | ✅ stub | ❌ | ✅ | ❌ |
| 📰 **公众号 wechat-official** | ✅ | ✅ stub | ❌ | ✅ | ❌ |

> v0.3 起，每个平台按"先 stub → 再替换为真实实现"的节奏分平台上线；本表是 roadmap 视图，不是承诺时间表。

### v0.2 的"非目标"清单

| 不在 v0.2 做 | 原因 |
|---------------|------|
| App 端通道（uiautomator2 / Appium） | v1+；v0.2 统一走 Web |
| 多平台**发布**笔记 | xhs-info-crawl 时代已有发布能力，但 media-manager 重新定位为"养号 + 监控"，**不继承发布** |
| **笔记管理** / **内容日历** / **素材库** | 同上，业务范围被裁掉 |
| **工作流 / 规则引擎** | v0 不做；先让单次养号跑稳 |
| **数据中心 / BI 报表** | v0 不做；活跃度 + 收藏夹历史已满足"看"的需求 |
| **自研 Chrome 扩展** | 复用 OpenCLI + Patchright，零自研 |
| **多租户** | 单租户假设；多租户 v1+ |

---

## 6. 与 xhs-info-crawl 的边界

media-manager v0.2 是 xhs-info-crawl 的"**减法 + 升级**"继承者：基建（OpenCLI / ChromePool / Chrome 实例隔离）全量复用，业务范围被严格收敛到"养号 + 监控"。

| 维度 | xhs-info-crawl（v0.1 继承基线） | media-manager v0.2 |
|------|-------------------------------|---------------------|
| 产品定位 | 小红书信息采集 + 多账号运营 | 多平台账号管理 + 自动化养号 |
| 平台支持 | 1 平台（小红书），多账号 | 8 平台抽象 + 1 平台完整实现 + 7 平台 stub |
| 核心能力 | 采集笔记 / 博主 / 活动 / OCR / 海报 | 账号 CRUD / 养号编排 / 收藏夹快照 |
| 浏览器自动化 | Playwright + OpenCLI | **Patchright** + OpenCLI + stealth + 真人行为 |
| 发布能力 | ✅ 有（继承自 social-auto-upload / PostFlow） | ❌ **无**（明确不继承） |
| 笔记管理 | ✅ 有（CRUD） | ❌ **无** |
| 内容日历 | ✅ 有 | ❌ **无** |
| 素材库 / 海报 | ✅ 有 | ❌ **无** |
| 数据中心 / 报表 | ✅ 有 | ❌ **无**（活跃度 + 收藏夹历史顶替） |
| 规则引擎 / 工作流 | ❌ | ❌（v0 都不做） |
| 收藏夹抓取 | 有但非主路径 | ✅ **核心能力** |
| 定时任务 | ✅ 已有 Celery beat | ✅ 沿用 + 增加平台维度 |
| 操作员 / 权限 | ✅ | ✅ 沿用 |
| 审计日志 | ✅ | ✅ 沿用 |

**一句话总结：xhs-info-crawl 是"采集 + 发布 + 管理的瑞士军刀"，media-manager v0.2 是"养号 + 监控的手术刀"——把多出来的刀片（发布 / 海报 / 内容日历）拆掉，把刀刃（养号编排 + 反检测）磨利。**

---

## 7. 关键产品原则

为了避免 scope creep，v0.2 严格遵守以下 6 条产品原则。每条原则都对应一个"如果违反就重写"的反向 case。

| # | 原则 | 反向 case（出现就违反） |
|---|------|------------------------|
| P1 | **安全第一**：默认 `nurture_global_enabled = false`，必须显式开启 | v0.2 一上线默认开养号 |
| P2 | **平台渐进**：先打透小红书，再扩其他平台 | 8 平台并行实现，质量全拉胯 |
| P3 | **可回滚**：所有配置（账号 / 开关 / 调度）都能秒级关闭 | 某个平台风控升级，无法一键停 |
| P4 | **可观察**：每个养号任务都有 task_id、进度、结果、错误 | 任务跑飞了，只能重启 |
| P5 | **可审计**：操作员所有写操作进 `audit_logs` | 误删账号，无人背锅 |
| P6 | **最小 UI**：每个页面只做一件事，不堆功能 | 单页塞 4 个 Tab + 抽屉 + 嵌套表单 |

---

## 8. 成功指标（v0.2 验收口径）

| 维度 | 指标 | 目标值 |
|------|------|--------|
| 功能 | xhs 真实养号跑通（浏览→收藏→抓取收藏夹）1 次 | 100% 流程通过 |
| 性能 | 单账号单次养号（30 min）CPU 占用峰值 | < 30%（本地 8C 机器） |
| 性能 | Celery worker 任务排队延迟 | P95 < 5s |
| 安全 | `https://bot.sannysoft.com/` 反检测测试 | 全绿（手动） |
| 安全 | stealth.min.js 体积 | > 30KB |
| 稳定 | 7 平台 stub 调用 6 个方法均抛 `NotImplementedError` | 100% 一致 |
| 体验 | 管理员创建账号 → 启动养号 → 看到收藏夹端到端 | ≤ 5 次点击 |
| 体验 | 操作员启动养号 → 看到进度 | ≤ 3 次点击 |

---

## 9. 文档导航

| 文档 | 内容 | 阅读对象 |
|------|------|----------|
| [`01-product-overview.md`](01-product-overview.md)（本文） | 定位、角色、能力矩阵、v0.2 vs v0.3、xhs 边界 | PM / 新人 / 评审 |
| [`02-information-architecture.md`](02-information-architecture.md) | Navbar / 菜单树 / 路由 / Tab 影响 | 前端 / 设计 |
| [`08-business-flows.md`](08-business-flows.md) | 7 个核心流程的时序图 | 后端 / 全栈 / 测试 |
| `docs/superpowers/specs/2026-08-16-v02-account-management-design.md` | 详细技术 spec | 后端 / 架构师 |
| `docs/superpowers/plans/2026-08-16-v02-account-management.md` | 实施计划（Task 1-12） | 全栈 / Agent |
| `reference/anti-detection-notes.md` | 反检测三件套配方 | 浏览器自动化方向 |

---

## 10. 名词表

| 名词 | 解释 |
|------|------|
| **养号（Nurture）** | 通过模拟真人浏览 / 点赞 / 收藏等行为，让社交平台账号的"活跃度评分"维持在健康区间，避免被风控降权 |
| **登录态（Login Status）** | 账号 cookie / session 的有效性；分为 `valid` / `cookie_invalid` / `banned` / `unknown` |
| **CDP 端口** | Chrome DevTools Protocol 端口；每个账号独占一个端口，由 `ChromePool` 分配，互不干扰 |
| **动作集（Action Set）** | 一组预定义的动作模板（如"浏览 30 min + 点赞 5 条 + 收藏 3 条"），可被单次养号和定时养号复用 |
| **收藏夹快照（Favorite Snapshot）** | 某时刻某账号收藏夹内容的完整 JSON 序列化，用于历史对比 |
| **总开关（Global Switch）** | `nurture_global_enabled`，系统级一键关停所有养号；不关时按单账号 `enabled` 字段决定 |
| **静默时段（Silent Hours）** | 0:00-6:00 不执行养号；由 `policy.SILENT_HOURS = (0, 6)` 定义 |
| **风控（Risk Control）** | 平台对异常账号的限制（限流 / 验证码 / 封号）；风控事件写入 `risk_events` 表 |
| **反检测三件套** | Patchright（替换 Playwright） + stealth.min.js（puppeteer-extra evasions） + 真人行为随机化（human_type / human_click / random_scroll） |
