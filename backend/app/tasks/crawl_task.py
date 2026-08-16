"""Celery 抓取任务 facade。

原 ``crawl_task.py`` 1095 行的单文件实现已按职责拆分到 ``app.tasks.crawl.*``
子模块（runtime / accounts / notes / search）。本模块作为 **facade** 兼
**Celery task 入口**，原因如下：

1. **Celery task name 兼容性**：``celery_app`` 的 ``imports`` + ``beat_schedule``
   期望 ``app.tasks.crawl_task.scheduled_dispatch`` 与 ``app.tasks.crawl_task.run``
   两个名字；切换装饰位置会破坏 beat 调度。
2. **测试 monkeypatch 兼容**：24 个测试文件通过
   ``monkeypatch.setattr("app.tasks.crawl_task.X", ...)`` 直接替换本模块符号；
   facade 暴露同名符号后这些 patch 仍生效。
3. **API 与数据库模型导入路径不变**：外部 ``from app.tasks.crawl_task import run_crawl``
   等语句零改动。

按职责拆分的子模块见 ``app.tasks.crawl``。``run_crawl`` / ``scheduled_dispatch`` 的
**任务主体**仍在 facade 内实现（便于通过 facade 模块 globals 解析被 monkeypatch
的 helper）；其余单条笔记处理、搜索、账号/ChromePool、运行守卫等独立职责下放
到子模块。
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
import logging

from sqlalchemy import func, select, update

# 第三方依赖
from app.core.config import get_settings  # noqa: F401  (re-exported for tests)
from app.core.database import SessionLocal  # noqa: F401  (re-exported for tests)
from app.services.extraction import extract_activities  # noqa: F401  (re-exported for tests)
from app.services.minimax import MiniMaxClient  # noqa: F401  (re-exported for tests)
from app.services.ocr import OCRService  # noqa: F401  (re-exported for tests)
from app.services.opencli_adapter import OpenCLIAdapter  # noqa: F401  (re-exported for tests)
from app.services.paddleocr_adapter import PaddleOCREngine  # noqa: F401  (re-exported for tests)
from app.services.pipeline import deduplicate_results, title_matches_keywords  # noqa: F401
from app.services.browser_launcher import open_xhs_login  # noqa: F401  (re-exported for tests)

# 子模块符号
from app.tasks.crawl.accounts import (  # noqa: F401
    _make_chrome_pool_for_task,
    _resolve_cdp_endpoint_for_account,
    load_xhs_accounts,
)
from app.tasks.crawl.notes import (  # noqa: F401
    StagedNote,
    cleanup_incomplete_note,
    download_and_ocr,
    extract_and_save,
    prepare_existing_note,
    process_note,
)
from app.tasks.crawl.notes import _extract_engagement  # noqa: F401  (re-exported for tests)
from app.tasks.crawl.runtime import (  # noqa: F401
    ExecutionStopped,
    ExecutionSuperseded,
    _BUSY_STATUSES,
    _DISPATCH_TZ,
    assert_execution_active,
    find_opencli,
    finish_stop_if_requested,
    log,
    rate_limit_sleep,
    set_progress,
)
from app.tasks.crawl.search import (  # noqa: F401
    _collect_cities_from_groups,
    _collect_crawl_results,
    _expand_blogger_groups,
    throttled_search,
)

# Celery 实例
from app.tasks.celery_app import celery_app

# 其他 imports（任务主体用）
from app.models.schedule import ScheduledCrawl
from app.models.task import CrawlTask
from app.services.crawler import AuthenticationRequired, CrawlHalted, VerificationRequired
from app.services.chrome_pool import ChromeLaunchError
from app.services.note_identity import extract_platform_note_id
from app.services.pipeline import run_stage
from app.services.search_rate_limit import SearchRateLimiter


logger = logging.getLogger(__name__)


# ============================================================
# Celery task 主体
# ============================================================


@celery_app.task(name="app.tasks.crawl_task.scheduled_dispatch")
def scheduled_dispatch(now=None) -> None:
    """每分钟由 beat 触发：匹配到点的 enabled 定时任务并创建抓取任务。

    - slot 幂等：last_fired_slot == 当前分钟则跳过（防 beat 重启/重复 tick 重发）；
    - 单任务约束：已有 PENDING/RUNNING/STOP_REQUESTED 任务时跳过本次触发
      （保守语义：定时任务不打断人工任务，与手动 crawl 的"顶替"语义刻意不同）。
    """
    now = (now or datetime.now(_DISPATCH_TZ)).astimezone(_DISPATCH_TZ)
    slot = now.strftime("%Y-%m-%dT%H:%M")
    db = SessionLocal()
    try:
        # day_of_week == 8 表示"每天触发"，跳过星期匹配
        schedules = db.scalars(
            select(ScheduledCrawl).where(
                ScheduledCrawl.enabled.is_(True),
                (
                    (ScheduledCrawl.day_of_week == 8)
                    | (ScheduledCrawl.day_of_week == now.isoweekday())
                ),
                ScheduledCrawl.hour == now.hour,
                ScheduledCrawl.minute == now.minute,
            )
        ).all()
        if not schedules:
            return
        busy = db.scalar(
            select(func.count()).select_from(CrawlTask).where(CrawlTask.status.in_(_BUSY_STATUSES))
        )
        for schedule in schedules:
            if schedule.last_fired_slot == slot:
                continue
            if busy:
                logger.warning(
                    "scheduled_dispatch: 任务进行中，跳过 schedule id=%s slot=%s", schedule.id, slot
                )
                continue
            params: dict = {
                "type": "scheduled",
                "city": schedule.city_code,
                "keyword_group_ids": schedule.keyword_group_ids or [],
                "blogger_ids": _expand_blogger_groups(db, schedule.city_code, schedule.blogger_group_ids or []),
                "schedule_id": schedule.id,
                "schedule_name": schedule.name,
                "fired_slot": slot,
            }
            if schedule.recent_filter:
                params["recent_filter"] = schedule.recent_filter
            task = CrawlTask(type="scheduled", status="PENDING", params=params)
            db.add(task)
            db.commit()
            db.refresh(task)
            schedule.last_fired_slot = slot
            db.commit()
            run_crawl.delay(task.id, task.run_token)
            busy = True  # 同一 tick 后续 schedule 不再叠加任务
    finally:
        db.close()


@celery_app.task(name="app.tasks.crawl_task.run", bind=True)
def run_crawl(self, task_id: int, run_token=None) -> None:
    """两阶段流水线：先批量 download + OCR，再批量 MiniMax + extract + archive。

    函数体内的 helper 引用（``SessionLocal`` / ``OpenCLIAdapter`` / ``download_and_ocr``
    / ``extract_and_save`` / ``throttled_search`` 等）通过本模块 globals 解析——
    这样测试中 ``monkeypatch.setattr("app.tasks.crawl_task.X", ...)`` 能影响 run_crawl
    的实际行为。
    """
    db = SessionLocal()
    if not run_token:
        db.close()
        return
    claimed = db.execute(
        update(CrawlTask)
        .where(
            CrawlTask.id == task_id,
            CrawlTask.status == "PENDING",
            CrawlTask.run_token == run_token,
        )
        .values(status="RUNNING", current_stage="SEARCHING", current_note=None, error_message=None)
    )
    db.commit()
    if claimed.rowcount != 1:
        db.close()
        return
    task = db.get(CrawlTask, task_id)
    settings = get_settings()
    if find_opencli(settings.opencli_bin) is None:
        message = (
            f"opencli 不可用：未找到命令 {settings.opencli_bin!r}"
            "（请运行 npm install -g @jackwener/opencli 或在 .env 配置 OPENCLI_BIN 指向其绝对路径）"
        )
        task.status = "FAILED"
        task.error_message = message
        task.current_stage = None
        task.finished_at = datetime.now(timezone.utc)
        db.commit()
        log(db, task.id, "ERROR", message)
        db.close()
        return
    accounts = load_xhs_accounts(db)
    if not accounts:
        accounts = [SimpleNamespace(name="默认", session_name="xhs-crawler", id=None)]
    # 为每个有 cdp_port 的账号启动独立 Chrome 实例（ChromePool）
    # 缺 cdp_port 的账号回退默认 Chrome Browser Bridge（向后兼容）
    chrome_pool = None
    if any(getattr(a, "cdp_port", None) is not None for a in accounts):
        try:
            chrome_pool = _make_chrome_pool_for_task(settings, db, accounts)
        except ChromeLaunchError as exc:
            log(db, task_id, "ERROR", f"Chrome 实例启动失败：{exc}")
            chrome_pool = None  # 退化为默认 CDP（向原 Chrome Browser Bridge）
    account_index = 0
    adapter = OpenCLIAdapter(
        settings,
        session=accounts[0].session_name,
        cdp_endpoint=_resolve_cdp_endpoint_for_account(accounts[0], chrome_pool),
    )
    # 注册 task_id 到 adapter 让 run() 自动绑定 PID（如果 adapter 支持）
    if hasattr(adapter, "bind_task"):
        adapter.bind_task(
            task.id,
            run_token,
            execution_guard=lambda: assert_execution_active(db, task.id, run_token),
            warning_sink=lambda message: log(db, task.id, "WARNING", message),
        )
    try:
        if task.started_at is None:
            task.started_at = datetime.now(timezone.utc)
        db.commit()
        log(db, task.id, "INFO", "登录预检：检查小红书登录状态")
        adapter.check_login()
        log(db, task.id, "INFO", "登录预检通过")
        results: list = []
        discovery_failures = 0
        consecutive_failures = 0

        rate_limiter = SearchRateLimiter(settings.search_interval_min, settings.search_interval_max)

        def _run_throttled_search(query: str, recent: str):
            return throttled_search(db, settings, task, adapter, query, recent, run_token, rate_limiter)

        results, discovery_failures = _collect_crawl_results(
            db, settings, task, adapter, _run_throttled_search, run_token,
        )

        results = deduplicate_results(results)
        task.total_notes = len(results)
        db.commit()

        def on_failure(entry, exc: Exception) -> None:
            db.rollback()
            cleanup_incomplete_note(db, entry[1]["url"])
            current = db.get(CrawlTask, task.id)
            current.failed_notes += 1
            current.error_message = str(exc)
            db.commit()
            log(db, current.id, "ERROR", f"笔记处理失败 [{entry[1]['url']}]：{exc}")

        def reset_adapter_session(current_adapter: OpenCLIAdapter, reason: str) -> OpenCLIAdapter:
            """强制重建 CDP 连接，释放 Chrome profile 状态。失败仅 WARNING，不中断任务。"""
            try:
                current_adapter.close_session()
            except Exception as exc:
                log(db, task.id, "WARNING", f"adapter.close_session 失败（{reason}，忽略继续）：{exc}")
            new_adapter = OpenCLIAdapter(
                settings,
                session=accounts[account_index].session_name,
                cdp_endpoint=_resolve_cdp_endpoint_for_account(accounts[account_index], chrome_pool),
            )
            if hasattr(new_adapter, "bind_task"):
                new_adapter.bind_task(
                    task.id,
                    run_token,
                    execution_guard=lambda: assert_execution_active(db, task.id, run_token),
                    warning_sink=lambda message: log(db, task.id, "WARNING", message),
                )
            return new_adapter

        def refresh_token_pool(entry) -> None:
            """token 池刷新：用 entry 的 _matched_keywords 重新跑 throttled_search，按 platform_note_id 匹配替换 URL。"""
            matched_keywords = entry[1].get("_matched_keywords") or []
            if not matched_keywords:
                return
            query = f"{entry[0]} {matched_keywords[0]}"
            log(db, task.id, "INFO", f"触发 token 池刷新：重新搜索 {query!r}")
            new_items = throttled_search(db, settings, task, adapter, query, "")
            if not new_items:
                log(db, task.id, "WARNING", "token 池刷新失败：throttled_search 返回空，跳过替换")
                return
            current_note_id = extract_platform_note_id(entry[1].get("url", ""))
            if not current_note_id:
                return
            for new_item in new_items:
                new_note_id = extract_platform_note_id(new_item.get("url", ""))
                if new_note_id == current_note_id:
                    entry[1]["url"] = new_item["url"]
                    log(db, task.id, "INFO", f"token 池刷新成功：note_id={current_note_id[:8]}... 替换为新 URL")
                    return

        attempts = settings.pipeline_stage_max_retries
        delay = settings.pipeline_stage_retry_delay_seconds

        # 阶段 1：逐篇下载 + OCR（串行，opencli 不支持并发），暂存 StagedNote
        staged_notes: list = []
        empty_streak = 0  # 连续空详情熔断计数器
        empty_threshold = max(1, settings.crawl_empty_detail_threshold)  # 防 0/负数
        reset_interval = max(0, settings.crawl_session_reset_interval)  # 0 表示禁用
        for entry in results:
            if finish_stop_if_requested(db, task.id, run_token):
                return
            try:
                matched_keywords = entry[1].get("_matched_keywords")
                if matched_keywords and not title_matches_keywords(entry[1].get("title", ""), matched_keywords):
                    task.skipped_notes += 1
                    db.commit()
                    log(db, task.id, "INFO", f"标题未包含关键词，已跳过 [{entry[1]['url']}] 标题={entry[1].get('title', '')!r} 关键词={matched_keywords}")
                    continue
                staged = download_and_ocr(db, task, run_token, entry[0], entry[1], adapter, settings)
                if staged is not None:
                    # 连续空详情熔断：note.content 视为空触发风控熔断
                    if not staged.note.content or not staged.note.content.strip():
                        empty_streak += 1
                        log(db, task.id, "WARNING", f"详情为空 {empty_streak}/{empty_threshold} url={entry[1]['url']}")
                        # 阈值 - 2 时尝试 token 池刷新（默认 5 - 2 = 3），早介入避免浪费剩余缓冲
                        # 仅当 entry 带 _matched_keywords（搜索结果）才刷新；博主条目无关键词，无刷新意义
                        if empty_streak == empty_threshold - 2 and entry[1].get("_matched_keywords"):
                            old_url = entry[1]["url"]
                            refresh_token_pool(entry)
                            if entry[1]["url"] != old_url:
                                # 刷新成功：用新 URL 重抓当前 entry
                                db.rollback()
                                cleanup_incomplete_note(db, old_url)
                                retry_staged = download_and_ocr(db, task, run_token, entry[0], entry[1], adapter, settings)
                                if retry_staged is not None:
                                    if retry_staged.note.content and retry_staged.note.content.strip():
                                        log(db, task.id, "INFO", f"token 池刷新后重抓成功 url={entry[1]['url']}")
                                        empty_streak = 0
                                        staged_notes.append(retry_staged)
                                        continue
                                    else:
                                        # 重抓仍空，按空详情继续累计
                                        staged = retry_staged
                                        empty_streak += 1
                                        log(db, task.id, "WARNING", f"token 池刷新后重抓仍为空 {empty_streak}/{empty_threshold} url={entry[1]['url']}")
                        if empty_streak >= empty_threshold:
                            raise CrawlHalted(
                                f"连续 {empty_streak} 篇笔记详情为空，疑似触发小红书风控。"
                                "请在 Chrome 重新打开小红书后点击「继续抓取」"
                            )
                    else:
                        empty_streak = 0
                    staged_notes.append(staged)
                    # 周期性重置 adapter 释放 Chrome profile 累积
                    if reset_interval and len(staged_notes) % reset_interval == 0:
                        log(db, task.id, "INFO", f"已处理 {len(staged_notes)} 篇，重置 adapter 释放 Chrome profile")
                        adapter = reset_adapter_session(adapter, f"周期性 reset @ {len(staged_notes)} 篇")
                    # 多账号轮询：每抓 N 篇主动切到下一个账号（避免触发频率限制）
                    # 仅当 ≥2 个账号时切；单账号 / 默认 session 时跳过
                    rotation_n = getattr(settings, "account_rotation_notes", 25) or 0
                    if (
                        rotation_n > 0
                        and len(accounts) >= 2
                        and all(getattr(a, "cdp_port", None) is not None for a in accounts)
                        and len(staged_notes) % rotation_n == 0
                    ):
                        next_idx = (account_index + 1) % len(accounts)
                        old_name = accounts[account_index].name
                        new_name = accounts[next_idx].name
                        log(
                            db,
                            task.id,
                            "INFO",
                            f"账号轮询：每 {rotation_n} 篇切换一次，{old_name!r} → {new_name!r}（已抓 {len(staged_notes)} 篇）",
                        )
                        account_index = next_idx
                        adapter = OpenCLIAdapter(
                            settings,
                            session=accounts[account_index].session_name,
                            cdp_endpoint=_resolve_cdp_endpoint_for_account(accounts[account_index], chrome_pool),
                        )
                        if hasattr(adapter, "bind_task"):
                            adapter.bind_task(
                                task.id,
                                run_token,
                                execution_guard=lambda: assert_execution_active(db, task.id, run_token),
                                warning_sink=lambda message: log(db, task.id, "WARNING", message),
                            )
                # 正常返回（含标题不匹配/已存在等跳过）说明链路健康，连续失败计数清零
                consecutive_failures = 0
            except ExecutionStopped:
                db.rollback()
                cleanup_incomplete_note(db, entry[1]["url"])
                finish_stop_if_requested(db, task.id, run_token)
                return
            except ExecutionSuperseded:
                db.rollback()
                return
            except CrawlHalted:
                # 详情空值熔断等 CrawlHalted 由 for 循环抛出；阶段 1 不吞咽，重新向上传播
                # 让 run_crawl 顶部 except (CrawlHalted) 处理（写 PAUSED + error_message）
                raise
            except (AuthenticationRequired, VerificationRequired) as exc:
                # 当前账号失效（未登录/扫码超时/风控验证），切换到下一个账号并重试当前笔记一次。
                # 每篇笔记最多切换一次，避免死循环；retry 再失效则跳过本篇，下一篇继续用新账号。
                db.rollback()
                cleanup_incomplete_note(db, entry[1]["url"])
                account_index += 1
                if account_index >= len(accounts):
                    raise CrawlHalted(f"所有账号均已失效，请扫码登录后继续。最近错误：{exc}")
                old_name = accounts[account_index - 1].name
                new_name = accounts[account_index].name
                log(db, task.id, "INFO", f"账号 {old_name!r} 失效（{exc}），切换到 {new_name!r}")
                adapter = OpenCLIAdapter(
                    settings,
                    session=accounts[account_index].session_name,
                    cdp_endpoint=_resolve_cdp_endpoint_for_account(accounts[account_index], chrome_pool),
                )
                if hasattr(adapter, "bind_task"):
                    adapter.bind_task(
                        task.id,
                        run_token,
                        execution_guard=lambda: assert_execution_active(db, task.id, run_token),
                        warning_sink=lambda message: log(db, task.id, "WARNING", message),
                    )
                # 重试当前笔记一次
                try:
                    staged = download_and_ocr(db, task, run_token, entry[0], entry[1], adapter, settings)
                    if staged is not None:
                        staged_notes.append(staged)
                    consecutive_failures = 0
                except (AuthenticationRequired, VerificationRequired) as retry_exc:
                    # 新账号也失效，跳过本篇，下一篇继续用新账号（account_index 已增）
                    db.rollback()
                    cleanup_incomplete_note(db, entry[1]["url"])
                    log(db, task.id, "WARNING", f"切换到账号 {new_name!r} 后仍失效：{retry_exc}，跳过该笔记")
                    continue
                except ExecutionStopped:
                    db.rollback()
                    cleanup_incomplete_note(db, entry[1]["url"])
                    finish_stop_if_requested(db, task.id, run_token)
                    return
                except ExecutionSuperseded:
                    db.rollback()
                    return
                except Exception as retry_exc:
                    on_failure(entry, retry_exc)
                    continue
            except Exception as exc:
                consecutive_failures += 1
                on_failure(entry, exc)
                # 连续失败达到阈值视为系统性问题（登录态掉线/风控/opencli 异常），
                # 熔断为 PAUSED 交给用户决策，避免整批笔记逐篇失败空跑
                if consecutive_failures >= settings.consecutive_note_failure_limit:
                    raise CrawlHalted(
                        f"已连续 {consecutive_failures} 篇笔记处理失败，疑似登录态失效或触发风控。"
                        f"最近一次错误：{exc}。请检查浏览器登录/验证状态后点「检测登录并继续」，或「结束抓取」。"
                    )

        # 阶段 2：批量并行 MiniMax + 写 DB
        if staged_notes:
            if settings.minimax_api_key:
                client = MiniMaxClient(settings)
                texts = [s.combined_text for s in staged_notes]
                reference = staged_notes[0].reference_now
                try:
                    payloads = run_stage(
                        lambda: client.extract_many_parallel(texts, reference),
                        attempts, delay,
                    )
                except Exception as exc:
                    log(db, task.id, "WARNING", f"MiniMax 批量提取失败，降级规则提取：{exc}")
                    extracted_list = [extract_activities(s.combined_text, s.reference_now, None) for s in staged_notes]
                else:
                    # 复用 extract_activities 的 normalize 逻辑：llm callable 直接返回预提取的 payload
                    extracted_list = [
                        extract_activities(s.combined_text, s.reference_now, lambda _text, p=payload: p)
                        for s, payload in zip(staged_notes, payloads)
                    ]
            else:
                extracted_list = [extract_activities(s.combined_text, s.reference_now, None) for s in staged_notes]

            for staged, extracted in zip(staged_notes, extracted_list):
                if finish_stop_if_requested(db, task.id, run_token):
                    return
                try:
                    extract_and_save(db, task, run_token, staged, extracted, settings)
                except ExecutionStopped:
                    db.rollback()
                    finish_stop_if_requested(db, task.id, run_token)
                    return
                except ExecutionSuperseded:
                    db.rollback()
                    return
                except AuthenticationRequired:
                    raise
                except Exception as exc:
                    db.rollback()
                    current = db.get(CrawlTask, task.id)
                    current.failed_notes += 1
                    current.error_message = str(exc)
                    db.commit()
                    log(db, task.id, "ERROR", f"笔记保存失败 [{staged.note.source_url}]：{exc}")
        if finish_stop_if_requested(db, task.id, run_token):
            return
        task = db.get(CrawlTask, task.id)
        task.status = "COMPLETED_WITH_ERRORS" if task.failed_notes or discovery_failures else "COMPLETED"
        task.current_stage = None
        task.current_note = None
        task.finished_at = datetime.now(timezone.utc)
        db.commit()
        log(db, task.id, "INFO", "completed")
    except ExecutionStopped:
        db.rollback()
        finish_stop_if_requested(db, task_id, run_token)
    except ExecutionSuperseded:
        db.rollback()
    except (AuthenticationRequired, CrawlHalted) as exc:
        task = db.get(CrawlTask, task_id)
        task.status = "PAUSED"
        task.error_message = str(exc)
        db.commit()
        log(db, task.id, "ERROR", str(exc))
        # 未登录（whoami 超时归类）、安全验证与连续失败熔断都需要用户在浏览器里
        # 检查并完成扫码/验证，统一自动打开登录页；打开失败不影响 PAUSED 状态。
        page_kind = "验证页面" if isinstance(exc, VerificationRequired) else "登录页面，请完成扫码后点击「继续抓取」"
        try:
            open_xhs_login(settings)
            log(db, task.id, "INFO", f"已自动打开 Chrome 小红书{page_kind}")
        except Exception as launch_exc:
            log(db, task.id, "WARNING", f"自动打开 Chrome 失败：{launch_exc}")
    except Exception as exc:
        db.rollback()
        task = db.get(CrawlTask, task_id)
        task.status = "FAILED"
        task.error_message = str(exc)
        task.current_stage = None
        db.commit()
        log(db, task.id, "ERROR", str(exc))
    finally:
        # 不释放 chrome_pool——它是全局单例，由 atexit 在后端退出时统一 release
        # 这样账号已启动的 Chrome 实例可在任务间持续运行（用户已登录的 cookie 保持有效）
        db.close()
