import json
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.settings._deps import DB
from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.activity import Activity
from app.models.blogger_group import BloggerGroup
from app.models.config import Blogger, City
from app.models.keyword_group import KeywordGroup
from app.models.note import Note, NoteImage
from app.models.report import WeeklyReport
from app.services.report import generate_note_markdown, generate_note_xlsx, strip_report_images


router = APIRouter(prefix="/reports", tags=["reports"])


class GenerateRequest(BaseModel):
    week: str
    cities: list[str] = Field(default_factory=list)
    # 可选：按关键词/关键词组/博主/博主组进一步过滤；任一为空表示不应用该维度
    keyword_group_ids: list[int] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    blogger_group_ids: list[int] = Field(default_factory=list)
    blogger_ids: list[int] = Field(default_factory=list)


def week_bounds(week: str) -> tuple[datetime, datetime]:
    """返回 ISO 周的 naive 边界（北京墙钟口径，与 Note.published_at 存储一致）。"""
    match = re.fullmatch(r"(\d{4})-W(\d{2})", week)
    if match is None:
        raise ValueError("invalid ISO week")
    try:
        start = datetime.fromisocalendar(int(match.group(1)), int(match.group(2)), 1)
    except ValueError as exc:
        raise ValueError("invalid ISO week") from exc
    return start, start + timedelta(days=7)


def select_notes(db: Session, payload: "GenerateRequest"):
    """从 payload 拉取符合条件的 note：city + 关键词/关键词组 + 博主/博主组；任一过滤为空则跳过该维度。"""
    start, end = week_bounds(payload.week)
    stmt = select(Note).where(
        Note.review_status == "APPROVED",
        Note.published_at.is_not(None),
        Note.published_at >= start,
        Note.published_at < end,
    )
    if payload.cities:
        stmt = stmt.where(Note.city_code.in_(payload.cities))
    # 关键词组：展开组内关键词 + 直接关键词
    keyword_set: set[str] = set(payload.keywords or [])
    if payload.keyword_group_ids:
        from app.models.keyword_group import KeywordGroupWord, KeywordGroup
        rows = db.execute(
            select(KeywordGroupWord.word)
            .join(KeywordGroup, KeywordGroup.id == KeywordGroupWord.keyword_group_id)
            .where(KeywordGroup.id.in_(payload.keyword_group_ids), KeywordGroupWord.enabled.is_(True))
        ).all()
        keyword_set.update(row[0] for row in rows if row[0])
    if keyword_set:
        # 用 Note.matched_keywords JSON list 或标题/内容模糊匹配
        # matched_keywords 是 JSON 数组文本，用 LIKE 子串匹配
        from sqlalchemy import or_
        like_clauses = [Note.matched_keywords.like(f"%{kw}%") for kw in keyword_set]
        like_clauses.extend([Note.title.ilike(f"%{kw}%") for kw in keyword_set])
        stmt = stmt.where(or_(*like_clauses))
    # 博主过滤
    blogger_id_set: set[int] = set(payload.blogger_ids or [])
    if payload.blogger_group_ids:
        from app.models.blogger_group import BloggerGroupMember
        rows = db.scalars(
            select(BloggerGroupMember.blogger_id).where(BloggerGroupMember.group_id.in_(payload.blogger_group_ids))
        ).all()
        blogger_id_set.update(rows)
    if blogger_id_set:
        stmt = stmt.where(Note.matched_blogger_id.in_(blogger_id_set))
    notes = list(db.scalars(stmt.order_by(Note.published_at, Note.id)).all())
    entries = []
    for note in notes:
        activities = list(db.scalars(
            select(Activity)
            .where(Activity.note_id == note.id, Activity.deleted_at.is_(None))
            .order_by(Activity.id)
        ).all())
        images = list(db.scalars(select(NoteImage).where(NoteImage.note_id == note.id).order_by(NoteImage.id)).all())
        entries.append((note, activities, images))
    return entries


def report_signature(week: str, cities: list[str], kg_ids: list[int], keywords: list[str], bg_ids: list[int], blogger_ids: list[int]) -> str:
    """规范化组合签名：week + 各筛选维度（排序）拼接，用于判重。"""
    def _join(items: list) -> str:
        return "\x1f".join(sorted(str(i) for i in items))
    return "\x1f".join([week, _join(cities), _join(kg_ids), _join(keywords), _join(bg_ids), _join(blogger_ids)])


def build_report_name(db: Session, week: str, cities: list[str], kg_ids: list[int], keywords: list[str], bg_ids: list[int], blogger_ids: list[int]) -> str:
    """自动拼接可读名称：week · 城市 · 关键词/关键词组 · 博主/博主组。"""
    parts = [week]
    if cities:
        rows = db.execute(select(City.code, City.name).where(City.code.in_(cities))).all()
        name_by_code = {code: name for code, name in rows}
        parts.append("、".join(name_by_code.get(code, code) for code in cities))
    if kg_ids:
        names = db.scalars(select(KeywordGroup.name).where(KeywordGroup.id.in_(kg_ids))).all()
        parts.append("关键词组：" + "、".join(names))
    if keywords:
        parts.append("关键词：" + "、".join(keywords))
    if bg_ids:
        names = db.scalars(select(BloggerGroup.name).where(BloggerGroup.id.in_(bg_ids))).all()
        parts.append("博主组：" + "、".join(names))
    if blogger_ids:
        names = db.scalars(select(Blogger.username).where(Blogger.id.in_(blogger_ids))).all()
        parts.append("博主：" + "、".join(names))
    return " · ".join(parts)

@router.get("")
def list_reports(_: Annotated[dict[str,str],Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):
    rows=db.scalars(select(WeeklyReport).order_by(WeeklyReport.id.desc())).all()
    return {'code':200,'message':'success','data':[{'id':x.id,'week':x.week,'name':x.name,'cities':json.loads(x.cities),'keyword_group_ids':json.loads(x.keyword_group_ids),'keywords':json.loads(x.keywords),'blogger_group_ids':json.loads(x.blogger_group_ids),'blogger_ids':json.loads(x.blogger_ids),'note_count':x.note_count,'activity_count':x.activity_count,'status':x.status,'created_at':x.created_at.isoformat()} for x in rows]}

@router.get("/{report_id}")
def get_report(report_id:int,_:Annotated[dict[str,str],Depends(get_current_user)],db:Annotated[Session,Depends(get_db)]):
    report=db.get(WeeklyReport,report_id)
    if not report: raise HTTPException(404,'周报不存在')
    return {'code':200,'message':'success','data':{'id':report.id,'week':report.week,'name':report.name,'cities':json.loads(report.cities),'keyword_group_ids':json.loads(report.keyword_group_ids),'keywords':json.loads(report.keywords),'blogger_group_ids':json.loads(report.blogger_group_ids),'blogger_ids':json.loads(report.blogger_ids),'activity_count':report.activity_count,'status':report.status,'content':report.content}}


@router.post("/generate")
def generate_report(payload: GenerateRequest, _: Annotated[dict[str, str], Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    try:
        entries = select_notes(db, payload)
    except ValueError:
        raise HTTPException(status_code=422, detail="周次格式无效，请使用 YYYY-Www") from None
    if not entries:
        raise HTTPException(status_code=422, detail="所选城市和周次没有已审核推文，请先在活动管理中审核通过")
    note_count = len(entries)
    activity_count = sum(len(activities) for _, activities, _ in entries)
    content = generate_note_markdown(payload.week, payload.cities, entries)
    signature = report_signature(payload.week, payload.cities, payload.keyword_group_ids, payload.keywords, payload.blogger_group_ids, payload.blogger_ids)
    report = db.scalar(select(WeeklyReport).where(WeeklyReport.signature == signature))
    if report is None:
        report = WeeklyReport(
            week=payload.week,
            name=build_report_name(db, payload.week, payload.cities, payload.keyword_group_ids, payload.keywords, payload.blogger_group_ids, payload.blogger_ids),
            signature=signature,
            cities=json.dumps(payload.cities),
            keyword_group_ids=json.dumps(payload.keyword_group_ids),
            keywords=json.dumps(payload.keywords),
            blogger_group_ids=json.dumps(payload.blogger_group_ids),
            blogger_ids=json.dumps(payload.blogger_ids),
            note_count=note_count,
            activity_count=activity_count,
            content=content,
            status="draft",
        )
        db.add(report)
    else:
        report.week = payload.week
        report.name = build_report_name(db, payload.week, payload.cities, payload.keyword_group_ids, payload.keywords, payload.blogger_group_ids, payload.blogger_ids)
        report.cities = json.dumps(payload.cities)
        report.keyword_group_ids = json.dumps(payload.keyword_group_ids)
        report.keywords = json.dumps(payload.keywords)
        report.blogger_group_ids = json.dumps(payload.blogger_group_ids)
        report.blogger_ids = json.dumps(payload.blogger_ids)
        report.note_count = note_count
        report.activity_count = activity_count
        report.content = content
        report.status = "draft"
        report.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(report)
    return {"code": 200, "message": "success", "data": {"id": report.id, "week": report.week, "name": report.name, "cities": payload.cities, "keyword_group_ids": payload.keyword_group_ids, "keywords": payload.keywords, "blogger_group_ids": payload.blogger_group_ids, "blogger_ids": payload.blogger_ids, "note_count": report.note_count, "activity_count": report.activity_count, "status": report.status}}


@router.delete("/{report_id}")
def delete_report(report_id: int, _: Annotated[dict[str, str], Depends(get_current_user)], db: Annotated[Session, Depends(get_db)]):
    report = db.get(WeeklyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="周报不存在")
    db.delete(report)
    db.commit()
    return {"code": 200, "message": "success", "data": {"id": report_id}}


@router.get("/image/{storage_key:path}")
def report_image(storage_key: str, _: DB = None):
    """无鉴权地返回周报引用的本地图片（供预览 <img> 直接加载）。

    安全：resolve 后必须仍在 data_dir 内，防止目录穿越。
    """
    data_root = get_settings().data_dir.resolve()
    path = (data_root / storage_key).resolve()
    if not path.is_relative_to(data_root) or not path.is_file():
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(path)


@router.get("/{report_id}/download")
def download_report(report_id: int, _: Annotated[dict[str, str], Depends(get_current_user)], db: Annotated[Session, Depends(get_db)], format: Annotated[Literal["md", "xlsx"], Query()] = "md"):
    report = db.get(WeeklyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="周报不存在")
    base = re.sub(r"[^\w\u4e00-\u9fff-]", "_", report.name or report.week)
    base = re.sub(r"_+", "_", base).strip("_")
    filename = f"{base}.{format}"
    if format == "md":
        # md 下载不输出图片地址：剥离周报正文里生成的内联图片行
        content = strip_report_images(report.content)
        return Response(content, media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})
    entries = select_notes(db, GenerateRequest(
        week=report.week,
        cities=json.loads(report.cities),
        keyword_group_ids=json.loads(report.keyword_group_ids),
        keywords=json.loads(report.keywords),
        blogger_group_ids=json.loads(report.blogger_group_ids),
        blogger_ids=json.loads(report.blogger_ids),
    ))
    return Response(generate_note_xlsx(entries), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"})
