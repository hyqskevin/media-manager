# reference/

本目录存放**外部参考仓库的本地 clone**，仅供开发期查阅，**不入库**（`.gitignore` 已排除 `reference/*/`，仅跟踪 markdown 笔记）。

## 目录

- **`PostFlow/`** — [9k+ stars](https://github.com/yyyyaaaao/PostFlow) 视频上传工具，**核心反检测参考**：Patchright + stealth.min.js
- **`social-auto-upload/`** — 9k+ stars 主流视频上传方案（Chromium args + Playwright）
- **`socialcli/`** — 13 平台 Plugin 架构 + browser-cookie3 注入
- **`automie/`** — 插件架构 + Gemini AI
- **`xhs-info-crawl/`** — 本仓库继承自此工程（小红书抓取 + opencli 浏览器自动化），作为业务模型与 API 设计参考

## 反检测笔记

详见 `reference/anti-detection-notes.md`（**唯一入库的 reference 文件**），提炼自 PostFlow 的 stealth.min.js + patchright 模式，作为 v0.2 养号 Web 通道的反检测配方。