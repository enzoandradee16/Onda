import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from file_output import component, destination
from library import LibraryStore


class PlaylistFolderTests(unittest.TestCase):
    def test_playlist_tracks_stay_together_and_invalid_names_stay_inside_root(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            record = {"platform": "Deezer", "id": "12", "artists": ["Artist"], "album": "Album"}
            for organization in ("Catálogo", "Artista", "Artista / Álbum", "Pasta de destino"):
                config = {"folder": folder, "playlist_title": "Minhas favoritas", "organization": organization}
                self.assertEqual(destination(config, record), root / "Minhas favoritas")
            for title in ("../Outra/pasta", "CON", "Rock: anos 80?", ".."): 
                path = destination({"folder": folder, "playlist_title": title})
                self.assertEqual(path.parent, root)
                self.assertEqual(path.name, component(title))
            self.assertEqual(destination({"folder": folder, "organization": "Artista"}, record), root / "Artist")

    def test_direct_playlist_uses_original_title_from_each_entry(self):
        with tempfile.TemporaryDirectory() as folder:
            config = {"folder": folder, "playlist": True}
            info = {"playlist_title": "Minha playlist original", "playlist_index": 1}
            self.assertEqual(destination(config, info=info), Path(folder).resolve() / "Minha playlist original")
            self.assertEqual(destination({**config, "playlist": False}, info=info), Path(folder).resolve())
            self.assertEqual(destination(config, info={"playlist_id": "PL_ID"}), Path(folder).resolve() / "Playlist")

    def test_playlist_title_survives_queue_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LibraryStore(Path(folder) / "library.sqlite3")
            store.save_queue([{"url": "https://www.deezer.com/track/12", "mode": "mp3", "folder": folder,
                               "playlist_title": "Favoritas", "state": "Na fila"}])
            self.assertEqual(store.load_queue()[0]["playlist_title"], "Favoritas")

    @unittest.skipUnless(os.environ.get("ONDA_FFMPEG"), "Worker integration")
    def test_worker_publishes_in_playlist_folder(self):
        from engine import run_worker
        def download(url, options, configure, saved):
            from yt_dlp import YoutubeDL
            def add(processor, when=None):
                if when == "after_move":
                    path = Path(options["paths"]["home"]) / "Artista - Música.wav"
                    path.write_bytes(b"completed audio")
                    processor.run({"filepath": str(path), "playlist_title": "Minha playlist", "playlist_index": 1})
            with YoutubeDL({"quiet": True}) as downloader, patch.object(downloader, "add_post_processor", side_effect=add):
                configure(downloader)
            return 0
        with tempfile.TemporaryDirectory() as folder:
            config = {"url": "https://www.youtube.com/playlist?list=PL_TEST", "mode": "original", "playlist": True,
                      "folder": folder, "ffmpeg": os.environ["ONDA_FFMPEG"]}
            output = io.StringIO()
            with patch("engine.download_with_recovery", side_effect=download), contextlib.redirect_stdout(output):
                code = run_worker(config)
            self.assertEqual(code, 0, output.getvalue())
            self.assertEqual((Path(folder) / "Minha playlist" / "Artista - Música.wav").read_bytes(), b"completed audio")
            self.assertFalse((Path(folder) / "Artista - Música.wav").exists())


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
class PlaylistFolderUiTests(unittest.TestCase):
    def test_import_title_is_captured_and_same_track_can_belong_to_two_playlists(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"LOCALAPPDATA": folder}):
            from app import App
            app = App()
            app.withdraw()
            try:
                app.folder.set(folder)
                app.mode.set("Áudio · MP3 (320 kbps)")
                row = {"title": "Song", "source_url": "https://www.deezer.com/track/12"}
                for title in ("Playlist A", "Playlist B"):
                    app.playlist_page.display({"title": title, "tracks": [row], "note": ""})
                    app.playlist_page.add()
                self.assertEqual(len(app.jobs), 2)
                self.assertEqual({job["playlist_title"] for job in app.jobs.values()}, {"Playlist A", "Playlist B"})
                self.assertTrue(all(Path(job["folder"]).resolve() == Path(folder).resolve() for job in app.jobs.values()))
                app.folder.set(str(Path(folder) / "Outra pasta"))
                self.assertTrue(all(Path(job["folder"]).resolve() == Path(folder).resolve() for job in app.jobs.values()))
            finally:
                app.destroy()


if __name__ == "__main__":
    unittest.main()
