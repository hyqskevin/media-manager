# 爬虫设计

## 爬虫工具

- **工具**：OpenCLI (`jackwener/OpenCLI`)
- **可执行文件**：默认按 worker 进程 PATH 解析；可用 `.env` 的 `OPENCLI_BIN` 配置绝对路径。**重启 celery worker/beat 时必须保证 opencli 可解析**（nvm 全局安装位于 `~/.nvm/versions/node/<版本>/bin`，nohup/非登录 shell 不带该 PATH）；任务启动时会预检，找不到直接 FAILED 并提示配置方法。
- **核心命令**：
  - `opencli xiaohongshu search --keyword "{keyword}" --limit {n}`
  - `opencli xiaohongshu note --url "{note_url}"`
  - `opencli xiaohongshu download "{note_url}" --output ./images`
- **登录态**：复用 Chrome 已登录 session，通过 CDP 连接

## 本地验证环境

### 浏览器 session 管理

opencli 自管理浏览器 session（CDP 模式连已存在浏览器，daemon+扩展模式用扩展接管），项目代码不传 `--user-data-dir`，也不引导用户在 `$HOME` 下创建独立 profile。

本地验证如需开启 CDP，仅指定调试端口与来源白名单即可，复用 Chrome 默认 profile：

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins="*"

# Linux
google-chrome \
  --remote-debugging-port=9222 \
  --remote-allow-origins="*"
```

启动后，在 Chrome 中登录小红书。

### 设置环境变量并测试

```bash
export OPENCLI_CDP_ENDPOINT="http://localhost:9222"
opencli doctor
opencli xiaohongshu search --keyword "上海 周末活动" --limit 10 -f json
```

## 抓取流程

### 登录态与 Cookie 前置检查

每次搜索、笔记详情或图片下载前必须先调用 `opencli xiaohongshu whoami -f json`。OpenCLI 通过浏览器扩展从当前 Chrome 会话中获取并复用 Cookie；应用不得读取、打印、写入日志、写入数据库或保存 Cookie 明文。

若检查返回错误码 77 / `AUTH_REQUIRED`：

1. 当前抓取任务切换为 `PAUSED`。

若 OpenCLI 返回明确的 captcha、安全验证、请完成验证或扫码验证信号，系统抛出 `VerificationRequired` 并同样进入 `PAUSED`。此时 crawler session 标签页必须保留，worker 最佳努力唤醒 Chrome，等待用户人工完成验证；不得自动填写或提交验证码。普通网络超时及无关“验证结果”不得误判。用户结束该 PAUSED 任务时关闭保留 session。
2. 停止后续搜索、详情和下载命令。
3. 管理端提示用户在当前 Chrome 登录小红书。
4. 用户登录后点击“测试连接”或“重试”，系统重新执行 `whoami`。
5. 仅当登录检查通过后才恢复爬虫流程。

### 搜索频率与周配额

关键词搜索受两层控制（`app/services/search_rate_limit.py`，关联 spec `docs/superpowers/specs/2026-07-25-crawl-rate-limit-design.md`）：

1. **任务内随机间隔**：同一任务的关键词搜索之间 sleep `SEARCH_INTERVAL_MIN`~`SEARCH_INTERVAL_MAX`（默认 10-15 秒）的随机值；任务内第一次搜索不等待。sleep 按 0.5 秒分片并检查执行栅栏，"停止抓取"0.5 秒内响应。
2. **周搜索配额**：`search_usage` 表按 ISO 周（Asia/Shanghai，`week_key` 如 `2026-W30`）全局累计 `search_recent` 调用次数（跨任务）；达到 `WEEKLY_SEARCH_LIMIT`（默认 500/周）后记录 WARNING 并跳过剩余关键词搜索，任务仍正常完成，不算失败。

配额仅约束关键词搜索，博主抓取不受限。

### 搜索筛选与滚动加载

关键词搜索不只依赖 OpenCLI adapter 的默认结果。登录检查通过后，浏览器流程必须：

1. 打开小红书搜索结果页。
2. 点击结果区右侧“筛选”。
3. 选择排序“最新”。
4. 读取当前城市的 `recent_filter`，选择“不限、一天内、一周内、半年内”中的对应原生选项；“不限”不点击时间选项。

5. 关闭筛选层或等待结果刷新。
6. 按配置多轮向下滚动，收集更多笔记卡片。
7. 若 OpenCLI 返回标准发布时间字段，则按城市配置的时间范围再次校验；浏览器原生筛选仍是主约束。

### 登录恢复

仪表盘可调用本地浏览器启动接口打开 Chrome 小红书主站。用户完成登录后，restart 接口先调用 OpenCLI `whoami`；成功才将原 `PAUSED` 任务重新入队，失败保持暂停。任务续跑不得覆盖原 `started_at`。

### 活动日期二次校验

原生时间筛选完成后，提取结果仍需经过业务窗口校验。窗口取任务首次开始日（Asia/Shanghai）至未来 60 天；明确越界活动记录日志后跳过，未知日期保留为 `NEEDS_REVIEW`。MiniMax 提示词只用于降低错误率，后端校验结果具有最终权威。

### 标题关键词硬过滤

- 每条关键词搜索结果记录触发搜索的关键词；同一 URL 的多个命中关键词合并后再去重。
- 仅当小红书笔记标题精确包含至少一个对应关键词时，才进入详情下载、OCR 和 MiniMax 提取。
- 中文按子串匹配，英文忽略大小写；只忽略标题与关键词两端空白，不做分词、同义词扩展或语义放宽。
- 标题不匹配时增加 `skipped_notes` 并写 INFO 日志，博主白名单结果不受关键词标题过滤。

滚动停止条件：达到 `XHS_SEARCH_TARGET_COUNT`；达到最大轮次；或连续 `XHS_SCROLL_STAGNANT_ROUNDS` 轮没有新增卡片。默认每轮下拉 800px、目标 50 条、最多 8 轮、连续 2 轮无新增即停止。

### 笔记详情滚动

打开笔记详情后同样执行多轮下拉，以触发正文展开、图片和延迟内容加载。详情页最多滚动 `XHS_DETAIL_SCROLL_MAX_ROUNDS` 轮；连续两轮正文、图片 URL 和互动字段没有新增时停止。每轮滚动后必须等待页面稳定，再重新读取 DOM/网络数据，不得复用滚动前的元素 ref。

```python
def run_keyword_crawl(task_id: int, city_code: str, keyword: str):
    # 1. 调用 OpenCLI 搜索
    result = opencli.run(
        "xiaohongshu", "search",
        f"--keyword", f"{city_name} {keyword}",
        f"--limit", str(SEARCH_LIMIT),
        "-f", "json"
    )
    
    # 2. 解析搜索结果
    notes = parse_search_result(result)

    # 2.1 浏览器筛选：最新 + 城市 recent_filter；多轮滚动加载到目标数量
    notes = collect_search_results_with_scroll(target=SEARCH_TARGET_COUNT)
    
    # 3. 过滤近 7 天笔记
    notes = filter_recent_notes(notes, days=7)
    
    # 4. 保存到 notes 表（待处理状态）
    save_notes(task_id, notes, city_code, keyword)
    
    # 5. 间隔 10-15 秒
    time.sleep(random.randint(10, 15))
```

## 笔记详情下载

### 城市/周任务归档

自 2026-07-25 起，阶段一本地文件统一按「城市 + ISO 周（任务开始时间，Asia/Shanghai）」归档，不再按单日目录保存：

```text
data/archive/{city_code}/{ISO 年}-W{周}/task-{task_id}/
├── source.md
├── activities.md
├── activities.xlsx
└── images/
```

- `source.md` 保存笔记标题、正文、原文链接及逐图 OCR 文字。
- `activities.md` 与 `activities.xlsx` 每一项/每一行对应一个具体活动。
- 图片保留原文件名；数据库 `note_images.storage_key` 保存相对 `data/` 的路径。
- 同一任务抓取多篇笔记时，图片文件名必须包含笔记 ID，避免冲突。
- 旧版 `data/archive/YYYY-MM-DD/task-{task_id}/` 目录不迁移；既有 `storage_key` 指向旧路径，读取不受影响，清理脚本兼容两种目录深度。

### 一篇笔记拆分多个活动

PaddleOCR 对每张图片逐字识别后，系统以 `[IMAGE n]` 标记合并标题、正文和 OCR 文本。MiniMax-M3 必须返回 `activities` 数组；每个元素包含活动名称、时间、地点、费用、类型、摘要、置信度和 `source_image_indexes`。每个具体活动独立写入 `activities`，并共同保留原始笔记 `source_url`。

缺少时间或地点的条目仍然入库并标记 `NEEDS_REVIEW`；不得把整篇合集笔记降维为一条活动。

模型日期先经过白名单格式归一化，再进入数据库转换。支持完整 ISO 8601、`M/D`、`M月D日` 等明确日期；`4/5` 会按任务当前年份补全，`2026-07-18T晚间` 等无法确定具体时刻的文本不会直接传给 `datetime.fromisoformat`，而是将时间置空并标记 `NEEDS_REVIEW`。该校验同时使用严格正则和解析器，禁止猜测“晚间”等模糊时刻。

长 OCR 文本的 M3 推理超时由 `.env` 的 `MINIMAX_TIMEOUT_SECONDS` 控制，阶段一默认 180 秒。

```python
def download_note_details(note_id: int, note_url: str):
    # 1. 调用 OpenCLI 获取笔记详情
    detail = opencli.run("xiaohongshu", "note", "--url", note_url, "-f", "json")
    
    # 2. 保存标题、正文、互动数据
    update_note(note_id, detail)
    
    # 3. 通过统一 Storage 接口保存图片
    images = opencli.run("xiaohongshu", "download", note_url, "--output", tmp_dir)
    for img_path in images:
        storage_key = storage.save(img_path)
        save_note_image(note_id, storage_key, original_url=...)
```

## 错误处理

阶段一按单篇笔记隔离处理。下载、OCR、提取各阶段的重试次数和间隔由 `.env` 的 `PIPELINE_STAGE_MAX_RETRIES`、`PIPELINE_STAGE_RETRY_DELAY_SECONDS` 控制；单篇笔记最终失败时记录 URL、错误和失败计数，清理该笔记的残缺数据后继续下一篇。认证失效仍立即暂停整个任务。任务级失败可由仪表盘“继续抓取”沿用原任务 ID 续跑，已有活动的旧笔记视为完成，残缺旧笔记先清理再重试。

任务实时记录发现、下载、OCR、提取和失败数量，并记录当前阶段与当前笔记。正常跑完但存在单篇失败时状态为 `COMPLETED_WITH_ERRORS`，不会误报为整批失败。

用户请求停止后，API 先提交 `STOP_REQUESTED`，再结束当前已登记的 OpenCLI 子进程。每条业务命令在 `Popen` 前、PID 登记后和子进程退出后分别校验 `task_id + run_token`；退出后的检查保证 stop API 结束进程产生的非零退出码不会被误判为任务失败。停止或被新执行取代时不得再继续打开、滚动、解析或下载。搜索和详情流程从尝试打开 crawler session 标签页起使用 `finally` 做最多 10 秒的最佳努力关闭，清理失败只写 WARNING。worker 确认停止后写入 `STOPPED`，当前 `run_crawl` 返回；Celery worker 进程保持运行，可继续接收下一任务。已经没有 worker 执行的 `FAILED`、`PAUSED` 任务点击结束时直接进入 `STOPPED`。`STOPPED` 可按原任务 ID继续抓取，残缺笔记由既有清理逻辑处理。

| 错误码 | 含义 | 处理策略 |
|--------|------|----------|
| 0 | 成功 | 继续 |
| 66 | 结果为空 | 记录并跳过 |
| 69 | Browser Bridge 未连接 | 检查 Chrome/CDP，重试 |
| 75 | 超时 | 重试，最多 3 次 |
| 77 | 需要认证 | 暂停任务，发送告警 |
| 78 | 配置错误 | 记录错误，人工检查 |
| 130 | 用户中断 | 记录任务中断 |

## 反爬策略

- 关键词搜索间隔：10-15 秒
- 单账号每周搜索总量不超过 500 次（可配置）
- 使用 OpenCLI 的真实浏览器行为，避免低级别 HTTP 请求
- 遇到验证码或登录失效，立即暂停并告警
- 不抓取评论、私信等敏感内容
- 搜索和详情滚动均设置最大轮次及无新增提前停止条件，禁止无限滚动
# 2026-07-20 执行权与推文去重补充

- 每次任务执行生成 `run_token`；Celery 消息、worker 原子领取和 OpenCLI PID 注册均携带该令牌。
- worker 在搜索、详情、下载、逐图 OCR、模型提取、子活动写入和归档边界校验执行权与停止状态。
- 小红书 URL 统一解析 `platform_note_id`；不同 `xsec_token`、查询参数和支持的 URL 形式映射为同一推文。
- 搜索批次内和历史数据库均按 `platform_note_id` 提前去重，数据库唯一约束仅作为并发兜底。
- 模糊候选按推文标题、正文和 OCR/子活动摘要生成，不在同一推文内部比较活动。
