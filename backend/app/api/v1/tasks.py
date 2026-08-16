from datetime import datetime, timezone
from uuid import uuid4
from typing import Annotated, Literal
from fastapi import APIRouter,Depends,HTTPException,Query,status
from pydantic import BaseModel
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_admin
from app.models.task import CrawlTask,TaskLog
from app.models.blogger_city import BloggerCity
from app.models.config import Blogger, City
from app.core.config import get_settings
from app.services.crawler import AuthenticationRequired
from app.services.opencli_adapter import OpenCLIAdapter
router=APIRouter(prefix='/tasks',tags=['tasks']); Admin=Annotated[dict,Depends(require_admin)]; DB=Annotated[Session,Depends(get_db)]
class CrawlIn(BaseModel):
    type: str = 'mixed'
    # city 可选；空字符串/缺省 = 不限城市
    city: str = ''
    keywords: list[str] = []
    keyword_group_ids: list[int] = []
    recent_filter: Literal['不限','一天内','一周内','半年内']
    blogger_ids: list[int] = []
    blogger_group_ids: list[int] = []


class BatchDeleteIn(BaseModel):
    ids: list[int] = []
def dump(t): return {c.name:getattr(t,c.name) for c in t.__table__.columns}
@router.get('')
def tasks(_:Admin,db:DB,page:int=1,page_size:Annotated[int,Query(le=100)]=20):
    total=db.scalar(select(func.count()).select_from(CrawlTask)) or 0; rows=db.scalars(select(CrawlTask).order_by(CrawlTask.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {'code':200,'message':'success','data':{'items':[dump(x) for x in rows]},'pagination':{'page':page,'page_size':page_size,'total':total}}
@router.post('/crawl',status_code=status.HTTP_202_ACCEPTED)
def crawl(payload:CrawlIn,_:Admin,db:DB):
    running=db.scalar(select(CrawlTask).where(CrawlTask.status.in_(['PENDING','RUNNING','STOP_REQUESTED','SEARCH_DONE','DOWNLOADING','PROCESSING','DEDUPING'])))
    if running:
        from app.services.task_registry import kill as kill_task_pid
        pid_killed = kill_task_pid(running.id, run_token=running.run_token, timeout=5.0)
        if running.status == 'PENDING':
            running.status='STOPPED';running.current_stage=None;running.current_note=None;running.finished_at=datetime.now(timezone.utc)
        elif running.status == 'RUNNING':
            running.status='STOP_REQUESTED';running.current_stage=None;running.current_note=None
        db.add(TaskLog(task_id=running.id,level='INFO',message=f'被新任务顶替停止（子进程已 kill={pid_killed}）',created_at=datetime.now(timezone.utc)))
        db.commit()

    # city 可选：未传 / 空字符串 = 不限城市
    city = None
    if payload.city:
        city = db.scalar(select(City).where(City.code == payload.city, City.enabled.is_(True)))
        if not city:
            raise HTTPException(422, '请选择已启用的城市')

    # 关键词组校验：有 city 时必须挂在该城市且都 enabled；不限城市时只校验组自身 enabled
    if payload.keyword_group_ids:
        from app.models.keyword_group import KeywordGroup, KeywordGroupCity
        if city is not None:
            group_rows = db.execute(
                select(
                    KeywordGroup.id,
                    KeywordGroup.enabled,
                    KeywordGroupCity.enabled.label("city_link_enabled"),
                )
                .join(KeywordGroupCity, KeywordGroupCity.keyword_group_id == KeywordGroup.id)
                .where(
                    KeywordGroup.id.in_(payload.keyword_group_ids),
                    KeywordGroupCity.city_code == city.code,
                )
            ).all()
            valid_ids = {row.id for row in group_rows if row.enabled and row.city_link_enabled}
            if any(gid not in valid_ids for gid in payload.keyword_group_ids):
                raise HTTPException(422, '关键词组不属于所选城市或已停用')
        else:
            enabled_ids = set(db.scalars(
                select(KeywordGroup.id).where(
                    KeywordGroup.id.in_(payload.keyword_group_ids),
                    KeywordGroup.enabled.is_(True),
                )
            ).all())
            if any(gid not in enabled_ids for gid in payload.keyword_group_ids):
                raise HTTPException(422, '关键词组不存在或已停用')

    # 博主 ID 校验：有 city 时必须在该城市 blogger_cities.enabled；不限城市时只校验 blogger.enabled
    if payload.blogger_ids:
        if city is not None:
            configured_bloggers = set(db.scalars(
                select(BloggerCity.blogger_id).where(
                    BloggerCity.city_code == city.code,
                    BloggerCity.enabled.is_(True),
                )
            ).all())
            if any(bid not in configured_bloggers for bid in payload.blogger_ids):
                raise HTTPException(422, '博主不属于所选城市')
        else:
            enabled_bloggers = set(db.scalars(
                select(Blogger.id).where(
                    Blogger.id.in_(payload.blogger_ids),
                    Blogger.enabled.is_(True),
                )
            ).all())
            if any(bid not in enabled_bloggers for bid in payload.blogger_ids):
                raise HTTPException(422, '博主不存在或已停用')

    # 至少一个有效输入源
    if not payload.keywords and not payload.keyword_group_ids and not payload.blogger_ids and not payload.blogger_group_ids:
        raise HTTPException(422, '请至少启用一个关键词或博主')

    # 校验 effective 范围：keywords ∪ 关键词组 ∪ 博主 ∪ 博主组
    from app.services.crawl_scope import resolve_crawl_scope
    scope = resolve_crawl_scope(db, city, payload.model_dump())
    if not scope.keywords and not scope.bloggers:
        raise HTTPException(422, '所选关键词组/博主组均无启用项，请检查配置')
    now = datetime.now(timezone.utc)
    task=CrawlTask(type=payload.type,status='PENDING',run_token=str(uuid4()),params=payload.model_dump(),started_at=now); db.add(task); db.commit(); db.refresh(task)
    from app.tasks.crawl_task import run_crawl
    run_crawl.delay(task.id,task.run_token)
    return {'code':202,'message':'success','data':dump(task)}

@router.post('/{task_id}/restart',status_code=status.HTTP_202_ACCEPTED)
def restart(task_id:int,_:Admin,db:DB):
    task=db.get(CrawlTask,task_id)
    if not task: raise HTTPException(404,'任务不存在')
    if task.status not in ['FAILED','STOPPED','STOP_REQUESTED','PAUSED']: raise HTTPException(409,'仅失败、已停止或等待登录任务可以继续抓取')
    running=db.scalar(select(CrawlTask).where(CrawlTask.id!=task_id,CrawlTask.status.in_(['PENDING','RUNNING','STOP_REQUESTED','SEARCH_DONE','DOWNLOADING','PROCESSING','DEDUPING'])))
    if running: raise HTTPException(409,'TASK_IN_PROGRESS')
    city_code=task.params.get('city')
    # city 可选：未传 / 空字符串 = 不限城市。原任务如显式配置城市，城市被停用时报错
    city = None
    if city_code:
        city = db.scalar(select(City).where(City.code == city_code, City.enabled.is_(True)))
        if not city:
            raise HTTPException(422, '原任务城市已停用')
    if task.status == 'PAUSED':
        try:
            OpenCLIAdapter(get_settings()).check_login()
        except AuthenticationRequired as exc:
            raise HTTPException(409,'AUTH_REQUIRED') from exc
    if task.status == 'FAILED': task.failed_notes=0
    task.status='PENDING';task.run_token=str(uuid4());task.error_message=None;task.current_stage=None;task.current_note=None;task.finished_at=None
    # 重新启动后更新 started_at，让仪表盘 last_task 排序优先看到本次
    task.started_at=datetime.now(timezone.utc)
    db.add(TaskLog(task_id=task.id,level='INFO',message='任务继续抓取',created_at=datetime.now(timezone.utc)))
    db.commit();db.refresh(task)
    from app.tasks.crawl_task import run_crawl
    run_crawl.delay(task.id,task.run_token)
    return {'code':202,'message':'success','data':dump(task)}

@router.post('/{task_id}/stop',status_code=status.HTTP_202_ACCEPTED)
def stop(task_id:int,_:Admin,db:DB):
    task=db.get(CrawlTask,task_id)
    if not task: raise HTTPException(404,'任务不存在')
    if task.status in {'STOPPED','STOP_REQUESTED','COMPLETED','COMPLETED_WITH_ERRORS'}:
        return {'code':202,'message':'success','data':dump(task)}
    close_verification_session = task.status == 'PAUSED' and '安全验证' in (task.error_message or '')
    if task.status in {'PENDING','FAILED','PAUSED'}:
        task.status='STOPPED';task.current_stage=None;task.current_note=None;task.finished_at=datetime.now(timezone.utc)
    elif task.status == 'RUNNING':
        task.status='STOP_REQUESTED';task.current_stage=None;task.current_note=None
    else:
        raise HTTPException(409,'当前状态不支持结束抓取')
    # 必须先提交停止状态再 kill 子进程。worker 在子进程退出后会重新检查数据库；
    # 如果先 kill，它可能仍读到 RUNNING 并把正常停止误判为 FAILED。
    db.commit()
    if close_verification_session:
        try:
            OpenCLIAdapter(get_settings()).close_session()
        except Exception as exc:
            db.add(TaskLog(task_id=task.id,level='WARNING',message=f'关闭验证页面失败：{exc}',created_at=datetime.now(timezone.utc)))
            db.commit()
    from app.services.task_registry import kill as kill_task_pid
    pid_killed = kill_task_pid(task_id, run_token=task.run_token, timeout=5.0)
    db.add(TaskLog(task_id=task.id,level='INFO',message=f'已请求停止抓取（状态置为 {task.status}, 子进程已 kill={pid_killed}）',created_at=datetime.now(timezone.utc)))
    db.commit();db.refresh(task)
    return {'code':202,'message':'success','data':dump(task)}
@router.get('/{task_id}/logs')
def logs(task_id:int,_:Admin,db:DB): return {'code':200,'message':'success','data':[dump(x) for x in db.scalars(select(TaskLog).where(TaskLog.task_id==task_id).order_by(TaskLog.id)).all()]}


@router.delete('/batch')
def batch_delete(payload: BatchDeleteIn, _: Admin, db: DB):
    """批量软/硬删除抓取任务。

    校验：
    - ids 长度 1..100；
    - 每个 id 必须存在，否则返回 422 + 具体 id。
    """
    if len(payload.ids) < 1:
        raise HTTPException(422, '请选择要删除的任务（ids 不能为空）')
    if len(payload.ids) > 100:
        raise HTTPException(422, '一次最多删除 100 条任务')
    rows = db.scalars(select(CrawlTask).where(CrawlTask.id.in_(payload.ids))).all()
    existing_ids = {row.id for row in rows}
    missing = [task_id for task_id in payload.ids if task_id not in existing_ids]
    if missing:
        raise HTTPException(422, f'以下任务不存在：{",".join(str(mid) for mid in missing)}')
    db.execute(sa_delete(TaskLog).where(TaskLog.task_id.in_(payload.ids)))
    for row in rows:
        db.delete(row)
    db.commit()
    return {
        'code': 200,
        'message': 'success',
        'data': {'deleted_count': len(rows), 'deleted_ids': sorted(existing_ids)},
    }
