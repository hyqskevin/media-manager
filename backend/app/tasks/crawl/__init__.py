"""Celery 抓取任务实现拆分。

各子模块按职责划分，``app.tasks.crawl_task`` 作为 facade 重新导出所有符号，
以保持：

- Celery task 名字 ``app.tasks.crawl_task.run`` / ``app.tasks.crawl_task.scheduled_dispatch``
  与 ``celery_app`` 的 ``imports`` + ``beat_schedule`` 期望一致；
- 测试中 ``monkeypatch.setattr("app.tasks.crawl_task.X", ...)`` 的所有路径仍生效。

子模块：
- ``runtime``  任务守卫 / 日志 / 进度 / 异常类 / opencli 路径解析 / 频率 sleep
- ``accounts`` 账号加载 / Chrome CDP 端点解析 / ChromePool 启动
- ``notes``    单条笔记下载 + OCR + 提取 + 归档（含 StagedNote）
- ``search``   搜索阶段（含 throttled_search、博主/关键词组城市展开）
- ``runner``   Celery 任务 ``run_crawl`` 与 ``scheduled_dispatch``（任务编排主体）
"""
