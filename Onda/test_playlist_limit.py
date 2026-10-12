import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from engine import build_options
from library import LibraryStore
from playlist_import import load_playlist, load_text, spotify_playlist
from playlist_options import playlist_limit
from preferences import PreferenceStore


class PlaylistLimitTests(unittest.TestCase):
    def test_validation_and_download_options(self):
        for value in (True, 0, 5001, "invalid", None):
            with self.assertRaises(ValueError):
                playlist_limit(value)
        config = {"mode": "mp3", "folder": ".", "height": 1080, "playlist": True, "playlist_limit": 2000}
        self.assertEqual(build_options(config)["playlistend"], 2000)
        config["playlist"] = False
        self.assertEqual(build_options(config)["playlistend"], 1)

    def test_deezer_paginates_and_caps_partial_last_page(self):
        client = Mock()
        def get(url, **kwargs):
            if not url.endswith("/tracks"):
                return {"title": "Large playlist"}
            options = kwargs["params"]
            start, count = options["index"], options["limit"]
            return {"data": [{"id": i + 1, "title": f"Song {i}", "artist": {"name": "Artist"}}
                             for i in range(start, start + count)], "next": "https://untrusted.example/ignored"}
        client.get_json.side_effect = get
        result = load_playlist("https://www.deezer.com/playlist/123", client, limit=250)
        self.assertEqual(len(result["tracks"]), 250)
        calls = client.get_json.call_args_list[1:]
        self.assertEqual([c.kwargs["params"] for c in calls],
                         [{"index": 0, "limit": 100}, {"index": 100, "limit": 100}, {"index": 200, "limit": 50}])
        self.assertTrue(all(c.args[0] == "https://api.deezer.com/playlist/123/tracks" for c in calls))

    def test_youtube_and_text_import_allow_more_than_100(self):
        entries = [{"id": f"{i:011d}", "title": str(i)} for i in range(300)]
        with patch("yt_dlp.YoutubeDL") as downloader:
            downloader.return_value.__enter__.return_value.extract_info.return_value = {"title": "Large", "entries": entries}
            result = load_playlist("https://www.youtube.com/playlist?list=PL_TEST", Mock(), limit=250)
            self.assertEqual(downloader.call_args.args[0]["playlistend"], 250)
            self.assertEqual(len(result["tracks"]), 250)
        lines = "\n".join("https://www.youtube.com/watch?v=" + row["id"] for row in entries)
        self.assertEqual(len(load_text(lines, limit=250)["tracks"]), 250)

    def test_spotify_public_limit_and_availability_note(self):
        rows = [{"uri": "spotify:track:" + f"{i:022d}", "title": str(i)} for i in range(300)]
        entity = {"id": "A" * 22, "type": "playlist", "title": "Large", "trackList": rows}
        data = {"props": {"pageProps": {"state": {"data": {"entity": entity}}}}}
        result = spotify_playlist('<script id="__NEXT_DATA__">' + json.dumps(data) + '</script>', "A" * 22, limit=250)
        self.assertEqual(len(result["tracks"]), 250)
        self.assertIn("apenas parte", result["note"])

    def test_settings_and_queue_preserve_the_chosen_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            store = PreferenceStore(Path(folder) / "settings.json")
            store.save({"playlist_limit": "5000"})
            self.assertEqual(store.load()["playlist_limit"], "5000")
            self.assertNotIn("playlist_limit", PreferenceStore.clean({"playlist_limit": "999999"}))
            library = LibraryStore(Path(folder) / "library.sqlite3")
            library.save_queue([{"url": "https://www.youtube.com/playlist?list=PL_TEST", "mode": "mp3", "folder": folder,
                                 "playlist": True, "playlist_limit": 2000, "state": "Na fila"}])
            self.assertEqual(library.load_queue()[0]["playlist_limit"], 2000)


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
class PlaylistLimitUiTests(unittest.TestCase):
    def test_new_jobs_capture_limit_and_large_selection_is_added_in_one_batch(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"LOCALAPPDATA": folder}):
            from app import App
            app = App()
            app.withdraw()
            try:
                app.playlist.set(True)
                app.playlist_limit.set("2000")
                item = app.add(lines=["https://www.youtube.com/playlist?list=PL_TEST"])[0]
                app.playlist_limit.set("500")
                self.assertEqual(app.jobs[item]["playlist_limit"], 2000)
                page = app.playlist_page
                records = [{"title": str(i), "source_url": f"https://www.youtube.com/watch?v={i:011d}"} for i in range(250)]
                page.display({"title": "Large", "tracks": records, "note": ""})
                with patch.object(app, "add", return_value=["job"] * 250) as add:
                    page.add()
                    add.assert_called_once()
                    self.assertEqual(len(add.call_args.kwargs["lines"]), 250)
            finally:
                app.destroy()


if __name__ == "__main__":
    unittest.main()
