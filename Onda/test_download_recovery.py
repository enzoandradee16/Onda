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
    def run_download(self, errors, url="https://www.youtube.com/watch?v=example", saved=None):
        factory = MagicMock()
        factory.return_value.__enter__.return_value.download.side_effect = errors
        configure = MagicMock()
        options = build_options({"folder": ".", "mode": "video", "height": 720, "fps": 30})
        with patch("yt_dlp.YoutubeDL", factory), patch("engine.emit"):
            result = download_with_recovery(url, options, configure, saved or [])
        return result, factory, options

    def test_refreshes_once_preserving_constraints(self):
        result, factory, options = self.run_download([DownloadError("HTTP Error 403: Forbidden"), 0])
        self.assertEqual(result, 0)
        self.assertEqual(factory.call_count, 2)
        retry = factory.call_args.args[0]
        self.assertEqual(retry["check_formats"], "selected")
        self.assertEqual(retry["format"], options["format"])
        self.assertNotIn("check_formats", options)

    def test_repeated_403_stops(self):
        with self.assertRaisesRegex(RuntimeError, "YouTube recusou"):
            self.run_download([DownloadError("HTTP Error 403"), DownloadError("HTTP Error 403")])

    def test_other_errors_and_completed_playlist_are_not_retried(self):
        for error, url, saved in (
            ("HTTP Error 404", "https://youtube.com/watch?v=x", []),
            ("HTTP Error 403", "https://example.com/video", []),
            ("HTTP Error 403", "https://youtube.com/watch?v=x", ["completed.mp3"]),
        ):
            with self.subTest(error=error, url=url, saved=saved):
                factory = MagicMock()
                factory.return_value.__enter__.return_value.download.side_effect = DownloadError(error)
                with patch("yt_dlp.YoutubeDL", factory), patch("engine.emit"), self.assertRaises(Exception):
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
                info = {"id": "test", "title": "Test", "extractor": "test", "formats": [
                    {"format_id": "good", "url": base + "/good", "ext": "webm", "vcodec": "none",
                     "acodec": "opus", "abr": 128},
                    {"format_id": "blocked", "url": base + "/blocked", "ext": "webm", "vcodec": "none",
                     "acodec": "opus", "abr": 160},
                ]}
                options = build_options({"folder": folder, "mode": "original"})
                options.update(check_formats="selected", logger=MagicMock())
                with YoutubeDL(options) as downloader:
                    result = downloader.process_ie_result(info, download=True)
                self.assertEqual(result["format_id"], "good")
                self.assertIn("/blocked", requests)
                self.assertIn("/good", requests)
                from pathlib import Path
                self.assertEqual(next(Path(folder).glob("*.webm")).read_bytes(), b"audio-test" * 2048)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
