import os
import tempfile
import unittest
from unittest.mock import patch

from playlist_ui import search_text


class PlaylistSearchTests(unittest.TestCase):
    def test_accents_and_case_are_ignored(self):
        self.assertEqual(search_text("MÚSICA João"), "musica joao")


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
class PlaylistSearchUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {"LOCALAPPDATA": self.temp.name})
        self.environment.start()
        from app import App
        self.app = App(show_welcome=False)
        self.app.withdraw()
        self.page = self.app.playlist_page
        self.rows = [{"title": "Música de Verão", "artists": ["João"], "source_url": "https://www.deezer.com/track/1"},
                     {"title": "Outra música", "artists": ["Maria"], "source_url": "https://www.deezer.com/track/2"},
                     {"title": "Canção da noite", "artists": ["João"], "source_url": "https://www.deezer.com/track/3"}]
        self.page.display({"title": "Favoritas", "tracks": self.rows, "note": ""})

    def tearDown(self):
        self.app.destroy()
        self.environment.stop()
        self.temp.cleanup()

    def test_search_matches_title_and_artist_then_restores_rows_and_matches(self):
        page = self.page
        page.table.set("0", "match", "Versão conferida")
        page.filter_text.set("JOAO verao")
        self.assertEqual(page.table.get_children(), ("0",))
        self.assertEqual(page.filter_count.get(), "1 de 3")
        page.filter_text.set("joao")
        self.assertEqual(page.table.get_children(), ("0", "2"))
        page.filter_text.set("não existe")
        self.assertEqual(page.table.get_children(), ())
        self.assertEqual(page.filter_count.get(), "Nenhum resultado")
        page.filter_text.set("")
        self.assertEqual(page.table.get_children(), ("0", "1", "2"))
        self.assertEqual(page.table.set("0", "match"), "Versão conferida")
        self.assertEqual(page.filter_count.get(), "3 de 3")

    def test_adding_filtered_results_never_includes_hidden_selection(self):
        page = self.page
        page.filter_text.set("maria")
        page.table.selection_set(("0", "1", "2"))  # Defensive check for detached rows.
        with patch.object(self.app, "add", return_value=["job"]) as add:
            page.add()
            self.assertEqual(add.call_args.kwargs["lines"], [self.rows[1]["source_url"]])
            self.assertEqual(add.call_args.kwargs["overrides"]["playlist_title"], "Favoritas")

    def test_playlist_audio_and_streaming_fallback_do_not_use_links_quality(self):
        app, page = self.app, self.page
        app.mp3_quality.set("96 kbps")
        app.playlist_mp3_quality.set("192 kbps")
        app.playlist_mode.set("Vídeo · MP4")
        page.add()
        self.assertEqual(len(app.jobs), 3)
        for job in app.jobs.values():
            self.assertEqual(job["mode"], "mp3")
            self.assertEqual(job["audio_quality"], "192 kbps")
        self.assertEqual(app.mp3_quality.get(), "96 kbps")

    def test_playlist_video_options_and_preferences_are_independent(self):
        from engine import MODES
        from preferences import PreferenceStore
        app, page = self.app, self.page
        app.height.set("720p")
        app.fps.set("Original")
        app.playlist_mode.set("Vídeo · MP4")
        app.playlist_height.set("1440p")
        app.playlist_fps.set("60 fps")
        page.format_changed()
        self.assertTrue(page.fps_combo.winfo_manager())
        self.assertEqual(page.quality_combo.cget("textvariable"), str(app.playlist_height))
        page.display({"title": "Vídeos", "note": "", "tracks": [{"title": "Teste", "source_url": "https://www.youtube.com/watch?v=bj-AE5cEaVo"}]})
        page.add()
        job = next(iter(app.jobs.values()))
        self.assertEqual((job["mode"], job["height"], job["fps"]), ("mp4", 1440, 60))
        app.playlist_mode.set(next(key for key, value in MODES.items() if value == "mp3"))
        page.format_changed()
        self.assertFalse(page.fps_combo.winfo_manager())
        self.assertEqual(app.height.get(), "720p")
        store = PreferenceStore(path=__import__("pathlib").Path(self.temp.name) / "roundtrip.json")
        store.save({name: variable.get() for name, variable in app.preference_fields.items()})
        values = store.load()
        self.assertEqual(values["playlist_height"], "1440p")
        self.assertEqual(values["height"], "720p")

    def test_loading_another_playlist_discards_detached_rows_and_resets_filter(self):
        self.page.filter_text.set("maria")
        self.page.display({"title": "Nova playlist", "tracks": [self.rows[0]], "note": ""})
        self.assertEqual(self.page.filter_text.get(), "")
        self.assertEqual(self.page.table.get_children(), ("0",))
        self.assertFalse(self.page.table.exists("2"))
        self.assertEqual(self.page.selected_keys(), ["0"])
        self.assertEqual(self.page.playlist_title, "Nova playlist")


if __name__ == "__main__":
    unittest.main()
