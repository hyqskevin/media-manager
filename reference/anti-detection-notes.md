# 浏览器自动化反检测技术参考

> 提取自 `reference/` 下 4 个主流开源项目，作为 media-manager v0.2 反检测方案的参考。
> 核心目标：让 Patchright/Playwright 驱动的浏览器在 Web 端养号场景下被识别为"正常人"。

## 1. 参考项目概览

| 项目 | 路径 | 核心反检测做法 | 关键模块 |
| --- | --- | --- | --- |
| **PostFlow** | `reference/PostFlow/` | **Patchright + stealth.min.js** 注入 | `utils/stealth.min.js`、`utils/base_social_media.py::set_init_script`、`uploader/douyin_uploader/main.py::cookie_auth` |
| **social-auto-upload** | `reference/social-auto-upload/` | 仅靠 Chromium args + Playwright | `utils/browser_hook.py` |
| **socialcli** | `reference/socialcli/` | `browser-cookie3` 抽取本地浏览器 cookie 优先；Playwright fallback | `platforms/base.py::login_with_browser_cookies` |
| **automie** | `reference/automie/` | 单例 Playwright + storage_state | `core/engine.py::get_context` |

> **结论**：4 个项目里只有 PostFlow 做到了对得上一线风控的"实战级"反检测。
> 其它三个要么靠浏览器 cookie 注入（socialcli）来绕过登录态校验，要么用最小 Chromium 配置（social-auto-upload / automie）。
> v0.2 我们直接照搬 PostFlow 的做法。

## 2. 反检测三件套（v0.2 必装）

### 2.1 Patchright（核心）

- **定位**：Playwright 的反检测 fork，移除 `navigator.webdriver`、`CDC_*` 等 Playwright 注入的特征变量。
- **用法**：直接 `pip install patchright`，`import patchright.async_api as pw`。
- **验证**：打开 `https://bot.sannysoft.com/` 或 `https://abrahamjuliot.github.io/creepjs/`，`navigator.webdriver` 必须为 `undefined`。
- **参考**：`reference/PostFlow/uploader/douyin_uploader/main.py` 里 `from patchright.async_api import async_playwright`。

> **不要用 Playwright 官方包**。Playwright 1.40+ 已经把 `navigator.webdriver` 改成 `true`，风控立马识别。
> Patchright 是社区维护的反检测 fork，截至 2025 仍持续更新。

### 2.2 stealth.min.js（必须的 8 项 JS 层 mock）

- **来源**：`puppeteer-extra` 的 `extract-stealth-evasions` 自动生成（MIT）。
- **文件**：`reference/PostFlow/utils/stealth.min.js`（直接 copy 过来用，约 50KB）。
- **注入方式**：每个 BrowserContext 通过 `context.add_init_script(path=stealth_js_path)` 注入。
  - **必须在 `new_context()` 之后立刻调用**，否则来不及生效。
  - **每个 context 一次即可**，因为 `add_init_script` 会作用于所有 page。
- **参考实现**：`reference/PostFlow/utils/base_social_media.py`：
  ```python
  async def set_init_script(context):
      stealth_js_path = Path(BASE_DIR / "utils/stealth.min.js")
      await context.add_init_script(path=stealth_js_path)
      return context
  ```

#### 8 项核心 evasion（stealth.min.js 涵盖）

| # | 模块 | 被风控探测点 | 修复方式 |
| --- | --- | --- | --- |
| 1 | `chrome.app` | `window.chrome.app` 缺失 | 完整 mock（含 isInstalled / getDetails） |
| 2 | `chrome.csi` | 性能指标异常 | 返回合法 timing 数据 |
| 3 | `chrome.loadTimes` | 协议信息异常 | mock h2/hq/NPN/ALPN |
| 4 | `chrome.runtime` | 扩展 ID 探测 | 完整 mock + sendMessage/connect 抛错 |
| 5 | `HTMLMediaElement.canPlayType` | codec 列表异常 | 补回 `avc1.42E01E`、`audio/x-m4a` 等 |
| 6 | `navigator.hardwareConcurrency` | CPU 核数异常 | 固定为 4（可配置） |
| 7 | `navigator.languages` | 语言列表异常 | 固定 `['zh-CN', 'zh']` |
| 8 | `navigator.plugins` + `mimeTypes` | 插件表为空 | 注入 Chrome PDF / Native Client 等真实插件 |
| 9 | `navigator.webdriver` | 必为 `true` | 直接 `delete Object.getPrototypeOf(navigator).webdriver` |
| 10 | `WebGLRenderingContext.getParameter` | SwiftShader 字样暴露 headless | 改写 UNMASKED_VENDOR_WEBGL / UNMASKED_RENDERER_WEBGL |
| 11 | `window.outerWidth/outerHeight` | headless 为 0 | 用 `innerWidth + 85` 模拟 |
| 12 | iframe `contentWindow` proxy | `iframe.contentWindow.self === window.top` 检测失败 | Proxy 拦截 iframe 创建 |

> **必须 12 项全部覆盖**。少一项都会被 CreepJS / bot.sannysoft 标红。

### 2.3 真人行为随机化（PostFlow 没做但 v0.2 必须加）

- **输入延迟**：每个字符 30-150ms 随机（不能固定 50ms）。
- **点击延迟**：点击前先 `mouse.move` 到目标附近，再随机 0.5-3s 后点击。
- **滚动延迟**：进入页面后随机滚动 1-3 次，每次 200-800px，间隔 0.5-2s。
- **页面停留**：每个页面至少停留 3-8s，模拟阅读。
- **操作间隔**：连续操作之间 1-5s 随机。

> PostFlow 自动化上传没有这些，因为它是"机器操作"，而 v0.2 是"模拟真人养号"，必须加。

## 3. cookie_auth 流程模板（PostFlow 模式）

```python
# reference/PostFlow/uploader/douyin_uploader/main.py
async def cookie_auth(account_file: str) -> bool:
    """
    验证 cookie 是否有效（对应 media-manager 的 Account.check_login）。
    核心：launch → new_context(storage_state) → set_init_script → new_page → 访问落地页 → 判登录文案。
    """
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True,
            channel="chrome",  # 用系统 Chrome，UA/字体/插件一致
        )
        try:
            context = await browser.new_context(storage_state=account_file)
            context = await set_init_script(context)  # ← 关键：注入 stealth
            page = await context.new_page()
            await page.goto("https://creator.douyin.com/creator-micro/content/upload")
            try:
                await page.wait_for_url("...upload", timeout=5000)
            except Exception:
                return False

            # 通过探测登录文案来判断是否掉登录
            if await page.get_by_text("手机号登录").count() \
               or await page.get_by_text("扫码登录").count():
                return False
            return True
        finally:
            await browser.close()
```

**v0.2 落地要点**：
1. `account_file` 用 Playwright 的 `storage_state`（包含 cookies + localStorage），不是单纯 cookie dict。
2. `set_init_script` 必须在 `new_context` 之后、`new_page` 之前调用。
3. `headless=True` + `channel="chrome"`，**必须**走系统 Chrome（macOS 自带）而非 playwright bundled chromium，否则 `chrome.app` mock 会失效。
4. 判断登录与否用"登录文案反查"而非 URL 跳转（很多平台登录后 URL 不变）。

## 4. Launch 参数（不能省）

参考 `reference/social-auto-upload/utils/browser_hook.py`，补全 v0.2 的 launch args：

```python
{
    'headless': True,
    'channel': 'chrome',          # ← 系统 Chrome
    'args': [
        '--disable-blink-features=AutomationControlled',  # 关键
        '--lang=zh-CN',
        '--disable-infobars',
        '--start-maximized',
        '--no-sandbox',
        '--disable-web-security',
    ]
}
```

> `--disable-blink-features=AutomationControlled` 必须加，否则 `navigator.webdriver` 会被 Blink 标记。

## 5. 行为守则（风控经验）

> 来自多个养号项目 + CreepJS 实战数据。

1. **一个账号一个 BrowserContext**：不要共享 cookies / fingerprint。
2. **每天每账号 ≤ 4 小时**：超过会被风控。
3. **静默时段**：凌晨 0-6 点不操作（人类睡觉），违规即风控。
4. **操作间隔**：单次操作至少 3s 间隔，复杂操作（点赞/收藏）5-15s。
5. **页面停留**：每页至少 5-15s，模拟阅读。
6. **点赞/收藏频率**：每小时 ≤ 10 次，每天 ≤ 50 次。
7. **跨账号轮换**：用完一个账号不要立刻切下一个，等 10-30 分钟。
8. **IP 一致性**：同一个账号绑定同一 IP，不要频繁切。
9. **UA 一致性**：同一个账号用同一 UA，不要每次都换。
10. **失败重试**：被风控弹窗/验证码触发后立即停止，24h 后再试。

## 6. v0.2 反检测落地清单（actionable checklist）

| 步骤 | 文件 | 操作 |
| --- | --- | --- |
| 1 | `requirements.txt` | 加 `patchright==1.55.0`、`playwright` 移除或仅保留类型 |
| 2 | `apps/worker/anti_detection/stealth.min.js` | 从 `reference/PostFlow/utils/stealth.min.js` copy 过来 |
| 3 | `apps/worker/anti_detection/context.py` | 新增 `async def new_stealth_context(browser, storage_state=None) -> BrowserContext` 封装 `set_init_script` + launch args |
| 4 | `apps/worker/anti_detection/human.py` | 新增 `human_type` / `human_click` / `random_scroll` / `human_pause` 4 个工具函数 |
| 5 | `apps/worker/anti_detection/policy.py` | 新增守则常量（MAX_HOURS_PER_DAY=4、SILENT_HOURS=(0,6)、MAX_LIKES_PER_HOUR=10 等） |
| 6 | `apps/worker/channels/chrome.py` | 复用现有 ChromePool，注入 stealth + human 工具 |
| 7 | `apps/worker/adapters/xhs_web.py` | 在 `check_login` / `browse_home` / `like_note` / `favorite_note` 全程使用 human 工具 |

## 7. 验证清单（开发期自查）

每个 PR 必须跑：

1. `bot.sannysoft.com` → 全绿（无红色 ❌）
2. `creepjs` → `navigator.webdriver=undefined`、fingerprint 稳定
3. `https://www.xiaohongshu.com/` 真实访问 → 不弹验证码
4. `https://creator.xiaohongshu.com/` 登录态正常
5. 收藏夹页面能解析出笔记列表（前端 AccountsView 能看到 snapshot）

## 8. 反检测局限（必须告知用户）

- **100% 绕过不可能**：风控持续升级，CreepJS 等检测工具也在更新。
- **养号 ≠ 必成功**：只能说降低被识别概率，长期仍需真人行为配合。
- **App 通道更强**：v1+ 上 App 通道（手机端模拟）会比 Web 通道难被识别一个量级。本期暂不做。
- **平台间差异大**：小红书、抖音风控最严；B 站、微博相对宽松。

## 9. 一句话总结

> **Patchright + stealth.min.js + 真人随机延迟 + 行为守则 = v0.2 反检测的完整配方。**
> 缺一不可。代码路径直接照抄 PostFlow，但行为随机化要自己加，因为 PostFlow 是"机器发视频"，我们是"养号"。