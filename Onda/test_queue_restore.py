import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from library import LibraryStore


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
class QueueRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"LOCALAPPDATA": self.temp.name})
        self.env.start()
        self.store = LibraryStore(Path(self.temp.name) / "Onda" / "library.sqlite3")
        self.app = None

    def tearDown(self):
        if self.app:
            self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def records(self, count):
        return [
            {
                "url": f"https://example.com/{i}",
                "mode": "mp3" if i % 2 == 0 else "m4a",
                "audio_quality": "192 kbps" if i % 2 == 0 else "128 kbps",
                "height": 720,
                "folder": str(Path(self.temp.name) / str(i % 7)),
                "playlist": False,
                "playlist_title": f"Lista {i % 7}",
                "state": "Falhou" if i % 3 == 0 else "Na fila",
                "confirm_version": i % 2 == 0,
                "review_metadata": False,
                "fps": None,
            }
            for i in range(count)
        ]

    def test_bulk_restore_preserves_order_options_and_failed_duplicates_with_one_save(
        self,
    ):
        from app import App

        records = self.records(2000)
        records.append(dict(records[0]))
        self.store.save_queue(records)
        original_save = LibraryStore.save_queue
        with patch.object(
            LibraryStore, "save_queue", autospec=True, side_effect=original_save
        ) as save:
            self.app = App(show_welcome=False)
            self.app.withdraw()
            self.assertEqual(save.call_count, 1)
        restored = list(self.app.jobs.values())
        self.assertEqual(len(restored), len(records))
        for expected, actual in zip(records, restored):
            for key in expected:
                self.assertEqual(actual[key], expected[key], key)
        self.assertEqual(len(self.store.load_queue()), len(records))
        self.assertFalse(self.app.running)
        self.assertIsNone(self.app.active)
        with patch.object(
            LibraryStore, "save_queue", autospec=True, side_effect=original_save
        ) as save:
            self.app.add(lines=["https://example.com/extra"])
            self.assertEqual(save.call_count, 1)
        self.assertEqual(len(self.store.load_queue()), len(records) + 1)

    def test_interrupted_restore_does_not_replace_original_queue_with_partial_list(
        self,
    ):
        from app import App
        from tkinter import ttk

        records = self.records(5)
        self.store.save_queue(records)
        original_insert = ttk.Treeview.insert
        calls = [0]

        def insert(tree, *args, **kwargs):
            if tuple(tree["columns"]) == ("name", "format", "size", "status"):
                calls[0] += 1
                if calls[0] == 2:
                    raise RuntimeError("Simulated interruption")
            return original_insert(tree, *args, **kwargs)

        with patch.object(ttk.Treeview, "insert", insert):
            self.app = App(show_welcome=False)
            self.app.withdraw()
        self.assertEqual(len(self.app.jobs), 1)
        self.assertEqual(self.store.load_queue(), records)

    def test_empty_queue_does_not_write_during_startup(self):
        from app import App

        with patch.object(LibraryStore, "save_queue", autospec=True) as save:
            self.app = App(show_welcome=False)
            self.app.withdraw()
            save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
