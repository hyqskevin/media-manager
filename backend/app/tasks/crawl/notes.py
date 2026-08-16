"""单条笔记的两阶段处理：download + OCR → StagedNote；extract + archive → Activity。

阶段 1（``download_and_ocr``）：拉取详情 + 图片 + OCR，生成 StagedNote；
阶段 2（``extract_and_save``）：校验活动 + 写 Activity + 归档 + 更新 Note 状态；
向后兼容包装（``process_note``）：阶段 1 + 单篇 MiniMax 提取 + 阶段 2（旧路径，已不
被 ``run_crawl`` 主流程使用，保留以兼容直接调用方）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import shutil

from sqlalchemy import delete, select

from app.models.activity import Activity
from app.models.note import Note, NoteImage
from app.models.task import CrawlTask
from app.services.archive import archive_task_folder, archive_task_result
from app.services.dedup import create_note_duplicate_candidates
from app.services.extraction import extract_activities
from app.services.minimax import MiniMaxClient
from app.services.note_id_published_at import note_id_published_at
from app.services.note_identity import extract_platform_note_id
from app.services.ocr import OCRService
from app.services.opencli_adapter import OpenCLIAdapter
from app.services.paddleocr_adapter import PaddleOCREngine
from app.services.pipeline import run_stage

from app.tasks.crawl.runtime import assert_execution_active, log, set_progress


def _extract_engagement(detail: dict, field: str) -> int | None:
    """从 opencli note 详情中提取互动数。

    字段名映射：opencli 实际返回可能是 liked_count / collected_count 等。
    实施时若已确认实际字段名，替换候选列表。
    """
    if not isinstance(detail, dict):
        return None
    candidates = {
        "like_count": ("like_count", "liked_count", "likes"),
        "collect_count": ("collect_count", "collected_count", "collects"),
        "comment_count": ("comment_count", "comments"),
    }.get(field, (field,))
    for key in candidates:
        if key in detail and detail[key] is not None:
            try:
                return int(detail[key])
            except (TypeError, ValueError):
                return None
    return None


@dataclass
class StagedNote:
    """阶段 1 产出、阶段 2 消费的中间结构。

    - note：已写入 DB 的 Note（状态为 OCR_DONE / DOWNLOADED）
    - combined_text：标题+正文+OCR 拼接文本，供 MiniMax/规则提取
    - reference_now：活动日期推断基准（Note.published_at 或 task.started_at）
    - started_at：任务开始时间，用于归档目录
    - image_rows：[(image_path, NoteImage)]，归档时复制图片用
    """

    note: Note
    combined_text: str
    reference_now: datetime
    started_at: datetime
    image_rows: list[tuple]


def cleanup_incomplete_note(db, source_url: str) -> None:
    platform_note_id = extract_platform_note_id(source_url)
    note = db.scalar(
        select(Note).where(
            Note.platform_note_id == platform_note_id if platform_note_id else Note.source_url == source_url
        )
    )
    if note is None or note.status == "PROCESSED":
        return
    db.execute(delete(Activity).where(Activity.note_id == note.id))
    db.execute(delete(NoteImage).where(NoteImage.note_id == note.id))
    db.delete(note)
    db.commit()


def prepare_existing_note(db, source_url: str) -> bool:
    """Return True when a note is already complete; remove partial legacy rows otherwise."""
    platform_note_id = extract_platform_note_id(source_url)
    note = db.scalar(
        select(Note).where(
            Note.platform_note_id == platform_note_id if platform_note_id else Note.source_url == source_url
        )
    )
    if note is None:
        return False
    has_activity = db.scalar(select(Activity.id).where(Activity.note_id == note.id).limit(1)) is not None
    if note.status == "PROCESSED" or has_activity:
        changed = False
        if note.source_url != source_url:
            note.source_url = source_url
            changed = True
        if note.status != "PROCESSED":
            note.status = "PROCESSED"
            changed = True
        if changed:
            db.commit()
        return True
    cleanup_incomplete_note(db, source_url)
    return False


def download_and_ocr(db, task: CrawlTask, run_token: str, city: str, item: dict, adapter: OpenCLIAdapter, settings) -> StagedNote | None:
    """阶段 1：下载笔记详情 + 图片 + OCR，返回 StagedNote 或 None（跳过/失败）。

    不调用 MiniMax，不写 Activity。保留 assert_execution_active / set_progress 调用。
    """
    from app.services.crawl_city_guard import assert_city_code_exists
    from app.services.published_at import extract_published_at

    assert_execution_active(db, task.id, run_token)
    note_url = (item.get("url") or "").strip()
    if not note_url:
        log(db, task.id, "WARNING", f"跳过笔记：url 为空 title={item.get('title', '')!r}")
        return None
    # 多城市博主：若博主实际挂在 [hz] 而任务调度城市是 nb，把 city 改成 hz 让 note.city_code 正确归桶。
    matched_blogger_cities = item.get("_matched_blogger_cities")
    if matched_blogger_cities and city not in matched_blogger_cities and len(matched_blogger_cities) == 1:
        corrected = matched_blogger_cities[0]
        log(
            db, task.id, "WARNING",
            f"博主挂城市 {matched_blogger_cities} 与任务城市 {city!r} 不一致，按博主实际城市修正为 {corrected!r}",
        )
        city = corrected
    # 关键词组排除词过滤（抓取后过滤笔记）：命中关键词但内容含排除词的笔记直接跳过
    matched_kws = item.get("_matched_keywords") or []
    if matched_kws:
        from app.models.keyword_group import KeywordGroup, KeywordGroupCity, KeywordGroupWord
        from app.models.config import City as CityModel
        # 找挂当前 city 的 enabled 关键词组
        group_ids = db.scalars(
            select(KeywordGroupCity.keyword_group_id)
            .join(KeywordGroup, KeywordGroup.id == KeywordGroupCity.keyword_group_id)
            .where(KeywordGroupCity.city_code == city, KeywordGroupCity.enabled.is_(True), KeywordGroup.enabled.is_(True))
        ).all()
        if group_ids:
            excluded_words: set[str] = set()
            for kg_id in group_ids:
                json_text = db.scalar(select(KeywordGroup.excluded_words_json).where(KeywordGroup.id == kg_id)) or "[]"
                try:
                    excluded_words.update(str(w).strip() for w in __import__("json").loads(json_text) if str(w).strip())
                except Exception:
                    pass
            if excluded_words:
                title = (item.get("title") or "").strip()
                # 命中排除词？注意：排除词匹配只看 title（这是开放搜索的快速预筛），content 过滤交给后续 OCR 阶段精细化。
                hit = next((w for w in excluded_words if w in title), None)
                if hit:
                    log(db, task.id, "INFO", f"关键词组排除词命中：title 含 '{hit}'，跳过 url={note_url}")
                    return None
    if not assert_city_code_exists(db, city):
        log(db, task.id, "ERROR", f"city_code 不在 cities 表：{city!r}，跳过该笔记 url={note_url}")
        task.skipped_activities += 1
        return None
    if prepare_existing_note(db, note_url):
        return None

    attempts = settings.pipeline_stage_max_retries
    delay = settings.pipeline_stage_retry_delay_seconds
    started_at = task.started_at or datetime.now(timezone.utc)
    set_progress(db, task, run_token, "DOWNLOADING", item.get("title") or note_url)
    detail = run_stage(lambda: adapter.note(note_url), attempts, delay)
    assert_execution_active(db, task.id, run_token)
    # 优先级 1：基于 note ID（雪花算法）反推时间戳，精度到秒，最可靠。
    # 优先级 2：DOM 文本解析（"3天前" / "07-19" 等）。
    # 优先级 3：started_at 兜底。
    snowflake_at = note_id_published_at(note_url)
    dom_at = extract_published_at(detail, fallback_now=started_at)
    if snowflake_at is not None:
        published_at = snowflake_at
    elif dom_at is not None:
        published_at = dom_at
    else:
        published_at = None
    if published_at is None:
        log(db, task.id, "INFO", f"未解析真实发布时间：{item.get('title') or note_url}")
    note = Note(
        task_id=task.id,
        platform_note_id=extract_platform_note_id(note_url) or note_url.split("/")[-1].split("?")[0],
        title=item.get("title", ""),
        content=detail.get("content", ""),
        source_url=note_url,
        city_code=city,
        status="DOWNLOADED",
        published_at=published_at,
        raw_data=detail,
        matched_keywords=item.get("_matched_keywords") or [],
        matched_blogger_id=item.get("_matched_blogger_id"),
        matched_blogger_username=item.get("_matched_blogger_username"),
        like_count=_extract_engagement(detail, "like_count"),
        collect_count=_extract_engagement(detail, "collect_count"),
        comment_count=_extract_engagement(detail, "comment_count"),
    )
    db.add(note)
    db.flush()
    folder = archive_task_folder(settings.archive_dir, started_at, task.id, city)
    download_dir = folder / ".downloads" / note.platform_note_id
    images = run_stage(lambda: adapter.download(note_url, download_dir), attempts, delay)
    assert_execution_active(db, task.id, run_token)
    task.downloaded_notes += 1
    db.commit()

    set_progress(db, task, run_token, "OCR", note.title)
    ocr = OCRService(PaddleOCREngine(settings), settings.ocr_min_confidence) if settings.ocr_enabled else None
    ocr_texts: list[str] = []
    image_rows: list[tuple] = []
    assert_execution_active(db, task.id, run_token)
    if ocr:
        # 并行 OCR：process_batch 用 ThreadPoolExecutor 并行处理所有图片，子线程内含重试
        ocr_results = ocr.process_batch(
            images,
            workers=settings.ocr_parallel_workers,
            attempts=attempts,
            delay=delay,
        )
        assert_execution_active(db, task.id, run_token)
        data_root = settings.data_dir.resolve()
        for index, (image, result) in enumerate(zip(images, ocr_results), 1):
            # storage_key 用相对 data_dir 的路径，与 API 端 FileResponse(data_root / storage_key) 一致
            try:
                storage_key = str(image.resolve().relative_to(data_root))
            except ValueError:
                # image 不在 data_root 下，落到 .downloads/<platform_note_id> 目录（兜底）
                storage_key = str(image)
            image_row = NoteImage(
                note_id=note.id,
                storage_key=storage_key,
                original_url="",  # 小红书图片原始 URL 不持久化（防盗链）；相对路径即足够
                ocr_text=result["text"],
                ocr_status=result["status"],
                ocr_error=result["error"],
            )
            db.add(image_row)
            image_rows.append((image, image_row))
            if result["text"]:
                ocr_texts.append(f"[IMAGE {index}]\n{result['text']}")
    else:
        data_root = settings.data_dir.resolve()
        for index, image in enumerate(images, 1):
            result = {"status": "disabled", "text": "", "error": ""}
            try:
                storage_key = str(image.resolve().relative_to(data_root))
            except ValueError:
                storage_key = str(image)
            image_row = NoteImage(
                note_id=note.id,
                storage_key=storage_key,
                original_url="",
                ocr_text=result["text"],
                ocr_status=result["status"],
                ocr_error=result["error"],
            )
            db.add(image_row)
            image_rows.append((image, image_row))
    note.status = "OCR_DONE" if ocr else "DOWNLOADED"
    task.ocr_notes += 1
    db.commit()

    combined = f"标题：{note.title}\n正文：{note.content}\n" + "\n".join(ocr_texts)
    # reference_now 必须是"笔记发布当天"对应的本地日期（CST），无年份推断时才正确。
    # 错误做法：把 aware UTC 直接 .replace(tzinfo=None) 会保留 UTC 时间数值却被当本地解析，
    # 导致活动日期推断比实际早 8 小时（同一天内），容易把当天/次日误判成过去。
    # 修正：转 Asia/Shanghai 后归零到 00:00，并向前减 2 天作为推断基准，
    # 避免"凌晨发布的笔记提到当天活动"被误判成上一年（datetime 比较只看数值不区分凌晨）。
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    _CST = ZoneInfo("Asia/Shanghai")
    def _to_local_midnight(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(hour=0, minute=0, second=0, microsecond=0)
        local = value.astimezone(_CST).replace(tzinfo=None)
        return local.replace(hour=0, minute=0, second=0, microsecond=0)
    base_day = _to_local_midnight(note.published_at) if note.published_at else _to_local_midnight(started_at)
    reference_now = base_day - timedelta(days=2)
    return StagedNote(
        note=note,
        combined_text=combined,
        reference_now=reference_now,
        started_at=started_at,
        image_rows=image_rows,
    )


def extract_and_save(db, task: CrawlTask, run_token: str, staged: StagedNote, extracted, settings) -> bool:
    """阶段 2：校验活动 + 写 Activity + 归档 + 更新 Note 状态。

    接收已提取的 extracted（list[dict]），不调用 MiniMax。
    返回 True 表示 PROCESSED，False 表示无活动被过滤。
    """
    note = staged.note
    city = note.city_code
    started_at = staged.started_at
    image_rows = staged.image_rows
    set_progress(db, task, run_token, "EXTRACTING", note.title)
    assert_execution_active(db, task.id, run_token)

    from app.services.activity_validator import classify_zero_activity, validate_activities

    classification = classify_zero_activity(note, extracted)
    if classification in {"all_before_publish", "no_activity_signals"}:
        note.status = "NO_ACTIVITIES"
        log(db, task.id, "INFO", f"未提取到有效活动 原因={classification} url={note.source_url}")
        if classification == "all_before_publish" and extracted:
            preview = "; ".join(
                f"{a.get('name')!r}@{a.get('start_time')}" for a in extracted[:5]
            )
            suffix = "" if len(extracted) <= 5 else f" (共 {len(extracted)} 条)"
            log(db, task.id, "INFO", f"被拒绝活动预览：{preview}{suffix}")
        task.extracted_notes += 1
        db.commit()
        set_progress(db, task, run_token, "ARCHIVING", note.title)
        return False
    if classification == "minimax_empty_retryable":
        note.status = "EMPTY_RESULT_RETRYABLE"
        log(db, task.id, "INFO", f"MiniMax 返回空但有信号，可重试 url={note.source_url}")
        task.extracted_notes += 1
        db.commit()
        set_progress(db, task, run_token, "ARCHIVING", note.title)
        return False

    accepted, rejected = validate_activities(note, extracted)
    for reason in rejected:
        log(db, task.id, "INFO", f"跳过活动 原因={reason}")
    if not accepted:
        note.status = "NO_ACTIVITIES"
        log(db, task.id, "INFO", f"全部活动被过滤 url={note.source_url}")
        task.extracted_notes += 1
        db.commit()
        set_progress(db, task, run_token, "ARCHIVING", note.title)
        return False

    for fields in accepted:
        assert_execution_active(db, task.id, run_token)
        activity = Activity(
            note_id=note.id,
            name=fields.get("name") or note.title,
            city_code=city,
            start_time=datetime.fromisoformat(fields["start_time"]) if fields.get("start_time") else None,
            end_time=datetime.fromisoformat(fields["end_time"]) if fields.get("end_time") else None,
            location=fields.get("location") or "",
            price=fields.get("price") or "",
            type=fields.get("type") or "其他",
            source_url=note.source_url,
            source_image_indexes=fields.get("source_image_indexes") or [],
            summary=fields.get("summary") or note.content[:300],
            confidence=float(fields.get("confidence") or 0),
        )
        db.add(activity)
        db.flush()

    set_progress(db, task, run_token, "ARCHIVING", note.title)
    assert_execution_active(db, task.id, run_token)
    task_note_ids = select(Note.id).where(Note.task_id == task.id)
    task_activities = list(db.scalars(select(Activity).where(Activity.note_id.in_(task_note_ids)).order_by(Activity.id)).all())
    archive_task_result(settings.archive_dir, started_at, task.id, note, image_rows, task_activities, city)
    assert_execution_active(db, task.id, run_token)
    create_note_duplicate_candidates(db, note)
    folder = archive_task_folder(settings.archive_dir, started_at, task.id, city)
    shutil.rmtree(folder / ".downloads", ignore_errors=True)
    note.status = "PROCESSED"
    task.extracted_notes += 1
    task.success_notes = task.extracted_notes
    db.commit()
    return True


def process_note(db, task: CrawlTask, run_token: str, city: str, item: dict, adapter: OpenCLIAdapter, settings) -> bool:
    """向后兼容包装：download_and_ocr + 单篇 MiniMax 提取 + extract_and_save。

    供直接调用 process_note 的旧路径使用；run_crawl 已改为两阶段流水线，不再走这里。
    """
    staged = download_and_ocr(db, task, run_token, city, item, adapter, settings)
    if staged is None:
        return False
    attempts = settings.pipeline_stage_max_retries
    delay = settings.pipeline_stage_retry_delay_seconds
    if settings.minimax_api_key:
        client = MiniMaxClient(settings)
        try:
            extracted = run_stage(lambda: extract_activities(staged.combined_text, staged.reference_now, lambda text: client.extract_many(text, staged.started_at)), attempts, delay)
        except Exception as exc:
            log(db, task.id, "WARNING", f"MiniMax 提取失败，已降级规则提取：{exc}")
            extracted = extract_activities(staged.combined_text, staged.reference_now, None)
    else:
        extracted = extract_activities(staged.combined_text, staged.reference_now, None)
    return extract_and_save(db, task, run_token, staged, extracted, settings)
