from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal


class DownloadCancelled(Exception):
    """Raised when the user cancels an active download."""


class DownloadError(RuntimeError):
    """A user-facing download error."""


Quality = Literal["best", "1080", "720", "480"]
Mode = Literal["video", "audio"]


@dataclass(slots=True)
class DownloadOptions:
    url: str
    output_dir: Path
    mode: Mode = "video"
    quality: Quality = "best"
    playlist: bool = False
    browser: str | None = None
    proxy: str | None = None
    fallback_to_you_get: bool = True


@dataclass(slots=True)
class Progress:
    status: str
    percent: float | None = None
    speed: str = ""
    eta: str = ""
    filename: str = ""
    message: str = ""


ProgressCallback = Callable[[Progress], None]
LogCallback = Callable[[str], None]


def find_ffmpeg() -> str:
    """Return a usable ffmpeg executable, including the bundled fallback."""
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # pragma: no cover - depends on installation
        raise DownloadError(
            "未找到 ffmpeg。请重新安装依赖：pip install -e .，"
            "或从 https://ffmpeg.org 安装 ffmpeg。"
        ) from exc


class Downloader:
    def __init__(
        self,
        progress_callback: ProgressCallback | None = None,
        log_callback: LogCallback | None = None,
    ) -> None:
        self._on_progress = progress_callback or (lambda _: None)
        self._on_log = log_callback or (lambda _: None)
        self._cancelled = threading.Event()
        self._process: subprocess.Popen[str] | None = None

    def cancel(self) -> None:
        self._cancelled.set()
        process = self._process
        if process and process.poll() is None:
            process.terminate()

    def download(self, options: DownloadOptions) -> None:
        url = options.url.strip()
        if not url.startswith(("http://", "https://")):
            raise DownloadError("请输入以 http:// 或 https:// 开头的有效链接。")
        options.output_dir.expanduser().mkdir(parents=True, exist_ok=True)
        self._cancelled.clear()

        try:
            self._download_with_ytdlp(options)
        except DownloadCancelled:
            raise
        except Exception as primary_error:
            if not options.fallback_to_you_get or options.mode == "audio":
                raise self._friendly_error(primary_error) from primary_error
            self._on_log(f"yt-dlp 下载失败，尝试 you-get：{primary_error}")
            try:
                self._download_with_you_get(options)
            except DownloadCancelled:
                raise
            except Exception as fallback_error:
                raise DownloadError(
                    "两个下载引擎均未成功。\n"
                    f"yt-dlp：{primary_error}\n"
                    f"you-get：{fallback_error}"
                ) from fallback_error

    def _download_with_ytdlp(self, options: DownloadOptions) -> None:
        try:
            import yt_dlp
        except ImportError as exc:
            raise DownloadError("缺少 yt-dlp，请先运行：pip install -e .") from exc

        ffmpeg = find_ffmpeg()
        self._on_log(f"使用 yt-dlp；ffmpeg：{ffmpeg}")
        output = str(options.output_dir.expanduser().resolve() / "%(title).180B [%(id)s].%(ext)s")

        if options.mode == "audio":
            media_format = "bestaudio/best"
            postprocessors = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "0",
            }]
        else:
            limit = "" if options.quality == "best" else f"[height<={options.quality}]"
            media_format = f"bestvideo*{limit}+bestaudio/best{limit}/best"
            postprocessors = []

        ydl_options: dict = {
            "format": media_format,
            "outtmpl": output,
            "noplaylist": not options.playlist,
            "merge_output_format": "mp4",
            "ffmpeg_location": ffmpeg,
            "postprocessors": postprocessors,
            "progress_hooks": [self._progress_hook],
            "logger": _YtdlpLogger(self._on_log),
            "windowsfilenames": sys.platform == "win32",
            "retries": 5,
            "fragment_retries": 5,
            "continuedl": True,
            "quiet": True,
            "no_warnings": False,
        }
        if options.browser:
            ydl_options["cookiesfrombrowser"] = (options.browser,)
        if options.proxy:
            ydl_options["proxy"] = options.proxy

        with yt_dlp.YoutubeDL(ydl_options) as ydl:
            code = ydl.download([options.url])
        if code:
            raise DownloadError(f"yt-dlp 返回错误代码 {code}")
        self._on_progress(Progress(status="finished", percent=100, message="下载及合并完成"))

    def _progress_hook(self, data: dict) -> None:
        if self._cancelled.is_set():
            raise DownloadCancelled("下载已取消")
        status = data.get("status", "downloading")
        filename = Path(data.get("filename", "")).name
        if status == "finished":
            self._on_progress(
                Progress(status="processing", percent=100, filename=filename, message="正在合并/转换…")
            )
            return
        total = data.get("total_bytes") or data.get("total_bytes_estimate")
        downloaded = data.get("downloaded_bytes", 0)
        percent = downloaded * 100 / total if total else None
        self._on_progress(
            Progress(
                status="downloading",
                percent=percent,
                speed=_human_bytes(data.get("speed"), suffix="/s"),
                eta=_format_eta(data.get("eta")),
                filename=filename,
                message="正在下载",
            )
        )

    def _download_with_you_get(self, options: DownloadOptions) -> None:
        if self._cancelled.is_set():
            raise DownloadCancelled("下载已取消")
        try:
            import you_get  # noqa: F401
        except ImportError as exc:
            raise DownloadError("缺少 you-get，请先运行：pip install -e .") from exc

        if getattr(sys, "frozen", False):
            command = [sys.executable, "--you-get-worker", "--output-dir", str(options.output_dir), options.url]
        else:
            command = [sys.executable, "-m", "you_get", "--output-dir", str(options.output_dir), options.url]
        env = os.environ.copy()
        ffmpeg = find_ffmpeg()
        ffmpeg_dir = str(_ffmpeg_path_directory(ffmpeg))
        env["PATH"] = ffmpeg_dir + os.pathsep + env.get("PATH", "")
        self._on_log("使用 you-get 回退引擎")
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self._process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            creationflags=creationflags,
        )
        assert self._process.stdout is not None
        for line in self._process.stdout:
            if self._cancelled.is_set():
                self._process.terminate()
                raise DownloadCancelled("下载已取消")
            clean = line.rstrip()
            if clean:
                self._on_log(clean)
                match = re.search(r"(\d+(?:\.\d+)?)%", clean)
                self._on_progress(
                    Progress(status="downloading", percent=float(match.group(1)) if match else None, message="you-get 下载中")
                )
        return_code = self._process.wait()
        self._process = None
        if return_code != 0:
            raise DownloadError(f"you-get 返回错误代码 {return_code}")
        self._on_progress(Progress(status="finished", percent=100, message="下载及合并完成"))

    @staticmethod
    def _friendly_error(error: Exception) -> DownloadError:
        message = str(error)
        if "Sign in" in message or "cookies" in message.lower():
            message += "\n该站点可能要求登录，请在界面中选择已登录该网站的浏览器。"
        return DownloadError(message)


class _YtdlpLogger:
    def __init__(self, callback: LogCallback) -> None:
        self.callback = callback

    def debug(self, message: str) -> None:
        if not message.startswith("[debug]"):
            self.callback(message)

    def info(self, message: str) -> None:
        self.callback(message)

    def warning(self, message: str) -> None:
        self.callback(f"警告：{message}")

    def error(self, message: str) -> None:
        self.callback(f"错误：{message}")


def _human_bytes(value: float | None, suffix: str = "") -> str:
    if value is None:
        return ""
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if size < 1024 or unit == "GiB":
            return f"{size:.1f} {unit}{suffix}"
        size /= 1024
    return ""


def _format_eta(seconds: int | None) -> str:
    if seconds is None:
        return ""
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


def _ffmpeg_path_directory(executable: str) -> Path:
    """Provide a directory containing a conventionally named ffmpeg binary.

    imageio-ffmpeg names its bundled executable with platform/version details,
    while you-get looks up the literal command ``ffmpeg`` on PATH.
    """
    source = Path(executable)
    expected_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    if source.name.lower() == expected_name.lower():
        return source.parent

    cache_dir = Path(tempfile.gettempdir()) / "video_down_ffmpeg"
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / expected_name
    if not target.exists() or target.stat().st_size != source.stat().st_size:
        temporary = target.with_suffix(target.suffix + ".tmp")
        shutil.copy2(source, temporary)
        temporary.replace(target)
    return cache_dir

