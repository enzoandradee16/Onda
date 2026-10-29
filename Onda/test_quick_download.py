import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from preferences import PreferenceStore


class PreviewPreferenceTests(unittest.TestCase):
    def test_roundtrip_and_boolean_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            store = PreferenceStore(Path(folder) / "settings.json")
            for value in (True, False):
                store.save({"background_preview": value})
                self.assertIs(store.load()["background_preview"], value)
        for value in (1, "true", None):
            self.assertNotIn(
                "background_preview",
                PreferenceStore.clean({"background_preview": value}),
            )


@unittest.skipUnless(
    os.environ.get("ONDA_UI_TESTS"), "Set ONDA_UI_TESTS for Tk integration"
)
class QuickDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"LOCALAPPDATA": self.temp.name})
        self.environment.start()
        from app import App

        self.app = App()
        self.app.withdraw()
        self.app.folder.set(self.temp.name)

    def tearDown(self):
        self.app.active = None
        self.app.bar.stop()
        self.app.destroy()
        self.environment.stop()
        self.temp.cleanup()

    def input(self, value):
        self.app.urls.delete("1.0", "end")
        self.app.urls.insert("1.0", value)

    def test_download_now_does_not_run_other_pending_items(self):
        app = self.app
        waiting = app.add(lines=["https://example.com/waiting"])[0]
        app.playlist.set(True)
        self.input("https://example.com/now")
        with (
            patch("app.binaries", return_value=True),
            patch("app.threading.Thread") as worker,
        ):
            app.download_now_button.invoke()
            self.assertEqual(app.pages.select(), str(app.queue_page))
            direct = app.active
            self.assertNotEqual(direct, waiting)
            self.assertEqual(app.jobs[direct]["url"], "https://example.com/now")
            self.assertFalse(app.jobs[direct]["playlist"])
            self.assertEqual(app.jobs[waiting]["state"], "Na fila")
            worker.return_value.start.assert_called_once()
            app.events.put(
                (direct, {"type": "exited", "success": True, "cancelled": False})
            )
            app.after_cancel(app._poll_after)
            app._poll_after = None
            app.poll_events()
            self.assertIsNone(app.active)
            self.assertFalse(app.running)
            self.assertIsNone(app.immediate_item)
            self.assertEqual(app.jobs[waiting]["state"], "Na fila")
            app.start()
            self.assertEqual(app.active, waiting)

    def test_queue_and_link_form_live_in_separate_tabs(self):
        app = self.app
        from tab_order import DEFAULT_ORDER

        self.assertEqual(len(app.pages.tabs()), len(DEFAULT_ORDER))
        self.assertTrue(str(app.urls).startswith(str(app.download_page)))
        self.assertTrue(str(app.tree).startswith(str(app.queue_page)))
        app.pages.select(app.download_page)
        self.input("https://example.com/pending")
        app.add()
        self.assertEqual(app.pages.select(), str(app.download_page))
        app.show_queue()
        self.assertEqual(app.pages.select(), str(app.queue_page))

    def test_playlist_now_starts_only_selected_items_and_opens_queue(self):
        app = self.app
        page = app.playlist_page
        page.ensure_ready()
        page.playlist_title = "Example album"
        page.records = {
            'chosen': dict(
                source_url='https://www.deezer.com/track/123',
                title='Chosen song',
                artists=['Artist'],
                duration_ms=200000,
            )
        }
        app.pages.select(page)
        with (
            patch.object(page, 'selected_keys', return_value=['chosen']),
            patch.object(app, 'start') as start,
        ):
            page.add(start=True)
        self.assertEqual(app.pages.select(), str(app.queue_page))
        self.assertEqual(start.call_args.kwargs['only_items'], list(app.jobs))

    def test_playlist_add_only_stays_in_playlist_tab(self):
        app = self.app
        page = app.playlist_page
        page.ensure_ready()
        page.playlist_title = "Example album"
        page.records = {
            'chosen': dict(
                source_url='https://www.deezer.com/track/123',
                title='Chosen song',
                artists=['Artist'],
                duration_ms=200000,
            )
        }
        app.pages.select(page)
        with (
            patch.object(page, 'selected_keys', return_value=['chosen']),
            patch.object(app, 'start') as start,
        ):
            page.add(start=False)
        self.assertEqual(app.pages.select(), str(page))
        start.assert_not_called()

    def test_reuses_matching_pending_item_without_duplicate(self):
        app = self.app
        pending = app.add(lines=["https://example.com/same"])[0]
        self.input("https://example.com/same")
        with patch("app.binaries", return_value=True), patch("app.threading.Thread"):
            app.download_now()
        self.assertEqual(app.active, pending)
        self.assertEqual(len(app.jobs), 1)

    def test_requires_one_link_and_preserves_input(self):
        for text in ("", "https://example.com/a\nhttps://example.com/b"):
            self.input(text)
            with patch("app.messagebox.showwarning") as warning:
                self.app.download_now()
            warning.assert_called_once()
            self.assertEqual(len(self.app.jobs), 0)
            self.assertEqual(self.app.urls.get("1.0", "end").strip(), text)

    def test_busy_download_adds_request_without_interrupting_worker(self):
        self.input("https://example.com/now")
        self.app.running = True
        self.app.active = "busy"
        self.app.parallel.workers.add("busy")
        with (
            patch("app.binaries", return_value=True),
            patch.object(self.app.parallel, "extend") as extend,
        ):
            self.app.download_now()
        extend.assert_called_once()
        self.assertEqual(len(self.app.jobs), 1)
        self.assertEqual(self.app.active, "busy")

    def test_switching_tabs_obeys_background_setting(self):
        app = self.app
        app.pages.select(app.download_page)
        app.update()
        with patch.object(app.effects_page, "stop_preview") as stop:
            app.background_preview.set(True)
            app.tab_changed()
            stop.assert_not_called()
            app.background_preview.set(False)
            app.tab_changed()
            stop.assert_called_once()

    def test_button_fits_minimum_window_width(self):
        app = self.app
        app.deiconify()
        app.geometry("840x720")
        app.pages.select(app.download_page)
        app.update()
        button = app.download_now_button
        self.assertTrue(button.winfo_ismapped())
        self.assertLessEqual(
            button.winfo_rootx() + button.winfo_width(),
            app.winfo_rootx() + app.winfo_width(),
        )


if __name__ == "__main__":
    unittest.main()
