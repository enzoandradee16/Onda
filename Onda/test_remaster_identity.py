import unittest
from unittest.mock import Mock
from record_identity import catalog_identity
from catalog_aliases import alternate_records
from catalog_match import rank_catalog, automatic_catalog


class RemasterIdentityTests(unittest.TestCase):
    def setUp(self):
        self.anchor = dict(
            title="Colette - Remastered 2022",
            artists=["Piero Piccioni"],
            album="Addio Alexandra / Remastered 2022",
            release_date="2022-01-07",
            duration_ms=105700,
            isrc="ITC002100939",
            track_number=9,
        )
        self.other = dict(
            self.anchor,
            title="Colette",
            album="Addio Alexandra",
            duration_ms=105000,
            source_url="https://www.deezer.com/track/4204565132",
        )

    def test_same_recording_and_exact_release_allow_omitted_remaster(self):
        self.assertEqual(catalog_identity(self.anchor, self.other), "isrc")

    def test_catalog_ranking_uses_verified_equivalence_in_both_directions(self):
        for anchor, other in (
            (self.anchor, self.other),
            (self.other, dict(self.anchor, source_url="spotify")),
        ):
            with self.subTest(title=anchor['title']):
                ranked = rank_catalog(anchor, [other])
                self.assertEqual(len(ranked), 1)
                self.assertTrue(automatic_catalog(anchor, ranked)['same_isrc'])

    def test_ranking_never_relaxes_unverified_versions(self):
        for changes in (
            dict(isrc=None),
            dict(release_date=None),
            dict(duration_ms=200000),
            dict(title="Colette Live"),
            dict(explicit=True),
        ):
            with self.subTest(changes=changes):
                self.assertEqual(
                    rank_catalog(
                        dict(self.anchor, explicit=False), [dict(self.other, **changes)]
                    ),
                    [],
                )

    def test_missing_or_different_identity_never_relaxes_version(self):
        for changes in [
            dict(isrc=None),
            dict(isrc="ITC002100938"),
            dict(release_date=None),
            dict(release_date="2022"),
            dict(release_date="2020-01-07"),
            dict(duration_ms=200000),
            dict(artists=["Other Artist"]),
        ]:
            with self.subTest(changes=changes):
                self.assertIsNone(
                    catalog_identity(self.anchor, dict(self.other, **changes))
                )

    def test_other_versions_remain_rejected(self):
        for label in ["Remix", "Live", "Rerecorded", "Instrumental"]:
            with self.subTest(label=label):
                self.assertIsNone(
                    catalog_identity(
                        self.anchor, dict(self.other, title="Colette " + label)
                    )
                )

    def test_isrc_lookup_confirms_full_release_before_adding_alias(self):
        client = Mock()
        client.get_json.return_value = dict(
            id=4204565132,
            title="Colette",
            artist=dict(name="Piero Piccioni"),
            duration=105,
            isrc="ITC002100939",
            album=dict(title="Addio Alexandra"),
        )
        client.fetch.return_value = self.other
        result = alternate_records(self.anchor, client)
        self.assertEqual(result[0]["identity_evidence"], "isrc")
        client.fetch.assert_called_once_with(self.other["source_url"])


if __name__ == "__main__":
    unittest.main()
