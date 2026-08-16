# 需求功能设计

## 功能清单

| 模块 | 功能 | 优先级 | 说明 |
|------|------|--------|------|
| 爬虫引擎 | 关键词搜索 | P0 | 按城市+关键词搜索近一周笔记 |
| 爬虫引擎 | 博主白名单抓取 | P0 | 按博主抓取近一周笔记 |
| 爬虫引擎 | 笔记详情获取 | P0 | 标题、正文、图片、互动数据 |
| 图片处理 | 图片下载 | P0 | 阶段一保存到本地目录；阶段二保存到 MinIO |
| 图片处理 | OCR 文字识别 | P0 | PaddleOCR 提取图片中的活动信息 |
| 数据清洗 | 字段提取 | P0 | 规则 + MiniMax LLM 提取活动时间/地点/费用等 |
| 数据清洗 | 活动去重 | P0 | 城市+日期+名称相似度模糊去重 |
| 数据存储 | 笔记/活动/图片存储 | P0 | 阶段一 SQLite + 本地文件；阶段二 PostgreSQL + MinIO |
| 任务调度 | 每周定时抓取 | P0 | Celery Beat 每周一执行 |
| 后台管理 | 仪表盘 | P0 | 本周数据概览 |
| 后台管理 | 活动列表 | P0 | 查看、筛选、编辑、删除活动 |
| 后台管理 | 去重审核 | P0 | 人工确认/合并去重候选 |
| 后台管理 | 配置中心 | P0 | 城市、关键词、博主白名单、OpenCLI 配置 |
| 后台管理 | 任务日志 | P0 | 查看每次任务执行状态与错误 |
| 后台管理 | 周报管理 | P0 | 预览、下载、重新生成 Markdown 周报 |
| 后台管理 | 表格导出 | P0 | 审核后的活动同时导出 Excel（.xlsx）与 Markdown（.md） |
| 安全 | 频率控制 | P1 | 关键词搜索间隔 10-15 秒 |
| 安全 | 失败告警 | P1 | 任务失败发送通知 |
| 扩展 | 多数据源 | P2 | 后续可接入微博、豆瓣等 |

## EARS 需求描述

### Ubiquitous（全局约束）

- The system shall only crawl publicly visible 小红书 notes and shall not access private messages, user profiles, or comments beyond what is publicly displayed.
- The system shall store all sensitive configuration (e.g., MiniMax API key, database credentials) in environment variables or encrypted secret stores, never in source code.
- The system shall use a request interval of 10-15 seconds between consecutive keyword searches to minimize platform load and account risk.

### Event-driven（事件触发）

- When the scheduled weekly crawl task starts at Monday 02:00, the system shall execute keyword searches for all configured cities and keywords, then download notes and images.
- When a note is successfully downloaded, the system shall trigger the OCR + field extraction pipeline within 5 minutes.
- When an activity record is created or updated, the system shall recalculate duplicate candidates and flag high-confidence duplicates for review.
- When a user clicks "Generate Weekly Report" in the admin panel, the system shall produce Excel and Markdown files grouped by city and activity type within 30 seconds.

### Unwanted（异常处理）

- If the 小红书 login session expires (OpenCLI returns authentication error), the system shall pause the crawl task and send an alert to the administrator.
- If OCR fails on an image, the system shall mark the image as "OCR_FAILED" and continue processing other images from the same note.
- If the field extraction pipeline fails to identify a required field (e.g., event time), the system shall mark the activity as "NEEDS_REVIEW" and include it in the admin review queue.
- If a duplicate candidate confidence score is between 0.4 and 0.7, the system shall place it in the manual review queue instead of auto-merging.

### State-driven（状态行为）

- While a crawl task is running, the system shall prevent another crawl task from starting and return a "TASK_IN_PROGRESS" status.
- While a note is being processed (downloaded, OCR, extracted), its status shall be updated in real-time and visible in the task log.
- While an activity is in the "NEEDS_REVIEW" state, it shall not be included in the weekly report until reviewed and approved.

### Optional（可选功能）

- Where the platform supports it, the system may allow searching notes by published date range (last 7 days) to reduce irrelevant results.
- Where multiple Chrome profiles are available, the system may rotate profiles to distribute crawl load across accounts.
