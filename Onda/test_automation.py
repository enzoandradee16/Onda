import base64
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from matching import score_candidate, select_candidate, AmbiguousMatch
from metadata import base_record
from tagging import apply_tags


def catalog():
    record = base_record("Apple / iTunes", "123456", "https://music.apple.com/br/song/123456", "Test catalog")
    record.update(title="Canção Azul", artists=["Artista Exemplo"], album="Álbum de Teste",
                  album_artists=["Artista Exemplo"], release_date="2024-05-01", duration_ms=200000,
                  track_number=2, disc_number=1, genre="Pop", isrc="BRABC2400001", explicit=False)
    return record


def candidate(**values):
    return dict({"id": "abcdefghijk", "title": "Artista Exemplo - Canção Azul (Official Audio)",
                 "channel": "Artista Exemplo - Topic", "duration": 200}, **values)


class MatchingTests(unittest.TestCase):
    def test_guest_credit_can_be_missing_from_youtube_title(self):
        record = dict(catalog(), title="Make Luv (feat. Oliver Cheatham)", artists=["Room 5"], duration_ms=212000)
        upload = candidate(title="Make Luv", channel="Room 5 - Topic", duration=213)
        self.assertGreater(score_candidate(record, upload), .9)

    def test_guest_credit_can_be_in_combined_artist(self):
        record = dict(catalog(), title="Make Luv", artists=["Room 5 featuring Oliver Cheatham"], duration_ms=212000)
        self.assertGreater(score_candidate(record, candidate(title="Make Luv", channel="Room 5 - Topic", duration=213)), .9)

    def test_credit_normalization_keeps_version_checks(self):
        record = dict(catalog(), title="Make Luv (feat. Oliver Cheatham)", artists=["Room 5"], duration_ms=212000)
        self.assertIsNone(score_candidate(record, candidate(title="Room 5 Make Luv feat. Oliver Cheatham Extended", duration=213)))

    def test_uncertain_duration_requires_explicit_choice(self):
        record = dict(catalog(), title="Make Luv", artists=["Room 5"], duration_ms=212000)
        with self.assertRaises(AmbiguousMatch) as caught:
            select_candidate(record, [candidate(title="Room 5 Make Luv (Extended)", duration=380)])
        self.assertTrue(caught.exception.candidates[0]["manual_review"])

    def test_manual_choices_exclude_unrelated_artists_and_karaoke(self):
        record = dict(catalog(), title="Make Luv", artists=["Room 5"], duration_ms=212000)
        for title in ("Someone Else Make Luv", "Room 5 Make Luv Karaoke"):
            with self.subTest(title=title), self.assertRaises(ValueError):
                select_candidate(record, [candidate(title=title, channel="Other", duration=380)])

    def test_correct_match(self):
        record = catalog()
        selected = select_candidate(record, [candidate()])
        self.assertEqual(selected["source_url"], "https://www.youtube.com/watch?v=abcdefghijk")
        self.assertGreaterEqual(selected["match_score"], .9)

    def test_versions_rejected(self):
        for version in ("live", "cover", "remix", "karaoke", "sped up", "slowed", "extended"):
            with self.subTest(version=version):
                self.assertIsNone(score_candidate(catalog(), candidate(title="Artista Exemplo Canção Azul " + version)))

    def test_wrong_artist_duration_and_missing_metadata(self):
        self.assertIsNone(score_candidate(catalog(), candidate(title="Canção Azul", channel="Outro Artista")))
        self.assertIsNone(score_candidate(catalog(), candidate(duration=300)))
        self.assertIsNone(score_candidate(catalog(), candidate(duration=None)))
        record = catalog()
        record["artists"] = []
        with self.assertRaises(ValueError):
            select_candidate(record, [candidate()])

    def test_ambiguous_titles_rejected(self):
        selected=select_candidate(catalog(), [candidate(), candidate(id="12345678901", title="Artista Exemplo Canção Azul Special")])
        self.assertEqual(selected['id'],candidate()['id'])

    def test_same_version_different_upload_offers_choice(self):
        with self.assertRaises(AmbiguousMatch) as caught:
            select_candidate(catalog(), [candidate(), candidate(id="12345678901")])
        self.assertEqual(len(caught.exception.candidates), 2)


@unittest.skipUnless(os.environ.get("ONDA_FFMPEG"), "Set ONDA_FFMPEG for audio tag integration")
class TagTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ffmpeg = str(Path(os.environ["ONDA_FFMPEG"]) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"))
        self.record = catalog()
        self.match = select_candidate(self.record, [candidate()])
        self.cover = (base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="), "image/png")

    def make_audio(self, extension):
        path = self.root / ("test." + extension)
        subprocess.run([self.ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "sine=frequency=440:duration=1", str(path)], check=True)
        return path

    def test_tags_and_artwork_in_all_formats(self):
        from mutagen.id3 import ID3
        from mutagen.mp4 import MP4
        from mutagen.flac import FLAC
        for extension in ("mp3", "m4a", "flac"):
            with self.subTest(extension=extension):
                path = self.make_audio(extension)
                sidecar = apply_tags(path, self.record, self.match, self.cover)
                provenance = json.loads(Path(sidecar).read_text(encoding="utf-8"))
                self.assertEqual(provenance["catalog"], self.record)
                self.assertEqual(provenance["audio_source"], self.match["source_url"])
                if extension == "mp3":
                    tags = ID3(path)
                    self.assertEqual(str(tags["TIT2"]), self.record["title"])
                    self.assertEqual(str(tags["TSRC"]), self.record["isrc"])
                    self.assertEqual(tags.getall("APIC")[0].data, self.cover[0])
                    self.assertEqual(json.loads(tags["TXXX:ONDA_METADATA"].text[0]), provenance)
                elif extension == "m4a":
                    tags = MP4(path)
                    self.assertEqual(tags["\u00a9nam"][0], self.record["title"])
                    self.assertEqual(tags["trkn"][0][0], 2)
                    self.assertEqual(bytes(tags["covr"][0]), self.cover[0])
                    self.assertEqual(json.loads(tags["----:com.apple.iTunes:ONDA_METADATA"][0]), provenance)
                else:
                    tags = FLAC(path)
                    self.assertEqual(tags["title"][0], self.record["title"])
                    self.assertEqual(tags["isrc"][0], self.record["isrc"])
                    self.assertEqual(tags.pictures[0].data, self.cover[0])
                # Verify the resulting audio still decodes.
                subprocess.run([self.ffmpeg, "-v", "error", "-i", str(path), "-f", "null", "-"], check=True)

    def test_tagging_failure_preserves_audio(self):
        path = self.make_audio("mp3")
        before = path.read_bytes()
        with patch("mutagen.id3.ID3.save", side_effect=OSError("test write failure")):
            with self.assertRaises(OSError):
                apply_tags(path, self.record, self.match, self.cover)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(path.with_suffix(".mp3.metadata.json").exists())

    def test_streaming_pipeline_tags_before_success(self, spotify_anchor=None):
        import functools
        import http.server
        import http.cookiejar
        import threading
        from yt_dlp.cookies import YoutubeDLCookieJar
        from engine import run_worker, download_with_recovery
        source = self.make_audio("wav")
        class SessionHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                if 'onda_test_session=search-session' not in self.headers.get('Cookie',''):
                    self.send_error(403, 'Search session was not retained')
                    return
                super().do_GET()
        handler = functools.partial(SessionHandler, directory=str(self.root))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        # This generic extractor identifies the synthetic fixture as "test".
        match = {**self.match, "id":"test", "title":"test", "duration":None, "selection":"user",
                 "source_url": f"http://127.0.0.1:{server.server_port}/{source.name}"}
        def search_with_session(record,logger,**_):
            jar=YoutubeDLCookieJar()
            jar.set_cookie(http.cookiejar.Cookie(0,'onda_test_session','search-session',None,False,
                '127.0.0.1',False,False,'/',True,False,None,True,None,None,{},False))
            logger.youtube_cookiejar=jar
            return match
        try:
            output = io.StringIO()
            config = {"url": spotify_anchor["source_url"] if spotify_anchor else self.record["source_url"], "folder": str(self.root / "out"), "mode": "mp3", "ffmpeg": os.environ["ONDA_FFMPEG"], "_cleanup_work": True}
            def fetch(url):
                return spotify_anchor if spotify_anchor and url == spotify_anchor["source_url"] else self.record
            def download_with_leftover(url,options,configure,saved):
                result=download_with_recovery(url,options,configure,saved)
                # yt-dlp may leave thumbnails/cache even when all media succeeded.
                (Path(options["paths"]["home"])/"unused-thumbnail.webp").write_bytes(b'temporary')
                return result
            with patch("metadata.MetadataClient.fetch", side_effect=fetch), patch("matching.find_youtube", side_effect=search_with_session), patch("tagging.fetch_cover", return_value=self.cover), patch("engine.download_with_recovery",side_effect=download_with_leftover), contextlib.redirect_stdout(output):
                code = run_worker(config)
            self.assertEqual(code, 0, output.getvalue())
            events = [json.loads(line) for line in output.getvalue().splitlines()]
            self.assertEqual(events[-1]["type"], "done")
            path = Path(events[-1]["files"][0])
            from mutagen.id3 import ID3
            self.assertEqual(str(ID3(path)["TALB"]), self.record["album"])
            self.assertTrue(path.with_suffix(".mp3.metadata.json").exists())
            self.assertFalse(list((self.root/"out").rglob(".onda-work")))
            if spotify_anchor:
                provenance = json.loads(path.with_suffix(".mp3.metadata.json").read_text(encoding="utf-8"))
                self.assertEqual(provenance["catalog"]["requested_source_url"], spotify_anchor["source_url"])
                self.assertEqual(provenance["catalog"]["platform"], "Spotify")
                self.assertEqual(provenance["catalog"]["metadata_sources"]["album"]["platform"],"Deezer")
                self.assertEqual(provenance["catalog"]["metadata_sources"]["title"]["platform"],"Spotify")
                self.assertEqual(provenance["catalog"]["catalog_match"]["selection"], "automatic")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_deezer_pipeline_keeps_catalog_folder_and_tags(self):
        self.record.update(platform="Deezer", id="123", source_url="https://www.deezer.com/track/123")
        self.test_streaming_pipeline_tags_before_success()
        self.assertTrue((self.root / "out" / "deezer-123").is_dir())

    def test_spotify_without_credentials_resolves_catalog_and_tags(self):
        from unittest.mock import Mock
        from test_spotify_optional import public_html, SPOTIFY, TRACK_ID
        anchor = base_record("Spotify", TRACK_ID, SPOTIFY, "Spotify oEmbed")
        anchor["title"] = self.record["title"]
        self.record.update(platform="Deezer", id="123", source_url="https://www.deezer.com/track/123", duration_ms=180000)
        response = Mock(is_redirect=False, text=public_html())
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch("metadata.MetadataClient.request", return_value=response), patch("metadata.MetadataClient.search", return_value=[self.record]):
            self.test_streaming_pipeline_tags_before_success(spotify_anchor=anchor)


if __name__ == "__main__":
    unittest.main()
