import json
import logging
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from app.core.config import Settings
from app.services.crawler import AuthenticationRequired, OpenCLITimeout, OpenCLIError, VerificationRequired, is_verification_required

logger = logging.getLogger(__name__)


class OpenCLIAdapter:
    def __init__(
        self,
        settings: Settings,
        session: str = "xhs-crawler",
        cdp_endpoint: str | None = None,
    ) -> None:
        """opencli 子进程适配器。

        Args:
            settings: 全局配置
            session: opencli browser session 名（逻辑命名空间）
            cdp_endpoint: 可选 CDP 端点 URL（如 http://127.0.0.1:9223）。传了后
                所有子进程通过环境变量 OPENCLI_CDP_ENDPOINT=<endpoint> 路由到对应
                Chrome 实例，实现账号级 cookie 隔离。
                None = 用当前 Chrome Browser Bridge 默认 profile（向后兼容）。
        """
        self.settings = settings
        self.session = session
        self.cdp_endpoint = cdp_endpoint
        self._bin = (settings.opencli_bin or "opencli").strip() or "opencli"
        self._current_task_id: int | None = None
        self._current_run_token: str | None = None
        self._execution_guard: Callable[[], None] | None = None
        self._warning_sink: Callable[[str], None] | None = None
        self._preserve_browser_tab = False

    def bind_task(
        self,
        task_id: int,
        run_token: str | None = None,
        execution_guard: Callable[[], None] | None = None,
        warning_sink: Callable[[str], None] | None = None,
    ) -> None:
        """绑定当前抓取任务 ID；所有后续 run() 调用都会注册到 task_registry。

        用法：
            adapter.bind_task(task.id)
            ... # 所有 run() 调用都会带 task_id
        """
        self._current_task_id = task_id
        self._current_run_token = run_token
        self._execution_guard = execution_guard
        self._warning_sink = warning_sink

    def _assert_execution_active(self, enforce_execution: bool) -> None:
        if enforce_execution and self._execution_guard is not None:
            self._execution_guard()

    def _warn(self, message: str) -> None:
        try:
            if self._warning_sink is not None:
                self._warning_sink(message)
            else:
                logger.warning(message)
        except Exception:
            logger.exception("OpenCLI warning sink failed")

    def _close_browser_tab(self) -> None:
        if self._preserve_browser_tab:
            return
        try:
            self.run(
                ["browser", self.session, "close"],
                enforce_execution=False,
                timeout=10,
            )
        except Exception as exc:
            self._warn(f"浏览器标签页清理失败: {exc}")

    def close_session(self) -> None:
        """Explicitly close a preserved crawler session after the user ends a paused task."""
        self._preserve_browser_tab = False
        self._close_browser_tab()

    @staticmethod
    def _kill_and_reap(proc: subprocess.Popen) -> None:
        if proc.poll() is None:
            proc.kill()
        proc.communicate()

    def _command_timeout(self) -> int:
        # Python 层超时 = opencli 内部超时 + 30 秒缓冲，缩短超时让 worker 能及时响应停止信号
        try:
            inner = int(os.environ.get('OPENCLI_BROWSER_COMMAND_TIMEOUT', '30'))
        except (TypeError, ValueError):
            inner = 30
        return max(inner + 30, 60)
    def run(
        self,
        args:list[str],
        *,
        task_id: int | None = None,
        run_token: str | None = None,
        enforce_execution: bool = True,
        timeout: int | None = None,
    ) -> Any:
        """执行 opencli 子进程命令。

        Args:
            args: opencli 子命令及参数
            task_id: 当前抓取任务 ID；如果传了，会把子进程 PID 注册到 task_registry，
                让用户点"停止抓取"时能立即 SIGTERM 当前 note。
                如果没传，使用 adapter._current_task_id（由 bind_task 设置）。
        """
        effective_task_id = task_id if task_id is not None else self._current_task_id
        effective_run_token = run_token if run_token is not None else self._current_run_token
        self._assert_execution_active(enforce_execution)
        effective_timeout = timeout if timeout is not None else self._command_timeout()
        # 注入 OPENCLI_CDP_ENDPOINT（如有）让 opencli 路由到指定 Chrome 实例
        proc_env = None
        if self.cdp_endpoint:
            import os as _os
            proc_env = {**_os.environ, "OPENCLI_CDP_ENDPOINT": self.cdp_endpoint}
        try:
            proc = subprocess.Popen(
                [self._bin, *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=proc_env,
            )
        except FileNotFoundError:
            raise OpenCLIError(
                f"opencli 不可用：未找到命令 {self._bin!r}"
                "（请运行 npm install -g @jackwener/opencli 或在 .env 配置 OPENCLI_BIN 指向其绝对路径）"
            )
        if effective_task_id is not None:
            from app.services.task_registry import register, unregister
            register(effective_task_id, proc.pid, run_token=effective_run_token)
        try:
            try:
                self._assert_execution_active(enforce_execution)
            except Exception:
                self._kill_and_reap(proc)
                raise
            try:
                stdout, stderr = proc.communicate(timeout=effective_timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                raise OpenCLITimeout(f'opencli 命令执行超过 {effective_timeout}s 被强制终止: {args}')
        finally:
            if effective_task_id is not None:
                from app.services.task_registry import unregister
                unregister(effective_task_id, run_token=effective_run_token)
        # 子进程可能由停止接口在另一进程中 kill。此时 -9 只是停止动作的结果，
        # 必须先重新读取任务所有权，避免把正常停止误写成 OpenCLIError/FAILED。
        self._assert_execution_active(enforce_execution)
        output = (stdout or "").strip()
        error_output = (stderr or "").strip() or output
        if proc.returncode and is_verification_required(f"{output}\n{error_output}"):
            self._preserve_browser_tab = True
            raise VerificationRequired("检测到小红书安全验证，请在 Chrome 完成后点击检测登录并继续")
        if proc.returncode == 77:
            raise AuthenticationRequired('请在 Chrome 登录小红书后重试')
        if proc.returncode == 75:
            # opencli 内部命令超时；提示用户调大 OPENCLI_BROWSER_COMMAND_TIMEOUT
            stderr_str = error_output
            raise OpenCLITimeout(
                f'opencli 内部命令超时（exit 75）：{stderr_str}；可调大 .env 中的 OPENCLI_BROWSER_COMMAND_TIMEOUT'
            )
        if proc.returncode:
            stderr_str = error_output
            # opencli 在 url/参数为空时返回 "✖ Missing url"
            if 'Missing url' in stderr_str:
                raise OpenCLIError(
                    f'opencli 缺少 url 参数：{args}；请检查笔记/博主链接是否为空'
                )
            raise OpenCLIError(stderr_str)
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output
    def check_login(self, foreground: bool = False):
        """登录预检：whoami 是轻量只读探测，正常 1~2s 返回。

        未扫码登录时 opencli 的 whoami 会在浏览器层阻塞等待扫码（不会以 exit 77
        快速退出），最终被 Python 层超时 kill。这种超时唯一现实诱因就是登录窗口
        等扫码，归类为 AuthenticationRequired，让任务走 PAUSED 流程提示用户扫码，
        而不是被当作普通抓取失败逐个博主/笔记白等 60s。

        foreground=True：拉起前台可见窗口，给用户扫码（管理后台 check-login 用）
        foreground=False：后台窗口（默认，run_crawl 启动预检用，不打扰用户）
        """
        cmd = ['xiaohongshu', 'whoami', '-f', 'json']
        if not foreground:
            cmd += ['--window', 'background']
        try:
            return self.run(cmd)
        except OpenCLITimeout as exc:
            raise AuthenticationRequired(
                '小红书登录检查超时：可能未登录或登录窗口正在等待扫码，'
                '请完成扫码登录后点击「继续抓取」'
            ) from exc
    @staticmethod
    def normalize_note(value:Any)->dict[str,Any]:
        if isinstance(value,dict): return value
        if isinstance(value,list) and all(isinstance(row,dict) and 'field' in row for row in value):
            return {str(row['field']):row.get('value') for row in value}
        raise OpenCLIError(f'unexpected note response: {type(value).__name__}')
    def _click_filter_option(self,text:str) -> None:
        target=json.dumps(text,ensure_ascii=False)
        script=f"""(() => {{ const targetText={target}; const span=[...document.querySelectorAll('.filter .tags span')].find(e=>e.textContent?.trim()===targetText); const option=span?.closest('.tags'); if(!option) return false; option.click(); return true }})()"""
        if not self.run(['browser',self.session,'eval',script]): raise OpenCLIError(f'filter option not found: {text}')
    def _open_filter_panel(self) -> None:
        probe="""(() => { const optionExists=[...document.querySelectorAll('.filter .tags span')].some(e=>e.textContent?.trim()==='最新'); return optionExists })()"""
        for _ in range(3):
            self.run(['browser',self.session,'click','.search-layout__top .filter'])
            self.run(['browser',self.session,'wait','time','1'])
            if self.run(['browser',self.session,'eval',probe]): return
        raise OpenCLIError('filter option not found: 最新')
    def search_recent(self,query:str,recent_filter:str='一周内')->list[dict[str,Any]]:
        if not query or not query.strip():
            raise OpenCLIError(f'search_recent: 查询关键词为空（query={query!r}）')
        # 前端文案 "当天" 对应小红书的 "一天内"（搜索面板无"当天"按钮）
        _FILTER_ALIAS = {'当天': '一天内'}
        actual_filter = _FILTER_ALIAS.get(recent_filter, recent_filter)
        self.check_login(); url=f'https://www.xiaohongshu.com/search_result?keyword={quote_plus(query)}'
        try:
            self.run(['browser',self.session,'open',url,'--window','background'])
            self.run(['browser',self.session,'wait','time','2'])
            self._open_filter_panel(); self._click_filter_option('最新')
            if recent_filter != '不限': self._click_filter_option(actual_filter)
            self.run(['browser',self.session,'wait','time','2'])
            script=r"""(() => Array.from(document.querySelectorAll('section')).map(s => { const links=[...s.querySelectorAll('a[href*="/search_result/"]')]; const title=s.querySelector('a[href*="/search_result/"] span')?.textContent?.trim(); const time=[...s.querySelectorAll('div')].map(x=>x.textContent?.trim()).find(x=>/^(\d+分钟前|\d+小时前|\d+天前|\d{2}-\d{2})$/.test(x||'')); return title&&links[0]?{title,url:new URL(links[0].getAttribute('href'),location.origin).href,published_text:time||''}:null }).filter(Boolean))()"""
            previous=0; stagnant=0; items=[]
            for _ in range(self.settings.xhs_search_scroll_max_rounds+1):
                items=self.run(['browser',self.session,'eval',script]) or []
                if len(items)>=self.settings.xhs_search_target_count: break
                stagnant=stagnant+1 if len(items)<=previous else 0
                if stagnant>=self.settings.xhs_scroll_stagnant_rounds: break
                previous=len(items); self.run(['browser',self.session,'scroll','down','--amount',str(self.settings.xhs_scroll_pixels)]); self.run(['browser',self.session,'wait','time','1'])
            return items[:self.settings.xhs_search_target_count]
        finally:
            self._close_browser_tab()
    def note(self,url:str)->dict[str,Any]:
        if not url or not url.strip():
            raise OpenCLIError(f'note: 笔记 url 为空，无法抓取详情')
        self.check_login()
        try:
            self.run(['browser',self.session,'open',url,'--window','background'])
            self.run(['browser',self.session,'wait','time','2'])
            previous=0; stagnant=0
            for _ in range(self.settings.xhs_detail_scroll_max_rounds):
                height=int(self.run(['browser',self.session,'eval','document.documentElement.scrollHeight']) or 0)
                stagnant=stagnant+1 if height<=previous else 0
                if stagnant>=self.settings.xhs_scroll_stagnant_rounds: break
                previous=height
                self.run(['browser',self.session,'scroll','down','--amount',str(self.settings.xhs_scroll_pixels)])
                self.run(['browser',self.session,'wait','time','1'])
            return self.normalize_note(self.run(['xiaohongshu','note',url,'-f','json','--window','background']))
        finally:
            self._close_browser_tab()
    def blogger_notes(self, username: str, profile_url: str = "") -> list[dict[str,Any]]:
        """博主笔记抓取：通过 user 命令拿带 xsec_token 的完整 URL。

        Args:
            username: 博主的用户名（返回结果中使用）
            profile_url: 博主主页 URL，从中提取 user-id（必填）

        Returns:
            list of {"title": str, "url": str, "author": str}，url 必须带 xsec_token
        """
        if not profile_url or not profile_url.strip():
            raise OpenCLIError(f'blogger_notes: profile_url 为空，跳过该博主')
        match = re.search(r'/user/profile/([^/?]+)', profile_url)
        if not match:
            raise OpenCLIError(f'blogger_notes: 无法从 profile_url 提取 user-id: {profile_url}')
        user_id = match.group(1)
        self.check_login()
        results = self.run(['xiaohongshu', 'user', user_id, '-f', 'json', '--window', 'background']) or []
        notes: list[dict[str, Any]] = []
        for item in results:
            url = (item.get('url') or '').strip()
            if not url or 'xsec_token' not in url:
                continue
            notes.append({
                'title': (item.get('title') or '博主笔记').strip(),
                'url': url,
                'author': username.strip() if username else '',
            })
        return notes[:self.settings.xhs_search_target_count]
    def download(self,url:str,output_dir:Path)->list[Path]:
        if not url or not url.strip():
            raise OpenCLIError(f'download: 笔记 url 为空，无法下载图片')
        self.check_login(); output_dir.mkdir(parents=True,exist_ok=True)
        before={path.resolve() for path in output_dir.rglob('*') if path.is_file()}
        self.run(['xiaohongshu','download',url,'--output',str(output_dir),'-f','json','--window','background'])
        suffixes={'.jpg','.jpeg','.png','.webp','.bmp'}
        return sorted(path for path in output_dir.rglob('*') if path.is_file() and path.resolve() not in before and path.suffix.lower() in suffixes)
