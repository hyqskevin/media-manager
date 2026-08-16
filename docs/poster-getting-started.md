# 海报生成上手文档

> 第一次使用本系统生成一张小红书 / 活动海报，请按本文件 6 步走。
> 关联: docs/superpowers/specs/2026-07-21-poster-generation-design.md

## 0. 前置

| 依赖 | 是否必须 | 检查 |
|---|---|---|
| 后端 dev API | ✅ | `make dev-api` |
| 前端 dev | ✅ | `cd frontend && npm run dev` |
| **MINIMAX_API_KEY** 环境变量 | ✅（若要走 AI 识别） | `echo $MINIMAX_API_KEY`，值为空则只能用"手动编辑 HTML" |
| **opencli** | 渲染 PNG 用，可选 | `which opencli` |
| Playwright（chromium） | 渲染 PNG 用，可选 | 内部默认依赖；未装时**走 opencli fallback** |

## 1. 设置 MINIMAX_API_KEY（如果不靠 AI 上传，**跳过**）

```bash
# 在 .env 或 shell：
export MINIMAX_API_KEY=your-key-here

# 也可直接写进 backend/.env：
echo 'MINIMAX_API_KEY=your-key-here' >> backend/.env
```

`app/core/config.py` 启动时校验，若 `parse-from-image` 报错 503 即 key 没配。

## 2. 登录管理端

浏览器打开 `http://127.0.0.1:5173/`，用 admin 账号登录（账号：admin、密码：Admin@123、若用 0012_seed_admin migration 初始化过）。

## 3. 配置中心 → 海报模板

路径：左侧导航 **配置中心** → 子 tab **海报模板** → **新增海报模板**。

### 3.1 方式 A：**上传一张参考海报，AI 解析**

1. 准备一张小红书 / 活动海报图（PNG / JPG ≤ 6MiB）；
2. 点 **AI 识别上传海报** 按钮，提交图片；
3. 后端调 MiniMax vision，返回草稿 HTML + parsed_meta；
4. 你在弹窗里**调整** HTML（占位符 `{{title}}`、`{{items}}` 必保留）；
5. 点保存。

> ⚠️ 若 `MINIMAX_API_KEY` 未配，返回 503 + "请设置 MINIMAX_API_KEY 或手动编写 HTML"。前端降级到方式 B。

### 3.2 方式 B：手动编写 HTML

弹窗里直接填：
- **名称**：必填；
- **HTML 模板**：必填，**必须含 `{{title}}` 和 `{{items}}` 两个占位符**；
- **CSS**（可选）：写 `.poster { background: #F26B2C; ... }` 样式。

可参考 spec §3.2 里的"橙橙周末合集"。

示例最小模板：
```html
<div class="poster">
  <h1 class="title">{{title}}</h1>
  <div class="items">{{items}}</div>
</div>
```
```css
.poster { background: #F26B2C; color: #fff; padding: 60px; font-family: sans-serif; }
.title { font-size: 64px; font-weight: 800; }
.items { margin-top: 30px; }
```

## 4. 海报制作 → 新建海报

路径：左侧导航 **海报制作** → **新建海报**。

**wizard 6 步**：

| 步 | 动作 | 入参 |
|---|---|---|
| 1 | 选范围（推文 / 活动） | 推文搜索 + 多选 |
| 2 | 选模板 | 单选刚才保存的模板 |
| 3 | 填字段 | 每条 item 一行 time_range / location / fee |
| 4 | 人工编辑 HTML | textarea 手改（可选） |
| 5 | 选原推文展示图 | **从 `/api/v1/posters/note-images/{note_id}` 拉的原推文图列表中单选**（一活动一张图） |
| 6 | 预览 + 生成 | 点"渲染为 PNG" |

预览阶段：iframe 加载 `GET /api/v1/poster-tasks/{id}/preview` 返回的 HTML。

## 5. 渲染为 PNG

点 **渲染为 PNG** → 后端 POST `/api/v1/poster-tasks/{id}/render`：

```
Playwright 优先（chromium headless）：
  page.set_content(html, wait_until="networkidle")
  page.screenshot(path=..., full_page=True)
  → 写到 data/posters/{id}.png
  
失败 fallback opencli（需要 opencli + http server）：
  python -m http.server 启动临时 http server
  opencli browser open http://127.0.0.1:N/_tmp.html
  opencli browser screenshot --output data/posters/{id}.png --full-page
```

产物可在 **海报列表 → 选中任务 → 下载** 拿到 PNG。

## 6. 海报列表

路径：左侧导航 **海报制作** → **海报列表**。

每行 = 任务名 / 模板名（join）/ item 数量 / 状态 (`draft` / `rendered` / `failed` / `archived`) / 操作。

操作：
- 查看（回到 wizard 第 6 步预览）
- 下载（`GET /api/v1/poster-tasks/{id}/download`）
- 删除（同步删除 PNG 文件）

## 7. 已知行为

- 单张图片 push 进 HTML：当前是 `image_url` 作为 `<img src>` 直接渲染。如果原图大、未设 max-width，可能溢出。建议模板里 `.row-image { max-width: 240px; }` 控宽。
- 模板 **不支持** JavaScript（XSS 防护），只能静态 HTML + CSS。
- 模板 **不支持**外部 `<script>`。
- 模板字体跨平台：默认 `PingFang SC` / `Noto Sans CJK SC` 兜底。

## 8. 常见错误

| HTTP | 原因 | 解决 |
|---|---|---|
| 401 | 未登录 / token 过期 | 重新登录 |
| 422 创建任务 | 模板不存在 | 重选模板 |
| 503 parse-from-image | `MINIMAX_API_KEY` 未配或 vision 模型不可用 | 设 env 或手动写 HTML |
| 503 render | playwright + opencli 都不可用 | 装 Playwright 或 opencli 任一个 |

## 9. CI / dev 测试

```bash
# 后端单元
cd backend && .venv/bin/pytest

# 后端 API 回放（需 dev API 起来）
make dev-api &
bash tests/scripts/test_poster_generation.sh

# 实际渲染（仅 dev，已写脚本占位，见 tests/poster-generation-CHANGELOG.md §3.2）
# bash tests/scripts/test_poster_real_render.sh
```
