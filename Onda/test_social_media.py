import base64
import functools
import http.server
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock

import requests
from social_media import download_post, save_media, kwai_images, session_for


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


class SocialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRz8AAAAASUVORK5CYII="
        )
        (cls.root / "image.png").write_bytes(cls.image)
        (cls.root / "second.png").write_bytes(cls.image)
        (cls.root / "clip.mp4").write_bytes(b"\0\0\0\x18ftypmp42" + b"fixture" * 100)
        (cls.root / "login.html").write_text("<html>Login</html>")
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(cls.root))
        )
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def test_mixed_carousel_filter_and_original_bytes(self):
        from gallery_dl.extractor.common import Message

        for mode, count in (("photos", 2), ("social", 3)):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:

                class Source:
                    subcategory = "post"
                    session = requests.Session()

                    def __iter__(inner):
                        # Deliberately reuse metadata, as TikTok's extractor does.
                        metadata = {"title": "Meu post", "user": "Autor"}
                        for name in ("image.png", "clip.mp4", "second.png"):
                            metadata["extension"] = name.split(".")[-1]
                            yield Message.Url, self.url + "/" + name, metadata

                events = []
                config = {
                    "url": "https://example.com/p/example/",
                    "mode": mode,
                    "folder": folder,
                    "duplicate_policy": "keep",
                }
                with patch("gallery_dl.extractor.find", return_value=Source()):
                    self.assertTrue(
                        download_post(
                            config,
                            lambda kind, **data: events.append({"type": kind, **data}),
                            Mock(),
                        )
                    )
                self.assertEqual(len(events[-1]["files"]), count)
                self.assertEqual(events[-1]["type"], "done")
                for name in events[-1]["files"]:
                    if name.endswith(".png"):
                        self.assertEqual(Path(name).read_bytes(), self.image)
                self.assertEqual(len([e for e in events if e["type"] == "file"]), count)
                self.assertTrue(any(e["type"] == "progress" for e in events))
                self.assertFalse((Path(folder) / ".onda-work").exists())

    def test_no_images_is_failure_not_done(self):
        class Source:
            subcategory = "post"
            session = requests.Session()

            def __iter__(self):
                return iter(())

        with (
            tempfile.TemporaryDirectory() as folder,
            patch("gallery_dl.extractor.find", return_value=Source()),
        ):
            emitter = Mock()
            with self.assertRaisesRegex(ValueError, "Nenhuma foto"):
                download_post(
                    {
                        "url": "https://example.com/p/empty/",
                        "mode": "photos",
                        "folder": folder,
                    },
                    emitter,
                    Mock(),
                )
            self.assertFalse(
                any(call.args[0] == "done" for call in emitter.call_args_list)
            )

    def test_real_tiktok_extractor_photo_post(self):
        from tiktok_media import TikTokMediaIE

        fixture = {
            "webapp.video-detail": {
                "statusCode": 0,
                "itemInfo": {
                    "itemStruct": {
                        "id": "1234567890123456789",
                        "desc": "Carrossel",
                        "author": {"uniqueId": "autor"},
                        "createTime": 1700000000,
                        "imagePost": {
                            "images": [
                                {
                                    "imageURL": {"urlList": [self.url + "/image.png"]},
                                    "imageWidth": 1,
                                    "imageHeight": 1,
                                },
                                {
                                    "imageURL": {"urlList": [self.url + "/second.png"]},
                                    "imageWidth": 1,
                                    "imageHeight": 1,
                                },
                            ]
                        },
                    }
                },
            }
        }
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.object(
                TikTokMediaIE,
                "_extract_web_data_and_status",
                return_value=(
                    fixture["webapp.video-detail"]["itemInfo"]["itemStruct"],
                    0,
                ),
            ),
        ):
            events = []
            self.assertTrue(
                download_post(
                    {
                        "url": "https://www.tiktok.com/@autor/photo/1234567890123456789",
                        "mode": "photos",
                        "folder": folder,
                    },
                    lambda kind, **data: events.append({"type": kind, **data}),
                    Mock(),
                )
            )
            self.assertEqual(len(events[-1]["files"]), 2)
            for name in events[-1]["files"]:
                self.assertEqual(Path(name).read_bytes(), self.image)

    def test_duplicate_skip_keeps_original(self):
        with tempfile.TemporaryDirectory() as folder, session_for() as session:
            config = {
                "url": self.url,
                "folder": folder,
                "mode": "photos",
                "duplicate_policy": "skip",
            }
            metadata = {"extension": "png", "title": "Foto", "user": "Autor"}
            emit = Mock()
            path = save_media(
                session, self.url + "/image.png", metadata, config, emit, Mock(), 1
            )
            Path(path).write_bytes(b"existing")
            self.assertEqual(
                save_media(
                    session, self.url + "/image.png", metadata, config, emit, Mock(), 1
                ),
                path,
            )
            self.assertEqual(Path(path).read_bytes(), b"existing")
            self.assertTrue(
                [call.kwargs for call in emit.call_args_list if call.args == ("file",)][
                    -1
                ]["skipped"]
            )

    def test_html_and_http_errors_never_publish(self):
        for name in ("login.html", "missing.png"):
            with (
                self.subTest(name=name),
                tempfile.TemporaryDirectory() as folder,
                session_for() as session,
            ):
                emit = Mock()
                with self.assertRaises((ValueError, requests.HTTPError)):
                    save_media(
                        session,
                        self.url + "/" + name,
                        {"extension": "png"},
                        {"url": self.url, "mode": "photos", "folder": folder},
                        emit,
                        Mock(),
                        1,
                    )
                self.assertFalse(list(Path(folder).glob("*.png")))
                self.assertFalse(
                    any(call.args[0] == "file" for call in emit.call_args_list)
                )

    def test_kwai_atlas_only_and_correct_post(self):
        html = '<meta property="og:image" content="https://cdn/cover.jpg"><script>window.__INIT_STATE__ = {"recommendation":{"photoId":"other","atlas":{"images":["https://cdn/wrong.jpg"]}},"photo":{"photoId":"123","atlas":{"images":[{"url":"https://cdn/a.jpg"}, "https://cdn/b.png"]}}};</script>'
        self.assertEqual(
            [url for url, _ in kwai_images(html, "https://m.kwai.com/photo/user/123")],
            ["https://cdn/a.jpg", "https://cdn/b.png"],
        )
        self.assertEqual(
            list(kwai_images(html, "https://m.kwai.com/photo/user/404")), []
        )
        self.assertEqual(
            list(
                kwai_images(
                    '<meta property="og:image" content="https://cdn/cover.jpg">',
                    "https://m.kwai.com/photo/user/123",
                )
            ),
            [],
        )

    def test_bad_cookie_file(self):
        with self.assertRaisesRegex(ValueError, "Netscape"):
            session_for("nonexistent-cookie-file.txt")


@unittest.skipUnless(
    os.environ.get("ONDA_UI_TESTS"), "Set ONDA_UI_TESTS for Tk integration"
)
class QueueUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"LOCALAPPDATA": self.temp.name})
        self.environment.start()
        from app import App

        self.app = App()
        self.app.withdraw()
        self.app.folder.set(self.temp.name)

    def tearDown(self):
        self.app.destroy()
        self.environment.stop()
        self.temp.cleanup()

    def test_remove_multiple_and_queue_persistence(self):
        items = self.app.add(
            lines=[
                "https://example.com/a",
                "https://example.com/b",
                "https://example.com/c",
            ]
        )
        self.app.tree.selection_set(items[:2])
        self.app.remove()
        self.assertEqual(list(self.app.jobs), items[2:])
        self.assertEqual(len(self.app.library.load_queue()), 1)

    def test_active_removal_waits_for_worker_then_resumes(self):
        app = self.app
        items = app.add(lines=["https://example.com/a", "https://example.com/b"])
        app.active = items[0]
        app.running = True
        app.set_state(items[0], "Em andamento")
        app.tree.selection_set(items[0])

        def cancel():
            app.running = False
            app.cancelled.set()

        with (
            patch("app.messagebox.askyesno", return_value=True),
            patch.object(app, "cancel", side_effect=cancel),
        ):
            app.remove()
        self.assertIn(items[0], app.jobs)
        self.assertEqual(len(app.library.load_queue()), 1)
        app.events.put(
            (items[0], {"type": "exited", "cancelled": True, "success": False})
        )
        app.after_cancel(app._poll_after)
        app._poll_after = None
        with patch.object(app, "next_job") as next_job:
            app.poll_events()
            next_job.assert_called_once()
        self.assertNotIn(items[0], app.jobs)
        self.assertTrue(app.running)
        self.assertIsNone(app.active)

    def test_declining_active_removal_keeps_everything(self):
        app = self.app
        items = app.add(lines=["https://example.com/a"])
        app.active = items[0]
        app.tree.selection_set(items[0])
        with (
            patch("app.messagebox.askyesno", return_value=False),
            patch.object(app, "cancel") as cancel,
        ):
            app.remove()
            cancel.assert_not_called()
        self.assertIn(items[0], app.jobs)

    def test_photo_quality_controls_and_restore(self):
        from engine import MODES

        app = self.app
        app.mode.set(next(label for label, mode in MODES.items() if mode == "photos"))
        app.update()
        self.assertEqual(app.format_label.get(), "Fotos / carrossel")
        self.assertEqual(str(app.quality_selector["state"]), "disabled")
        self.assertEqual(app.fps_selector.winfo_manager(), "")
        added = app.add(lines=["https://example.com/p/example/"])
        self.assertEqual(app.jobs[added[0]]["mode"], "photos")
        self.assertEqual(app.library.load_queue()[0]["mode"], "photos")

    def test_mp4_quality_fps_and_queue(self):
        from engine import MODES

        app = self.app
        app.mode.set(next(label for label, mode in MODES.items() if mode == "mp4"))
        app.fps.set("30 fps")
        app.update()
        self.assertEqual(app.format_label.get(), "Vídeo (MP4)")
        self.assertEqual(str(app.quality_selector["state"]), "readonly")
        self.assertEqual(app.fps_selector.winfo_manager(), "grid")
        items = app.add(lines=["https://example.com/video"])
        self.assertEqual(app.jobs[items[0]]["fps"], 30)
        self.assertEqual(app.library.load_queue()[0]["mode"], "mp4")


if __name__ == "__main__":
    unittest.main()
