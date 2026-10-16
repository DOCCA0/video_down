from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .core import DownloadCancelled, DownloadError, DownloadOptions, Downloader, Progress


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("video_down")
        self.geometry("760x610")
        self.minsize(650, 520)
        self._events: queue.Queue[tuple[str, object]] = queue.Queue()
        self._worker: threading.Thread | None = None
        self._downloader: Downloader | None = None

        self.url = tk.StringVar()
        self.output = tk.StringVar(value=str(Path.home() / "Downloads" / "video_down"))
        self.mode = tk.StringVar(value="video")
        self.quality = tk.StringVar(value="best")
        self.browser = tk.StringVar(value="不读取 Cookie")
        self.proxy = tk.StringVar()
        self.playlist = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="准备就绪")
        self.detail = tk.StringVar(value="")

        self._build()
        self.after(100, self._drain_events)

    def _build(self) -> None:
        root = ttk.Frame(self, padding=20)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(8, weight=1)

        ttk.Label(root, text="video_down", font=("TkDefaultFont", 22, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(root, text="粘贴视频或音乐页面链接，音视频将自动合并").grid(row=1, column=0, sticky="w", pady=(2, 16))

        ttk.Label(root, text="链接").grid(row=2, column=0, sticky="w")
        url_row = ttk.Frame(root)
        url_row.grid(row=3, column=0, sticky="ew", pady=(4, 12))
        url_row.columnconfigure(0, weight=1)
        ttk.Entry(url_row, textvariable=self.url).grid(row=0, column=0, sticky="ew")
        ttk.Button(url_row, text="粘贴", command=self._paste).grid(row=0, column=1, padx=(8, 0))

        ttk.Label(root, text="保存到").grid(row=4, column=0, sticky="w")
        output_row = ttk.Frame(root)
        output_row.grid(row=5, column=0, sticky="ew", pady=(4, 12))
        output_row.columnconfigure(0, weight=1)
        ttk.Entry(output_row, textvariable=self.output).grid(row=0, column=0, sticky="ew")
        ttk.Button(output_row, text="选择…", command=self._choose_output).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(output_row, text="打开", command=self._open_output).grid(row=0, column=2, padx=(8, 0))

        options = ttk.LabelFrame(root, text="下载选项", padding=12)
        options.grid(row=6, column=0, sticky="ew", pady=(0, 12))
        for column in range(4):
            options.columnconfigure(column, weight=1)
        ttk.Radiobutton(options, text="视频（MP4）", variable=self.mode, value="video", command=self._mode_changed).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(options, text="仅音频（MP3）", variable=self.mode, value="audio", command=self._mode_changed).grid(row=0, column=1, sticky="w")
        ttk.Checkbutton(options, text="下载播放列表", variable=self.playlist).grid(row=0, column=2, columnspan=2, sticky="w")
        ttk.Label(options, text="清晰度").grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.quality_box = ttk.Combobox(options, textvariable=self.quality, values=("best", "1080", "720", "480"), state="readonly", width=12)
        self.quality_box.grid(row=1, column=1, sticky="w", pady=(12, 0))
        ttk.Label(options, text="登录浏览器").grid(row=1, column=2, sticky="e", padx=(8, 8), pady=(12, 0))
        ttk.Combobox(options, textvariable=self.browser, values=("不读取 Cookie", "chrome", "edge", "firefox", "chromium", "brave", "opera"), state="readonly", width=16).grid(row=1, column=3, sticky="w", pady=(12, 0))
        ttk.Label(options, text="代理（可选）").grid(row=2, column=0, sticky="w", pady=(12, 0))
        ttk.Entry(options, textvariable=self.proxy).grid(row=2, column=1, columnspan=3, sticky="ew", pady=(12, 0))

        action_row = ttk.Frame(root)
        action_row.grid(row=7, column=0, sticky="ew")
        action_row.columnconfigure(0, weight=1)
        self.progress = ttk.Progressbar(action_row, mode="determinate", maximum=100)
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.start_button = ttk.Button(action_row, text="开始下载", command=self._start)
        self.start_button.grid(row=0, column=1)
        self.cancel_button = ttk.Button(action_row, text="取消", command=self._cancel, state="disabled")
        self.cancel_button.grid(row=0, column=2, padx=(8, 0))

        log_frame = ttk.Frame(root)
        log_frame.grid(row=8, column=0, sticky="nsew", pady=(12, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(2, weight=1)
        ttk.Label(log_frame, textvariable=self.status, font=("TkDefaultFont", 11, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(log_frame, textvariable=self.detail).grid(row=1, column=0, sticky="w", pady=(2, 6))
        self.log = tk.Text(log_frame, height=9, wrap="word", state="disabled")
        self.log.grid(row=2, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scrollbar.set)

    def _paste(self) -> None:
        try:
            self.url.set(self.clipboard_get().strip())
        except tk.TclError:
            pass

    def _choose_output(self) -> None:
        directory = filedialog.askdirectory(initialdir=self.output.get())
        if directory:
            self.output.set(directory)

    def _open_output(self) -> None:
        path = Path(self.output.get()).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _mode_changed(self) -> None:
        self.quality_box.configure(state="disabled" if self.mode.get() == "audio" else "readonly")

    def _start(self) -> None:
        if self._worker and self._worker.is_alive():
            return
        if not self.url.get().strip():
            messagebox.showwarning("缺少链接", "请先粘贴视频或音乐链接。")
            return
        if not self.output.get().strip():
            messagebox.showwarning("缺少目录", "请选择保存目录。")
            return

        self.progress.configure(mode="indeterminate", value=0)
        self.progress.start(12)
        self.status.set("正在准备…")
        self.detail.set("")
        self.start_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self._downloader = Downloader(
            progress_callback=lambda item: self._events.put(("progress", item)),
            log_callback=lambda text: self._events.put(("log", text)),
        )
        browser = self.browser.get()
        options = DownloadOptions(
            url=self.url.get(),
            output_dir=Path(self.output.get()),
            mode=self.mode.get(),
            quality=self.quality.get(),
            playlist=self.playlist.get(),
            browser=None if browser == "不读取 Cookie" else browser,
            proxy=self.proxy.get().strip() or None,
        )
        self._worker = threading.Thread(target=self._run_download, args=(options,), daemon=True)
        self._worker.start()

    def _run_download(self, options: DownloadOptions) -> None:
        try:
            assert self._downloader is not None
            self._downloader.download(options)
        except DownloadCancelled:
            self._events.put(("cancelled", None))
        except (DownloadError, Exception) as exc:
            self._events.put(("error", str(exc)))
        else:
            self._events.put(("done", None))

    def _cancel(self) -> None:
        if self._downloader:
            self.status.set("正在取消…")
            self._downloader.cancel()

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload = self._events.get_nowait()
                if kind == "progress":
                    self._show_progress(payload)
                elif kind == "log":
                    self._append_log(str(payload))
                elif kind == "done":
                    self._finish("下载完成", success=True)
                elif kind == "cancelled":
                    self._finish("下载已取消")
                elif kind == "error":
                    self._finish("下载失败")
                    messagebox.showerror("下载失败", str(payload))
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _show_progress(self, item: Progress) -> None:
        if item.percent is None:
            if str(self.progress["mode"]) != "indeterminate":
                self.progress.configure(mode="indeterminate")
                self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate", value=item.percent)
        self.status.set(item.message or item.status)
        details = [part for part in (item.filename, item.speed, f"剩余 {item.eta}" if item.eta else "") if part]
        self.detail.set(" · ".join(details))

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _finish(self, text: str, success: bool = False) -> None:
        self.progress.stop()
        if success:
            self.progress.configure(mode="determinate", value=100)
        else:
            self.progress.configure(mode="determinate", value=0)
        self.status.set(text)
        self.start_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

