from pathlib import Path
from unittest import TestCase
from unittest.mock import call, patch

from video_down.core import DownloadError, DownloadOptions, Downloader


class BrowserCookieRetryTests(TestCase):
    def setUp(self) -> None:
        self.options = DownloadOptions(
            url="https://example.com/video",
            output_dir=Path("downloads"),
            browser="edge",
        )

    def test_retries_without_browser_cookies_before_fallback(self) -> None:
        logs: list[str] = []
        downloader = Downloader(log_callback=logs.append)

        with (
            patch.object(
                downloader,
                "_download_with_ytdlp",
                side_effect=[Exception("Could not copy Chrome cookie database"), None],
            ) as ytdlp,
            patch.object(downloader, "_download_with_you_get") as you_get,
        ):
            downloader.download(self.options)

        self.assertEqual(
            [item.args[0].browser for item in ytdlp.call_args_list],
            ["edge", None],
        )
        you_get.assert_not_called()
        self.assertTrue(any("无 Cookie 模式重试" in message for message in logs))

    def test_falls_back_after_cookie_free_retry_fails(self) -> None:
        downloader = Downloader()

        with (
            patch.object(
                downloader,
                "_download_with_ytdlp",
                side_effect=[
                    Exception("Could not copy Chrome cookie database"),
                    DownloadError("video unavailable"),
                ],
            ) as ytdlp,
            patch.object(downloader, "_download_with_you_get") as you_get,
        ):
            downloader.download(self.options)

        self.assertEqual(ytdlp.call_count, 2)
        you_get.assert_called_once_with(self.options)

    def test_does_not_retry_unrelated_errors_without_cookies(self) -> None:
        downloader = Downloader()

        with (
            patch.object(
                downloader,
                "_download_with_ytdlp",
                side_effect=DownloadError("video unavailable"),
            ) as ytdlp,
            patch.object(downloader, "_download_with_you_get") as you_get,
        ):
            downloader.download(self.options)

        self.assertEqual(ytdlp.call_args_list, [call(self.options)])
        you_get.assert_called_once_with(self.options)
