import base64
import hashlib
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

import requests
from playlist_files import load_csv, export_text
from playlist_import import load_text, load_playlist
from spotify_account import SpotifyAccount, authorize, callback_page
from metadata import MetadataError

ID = "A" * 22
CLIENT = "a" * 32


class PlaylistFilesTests(unittest.TestCase):
    def test_exportify_csv_preserves_quoted_titles_and_normalizes_uris(self):
        data = '\ufeffTrack URI,Track Name,Artist Name(s),Duration (ms)\nspotify:track:' + ID + ',"Título, com vírgula",João;Maria,123000\nspotify:local:bad,Local,Someone,0\n'
        result = load_csv(data)
        self.assertEqual(len(result["tracks"]), 1)
        row = result["tracks"][0]
        self.assertEqual(row["title"], "Título, com vírgula")
        self.assertEqual(row["artists"], ["João", "Maria"])
        self.assertEqual(row["duration_ms"], 123000)
        self.assertEqual(row["source_url"], "https://open.spotify.com/track/" + ID)
        self.assertIn("1 linhas", result["note"])

    def test_csv_large_list_cap_and_missing_columns(self):
        data = 'Track URL;Track Name\n' + ('https://open.spotify.com/track/' + ID + ';Música\n') * 1300
        self.assertEqual(len(load_csv(data, limit=2000)["tracks"]), 1300)
        result = load_csv(data, limit=100)
        self.assertEqual(len(result["tracks"]), 100)
        self.assertIn("Limite", result["note"])
        with self.assertRaises(MetadataError):
            load_csv("Title,Artist\nMusic,Someone\n")

    def test_export_txt_and_m3u_roundtrip(self):
        rows = [{"source_url": "spotify:track:" + ID, "title": "Música\n#fake", "artists": ["João"], "duration_ms": 123000},
                {"source_url": "https://www.youtube.com/watch?v=bj-AE5cEaVo", "title": "Vídeo"}]
        for m3u in (False, True):
            content = export_text(rows, m3u=m3u)
            self.assertEqual(len(load_text(content)["tracks"]), 2)
            self.assertNotIn("\n#fake", content)
            if m3u:
                self.assertIn("#EXTINF:123,João - Música #fake", content)


class SpotifyAccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "spotify-account.dpapi"
        self.account = SpotifyAccount(self.path)

    def test_pagination_reads_all_1300_and_uses_only_spotify_endpoint(self):
        account = self.account
        def get(path, params=None):
            if params is None:
                return {"name": "Minha lista"}
            offset = params["offset"]
            count = min(params["limit"], 1300 - offset)
            track = {"id": ID, "type": "track", "name": "Faixa", "artists": [{"name": "Artista"}], "duration_ms": 1000}
            return {"items": [{"item": track}] * count, "total": 1300, "next": "https://untrusted.invalid/ignored" if offset + count < 1300 else None}
        account.get = Mock(side_effect=get)
        result = account.playlist(ID, limit=2000)
        self.assertEqual(len(result["tracks"]), 1300)
        self.assertEqual(account.get.call_count, 27)
        self.assertEqual(account.get.call_args.args[0], f"playlists/{ID}/items")
        self.assertEqual(account.get.call_args.args[1], {"offset": 1250, "limit": 50})

    def test_skips_unavailable_and_supports_legacy_track_key(self):
        track = {"id": ID, "type": "track", "name": "Song", "artists": []}
        self.account.get = Mock(side_effect=[{"name": "List"}, {"items": [{"item": None}, {"track": track}, {"item": {**track, "type": "episode"}}, {"item": track, "is_local": True}], "next": "ignored", "total": 200}])
        result = self.account.playlist(ID, limit=4)
        self.assertEqual(len(result["tracks"]), 1)
        self.assertIn("3 itens", result["note"])
        self.assertIn("Limite de 4", result["note"])

    def test_account_routing_and_public_fallback(self):
        client = Mock()
        self.account.client_id = CLIENT
        self.account.refresh_token = "fake-refresh"
        self.account.playlist = Mock(return_value={"title": "Full", "tracks": []})
        load_playlist("https://open.spotify.com/playlist/" + ID, client, limit=2000, account=self.account)
        self.account.playlist.assert_called_once()
        client.request.assert_not_called()

    def test_refresh_rotation_and_encrypted_remember(self):
        self.account.accept(CLIENT, {"access_token": "fake-access", "refresh_token": "fake-refresh", "expires_in": 3600}, remember=True)
        self.assertNotIn(b"fake-refresh", self.path.read_bytes())
        restored = SpotifyAccount(self.path)
        self.assertTrue(restored.connected)
        with patch("spotify_account.token_request", return_value={"access_token": "renewed", "refresh_token": "rotated", "expires_in": 3600}) as refresh:
            self.assertEqual(restored.token(), "renewed")
            self.assertEqual(restored.token(), "renewed")
            self.assertEqual(refresh.call_count, 1)
        self.assertEqual(SpotifyAccount(self.path).refresh_token, "rotated")
        restored.disconnect()
        self.assertFalse(self.path.exists())
        self.assertFalse(restored.connected)

    def test_session_only_connection_has_no_file(self):
        self.account.accept(CLIENT, {"access_token": "access", "refresh_token": "refresh"}, remember=False)
        self.assertTrue(self.account.connected)
        self.assertFalse(self.path.exists())

    def test_oauth_loopback_checks_state_and_pkce_and_exchanges_code(self):
        seen = {}
        finished = threading.Event()
        errors = []
        def opener(url):
            query = parse_qs(urlsplit(url).query)
            seen.update(query)
            def callback():
                try:
                    wrong = requests.get(query["redirect_uri"][0], params={"state": "wrong", "code": "wrong"}, timeout=5)
                    self.assertEqual(wrong.status_code, 400)
                    self.assertNotIn('setTimeout', wrong.text)
                    correct = requests.get(query["redirect_uri"][0], params={"state": query["state"][0], "code": "test-code"}, timeout=5)
                    self.assertEqual(correct.status_code, 200)
                    self.assertIn('text/html', correct.headers['Content-Type'])
                    self.assertEqual(correct.headers['Cache-Control'], 'no-store')
                    self.assertIn('}, 3000)', correct.text)
                    self.assertIn('window.close()', correct.text)
                    self.assertNotIn('test-code', correct.text)
                    self.assertNotIn(query['state'][0], correct.text)
                except Exception as exc:
                    errors.append(exc)
                finally:
                    finished.set()
            threading.Thread(target=callback, daemon=True).start()
            return True
        with patch("spotify_account.token_request", return_value={"access_token": "access", "refresh_token": "refresh"}) as exchange:
            client_id, result = authorize(CLIENT, threading.Event(), opener=opener, port=0, timeout=5)
        self.assertTrue(finished.wait(5))
        self.assertFalse(errors)
        data = exchange.call_args.args[0]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(data["code_verifier"].encode()).digest()).decode().rstrip("=")
        self.assertEqual(challenge, seen["code_challenge"][0])
        self.assertEqual(data["code"], "test-code")
        self.assertNotIn("client_secret", data)
        self.assertEqual(client_id, CLIENT)

    def test_oauth_cancel_and_browser_failure_release_local_port(self):
        cancel = threading.Event()
        cancel.set()
        with self.assertRaisesRegex(MetadataError, "cancelada"):
            authorize(CLIENT, cancel, opener=lambda _: True, port=0)
        with self.assertRaisesRegex(MetadataError, "navegador"):
            authorize(CLIENT, threading.Event(), opener=lambda _: False, port=0)

    def test_callback_return_is_fixed_and_has_no_automatic_action_on_invalid_state(self):
        self.assertIn('onda://spotify-return', callback_page(True, True, 'onda://spotify-return').decode())
        self.assertNotIn('setTimeout', callback_page(False, False).decode())
        self.assertIn('não concedida', callback_page(True, False).decode())
        with self.assertRaises(ValueError):
            callback_page(True, True, 'https://example.com/untrusted')

    def test_forbidden_and_rate_limit_do_not_return_partial_success(self):
        self.account.token = Mock(return_value="fake")
        for code, expected in ((403, "sua ou colaborativa"), (429, "Aguarde")):
            response = Mock(status_code=code, headers={"Retry-After": "10"})
            context = Mock()
            context.__enter__ = Mock(return_value=response)
            context.__exit__ = Mock(return_value=False)
            with patch("spotify_account.requests.get", return_value=context):
                with self.assertRaisesRegex(MetadataError, expected):
                    self.account.get("playlists/" + ID)


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS"), "Tk integration")
class PlaylistAccountUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"LOCALAPPDATA": self.temp.name})
        self.env.start()
        from app import App
        self.app = App(show_welcome=False)
        self.app.withdraw()
        self.page = self.app.playlist_page

    def tearDown(self):
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def test_actions_fit_minimum_window_and_closing_app_cancels_connection(self):
        self.app.deiconify()
        self.app.geometry("840x720")
        self.app.pages.select(self.page)
        self.app.update()
        for button in (self.page.import_button, self.page.export_button, self.page.spotify_button):
            self.assertGreater(button.winfo_width(), 50)
            self.assertLessEqual(button.winfo_rootx() + button.winfo_width(), self.app.winfo_rootx() + self.app.winfo_width())
        self.page.connect_spotify()
        dialog = self.page.spotify_window
        self.app.update()
        self.assertTrue(dialog.winfo_exists())
        dialog.close()
        self.assertTrue(dialog.cancel.is_set())

    def test_csv_import_export_all_even_when_filtered_and_connection_window(self):
        csv = Path(self.temp.name) / "Minha lista.csv"
        csv.write_text('Track URI,Track Name,Artist Name(s)\nspotify:track:' + ID + ',Primeira,Artista\nspotify:track:' + "B" * 22 + ',Segunda,Outro\n', encoding="utf-8")
        with patch("playlist_ui.filedialog.askopenfilename", return_value=str(csv)):
            self.page.text_file()
        self.assertEqual(self.page.playlist_title, "Minha lista")
        self.assertEqual(len(self.page.records), 2)
        self.page.filter_text.set("primeira")
        out = Path(self.temp.name) / "saved.m3u"
        with patch("playlist_ui.filedialog.asksaveasfilename", return_value=str(out)):
            self.page.export_file()
        self.assertEqual(len(load_text(out.read_text(encoding="utf-8"))["tracks"]), 2)
        self.page.connect_spotify()
        dialog = self.page.spotify_window
        self.assertIn("127.0.0.1", dialog.redirect.get())
        dialog.close()
        self.assertTrue(dialog.cancel.is_set())
        self.assertFalse(dialog.winfo_exists())


if __name__ == "__main__":
    unittest.main()
