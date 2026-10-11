import json
import unittest
from unittest.mock import Mock, patch

from metadata import MetadataClient, MetadataError, apple_record, apple_artwork, is_streaming_link, parse_link, spotify_record

TRACK = "11dFghVXANMlKmJXsNCbNl"
SPOTIFY = "https://open.spotify.com/track/" + TRACK
APPLE = "https://music.apple.com/br/album/nome/123?i=456"


class LinkTests(unittest.TestCase):
    def test_spotify_variants(self):
        for link in (SPOTIFY + "?si=test", "spotify:track:" + TRACK,
                     "https://open.spotify.com/intl-pt/track/" + TRACK,
                     "https://open.spotify.com/embed/track/" + TRACK):
            self.assertEqual(parse_link(link), ("spotify", TRACK, None, SPOTIFY))

    def test_apple_song_beats_album_id(self):
        self.assertEqual(parse_link(APPLE)[1:3], ("456", "br"))
        self.assertEqual(parse_link("https://music.apple.com/us/song/title/456")[1:3], ("456", "us"))
        self.assertEqual(parse_link("https://itunes.apple.com/pt/album/title/id123?i=456")[1], "456")

    def test_rejects_non_songs_and_bad_links(self):
        for link in ("https://open.spotify.com/album/" + TRACK, "https://music.apple.com/br/album/title/123",
                     "https://open.spotify.com.evil.test/track/" + TRACK, "file:///test",
                     "https://user:pass@open.spotify.com/track/" + TRACK, "https://open.spotify.com:bad/track/x"):
            with self.subTest(link=link), self.assertRaises(MetadataError):
                parse_link(link)
        self.assertFalse(is_streaming_link("https://open.spotify.com.evil.test/track/" + TRACK))


class ProviderTests(unittest.TestCase):
    def test_apple_cover_requests_high_resolution_same_image(self):
        url = "https://is1-ssl.mzstatic.com/image/thumb/album.jpg/100x100bb.jpg"
        self.assertEqual(apple_artwork(url), url.replace("100x100", "1200x1200"))
        data = {"results": [{"trackId": 456, "kind": "song", "trackName": "Song", "artworkUrl100": url}]}
        self.assertEqual(apple_record(data, "456", APPLE)["cover_url"], apple_artwork(url))
        self.assertIsNone(apple_artwork(None))
        self.assertEqual(apple_artwork("https://other.test/100x100bb.jpg"), "https://other.test/100x100bb.jpg")

    def setUp(self):
        self.client = MetadataClient()
        self.addCleanup(self.client.close)

    def test_spotify_public_does_not_invent_artist(self):
        self.client.get_json = Mock(return_value={"title": "Título - com hífen", "thumbnail_url": "https://example.com/cover"})
        result = self.client.fetch(SPOTIFY)
        self.assertEqual(result["title"], "Título - com hífen")
        self.assertEqual(result["artists"], [])
        self.assertIsNone(result["album"])
        self.assertEqual(result["source_url"], SPOTIFY)
        self.assertNotIn("html", result)

    def test_spotify_complete_metadata(self):
        result = spotify_record({"id": TRACK, "name": "Música", "artists": [{"name": "Artista"}],
                                 "album": {"name": "Álbum", "release_date": "2020-01", "images": []},
                                 "duration_ms": 123456, "explicit": False, "external_ids": {"isrc": "BRXXX1234567"}}, TRACK, SPOTIFY)
        self.assertEqual(result["isrc"], "BRXXX1234567")
        self.assertEqual(result["artists"], ["Artista"])
        self.assertFalse(result["explicit"])
        self.assertIsNone(result["cover_url"])

    def test_apple_selects_exact_song_not_album(self):
        data = {"results": [{"collectionId": 123, "collectionName": "Wrong row"},
                            {"trackId": 456, "kind": "song", "trackName": "Canção", "artistName": "Cantora",
                             "trackTimeMillis": 250000, "trackExplicitness": "notExplicit"}]}
        result = apple_record(data, "456", APPLE)
        self.assertEqual(result["title"], "Canção")
        self.assertEqual(result["duration_ms"], 250000)
        self.assertFalse(result["explicit"])
        self.assertIsNone(result["isrc"])
        with self.assertRaises(MetadataError):
            apple_record(data, "999", APPLE)

    def test_apple_uses_link_region(self):
        self.client.get_json = Mock(return_value={"results": [{"trackId": 456, "kind": "song", "trackName": "X"}]})
        self.client.fetch(APPLE)
        self.assertEqual(self.client.get_json.call_args.kwargs["params"], {"id": "456", "country": "br"})

    def test_token_cached_and_credentials_not_exported(self):
        client = MetadataClient("test-client", "test-secret")
        self.addCleanup(client.close)
        client.get_json = Mock(side_effect=[{"access_token": "private-token", "expires_in": 3600},
                                           {"id": TRACK, "name": "Track"}, {"id": TRACK, "name": "Track"}])
        first, second = client.fetch(SPOTIFY), client.fetch(SPOTIFY)
        self.assertEqual(client.get_json.call_count, 3)
        self.assertNotIn("private-token", json.dumps([first, second]))
        self.assertNotIn("test-secret", json.dumps(first))
        self.assertEqual(client.get_json.call_args.kwargs["headers"], {"Authorization": "Bearer private-token"})

    def test_partial_credentials(self):
        self.client.client_id = "id-only"
        with self.assertRaisesRegex(MetadataError, "juntos"):
            self.client.fetch(SPOTIFY)

    def test_http_errors_are_safe(self):
        for status, expected in ((401, "autenticação"), (403, "autenticação"), (404, "HTTP 404"), (429, "30 segundos")):
            response = Mock(status_code=status, headers={"Retry-After": "30"})
            self.client.session.request = Mock(return_value=response)
            with self.subTest(status=status), self.assertRaisesRegex(MetadataError, expected):
                self.client.get_json("https://api.spotify.com/test")
            self.assertFalse(self.client.session.request.call_args.kwargs["allow_redirects"])

    def test_short_link_rejects_untrusted_redirect(self):
        response = Mock(is_redirect=True, headers={"Location": "https://unrelated.example/test"})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        self.client.request = Mock(return_value=response)
        with self.assertRaises(MetadataError):
            self.client.resolve_short_link("https://spotify.link/example")
        self.client.request.assert_called_once()

    def test_empty_and_invalid_api_responses(self):
        with self.assertRaises(MetadataError):
            apple_record({"results": []}, "123", APPLE)
        self.client.get_json = Mock(return_value={})
        with self.assertRaises(MetadataError):
            self.client.fetch(SPOTIFY)


if __name__ == "__main__":
    unittest.main()
