from copy import deepcopy
from unittest.mock import Mock, patch, MagicMock
import unittest
from matching import words, score_candidate, find_youtube, NoCompatibleMatch
from record_identity import catalog_identity
from catalog_aliases import alternate_records
from catalog_match import rank_catalog

ANCHOR = {
    'title': 'トーキョーレギー',
    'artists': ['Masayoshi Takanaka'],
    'album': 'Seychelles',
    'track_number': 2,
    'disc_number': 1,
    'duration_ms': 260333,
}
OTHER = dict(
    ANCHOR,
    title='Tokyo Reggie',
    duration_ms=260000,
    source_url='https://www.deezer.com/track/1548138282',
)
VIDEO = {
    'id': 'abcdefghijk',
    'title': 'Tokyo Reggie',
    'channel': 'Masayoshi Takanaka - Topic',
    'duration': 260,
}


class CatalogTitleFallbackTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("artist_alias_lookup.discover_aliases", return_value=[])
        self.lookup = patcher.start()
        self.addCleanup(patcher.stop)

    def test_unicode_titles_are_preserved_and_unrelated_titles_do_not_match(self):
        self.assertTrue(words('トーキョーレギー'))
        self.assertTrue(words('Москва'))
        self.assertTrue(words('你好'))
        self.assertNotEqual(words('トーキョーレギー'), words('憧れのセーシェル諸島'))
        self.assertIsNotNone(
            score_candidate(ANCHOR, dict(VIDEO, title=ANCHOR['title']))
        )
        self.assertIsNone(
            score_candidate(ANCHOR, dict(VIDEO, title='憧れのセーシェル諸島'))
        )

    def test_album_track_requires_artist_duration_and_disc(self):
        self.assertEqual(catalog_identity(ANCHOR, OTHER), 'album-track')
        for fields in (
            {'artists': ['Other artist']},
            {'album': 'Other album'},
            {'track_number': 3},
            {'disc_number': 2},
            {'duration_ms': 300000},
            {'duration_ms': None},
            {'track_number': None, 'playlist_index': 2},
            {'title': 'Tokyo Reggie Live'},
        ):
            with self.subTest(fields=fields):
                self.assertIsNone(catalog_identity(ANCHOR, dict(OTHER, **fields)))

    def test_matching_isrc_can_bridge_album_names_but_conflicting_isrc_never_does(self):
        anchor = dict(ANCHOR, isrc='JP-KT0-76-00702')
        self.assertEqual(
            catalog_identity(
                anchor, dict(OTHER, isrc='JPKT07600702', album='Localized album')
            ),
            'isrc',
        )
        self.assertIsNone(catalog_identity(anchor, dict(OTHER, isrc='JPKT07600703')))
        self.assertIsNone(
            catalog_identity(
                anchor, dict(OTHER, isrc='JPKT07600702', artists=['Someone else'])
            )
        )

    def test_catalog_ranking_accepts_verified_alternate_but_not_track_number_alone(
        self,
    ):
        self.assertEqual(rank_catalog(ANCHOR, [OTHER])[0]['title'], 'Tokyo Reggie')
        self.assertEqual(rank_catalog(ANCHOR, [dict(OTHER, album='Other album')]), [])
        self.assertEqual(rank_catalog(ANCHOR, [dict(OTHER, track_number=3)]), [])

    def test_album_lookup_fetches_missing_track_number_and_keeps_original_untouched(
        self,
    ):
        original = deepcopy(ANCHOR)
        client = Mock()
        client.search.return_value = [dict(OTHER, track_number=None)]
        client.fetch.return_value = OTHER
        rows = alternate_records(ANCHOR, client)
        self.assertEqual(rows[0]['identity_evidence'], 'album-track')
        client.get_json.assert_not_called()
        client.fetch.assert_called_once_with(OTHER['source_url'])
        self.assertIn('Seychelles', client.search.call_args.args[0])
        self.assertEqual(ANCHOR, original)

    def test_isrc_lookup_is_first_and_avoids_unneeded_searches(self):
        client = Mock()
        client.get_json.return_value = {
            'id': 1548138282,
            'title': 'Tokyo Reggie',
            'artist': {'name': 'Masayoshi Takanaka'},
            'album': {'title': 'Seychelles'},
            'duration': 260,
            'isrc': 'JPKT07600702',
            'track_position': 2,
            'disk_number': 1,
        }
        rows = alternate_records(dict(ANCHOR, isrc='JPKT07600702'), client)
        self.assertEqual(rows[0]['identity_evidence'], 'isrc')
        client.search.assert_not_called()

    def test_lookup_is_bounded_and_missing_metadata_does_not_trigger_network(self):
        client = Mock()
        client.search.return_value = [
            dict(
                OTHER,
                title=f'Alternative {i}',
                source_url=f'https://www.deezer.com/track/{i}',
                track_number=None,
            )
            for i in range(50)
        ]
        client.fetch.return_value = dict(OTHER, track_number=3)
        self.assertEqual(alternate_records(ANCHOR, client), [])
        self.assertEqual(client.fetch.call_count, 6)
        empty = Mock()
        self.assertEqual(alternate_records({'title': 'No metadata'}, empty), [])
        empty.search.assert_not_called()
        empty.get_json.assert_not_called()

    def test_verified_alias_drives_youtube_query_and_records_provenance(self):
        downloader = MagicMock()
        downloader.__enter__.return_value.extract_info.side_effect = [
            {'entries': []},
            {'entries': []},
            {'entries': [VIDEO]},
        ]
        alias = dict(OTHER, identity_evidence='album-track')
        original = deepcopy(ANCHOR)
        with (
            patch('yt_dlp.YoutubeDL', return_value=downloader),
            patch('catalog_aliases.alternate_records', return_value=[alias]),
        ):
            result = find_youtube(ANCHOR, Mock(), prefer_best=True)
        self.assertEqual(result['id'], VIDEO['id'])
        self.assertEqual(result['title_alias']['verified_by'], 'album-track')
        self.assertEqual(result['title_alias']['original_title'], ANCHOR['title'])
        query = downloader.__enter__.return_value.extract_info.call_args.args[0]
        self.assertIn('Tokyo Reggie', query)
        self.assertIn('Seychelles', query)
        self.assertEqual(ANCHOR, original)

    def test_alias_does_not_relax_youtube_duration_or_version_guards(self):
        for candidate in (
            dict(VIDEO, duration=360),
            dict(VIDEO, title='Tokyo Reggie Remix'),
        ):
            downloader = MagicMock()
            downloader.__enter__.return_value.extract_info.side_effect = [
                {'entries': []},
                {'entries': []},
                {'entries': [candidate]},
            ]
            with (
                self.subTest(candidate=candidate),
                patch('yt_dlp.YoutubeDL', return_value=downloader),
                patch(
                    'catalog_aliases.alternate_records',
                    return_value=[dict(OTHER, identity_evidence='album-track')],
                ),
            ):
                with self.assertRaises(NoCompatibleMatch):
                    find_youtube(ANCHOR, Mock(), prefer_best=True)

    def test_successful_direct_match_and_network_errors_do_not_launch_catalog_fallback(
        self,
    ):
        downloader = MagicMock()
        downloader.__enter__.return_value.extract_info.return_value = {
            'entries': [dict(VIDEO, title=ANCHOR['title'])]
        }
        with (
            patch('yt_dlp.YoutubeDL', return_value=downloader),
            patch('catalog_aliases.alternate_records') as aliases,
        ):
            self.assertEqual(find_youtube(ANCHOR, Mock())['id'], VIDEO['id'])
            aliases.assert_not_called()
        downloader.__enter__.return_value.extract_info.side_effect = RuntimeError(
            'YouTube verification required'
        )
        with (
            patch('yt_dlp.YoutubeDL', return_value=downloader),
            patch('catalog_aliases.alternate_records') as aliases,
        ):
            with self.assertRaisesRegex(RuntimeError, 'verification'):
                find_youtube(ANCHOR, Mock())
            aliases.assert_not_called()


if __name__ == '__main__':
    unittest.main()
