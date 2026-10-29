"""Bounded HTTP 403 recovery and real format fallback against a local server."""

import http.server
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from engine import build_options, download_with_recovery


class RecoveryTests(unittest.TestCase):
    def run_download(
        self, errors, url="https://www.youtube.com/watch?v=example", saved=None
    ):
        factory = MagicMock()
        factory.return_value.__enter__.return_value.download.side_effect = errors
        configure = MagicMock()
        options = build_options(
            {"folder": ".", "mode": "video", "height": 720, "fps": 30}
        )
        with patch("yt_dlp.YoutubeDL", factory), patch("engine.emit"):
            result = download_with_recovery(url, options, configure, saved or [])
        return result, factory, options

    def test_refreshes_once_preserving_constraints(self):
        result, factory, options = self.run_download(
            [DownloadError("HTTP Error 403: Forbidden"), 0]
        )
        self.assertEqual(result, 0)
        self.assertEqual(factory.call_count, 2)
        retry = factory.call_args.args[0]
        self.assertEqual(retry["check_formats"], "selected")
        self.assertEqual(retry["format"], options["format"])
        self.assertNotIn("check_formats", options)

    def test_retry_prefers_another_audio_stream_after_failed_full_transfer(self):
        factory = MagicMock()
        downloader = factory.return_value.__enter__.return_value
        processors = []
        downloader.add_post_processor.side_effect = (
            lambda pp, **kwargs: processors.append(pp)
        )

        def transfer(urls):
            if downloader.download.call_count == 1:
                processors[-1].run({'format_id': '251', 'vcodec': 'none'})
                raise DownloadError('HTTP Error 403')
            return 0

        downloader.download.side_effect = transfer
        for selector in ('bestaudio', 'bestaudio/best'):
            downloader.download.reset_mock()
            processors.clear()
            with patch('yt_dlp.YoutubeDL', factory), patch('engine.emit'):
                download_with_recovery(
                    'https://youtube.com/watch?v=x',
                    {'format': selector},
                    lambda _: None,
                    [],
                )
            retry = factory.call_args.args[0]['format']
            self.assertTrue(
                retry.startswith('bestaudio[protocol^=m3u8][format_id!=251]/')
            )
            self.assertTrue(
                all('[format_id!=251]' in branch for branch in retry.split('/'))
            )
            if selector == 'bestaudio':
                self.assertNotIn('/best/', retry)

    def test_audio_final_attempt_waits_and_excludes_both_refused_formats(self):
        factory = MagicMock()
        downloader = factory.return_value.__enter__.return_value
        processors = []
        downloader.add_post_processor.side_effect = (
            lambda pp, **kwargs: processors.append(pp)
        )

        def transfer(urls):
            index = downloader.download.call_count
            if index < 3:
                processors[-1].run(
                    {'format_id': '251' if index == 1 else '234', 'vcodec': 'none'}
                )
                raise DownloadError('HTTP Error 403')
            return 0

        downloader.download.side_effect = transfer
        with (
            patch('yt_dlp.YoutubeDL', factory),
            patch('engine.emit'),
            patch('engine.time.sleep') as sleep,
        ):
            result = download_with_recovery(
                'https://youtube.com/watch?v=x',
                {'format': 'bestaudio'},
                lambda _: None,
                [],
            )
        self.assertEqual(result, 0)
        self.assertEqual(factory.call_count, 3)
        sleep.assert_called_once()
        self.assertTrue(1 <= sleep.call_args.args[0] < 2)
        for branch in factory.call_args.args[0]['format'].split('/'):
            self.assertIn('[format_id!=251]', branch)
            self.assertIn('[format_id!=234]', branch)

    def test_audio_persistent_denial_is_bounded_and_success_never_waits(self):
        for failures in (False, True):
            factory = MagicMock()
            downloader = factory.return_value.__enter__.return_value
            downloader.download.side_effect = (
                DownloadError('HTTP Error 403') if failures else [0]
            )
            with (
                patch('yt_dlp.YoutubeDL', factory),
                patch('engine.emit'),
                patch('engine.time.sleep') as sleep,
            ):
                if failures:
                    with self.assertRaisesRegex(RuntimeError, 'YouTube recusou'):
                        download_with_recovery(
                            'https://youtube.com/watch?v=x',
                            {'format': 'bestaudio/best'},
                            lambda _: None,
                            [],
                        )
                    self.assertEqual(factory.call_count, 3)
                    sleep.assert_called_once()
                else:
                    self.assertEqual(
                        download_with_recovery(
                            'https://youtube.com/watch?v=x',
                            {'format': 'bestaudio/best'},
                            lambda _: None,
                            [],
                        ),
                        0,
                    )
                    self.assertEqual(factory.call_count, 1)
                    sleep.assert_not_called()

    def test_repeated_403_stops(self):
        with self.assertRaisesRegex(RuntimeError, "YouTube recusou"):
            self.run_download(
                [DownloadError("HTTP Error 403"), DownloadError("HTTP Error 403")]
            )

    def test_other_errors_and_completed_playlist_are_not_retried(self):
        for error, url, saved in (
            ("HTTP Error 404", "https://youtube.com/watch?v=x", []),
            ("HTTP Error 403", "https://example.com/video", []),
            ("HTTP Error 403", "https://youtube.com/watch?v=x", ["completed.mp3"]),
        ):
            with self.subTest(error=error, url=url, saved=saved):
                factory = MagicMock()
                factory.return_value.__enter__.return_value.download.side_effect = (
                    DownloadError(error)
                )
                with (
                    patch("yt_dlp.YoutubeDL", factory),
                    patch("engine.emit"),
                    self.assertRaises(Exception),
                ):
                    download_with_recovery(url, {}, lambda _: None, saved)
                self.assertEqual(factory.call_count, 1)


class FormatFallbackTests(unittest.TestCase):
    def test_blocked_best_audio_falls_back_to_accessible_audio(self):
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append(self.path)
                if self.path == "/blocked":
                    self.send_error(403)
                    return
                body = b"audio-test" * 2048
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                base = f"http://127.0.0.1:{server.server_port}"
                info = {
                    "id": "test",
                    "title": "Test",
                    "extractor": "test",
                    "formats": [
                        {
                            "format_id": "good",
                            "url": base + "/good",
                            "ext": "webm",
                            "vcodec": "none",
                            "acodec": "opus",
                            "abr": 128,
                        },
                        {
                            "format_id": "blocked",
                            "url": base + "/blocked",
                            "ext": "webm",
                            "vcodec": "none",
                            "acodec": "opus",
                            "abr": 160,
                        },
                    ],
                }
                options = build_options({"folder": folder, "mode": "original"})
                options.update(check_formats="selected", logger=MagicMock())
                with YoutubeDL(options) as downloader:
                    result = downloader.process_ie_result(info, download=True)
                self.assertEqual(result["format_id"], "good")
                self.assertIn("/blocked", requests)
                self.assertIn("/good", requests)
                from pathlib import Path

                self.assertEqual(
                    next(Path(folder).glob("*.webm")).read_bytes(), b"audio-test" * 2048
                )
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
