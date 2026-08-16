from datetime import datetime, timedelta, timezone
from typing import Annotated
from fastapi import APIRouter,Depends
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.activity import Activity
from app.models.duplicate import NoteDuplicateCandidate
from app.models.note import Note
from app.models.schedule import ScheduledCrawl
from app.models.task import CrawlTask, TaskLog
router=APIRouter(prefix='/dashboard',tags=['dashboard'])

_SHANGHAI = timezone(timedelta(hours=8))


def _iso_week_start_utc_naive() -> datetime:
    """本周一 00:00（北京）对应的 UTC naive 时间点，用于匹配 UTC naive 存储的 created_at。"""
    now_sh = datetime.now(_SHANGHAI)
    monday_sh = (now_sh - timedelta(days=now_sh.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return monday_sh.astimezone(timezone.utc).replace(tzinfo=None)

_KNOWN_STATUSES={'COMPLETED','COMPLETED_WITH_ERRORS','FAILED','STOPPED'}

def _task_source(task:CrawlTask)->str:
    params=task.params or {}
    return 'scheduled' if params.get('type')=='scheduled' or params.get('schedule_id') else 'manual'

@router.get('/analytics')
def analytics(_:Annotated[dict,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):
    recent=list(db.scalars(select(CrawlTask).order_by(CrawlTask.id.desc()).limit(20)).all())
    recent.reverse()
    recent_tasks=[{'id':t.id,'source':_task_source(t),'schedule_name':(t.params or {}).get('schedule_name'),'status':t.status,'started_at':t.started_at,'total_notes':t.total_notes,'success_notes':t.success_notes,'failed_notes':t.failed_notes} for t in recent]
    last50=list(db.scalars(select(CrawlTask).order_by(CrawlTask.id.desc()).limit(50)).all())
    status_counts:dict[str,int]={}
    for t in last50:
        key=t.status if t.status in _KNOWN_STATUSES else 'OTHER'
        status_counts[key]=status_counts.get(key,0)+1
    scheduled_tasks=list(db.scalars(select(CrawlTask).order_by(CrawlTask.id.desc()).limit(500)).all())
    schedules=[]
    for s in db.scalars(select(ScheduledCrawl).order_by(ScheduledCrawl.id)).all():
        last_task=None
        for t in scheduled_tasks:
            if (t.params or {}).get('schedule_id')==s.id:
                last_task={'id':t.id,'status':t.status,'started_at':t.started_at}
                break
        schedules.append({'id':s.id,'name':s.name,'enabled':s.enabled,'day_of_week':s.day_of_week,'hour':s.hour,'minute':s.minute,'city_code':s.city_code,'last_task':last_task})
    return {'code':200,'message':'success','data':{'recent_tasks':recent_tasks,'status_counts':status_counts,'schedules':schedules}}
@router.get('/summary')
def summary(_:Annotated[dict,Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):
    # last_task：优先展示"正在抓取"的任务（RUNNING/PENDING/...），再按最近启动时间排序。
    # 这样正在抓取的任务不会被 id 更大但已停止的任务（或 started_at 为空的历史任务）盖掉。
    _ACTIVE = ['PENDING','RUNNING','STOP_REQUESTED','SEARCH_DONE','DOWNLOADING','PROCESSING','DEDUPING']
    active_rank = case(
        *[(CrawlTask.status == s, 0) for s in _ACTIVE],
        else_=1,
    )
    last = db.scalar(
        select(CrawlTask)
        .order_by(active_rank, CrawlTask.started_at.desc().nullslast(), CrawlTask.id.desc())
        .limit(1)
    )
    last_task=None
    if last:
        progress=round((last.extracted_notes+last.failed_notes+last.skipped_notes)*100/last.total_notes,1) if last.total_notes else None
        last_task={'id':last.id,'status':last.status,'total_notes':last.total_notes,'downloaded_notes':last.downloaded_notes,'ocr_notes':last.ocr_notes,'extracted_notes':last.extracted_notes,'success_notes':last.success_notes,'failed_notes':last.failed_notes,'skipped_notes':last.skipped_notes,'skipped_activities':last.skipped_activities,'current_stage':last.current_stage,'current_note':last.current_note,'error_message':last.error_message,'progress_percent':progress}
    # resumable_task：最近一个可继续抓取的任务（FAILED/STOPPED/STOP_REQUESTED/PAUSED）。
    # 当 last_task 本身正在运行（RUNNING/PENDING/...）时，单独展示给用户，避免被 RUNNING 任务覆盖。
    # 注意：STOP_REQUESTED 仍是中间态，按钮会被前端 disabled；这里仍然返回以方便前端拿到 task id。
    resumable_task=None
    if not last or last.status not in ["FAILED", "STOPPED", "STOP_REQUESTED", "PAUSED"]:
        resumable_row = db.scalar(
            select(CrawlTask)
            .where(CrawlTask.status.in_(["FAILED", "STOPPED", "STOP_REQUESTED", "PAUSED"]))
            .order_by(CrawlTask.id.desc())
            .limit(1)
        )
        if resumable_row:
            rprogress = round((resumable_row.extracted_notes + resumable_row.failed_notes + resumable_row.skipped_notes) * 100 / resumable_row.total_notes, 1) if resumable_row.total_notes else None
            resumable_task = {'id': resumable_row.id, 'status': resumable_row.status, 'total_notes': resumable_row.total_notes, 'downloaded_notes': resumable_row.downloaded_notes, 'ocr_notes': resumable_row.ocr_notes, 'extracted_notes': resumable_row.extracted_notes, 'success_notes': resumable_row.success_notes, 'failed_notes': resumable_row.failed_notes, 'skipped_notes': resumable_row.skipped_notes, 'skipped_activities': resumable_row.skipped_activities, 'current_stage': resumable_row.current_stage, 'current_note': resumable_row.current_note, 'error_message': resumable_row.error_message, 'progress_percent': rprogress}
    week_start = _iso_week_start_utc_naive()
    recent_logs = [
        {'id': log.id, 'task_id': log.task_id, 'level': log.level, 'message': log.message, 'created_at': log.created_at}
        for log in db.scalars(select(TaskLog).order_by(TaskLog.id.desc()).limit(5)).all()
    ]
    note_a_alias = Note.__table__.alias("note_a_alias")
    note_b_alias = Note.__table__.alias("note_b_alias")
    pending_dup_total = db.scalar(
        select(func.count())
        .select_from(NoteDuplicateCandidate)
        .join(note_a_alias, note_a_alias.c.id == NoteDuplicateCandidate.note_a_id)
        .join(note_b_alias, note_b_alias.c.id == NoteDuplicateCandidate.note_b_id)
        .where(
            NoteDuplicateCandidate.status == 'pending',
            note_a_alias.c.review_status.notin_(['DELETED', 'MERGED']),
            note_b_alias.c.review_status.notin_(['DELETED', 'MERGED']),
        )
    ) or 0
    return {'code':200,'message':'success','data':{'weekly_notes_count':db.scalar(select(func.count()).select_from(Note).where(Note.review_status.notin_(['DELETED','MERGED']), Note.created_at >= week_start)) or 0,'weekly_activities_count':db.scalar(select(func.count()).select_from(Activity).where(Activity.deleted_at.is_(None), Activity.created_at >= week_start)) or 0,'pending_duplicates':pending_dup_total,'pending_review':db.scalar(select(func.count()).select_from(Note).where(Note.review_status=='PENDING')) or 0,'last_task':last_task,'resumable_task':resumable_task,'recent_logs':recent_logs}}
