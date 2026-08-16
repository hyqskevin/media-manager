# 小红书活动信息抓取系统 - 用户使用说明

> 本文档面向**最终用户**。如果你是开发者,请看 [INSTALL.md](INSTALL.md)。

## 1. 程序简介

本程序是一个本地运行的小红书活动信息抓取工具,能自动抓取指定城市和关键词下的小红书笔记,用 AI 识别其中的活动信息(名称、时间、地点、类型),并支持导出 Excel/Markdown 报告和生成活动海报。

所有数据保存在本机,不上传到任何服务器。

## 2. 系统要求

| 项目 | 要求 |
|---|---|
| 操作系统 | macOS 12+ 或 Windows 10+ |
| 浏览器 | Google Chrome(最新版,用于登录小红书) |
| OpenCLI | OpenCLIApp 桌面应用(程序内提供下载链接) |
| 磁盘空间 | 基础包约 200MB,OCR 增强包另需约 1GB |
| 内存 | 建议 8GB 以上 |

**不需要单独安装 Python 或 Node.js,程序已内置运行时。**

## 3. 安装步骤

### 3.1 下载

1. 打开 [Releases 页面](https://github.com/hyqskevin/xhs-info-crawl/releases)
2. 找到最新版本,下载对应平台的 zip:
   - macOS(Apple Silicon/M1/M2):`xhs-info-crawl-<version>-macos.zip`
   - Windows:`xhs-info-crawl-<version>-windows.zip`

### 3.2 解压

- **macOS**:双击 zip 解压,得到 `xhs-info-crawl.app` 和 `xhs-info-crawl` 文件夹
- **Windows**:右键 zip → 解压到当前文件夹,得到 `xhs-info-crawl` 文件夹

### 3.3 启动

- **macOS**:
  - 首次启动:右键 `xhs-info-crawl.app` → 选择"打开"→ 在弹窗中点"打开"(绕过 Gatekeeper)
  - 后续启动:直接双击 `xhs-info-crawl.app`
- **Windows**:
  - 双击 `xhs-info-crawl` 文件夹内的 `start.bat`

## 4. 首次启动流程

1. 启动器窗口出现,顶部显示程序名称和版本号
2. "服务状态"卡片显示三个服务:
   - API:初始化中(约 5-10 秒)→ 运行中(绿色圆点)
   - Worker:初始化中 → 运行中
   - Beat:初始化中 → 运行中
3. 首次启动会自动初始化数据库(约 5-10 秒),期间请勿关闭窗口
4. 三个服务都显示绿色"运行中"后,即可进行下一步

## 5. 配置 OpenCLI(必需)

OpenCLI 是程序与小红书浏览器交互的桥梁,必须配置才能抓取数据。

### 5.1 下载安装

1. 在启动器面板找到"OpenCLI 连接"卡片
2. 点"下载 OpenCLI"按钮 → 系统浏览器打开 OpenCLI 官方下载页
3. 下载并安装 OpenCLIApp 桌面应用
4. 打开 OpenCLIApp,按提示安装 Chrome 扩展

### 5.2 测试连接

1. 确保 OpenCLIApp 已打开并运行
2. 确保 Chrome 已登录小红书(https://www.xiaohongshu.com)
3. 回到启动器,点"测试连接"按钮
4. 等待 5-10 秒,显示绿色 ✓ + 版本号 = 连接成功

### 5.3 连接失败排查

| 提示 | 原因 | 解决 |
|---|---|---|
| "未安装 OpenCLI" | 没装 OpenCLIApp | 点"下载 OpenCLI"安装 |
| "OpenCLIApp 未启动" | 装了但没打开 | 打开 OpenCLIApp 应用 |
| "未装 Chrome 扩展" | OpenCLIApp 里没装扩展 | 在 OpenCLIApp 里点"安装扩展" |
| 红色 ✗ + 错误信息 | 其他错误 | 查看日志卡片中的详细信息 |

## 6. 安装 OCR 增强(可选)

OCR 增强包让程序能识别笔记图片中的文字,提高活动信息提取准确率。不安装也能用,但只处理笔记文字部分。

### 6.1 安装

1. 在启动器面板找到"OCR 增强"卡片
2. 点"下载安装 OCR"按钮
3. 进度条显示下载进度(约 200-500MB,取决于平台)
4. 进度条到 100% 后,状态变"已安装"

### 6.2 测试

1. 点"测试 OCR"按钮
2. 等待 10-30 秒(首次加载模型较慢)
3. 显示绿色 ✓ = OCR 工作正常

### 6.3 注意事项

- OCR 增强包与主程序版本独立,可分别升级
- 安装 OCR 后会自动启用(`.env` 中 `OCR_ENABLED=true`)
- 卸载方法:删除 `data/paddlex/` 目录,并在 `.env` 中设 `OCR_ENABLED=false`

## 7. 打开网页使用

1. 确保三个服务都运行中,OpenCLI 已连接
2. 点启动器底部"打开网页"按钮
3. 系统浏览器打开 `http://127.0.0.1:<port>`(端口由启动器自动选择)
4. 登录页输入:
   - 用户名:`admin`
   - 密码:见 `.env` 文件中的 `INITIAL_ADMIN_PASSWORD`,默认 `Admin@123`
5. 进入仪表盘,开始配置城市、关键词组、博主,然后发起抓取

## 8. 端口冲突处理

如果默认端口 8000 被占用,启动器会自动递增寻找可用端口(8001、8002...直到 8020)。

- 无需手动配置,启动器自动处理
- 选中的端口会写入 `.env` 并显示在启动器日志中
- 浏览器打开网页时使用的是启动器选中的端口
- 如果 8000-8020 全部被占用,启动器会提示错误,需手动在 `.env` 中配置 `API_PORT`

## 9. 退出程序

- 点启动器底部的"退出"按钮 → 所有服务停止 → 窗口关闭
- 或直接关闭启动器窗口 → 自动触发停止全部服务
- 退出后,任务管理器(macOS:活动监视器;Windows:任务管理器)中不应有残留的 python 进程

## 10. 常见问题

### 10.1 macOS Gatekeeper 拦截

**现象**:双击 .app 提示"无法打开,因为无法验证开发者"

**解决**:右键 .app → 选择"打开" → 在弹窗中点"打开"。只需首次操作,后续直接双击即可。

### 10.2 OpenCLI 一直连接失败

**排查**:
1. 确认 OpenCLIApp 应用已打开(在 Dock 或任务栏可见)
2. 确认 Chrome 已登录小红书
3. 在 OpenCLIApp 中检查 Chrome 扩展是否已安装并启用
4. 查看启动器日志卡片,寻找具体错误信息

### 10.3 OCR 安装失败

**排查**:
1. 检查网络连接(OCR 包从 GitHub Release 下载)
2. 检查磁盘空间(需约 1GB)
3. 查看启动器日志,寻找下载错误
4. 重新点"下载安装 OCR"重试

### 10.4 端口全部被占用

**现象**:启动器提示"端口 8000-8020 全部被占用"

**解决**:
1. 关闭占用端口的程序(如其他开发服务器)
2. 或手动编辑 `.env` 文件,修改 `API_PORT` 为其他可用端口(如 9000)
3. 重启程序

### 10.5 数据备份与迁移

- 所有数据在 `xhs-info-crawl/data/` 目录下
- 备份:复制整个 `data/` 目录到其他位置
- 升级新版:下载新版 zip 解压,用旧版的 `data/` 目录替换新版的 `data/` 目录

### 10.6 忘记 admin 密码

- 打开 `xhs-info-crawl/.env` 文件
- 找到 `INITIAL_ADMIN_PASSWORD=`,记录密码
- 如果密码为空,默认密码是 `Admin@123`

## 11. 获取帮助

- [Releases 页面](https://github.com/hyqskevin/xhs-info-crawl/releases):下载新版本
- [Issues 页面](https://github.com/hyqskevin/xhs-info-crawl/issues):提交问题反馈
- [开发者文档](INSTALL.md):开发者安装说明
- [部署文档](docs/deployment.md):部署架构说明
