import unittest
from unittest.mock import Mock

from metadata import MetadataClient, MetadataError, deezer_record, is_streaming_link, parse_link


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.client = MetadataClient()
        self.addCleanup(self.client.close)
        self.track = {"id": 123, "title": "Música (Radio Edit)", "artist": {"name": "Artista"},
                      "album": {"title": "Álbum", "cover_xl": "https://example.test/art.jpg"},
                      "duration": 180, "preview": "https://example.test/preview.mp3", "isrc": "BRABC1234567"}

    def test_deezer_links_and_lookalikes(self):
        for url in ("https://deezer.com/track/123", "https://www.deezer.com/br/track/123?foo=1"):
            self.assertTrue(is_streaming_link(url))
            self.assertEqual(parse_link(url), ("deezer", "123", None, "https://www.deezer.com/track/123"))
        for url in ("https://deezer.com/album/123", "https://deezer.com/track/no", "https://deezer.com.evil.test/track/123"):
            with self.assertRaises(MetadataError):
                parse_link(url)
        self.assertFalse(is_streaming_link("https://deezer.com.evil.test/track/123"))

    def test_deezer_record_preserves_version_and_metadata(self):
        data = {**self.track, "contributors": [{"name": "Artista"}, {"name": "Convidada"}],
                "track_position": 2, "disk_number": 1, "release_date": "2021-03-01", "explicit_lyrics": False}
        record = deezer_record(data, "123", "https://www.deezer.com/track/123")
        self.assertEqual(record["title"], "Música (Radio Edit)")
        self.assertEqual(record["artists"], ["Artista", "Convidada"])
        self.assertEqual(record["duration_ms"], 180000)
        self.assertEqual(record["isrc"], data["isrc"])
        self.assertEqual(record["preview_url"], data["preview"])
        self.assertEqual(record["track_number"], 2)
        self.assertIsNone(record["genre"])

    def test_search_skips_invalid_rows_and_keeps_versions_separate(self):
        self.client.get_json = Mock(return_value={"data": [self.track, None, {"id": "oops"}, {**self.track, "id": 456, "title": "Música"}]})
        records = self.client.search("Artista Música")
        self.assertEqual([r["id"] for r in records], ["123", "456"])
        self.assertNotEqual(records[0]["title"], records[1]["title"])
        self.assertEqual(self.client.get_json.call_args.kwargs["params"]["q"], "Artista Música")

    def test_fetch_refreshes_metadata_by_track_id(self):
        self.client.get_json = Mock(return_value=self.track)
        record = self.client.fetch("https://deezer.com/pt/track/123")
        self.assertEqual(record["id"], "123")
        self.client.get_json.assert_called_once_with("https://api.deezer.com/track/123")
        self.client.get_json = Mock(return_value={**self.track, "id": 999})
        with self.assertRaises(MetadataError):
            self.client.fetch("https://deezer.com/track/123")

    def test_search_errors_empty_and_invalid_queries(self):
        self.client.get_json = Mock(return_value={"data": []})
        self.assertEqual(self.client.search("absent"), [])
        for data in ({"error": {"code": 4}}, {"data": "invalid"}):
            self.client.get_json = Mock(return_value=data)
            with self.assertRaises(MetadataError):
                self.client.search("Music")
        for query in (" ", "x", "x" * 301):
            with self.assertRaises(MetadataError):
                self.client.search(query)

    def test_apple_search_uses_song_rows_and_region(self):
        self.client.get_json = Mock(return_value={"results": [{"kind": "album", "collectionId": 5},
            {"kind": "song", "trackId": 456, "trackName": "Song", "artistName": "Artist", "previewUrl": "https://example.test/preview"}]})
        records = self.client.search("Song", "Apple / iTunes", country="pt")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_url"], "https://music.apple.com/pt/song/456")
        self.assertEqual(self.client.get_json.call_args.kwargs["params"]["entity"], "song")

    def test_deezer_short_redirect_rejects_unrelated_hosts(self):
        response = Mock(is_redirect=True, headers={"Location": "https://unrelated.test/track/123"})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        self.client.request = Mock(return_value=response)
        with self.assertRaises(MetadataError):
            self.client.fetch("https://link.deezer.com/s/abcd")
        self.assertEqual(self.client.request.call_count, 1)
