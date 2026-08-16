"""海报渲染：组装 HTML、调 Playwright 或 opencli 截图。

关联 spec: docs/superpowers/specs/2026-07-21-poster-generation-design.md

路径：
- assemble_html(template, task) -> str    纯函数，便于测试与 preview
- render_task_to_png(template, task, path) -> str  Playwright 优先，
  失败回退到 opencli。

运行时依赖：
- Playwright（可选）
- opencli（系统 CLI）作为兜底
"""
import base64
import html as html_lib
import re
import shutil
import subprocess
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.note import NoteImage
from app.models.poster import PosterTask, PosterTemplate


VIEWPORT = (1080, 1440)  # 小红书 3:4 竖版


def _escape(value: str | None) -> str:
    return html_lib.escape(value or "")


def resolve_item_image_urls(
    items: list[dict],
    db: Session,
    data_dir: str,
    mode: str = "file",
) -> list[dict]:
    """将 API 路径解析为本地路径。

    mode:
      - "file": file:// 绝对路径（Playwright set_content 用）
      - "base64": data:image/jpeg;base64,...（opencli HTTP 渲染用）
    返回新列表，不修改原 items。
    """
    if not items:
        return items
    base = Path(data_dir).resolve()
    resolved = []
    for item in items:
        item = dict(item)
        url = item.get("image_url") or ""
        m = re.match(r"/api/v1/posters/note-image-by-id/(\d+)", url)
        if m:
            image_id = int(m.group(1))
            image = db.get(NoteImage, image_id)
            if image:
                target = (base / image.storage_key).resolve()
                if target.exists():
                    if mode == "base64":
                        b64 = base64.b64encode(target.read_bytes()).decode()
                        item["image_url"] = f"data:image/jpeg;base64,{b64}"
                    else:
                        item["image_url"] = f"file://{target}"
        resolved.append(item)
    return resolved


# 卡片背景色（pastel 调色板，从参考图中提取）
CARD_COLORS = [
    "#FDF5EE",  # 浅桃色
    "#EDF3DD",  # 浅绿
    "#E6F1EF",  # 浅青
    "#EDDDCD",  # 浅米色
    "#D0E5EC",  # 浅蓝
    "#FCE4D6",  # 浅杏色
    "#E8F0E8",  # 浅薄荷
    "#F5E6D3",  # 浅驼色
]


def _render_item_html(item: dict, height: int = 0, bg_color: str = "#fff") -> str:
    fields = item.get("fields") or {}
    time_range = _escape(fields.get("time_range"))
    location = _escape(fields.get("location"))
    fee = _escape(fields.get("fee"))
    content = _escape(fields.get("content"))
    title = _escape(item.get("title") or fields.get("content") or "")
    image_url = item.get("image_url") or ""
    # 图片在右侧，文字在左侧
    img_cell = ""
    if image_url:
        img_cell = (
            f'<td class="card-img" width="240" valign="middle"'
            f' style="padding:16px;background:{bg_color};">'
            f'<img class="card-image" src="{_escape(image_url)}" alt=""'
            f' style="width:208px;height:208px;object-fit:cover;border-radius:12px;"/>'
            f'</td>'
        )
    return f'''
      <table class="card-table" border="0" cellspacing="0" cellpadding="0" width="100%" style="height:{height}px;border-radius:16px;overflow:hidden;background:{bg_color};">
        <tr style="height:{height}px;">
          <td class="card-body" valign="middle" style="padding:24px 16px 24px 28px;font-size:32px;color:#333;background:{bg_color};">
            <p class="card-title" style="margin:0 0 14px 0;font-size:40px;font-weight:800;color:#D35400;">{title}</p>
            <p style="margin:5px 0;display:flex;align-items:center;gap:10px;font-size:30px;">
              <span style="font-size:28px;">🕐</span> {time_range}
            </p>
            <p style="margin:5px 0;display:flex;align-items:center;gap:10px;font-size:30px;">
              <span style="font-size:28px;">📍</span> {location}
            </p>
            <p style="margin:5px 0;display:flex;align-items:center;gap:10px;font-size:30px;">
              <span style="font-size:28px;">🎫</span> {fee}
            </p>
            {f'<p style="margin:5px 0;color:#888;font-size:28px;">{content}</p>' if content else ''}
          </td>
          {img_cell}
        </tr>
      </table>'''.strip()


def render_poster_preview_html(
    template: PosterTemplate,
    task: PosterTask,
    items_override: list[dict] | None = None,
) -> str:
    """纯函数。返回用于 iframe 预览 / 文件落盘的完整 HTML。

    items_override: 可选，用于渲染时替换 task.items（如已解析图片 URL）。
    """
    items = items_override if items_override is not None else (task.items or [])
    items_count = max(len(items), 1)
    # 1080×1440 → 外框 16px → 内 1048×1408 → padding 40px → 可用 968×1328
    # header ~160px + gap 24px×N → 卡片区 ≈ 1328-160-24*(items_count-1) = 1168-24*items_count
    card_area = 1328 - 160 - 24 * (items_count - 1)
    card_height = max(240, card_area // items_count)
    items_wrapper_class = "items single-1" if items_count == 1 else "items"
    items_html = f'<div class="{items_wrapper_class}">' + \
        "\n".join(
            _render_item_html(
                item,
                card_height,
                bg_color=CARD_COLORS[i % len(CARD_COLORS)],
            )
            for i, item in enumerate(items)
        ) + \
        '</div>'
    css = template.css_text or ""
    body_html = template.html_template or ""
    body_html = body_html.replace("{{title}}", _escape(task.name))
    body_html = body_html.replace("{{items}}", items_html)
    base_css = (
        "*{box-sizing:border-box;margin:0;padding:0;}"
        "html,body{margin:0;padding:0;width:1080px;height:1440px;overflow:hidden;}"
        "body{font-family:'PingFang SC','Noto Sans CJK SC','Microsoft YaHei',sans-serif;"
        "background:#F26B2C;color:#333;}"  # 外框色
        ".poster-outer{width:1080px;height:1440px;padding:16px;"
        "box-sizing:border-box;background:#F26B2C;}"  # 外框 16px
        ".poster{width:1048px;height:1408px;background:#fff;"
        "display:flex;flex-direction:column;padding:40px;box-sizing:border-box;"
        "border-radius:12px;overflow:hidden;}"  # 内白卡片
        ".poster-header{text-align:center;margin-bottom:20px;flex-shrink:0;"
        "padding-bottom:16px;border-bottom:2px solid #F5E6D3;}"
        ".poster-header h1{font-size:56px;margin:0;font-weight:900;"
        "color:#D35400;letter-spacing:2px;}"
        ".poster-header .subtitle{font-size:28px;color:#C0A080;margin-top:6px;"
        "letter-spacing:4px;}"
        ".items{display:flex;flex-direction:column;gap:16px;flex:1;min-height:0;}"
        ".card-table{border-radius:16px;overflow:hidden;}"
        ".card-image{width:208px;height:208px;object-fit:cover;border-radius:12px;}"
        ".card-body{font-size:32px;color:#333;}"
        ".card-title{font-size:40px;font-weight:800;color:#D35400;}"
        ".footer{text-align:center;padding-top:12px;flex-shrink:0;"
        "font-size:22px;color:#ccc;letter-spacing:2px;}"
    )
    title_block = (
        f'<div class="poster-header"><h1>{_escape(task.name)}</h1>'
        f'<div class="subtitle">宁波周末活动精选</div></div>'
        if "{{title}}" not in (template.html_template or "") else ""
    )
    return f"""<!doctype html>
<html lang="zh">
<head>
<meta charset='utf-8'>
<style>{base_css}{css}</style>
</head>
<body>
<div class="poster-outer">
<div class="poster">
{title_block}
{body_html}
</div>
</div>
</body>
</html>"""


def _playwright_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
        return True
    except Exception:
        return False


def _playwright_render(html: str, path: str) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]})
        page = context.new_page()
        page.set_content(html, wait_until="networkidle")
        page.screenshot(path=path, full_page=True)
        browser.close()


def _opencli_render(html: str, path: str) -> None:
    """通过 opencli browser bridge 渲染 HTML → PNG。

    步骤：
    1. 写临时 html 到临时目录；
    2. 起 python http.server 暴露；
    3. opencli browser open http://... → screenshot；
    4. 清理。
    """
    import time
    import socket

    if shutil.which("opencli") is None:
        raise RuntimeError("opencli 未安装；安装 opencli 后重试")
    Path(path).parent.mkdir(parents=True, exist_ok=True)

    # 找可用端口
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    port = _free_port()
    # 临时目录放在项目内 data/tmp/ 下，避免污染系统 tempdir
    tmp_base = get_settings().tmp_dir
    tmp_base.mkdir(parents=True, exist_ok=True)
    tmp_dir = tmp_base / f"poster-render-{uuid.uuid4().hex[:8]}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_html = tmp_dir / "index.html"
    tmp_html.write_text(html, encoding="utf-8")

    server_proc = None
    try:
        server_proc = subprocess.Popen(
            [shutil.which("python3") or "python", "-m", "http.server", str(port), "--bind", "127.0.0.1"],
            cwd=tmp_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(0.5)

        url = f"http://127.0.0.1:{port}/index.html"
        open_proc = subprocess.run(
            ["opencli", "browser", "default", "open", url],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if open_proc.returncode != 0:
            raise RuntimeError(f"opencli browser open 失败: {open_proc.stderr or open_proc.stdout}")

        time.sleep(0.5)
        screenshot_proc = subprocess.run(
            ["opencli", "browser", "default", "screenshot", path,
             "--width", str(VIEWPORT[0]), "--height", str(VIEWPORT[1])],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if screenshot_proc.returncode != 0:
            raise RuntimeError(
                f"opencli browser screenshot 失败: {screenshot_proc.stderr or screenshot_proc.stdout}"
            )
    finally:
        if server_proc:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()
        try:
            shutil.rmtree(tmp_dir)
        except OSError:
            pass


def _render_html_to_png(html: str, output_path: str) -> str:
    """将 HTML 字符串渲染为 PNG。Playwright 优先，失败 fallback opencli。"""
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if _playwright_available():
        try:
            _playwright_render(html, str(output))
            return str(output)
        except Exception:
            pass
    _opencli_render(html, str(output))
    return str(output)


def render_task_to_png(
    template: PosterTemplate,
    task: PosterTask,
    output_path: str,
    db: Session | None = None,
    data_dir: str | None = None,
) -> str:
    """便捷方法：组装 HTML 后渲染为 PNG。

    db + data_dir: 可选，用于将 API 图片路径解析为本地 file:// 路径。
    """
    items = task.items or []
    if db is not None and data_dir is not None:
        items = resolve_item_image_urls(items, db, data_dir)
    html = render_poster_preview_html(template, task, items_override=items)
    return _render_html_to_png(html, output_path)
