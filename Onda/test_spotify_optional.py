import json
import contextlib
import io
import unittest
from unittest.mock import Mock

from catalog_match import CatalogChoiceRequired, rank_catalog, automatic_catalog
from metadata import MetadataClient, MetadataError, base_record
from spotify_public import parse_public_track

TRACK_ID = "11dFghVXANMlKmJXsNCbNl"
SPOTIFY = "https://open.spotify.com/track/" + TRACK_ID


def public_html(track_id=TRACK_ID, artists=None):
    entity = {
        "type": "track",
        "id": track_id,
        "title": "Canção Azul",
        "duration": 180000,
        "artists": artists if artists is not None else [{"name": "Artista Exemplo"}],
    }
    data = {
        "props": {
            "pageProps": {
                "state": {
                    "data": {"entity": entity},
                    "settings": {"session": {"accessToken": "never-copy-this-session"}},
                }
            }
        }
    }
    return (
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(data)
        + '</script>'
    )


def catalog(platform="Deezer", track_id="123", album="Álbum Azul"):
    url = (
        f"https://www.deezer.com/track/{track_id}"
        if platform == "Deezer"
        else f"https://music.apple.com/br/song/{track_id}"
    )
    record = base_record(platform, track_id, url, "test")
    record.update(
        title="Canção Azul",
        artists=["Artista Exemplo"],
        duration_ms=180000,
        album=album,
        cover_url="https://example.test/" + track_id + ".jpg",
        track_number=2,
        isrc="BRABC1234567",
    )
    return record


class OptionalSpotifyTests(unittest.TestCase):
    def setUp(self):
        self.client = MetadataClient()
        self.addCleanup(self.client.close)
        self.anchor = base_record("Spotify", TRACK_ID, SPOTIFY, "Spotify oEmbed")
        self.anchor["title"] = "Canção Azul"
        self.candidate = catalog()
        self.client.fetch = Mock(
            side_effect=lambda url: self.anchor if url == SPOTIFY else self.candidate
        )
        response = Mock(is_redirect=False, text=public_html())
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        self.client.request = Mock(return_value=response)
        self.client.search = Mock(return_value=[self.candidate])

    def test_public_identity_never_includes_session(self):
        record = parse_public_track(public_html(), TRACK_ID, SPOTIFY)
        self.assertEqual(record["artists"], ["Artista Exemplo"])
        self.assertEqual(record["duration_ms"], 180000)
        self.assertNotIn("never-copy-this-session", json.dumps(record))
        self.assertIsNone(record["album"])
        for html in (
            public_html("wrong"),
            public_html(artists=[]),
            '<script>{bad}</script>',
        ):
            with self.assertRaises(MetadataError):
                parse_public_track(html, TRACK_ID, SPOTIFY)

    def test_no_credentials_preserves_spotify_and_fills_only_missing_fields(self):
        self.anchor["cover_url"] = "https://example.test/spotify.jpg"
        result = self.client.resolve(SPOTIFY)
        self.assertEqual(result["platform"], "Spotify")
        self.assertEqual(result["requested_source_url"], SPOTIFY)
        self.assertEqual(result["cover_url"], "https://example.test/spotify.jpg")
        self.assertEqual(result["metadata_sources"]["isrc"]["platform"], "Deezer")
        self.assertEqual(result["isrc"], self.candidate["isrc"])
        self.assertEqual(result["catalog_match"]["selection"], "automatic")
        self.assertNotIn("never-copy-this-session", json.dumps(result))

    def test_multiple_releases_require_selection(self):
        other = catalog(track_id="456", album="Coletânea")
        self.client.search = Mock(return_value=[self.candidate, other])
        result = self.client.resolve(SPOTIFY)
        self.assertEqual(result['platform'], 'Spotify')
        self.assertIsNone(result['album'])
        self.client.fetch = Mock(
            side_effect=lambda url: self.anchor if url == SPOTIFY else other
        )
        result = self.client.resolve(SPOTIFY, selected_catalog_url=other["source_url"])
        self.assertEqual(result["album"], "Coletânea")
        self.assertEqual(result["catalog_match"]["selection"], "user")

    def test_metadata_auto_option_selects_best_compatible_catalog(self):
        worse = {**catalog(track_id="456"), "duration_ms": 181000}
        self.client.search = Mock(return_value=[worse, self.candidate])
        chooser = Mock(
            side_effect=AssertionError("Automatic metadata must not open a choice")
        )
        result = self.client.resolve(SPOTIFY, choose=chooser, automatic=True)
        self.assertEqual(
            result['metadata_supplements'][0]['source_url'],
            self.candidate['source_url'],
        )
        chooser.assert_not_called()

    def test_metadata_auto_option_resolves_tie_deterministically(self):
        self.client.search = Mock(
            return_value=[self.candidate, catalog(track_id="456")]
        )
        self.assertEqual(
            self.client.resolve(SPOTIFY, automatic=True)['metadata_supplements'][0][
                'source_url'
            ],
            self.candidate['source_url'],
        )

    def test_metadata_auto_option_does_not_accept_incompatible_version(self):
        self.client.search = Mock(
            return_value=[{**self.candidate, "title": "Canção Azul Remix"}]
        )
        self.assertNotIn(
            "metadata_supplements", self.client.resolve(SPOTIFY, automatic=True)
        )

    def test_explicit_metadata_choice_still_wins_over_automatic(self):
        other = catalog(track_id="456", album="Chosen album")
        self.client.fetch = Mock(
            side_effect=lambda url: self.anchor if url == SPOTIFY else other
        )
        result = self.client.resolve(
            SPOTIFY, selected_catalog_url=other["source_url"], automatic=True
        )
        self.assertEqual(
            result["metadata_supplements"][0]["source_url"], other["source_url"]
        )
        self.assertEqual(result["catalog_match"]["selection"], "user")
        self.client.search.assert_not_called()

    def test_auto_metadata_boolean_survives_preferences_and_transfer(self):
        from preferences import PreferenceStore
        from advanced_options import export_settings, import_settings

        self.assertTrue(PreferenceStore.clean({"auto_metadata": True})["auto_metadata"])
        for invalid in ("true", 1, None):
            self.assertNotIn(
                "auto_metadata", PreferenceStore.clean({"auto_metadata": invalid})
            )
        self.assertTrue(
            import_settings(
                export_settings({"auto_metadata": True}, "android"), "windows"
            )["auto_metadata"]
        )

    def test_title_only_never_selects_automatically(self):
        self.client.request.side_effect = MetadataError("Public page unavailable")
        with self.assertRaises(CatalogChoiceRequired):
            self.client.resolve(SPOTIFY)
        result = self.client.resolve(
            SPOTIFY, choose=lambda anchor, candidates: candidates[0]
        )
        self.assertEqual(result["catalog_match"]["selection"], "user")

    def test_wrong_versions_artists_and_durations_rejected_before_apple_fallback(self):
        wrong_artist = {**self.candidate, "artists": ["Outro Artista"]}
        remix = {**self.candidate, "title": "Canção Azul Remix"}
        wrong_duration = {**self.candidate, "duration_ms": 270000}
        apple = catalog("Apple / iTunes", "456")
        self.client.search.side_effect = [
            [wrong_artist, remix, wrong_duration],
            [apple],
        ]
        self.client.fetch = Mock(
            side_effect=lambda url: self.anchor if url == SPOTIFY else apple
        )
        result = self.client.resolve(SPOTIFY)
        self.assertEqual(result["platform"], "Spotify")
        self.assertEqual(
            result["metadata_supplements"][0]["platform"], "Apple / iTunes"
        )
        self.assertEqual(self.client.search.call_args.args[1], "Apple / iTunes")

    def test_deezer_outage_uses_apple(self):
        self.client.search.side_effect = [MetadataError("HTTP 503"), [self.candidate]]
        self.assertEqual(
            self.client.resolve(SPOTIFY)["metadata_supplements"][0]["source_url"],
            self.candidate["source_url"],
        )

    def test_existing_api_success_keeps_spotify(self):
        self.anchor.update(artists=["Artista Exemplo"], duration_ms=180000)
        result = self.client.resolve(SPOTIFY)
        self.assertEqual(result["platform"], "Spotify")
        self.client.request.assert_not_called()
        self.assertEqual(result['artists'], self.anchor['artists'])

    def test_invalid_or_partial_credentials_do_not_block_public_resolution(self):
        for secret in ("", "invalid-secret"):
            self.client.client_id, self.client.client_secret = "invalid-id", secret

            def fetch(url):
                if url == SPOTIFY:
                    raise MetadataError("Authentication refused")
                return self.candidate

            self.client.fetch = Mock(side_effect=fetch)
            result = self.client.resolve(SPOTIFY)
            self.assertEqual(result["platform"], "Spotify")
            self.assertNotIn("invalid-secret", json.dumps(result))

    def test_forged_choice_and_changed_track_details_are_rejected(self):
        other = catalog(track_id="999")
        # Force a user confirmation without a known artist.
        self.client.request.side_effect = MetadataError("No embed")
        with self.assertRaises(MetadataError):
            self.client.resolve(SPOTIFY, choose=lambda anchor, candidates: other)
        self.client.fetch = Mock(
            return_value={**self.candidate, "title": "Outra música"}
        )
        with self.assertRaises(MetadataError):
            self.client.confirm_catalog(self.anchor, self.candidate)

    def test_saved_catalog_choice_preserves_input_provenance(self):
        result = self.client.resolve(
            SPOTIFY, selected_catalog_url=self.candidate["source_url"]
        )
        self.assertEqual(result["requested_source_url"], SPOTIFY)
        self.assertEqual(result["catalog_match"]["selection"], "user")
        self.client.search.assert_not_called()

    def test_isrc_mismatch_is_rejected_and_equal_isrc_prioritized(self):
        anchor = {**self.candidate, "isrc": "BRABC1234567"}
        wrong = {**self.candidate, "isrc": "USABC7654321"}
        self.assertEqual(rank_catalog(anchor, [wrong]), [])
        ranked = rank_catalog(anchor, [self.candidate])
        self.assertTrue(ranked[0]["same_isrc"])
        self.assertEqual(automatic_catalog(anchor, ranked)["id"], "123")

    def test_no_match_reports_actionable_error_without_requiring_api(self):
        self.client.search.return_value = []
        result = self.client.resolve(SPOTIFY)
        self.assertEqual(result['platform'], 'Spotify')
        self.assertEqual(result['artists'], ['Artista Exemplo'])

    def test_worker_catalog_reply_is_limited_to_offered_candidates(self):
        from engine import ask_catalog

        output = io.StringIO()
        reply = json.dumps({"selected_id": self.candidate["source_url"]})
        with contextlib.redirect_stdout(output):
            chosen = ask_catalog(self.anchor, [self.candidate], io.StringIO(reply))
        self.assertEqual(chosen, self.candidate)
        event = json.loads(output.getvalue())
        self.assertEqual(event["type"], "choose_catalog")
        self.assertEqual(event["candidates"][0]["id"], self.candidate["source_url"])
        for invalid in ('', 'null', '{"selected_id":"https://unrelated.test/"}'):
            with (
                contextlib.redirect_stdout(io.StringIO()),
                self.assertRaises(ValueError),
            ):
                ask_catalog(self.anchor, [self.candidate], io.StringIO(invalid))
