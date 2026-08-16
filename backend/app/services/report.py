import re
from io import BytesIO
from urllib.parse import quote

from openpyxl import Workbook

from app.core.config import get_settings
from app.models.activity import Activity
from app.models.note import Note, NoteImage


CITY_NAMES = {"shanghai": "上海", "beijing": "北京"}

# 匹配周报生成的内联图片行，如：![图片 1](/api/v1/reports/image/xxx.jpg)
_IMAGE_LINE_RE = re.compile(r"^\s*!\[图片 \d+\]\([^)]*\)\s*$")


def _image_markdown_src(image: NoteImage) -> str | None:
    """返回图片在预览里的可访问 URL：优先本地 storage_key，回退 original_url。"""
    if image.storage_key:
        prefix = get_settings().api_v1_prefix
        return f"{prefix}/reports/image/{quote(image.storage_key)}"
    if image.original_url:
        return image.original_url
    return None


def strip_report_images(markdown: str) -> str:
    """去掉周报正文里生成的内联图片行（用于 md 下载，不输出图片地址）。"""
    return "\n".join(line for line in markdown.splitlines() if not _IMAGE_LINE_RE.match(line))


def format_activity_markdown(activity: Activity) -> str:
    start = activity.start_time.strftime("%Y-%m-%d %H:%M") if activity.start_time else "待确认"
    end = activity.end_time.strftime("%H:%M") if activity.end_time else ""
    time_text = f"{start} - {end}" if end else start
    return f"#### {activity.name}\n- **时间**：{time_text}\n- **地点**：{activity.location}\n- **费用**：{activity.price}\n- **来源**：[小红书笔记]({activity.source_url})\n- **简介**：{activity.summary}\n"


NoteReportEntry = tuple[Note, list[Activity], list[NoteImage]]


def _activity_lines(activities: list[Activity]) -> str:
    return "\n".join(
        f"{item.name} | {item.start_time.isoformat() if item.start_time else '时间待确认'} | {item.location} | {item.price} | {item.summary}"
        for item in activities
    )


def generate_note_markdown(week: str, cities: list[str], entries: list[NoteReportEntry]) -> str:
    lines = [f"# 本周推文周报（{week}）", "", f"城市：{'、'.join(CITY_NAMES.get(city, city) for city in cities)}", ""]
    for note, activities, images in entries:
        published = note.published_at.isoformat() if note.published_at else f"{note.created_at.isoformat()}（发布时间待确认）"
        image_lines = [f"![图片 {index}]({src})" for index, src in enumerate(
            (s for s in (_image_markdown_src(image) for image in images) if s), 1
        )]
        ocr = "\n\n".join(image.ocr_text for image in images if image.ocr_text)
        lines.extend([
            f"## {note.title}", "",
            f"- 发布时间：{published}",
            f"- 原文链接：{note.source_url}", "",
        ])
        for line in image_lines:
            lines.extend([line, ""])
        lines.extend([
            "### 推文正文", "", note.content or "无", "",
            "### 图片 OCR", "", ocr or "无", "",
            f"### 识别活动（{len(activities)}）", "",
        ])
        if activities:
            for item in activities:
                lines.extend([format_activity_markdown(item), ""])
        else:
            lines.extend(["未识别到活动", ""])
    return "\n".join(lines)


def generate_note_xlsx(entries: list[NoteReportEntry]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "本周推文"
    sheet.append(["推文标题", "发布时间", "城市", "原文链接", "正文", "OCR", "活动数", "活动详情"])
    for note, activities, images in entries:
        published = note.published_at.isoformat() if note.published_at else f"{note.created_at.isoformat()}（待确认）"
        ocr = "\n".join(image.ocr_text for image in images if image.ocr_text)
        sheet.append([note.title, published, CITY_NAMES.get(note.city_code, note.city_code), note.source_url, note.content, ocr, len(activities), _activity_lines(activities)])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
