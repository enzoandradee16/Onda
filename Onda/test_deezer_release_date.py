import unittest
from unittest.mock import Mock
from metadata import deezer_release_date


class ReleaseDateTests(unittest.TestCase):
    def test_fetch_missing_date(self):
        client = Mock()
        client.fetch.return_value = {"release_date": "2001-03-12"}
        record = {"source_url": "https://www.deezer.com/track/1"}
        self.assertEqual(deezer_release_date(record, client), "2001-03-12")
        client.fetch.assert_called_once_with(record["source_url"])

    def test_skip_existing_and_other_catalogs(self):
        client = Mock()
        self.assertEqual(deezer_release_date({"release_date": "2001"}, client), "2001")
        self.assertIsNone(
            deezer_release_date(
                {"source_url": "https://open.spotify.com/track/0123456789012345678901"},
                client,
            )
        )
        client.fetch.assert_not_called()

    def test_missing_detail_date(self):
        client = Mock()
        client.fetch.return_value = {}
        self.assertIsNone(
            deezer_release_date(
                {"source_url": "https://www.deezer.com/track/1"}, client
            )
        )

    def test_display_date_precision_and_timestamp(self):
        from metadata import display_release_date

        for raw, expected in [
            ("2020-08-28T12:00:00Z", "28/08/2020"),
            ("2020-08-28", "28/08/2020"),
            ("2020-08", "08/2020"),
            ("2020", "2020"),
            (None, ""),
            ("2020-02-31", "2020-02-31"),
        ]:
            with self.subTest(raw=raw):
                self.assertEqual(display_release_date(raw), expected)
