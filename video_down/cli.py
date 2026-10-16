from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import DownloadCancelled, DownloadError, DownloadOptions, Downloader, Progress


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="下载网络视频/音乐，并自动合并音视频")
    parser.add_argument("url", help="视频或音乐页面链接")
    parser.add_argument("-o", "--output", type=Path, default=Path("downloads"), help="保存目录")
    parser.add_argument("--audio", action="store_true", help="仅提取 MP3 音频")
    parser.add_argument("-q", "--quality", choices=("best", "1080", "720", "480"), default="best")
    parser.add_argument("--playlist", action="store_true", help="下载整个播放列表")
    parser.add_argument("--browser", choices=("chrome", "chromium", "edge", "firefox", "brave", "opera"), help="读取浏览器登录 Cookie")
    parser.add_argument("--proxy", help="代理地址，例如 http://127.0.0.1:7890")
    parser.add_argument("--no-fallback", action="store_true", help="不使用 you-get 回退")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    def progress(item: Progress) -> None:
        if item.percent is not None:
            print(f"\r{item.message} {item.percent:5.1f}% {item.speed} ETA {item.eta}   ", end="", flush=True)
        elif item.message:
            print(f"\r{item.message}   ", end="", flush=True)
        if item.status == "finished":
            print()

    downloader = Downloader(progress_callback=progress, log_callback=lambda msg: print(f"\n{msg}"))
    options = DownloadOptions(
        url=args.url,
        output_dir=args.output,
        mode="audio" if args.audio else "video",
        quality=args.quality,
        playlist=args.playlist,
        browser=args.browser,
        proxy=args.proxy,
        fallback_to_you_get=not args.no_fallback,
    )
    try:
        downloader.download(options)
        return 0
    except KeyboardInterrupt:
        downloader.cancel()
        print("\n下载已取消。", file=sys.stderr)
        return 130
    except (DownloadError, DownloadCancelled) as exc:
        print(f"\n失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

