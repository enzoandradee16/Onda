import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image


class CoverOptimizationTests(unittest.TestCase):
    def test_playback_artwork_keeps_resolution_without_changing_small_card_cache(self):
        from catalog_ui import cached_cover_png, cover_png

        raw = io.BytesIO()
        Image.new('RGB', (1200, 1000), 'blue').save(raw, format='JPEG')
        cached_cover_png.cache_clear()
        try:
            with patch(
                'tagging.fetch_cover', return_value=(raw.getvalue(), 'image/jpeg')
            ) as fetch:
                small = cover_png('https://fixture.example/high.jpg')
                large = cover_png('https://fixture.example/high.jpg', size=768)
                self.assertEqual(
                    large, cover_png('https://fixture.example/high.jpg', size=768)
                )
                self.assertEqual(fetch.call_count, 2)
            self.assertEqual(Image.open(io.BytesIO(small)).size, (124, 103))
            self.assertEqual(Image.open(io.BytesIO(large)).size, (768, 640))
        finally:
            cached_cover_png.cache_clear()

    def test_local_playback_artwork_uses_original_embedded_image(self):
        import base64, wave
        from mutagen.wave import WAVE
        from mutagen.id3 import APIC
        from audio_library import cover_preview

        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'local.wav'
            with wave.open(str(path), 'wb') as audio:
                audio.setparams((1, 2, 8000, 0, 'NONE', ''))
                audio.writeframes(b'\0\0' * 800)
            raw = io.BytesIO()
            Image.new('RGB', (1200, 1000), 'blue').save(raw, format='JPEG')
            tags = WAVE(path)
            tags.add_tags()
            tags.tags.add(APIC(mime='image/jpeg', type=3, data=raw.getvalue()))
            tags.save()
            self.assertEqual(
                Image.open(
                    io.BytesIO(base64.b64decode(cover_preview(path, size=768)))
                ).size,
                (768, 640),
            )
            self.assertEqual(
                Image.open(io.BytesIO(base64.b64decode(cover_preview(path)))).size,
                (240, 200),
            )

    def test_cover_preserves_proportions_caches_and_needs_no_ffmpeg(self):
        from catalog_ui import cached_cover_png, cover_png

        raw = io.BytesIO()
        Image.new("RGB", (710, 600), "red").save(raw, format="JPEG")
        cached_cover_png.cache_clear()
        try:
            with (
                patch(
                    "tagging.fetch_cover", return_value=(raw.getvalue(), "image/jpeg")
                ) as fetch,
                patch("subprocess.run", side_effect=AssertionError("No child process")),
            ):
                first = cover_png("https://fixture.example/cover.jpg", "missing-ffmpeg")
                self.assertEqual(
                    first,
                    cover_png("https://fixture.example/cover.jpg", "another-folder"),
                )
                fetch.assert_called_once()
            with Image.open(io.BytesIO(first)) as thumbnail:
                self.assertEqual(thumbnail.size, (124, 105))
                self.assertEqual(thumbnail.format, "PNG")
        finally:
            cached_cover_png.cache_clear()


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
class QueueOptimizationTests(unittest.TestCase):
    def test_many_title_events_save_once_and_keep_all_names(self):
        from app import App

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, {"LOCALAPPDATA": folder}),
        ):
            app = App(show_welcome=False)
            try:
                app.withdraw()
                jobs = [
                    {
                        "url": f"https://example.com/{i}",
                        "mode": "mp3",
                        "folder": folder,
                        "state": "Na fila",
                    }
                    for i in range(100)
                ]
                app.add(restored_jobs=jobs)
                for i, (identity, job) in enumerate(app.jobs.items()):
                    app.events.put(
                        (
                            identity,
                            {
                                "type": "queue_title",
                                "url": job["url"],
                                "title": f"Artista - Música {i}",
                            },
                        )
                    )
                app.after_cancel(app._poll_after)
                with patch.object(
                    app.library, "save_queue", wraps=app.library.save_queue
                ) as save:
                    app.poll_events()
                    self.assertEqual(save.call_count, 1)
                self.assertEqual(len(app.library.load_queue()), 100)
                self.assertTrue(
                    all(
                        job["display_name"].startswith("Artista - Música")
                        for job in app.library.load_queue()
                    )
                )
            finally:
                app.destroy()

    def test_history_search_debounces_and_unchanged_rows_keep_selection(self):
        from app import App

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, {"LOCALAPPDATA": folder}),
        ):
            app = App(show_welcome=False)
            try:
                app.withdraw()
                app.library.add_history(
                    str(Path(folder) / "Artista - Música.mp3"), "mp3"
                )
                pane = app.history_page
                pane.refresh()
                selected = pane.table.get_children()[0]
                pane.table.selection_set(selected)
                with patch.object(
                    pane.table, "delete", wraps=pane.table.delete
                ) as delete:
                    pane.refresh()
                    delete.assert_not_called()
                with patch.object(
                    app.library, "history", wraps=app.library.history
                ) as read:
                    for query in ("A", "Ar", "Art", "Artista"):
                        pane.query.set(query)
                    read.assert_not_called()
                    pane.refresh()
                    read.assert_called_once_with("Artista")
                self.assertEqual(pane.table.selection(), (selected,))
            finally:
                app.destroy()
