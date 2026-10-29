import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
class ClearQueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"LOCALAPPDATA": self.temp.name})
        self.env.start()
        from app import App

        self.app = App(show_welcome=False)
        self.app.withdraw()
        self.app.folder.set(self.temp.name)
        self.items = self.app.add(
            lines=[
                "https://example.com/a",
                "https://example.com/b",
                "https://example.com/c",
            ]
        )

    def tearDown(self):
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def test_clear_removes_all_and_persisted_queue_but_preserves_files_and_history(
        self,
    ):
        app = self.app
        file = Path(self.temp.name) / "baixado.mp3"
        file.write_bytes(b"saved file")
        app.library.add_history(file, "MP3", "https://example.com/a")
        app.set_state(self.items[0], "Concluído")
        app.set_state(self.items[1], "Falhou")
        app.clear_queue_button.invoke()
        self.assertEqual(app.jobs, {})
        self.assertEqual(app.tree.get_children(), ())
        self.assertEqual(app.library.load_queue(), [])
        self.assertEqual(file.read_bytes(), b"saved file")
        self.assertEqual(len(app.library.history()), 1)
        self.assertIn("disabled", app.clear_queue_button.state())

    def test_active_clear_waits_for_exit_and_never_resumes(self):
        app = self.app
        app.active, app.running = self.items[0], True
        app.set_state(app.active, "Em andamento")
        with (
            patch("app.messagebox.askyesno", return_value=True),
            patch.object(app, "cancel") as cancel,
        ):
            app.clear_queue()
            cancel.assert_called_once()
        self.assertEqual(list(app.jobs), [self.items[0]])
        self.assertFalse(app.jobs[app.active]["resume_after_remove"])
        self.assertEqual(app.library.load_queue(), [])
        app.events.put(
            (app.active, {"type": "exited", "cancelled": True, "success": False})
        )
        app.after_cancel(app._poll_after)
        app._poll_after = None
        app.poll_events()
        self.assertEqual(app.jobs, {})
        self.assertIsNone(app.active)
        self.assertFalse(app.running)

    def test_declining_active_clear_keeps_queue_and_saved_queue(self):
        app = self.app
        app.active = self.items[0]
        with (
            patch("app.messagebox.askyesno", return_value=False),
            patch.object(app, "cancel") as cancel,
        ):
            app.clear_queue()
            cancel.assert_not_called()
        self.assertEqual(list(app.jobs), self.items)
        self.assertEqual(len(app.library.load_queue()), 3)

    def test_alt_a_selects_queue_and_only_visible_playlist_rows(self):
        app = self.app
        app.deiconify()
        app.pages.select(app.queue_page)
        app.update()
        app.tree.focus_force()
        app.tree.event_generate("<Alt-a>")
        app.update()
        self.assertEqual(app.tree.selection(), tuple(self.items))
        page = app.playlist_page
        page.display(
            {
                "title": "List",
                "note": "",
                "tracks": [
                    {"title": "Primeira", "source_url": "https://example.com/1"},
                    {"title": "Segunda", "source_url": "https://example.com/2"},
                ],
            }
        )
        page.filter_text.set("segunda")
        app.pages.select(page)
        app.update()
        page.table.focus_force()
        page.table.event_generate("<Alt-a>")
        app.update()
        self.assertEqual(page.selected_keys(), ["1"])


if __name__ == "__main__":
    unittest.main()
