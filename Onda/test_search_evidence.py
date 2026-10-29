import unittest
from matching import words, version_signature, score_candidate
from record_identity import catalog_identity
from catalog_match import rank_catalog
from search_evidence import album_core, explicit_conflict


class SearchEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.record = dict(
            title="Don't Stop",
            artists=["Artist"],
            duration_ms=200000,
            album="Album",
            track_number=2,
            release_date="2000-01-01",
        )
        self.video = dict(
            id="abcdefghijk",
            title="Artist Don’t Stop",
            channel="Artist - Topic",
            duration=200,
        )

    def test_punctuation_width_and_accents(self):
        self.assertEqual(words("Don't"), words("Don’t"))
        self.assertEqual(words("Ｄｏｎｔ"), words("Dont"))
        self.assertEqual(words("Canción"), words("Cancion"))
        self.assertIsNotNone(score_candidate(self.record, self.video))

    def test_guest_credit_can_move_between_title_and_artists(self):
        other = dict(
            self.record,
            title="Don't Stop (feat. Guest)",
            artists=["Artist", "Guest"],
            source_url="other",
        )
        self.assertTrue(rank_catalog(self.record, [other]))

    def test_version_synonyms_preserve_recording_type(self):
        self.assertEqual(
            version_signature("Song Remastered"), version_signature("Song Remaster")
        )
        self.assertEqual(
            version_signature("Song ao vivo"), version_signature("Song Live")
        )
        for suffix in ("Remix", "Live", "Instrumental", "Slowed", "Re-recorded"):
            self.assertIsNone(
                score_candidate(
                    self.record, dict(self.video, title="Artist Don't Stop " + suffix)
                )
            )

    def test_localized_and_spaced_version_labels(self):
        for left, right in (
            ("Acústico", "Acoustic"),
            ("Remasterizado", "Remastered"),
            ("Sped Up", "Speed Up"),
            ("Slowed Down", "Slowed"),
            ("A Cappella", "Acappella"),
        ):
            with self.subTest(left=left, right=right):
                self.assertEqual(version_signature(left), version_signature(right))
                self.assertIsNotNone(
                    score_candidate(
                        dict(self.record, title="Don't Stop " + left),
                        dict(self.video, title="Artist Don't Stop " + right),
                    )
                )
                self.assertIsNone(
                    score_candidate(
                        self.record, dict(self.video, title="Artist Don't Stop " + left)
                    )
                )

    def test_equivalent_version_names_match_but_guest_credit_cannot_hide_remix(self):
        self.assertIsNotNone(
            score_candidate(
                dict(self.record, title="Don't Stop Remastered"),
                dict(self.video, title="Artist Don't Stop Remaster"),
            )
        )
        self.assertIsNotNone(
            score_candidate(
                dict(self.record, title="Don't Stop ao vivo"),
                dict(self.video, title="Artist Don't Stop Live"),
            )
        )
        self.assertIsNone(
            score_candidate(
                self.record,
                dict(self.video, title="Artist Don't Stop feat. Guest Remix"),
            )
        )

    def test_localized_artist_requires_same_isrc_title_and_duration(self):
        anchor = dict(self.record, isrc="USABC0000001", artists=["高​​中正義"])
        other = dict(
            self.record,
            isrc="USABC0000001",
            artists=["Masayoshi Takanaka"],
            source_url="other",
        )
        self.assertEqual(catalog_identity(anchor, other), "isrc")
        self.assertTrue(rank_catalog(anchor, [other]))
        for fields in (
            {"isrc": None},
            {"isrc": "USABC0000002"},
            {"title": "Another song"},
            {"duration_ms": 300000},
        ):
            self.assertIsNone(catalog_identity(anchor, dict(other, **fields)))

    def test_combined_artist_credit_and_nonadjacent_version_words(self):
        other = dict(self.record, source_url="other")
        self.assertTrue(
            rank_catalog(dict(self.record, artists=["Artist feat. Guest"]), [other])
        )
        self.assertEqual(version_signature("New love recording"), set())
        self.assertFalse(
            explicit_conflict(
                dict(self.record, title="Clean", explicit=True),
                dict(self.video, title="Artist Clean"),
            )
        )

    def test_explicit_and_clean_conflicts(self):
        self.assertTrue(
            explicit_conflict(
                dict(self.record, explicit=True),
                dict(self.video, title="Don't Stop Clean"),
            )
        )
        self.assertIsNone(
            score_candidate(
                dict(self.record, explicit=False), dict(self.video, explicit=True)
            )
        )
        self.assertIsNotNone(
            score_candidate(dict(self.record, explicit=True), self.video)
        )

    def test_album_editions_only_affect_ranking_not_track_identity(self):
        self.assertEqual(album_core("Album (Deluxe Edition)"), album_core("Album"))
        self.assertNotEqual(album_core("Album (Live)"), album_core("Album"))
        other = dict(
            self.record, title="Translated title", album="Album (Deluxe Edition)"
        )
        self.assertIsNone(catalog_identity(self.record, other))
        self.assertEqual(
            catalog_identity(
                dict(self.record, isrc="USABC0000001"), dict(other, isrc="USABC0000001")
            ),
            "isrc",
        )

    def test_release_year_prefers_original_but_accepts_reissue_with_same_title(self):
        original = dict(self.record, source_url="original")
        reissue = dict(original, release_date="2020-01-01", source_url="reissue")
        self.assertEqual(
            [x["source_url"] for x in rank_catalog(self.record, [reissue, original])],
            ["original", "reissue"],
        )
        self.assertIsNone(
            catalog_identity(self.record, dict(reissue, title="Translated"))
        )

    def test_structured_topic_music_fields_do_not_override_untrusted_uploads(self):
        enriched = dict(
            self.video,
            title="Unhelpful localized upload title",
            track="Don't Stop",
            artist="Artist",
        )
        self.assertIsNotNone(score_candidate(self.record, enriched))
        self.assertIsNone(
            score_candidate(self.record, dict(enriched, channel="Unknown uploader"))
        )
        self.assertIsNone(score_candidate(self.record, dict(enriched, duration=400)))
        self.assertIsNone(
            score_candidate(
                self.record, dict(enriched, title="Artist Don't Stop Remix")
            )
        )


if __name__ == "__main__":
    unittest.main()
