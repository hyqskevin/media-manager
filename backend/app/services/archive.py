import shutil
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from openpyxl import Workbook

from app.models.activity import Activity
from app.models.note import Note, NoteImage

_LOCAL_TZ = ZoneInfo("Asia/Shanghai")


def resolve_storage_path(data_dir:Path,image_dir:Path,key:str)->Path:
    data_path=data_dir/key
    if data_path.exists(): return data_path
    return image_dir/key


def iso_week_folder_name(started_at: datetime) -> str:
    reference = started_at if started_at.tzinfo else started_at.replace(tzinfo=ZoneInfo("UTC"))
    iso_year, iso_week, _ = reference.astimezone(_LOCAL_TZ).isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def archive_task_folder(root: Path, started_at: datetime, task_id: int, city_code: str) -> Path:
    folder = root / city_code / iso_week_folder_name(started_at) / f"task-{task_id}"
    (folder / "images").mkdir(parents=True, exist_ok=True)
    return folder


def write_activity_exports(folder: Path, task_id: int, activities: list[Activity], image_links: dict[int, list[str]] | None = None) -> None:
    image_links = image_links or {}
    markdown = [f"# 活动抽取结果（任务 {task_id}）", ""]
    for item in activities:
        linked_images = image_links.get(item.id or 0, [])
        if not linked_images:
            linked_images = [f"来源图片 {index}" for index in (item.source_image_indexes or [])]
        markdown.extend([f"## {item.name}", "", f"- 时间：{item.start_time.isoformat() if item.start_time else '待确认'}", f"- 地点：{item.location}", f"- 费用：{item.price}", f"- 类型：{item.type}", f"- 来源图片：{'、'.join(linked_images)}", f"- 原文链接：{item.source_url}", f"- 简介：{item.summary}", ""])
    (folder / "activities.md").write_text("\n".join(markdown), encoding="utf-8")

    workbook = Workbook(); sheet = workbook.active; sheet.title = "活动"
    sheet.append(["活动名称", "开始时间", "结束时间", "地点", "费用", "类型", "来源图片", "原文链接", "简介"])
    for item in activities:
        sheet.append([item.name, item.start_time.isoformat() if item.start_time else "", item.end_time.isoformat() if item.end_time else "", item.location, item.price, item.type, ",".join(map(str, item.source_image_indexes or [])), item.source_url, item.summary])
    workbook.save(folder / "activities.xlsx")


def archive_task_result(root: Path, started_at: datetime, task_id: int, note: Note, image_rows: list[tuple[Path, NoteImage]], activities: list[Activity], city_code: str) -> Path:
    folder = archive_task_folder(root, started_at, task_id, city_code)
    source_sections = [f"# {note.title}", "", f"- 原文链接：{note.source_url}", "", "## 正文", "", note.content, "", "## 图片 OCR", ""]
    image_links:dict[int,str]={}
    for index, (source, image) in enumerate(image_rows, 1):
        suffix = source.suffix.lower() or ".jpg"
        filename = f"{note.platform_note_id}_{index:02d}{suffix}"
        target = folder / "images" / filename
        if source.resolve() != target.resolve(): shutil.copy2(source, target)
        image.storage_key = target.relative_to(root.parent).as_posix()
        relative=f"images/{filename}"; image_links[index]=relative
        source_sections.extend([f"### 图片 {index}：{filename}", "", f"![图片 {index}]({relative})", "", image.ocr_text or f"OCR {image.ocr_status}", ""])
    source_path = folder / "source.md"
    existing = source_path.read_text(encoding="utf-8") if source_path.exists() else ""
    start=f"<!-- NOTE:{note.id}:START -->"; end=f"<!-- NOTE:{note.id}:END -->"; section=f"{start}\n"+"\n".join(source_sections)+f"\n{end}"
    pattern=rf"{re.escape(start)}.*?{re.escape(end)}"
    if re.search(pattern,existing,flags=re.S): updated=re.sub(pattern,section,existing,flags=re.S)
    elif note.source_url in existing: updated=section
    else: updated=existing+("\n\n---\n\n" if existing else "")+section
    source_path.write_text(updated, encoding="utf-8")

    activity_image_links = {
        item.id or 0: [f"[来源图片 {index}]({image_links[index]})" if index in image_links else f"来源图片 {index}" for index in (item.source_image_indexes or [])]
        for item in activities
        if item.note_id == note.id
    }
    write_activity_exports(folder, task_id, activities, activity_image_links)
    return folder
