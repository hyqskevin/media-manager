# CHANGELOG

## [Unreleased] — 2026-08-16

### Added: v0 范围声明（精简版）

继承基线已就位（v0.1 完整继承 xhs-info-crawl + 上级 Operate 设计），
本次新增 **v0 精简范围声明**：

- v0 只落地三块：**平台账号管理 + 自动养号 + 收藏夹**
- v0 不做：工作流 / 多平台发布 / 数据中心 / 素材库 / 内容日历 / 规则引擎
- v0 复用 xhs-info-crawl 的 opencli + chrome_pool，**不**自研 Chrome 扩展
- 8 平台支持矩阵：xhs / weibo / douyin / zhihu / twitter / bilibili / xiaoyuzhou / weixin

新增文档（避免与 xhs 继承基线同名冲突，加 `-v0` 后缀）：
- [docs/SPEC-v0.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/SPEC-v0.md)
- [docs/overview-v0.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/overview-v0.md)
- [docs/api-v0.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/api-v0.md)
- [docs/database-v0.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/database-v0.md)
- [docs/browser-bridge-v0.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/browser-bridge-v0.md)
- [docs/ui-v0.md](file:///Users/hanamaki_mac_mini/Documents/github/project/media-matrix/media-manager/docs/ui-v0.md)

继承基线（xhs-info-crawl 拷贝 + 上级 Operate 设计）：
- `docs/overview.md` / `docs/api.md` / `docs/database.md` / `docs/browser-bridge.md` / `docs/ui.md`
- `docs/requirements.md` / `docs/architecture.md` / `docs/business-flow.md` / `docs/crawler-design.md` /
  `docs/api-doc.md` / `docs/database-design.md` / `docs/ui-design.md` / `docs/phase-roadmap.md` /
  `docs/deployment.md` / `docs/security.md` / `docs/risks-todos.md` / `docs/acceptance.md` / `docs/appendix.md`

### v0 路线

| 阶段 | 交付 | 状态 |
|---|---|---|
| v0.1 | 仓库初始化 + 继承 xhs + v0 Spec 文档 | ✅ 当前 |
| v0.2 | media_accounts + platforms 表 + 账号 CRUD API | 计划 |
| v0.3 | chrome_pool 多账号独立端口 + 8 平台适配器 | 计划 |
| v0.4 | nurture_tasks + 浏览/点赞/收藏 + 前端触发 | 计划 |
| v0.5 | favorite_snapshots + 收藏夹入库 + 对比 UI | 计划 |
| v0.6 | nurture_schedules + Celery beat 定时 | 计划 |

---

## [v0.1] — 2026-08-15 及之前

继承自 xhs-info-crawl v0.1，含完整 xhs 爬虫功能 + 多平台浏览器自动化基建。
（详细历史见 xhs-info-crawl CHANGELOG）