import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from metadata import MetadataClient, MetadataError, deezer_record
from music_search import (
    parse_query,
    accepts,
    search_music,
    clear_cache,
    SearchCancelled,
)
from edition_evidence import date_parts, edition_conflicts
from record_identity import catalog_identity
from catalog_match import rank_catalog
from matching import (
    score_candidate,
    select_candidate,
    revalidate_match,
    NoCompatibleMatch,
)
from search_choices import ChoiceStore

TRACK = dict(
    title='Song',
    artists=['Artist'],
    album='Album',
    duration_ms=200000,
    release_date='2022-01-07',
    isrc='USABC2200001',
    source_url='https://www.deezer.com/track/1',
)
VIDEO = dict(
    id='abcdefghijk', title='Artist Song', channel='Artist - Topic', duration=200
)


class EditionTests(unittest.TestCase):
    def test_remaster_year_conflict_survives_same_isrc(self):
        a = dict(TRACK, title='Song - Remastered 2011')
        b = dict(TRACK, title='Song - 2022 Remaster')
        self.assertTrue(edition_conflicts(a, b))
        self.assertIsNone(catalog_identity(a, b))
        self.assertEqual(rank_catalog(a, [b]), [])
        self.assertIsNone(score_candidate(a, dict(VIDEO, title=b['title'])))
        self.assertIsNone(
            score_candidate(
                b, dict(VIDEO, title=a['title'], track=b['title'], artist='Artist')
            )
        )

    def test_remixer_and_live_context(self):
        for left, right in [
            ('Song (Alice Remix)', 'Song (Bob Remix)'),
            ('Song (Live at Rome 1990)', 'Song (Live at London 1991)'),
            ('Song (Radio Edit)', 'Song (Single Edit)'),
        ]:
            with self.subTest(left=left):
                self.assertTrue(
                    edition_conflicts(dict(TRACK, title=left), dict(TRACK, title=right))
                )
                self.assertEqual(
                    rank_catalog(dict(TRACK, title=left), [dict(TRACK, title=right)]),
                    [],
                )
        self.assertEqual(
            edition_conflicts(
                dict(title='Song (Alice Remix)'),
                dict(title='Artist - Song (Alice Remix)'),
            ),
            [],
        )
        self.assertEqual(
            edition_conflicts(
                dict(title='Song - Alice Remix'),
                dict(title='Artist - Song - Alice Remix'),
            ),
            [],
        )

    def test_full_timestamp_release_is_same_day_but_partial_is_not_proof(self):
        a = dict(TRACK, title='Song - Remastered 2022')
        self.assertEqual(
            catalog_identity(a, dict(TRACK, release_date='2022-01-07T00:00:00Z')),
            'isrc',
        )
        for date in ('2022', '2022-01', '2022-02-31', '2022-99-01'):
            self.assertIsNone(catalog_identity(a, dict(TRACK, release_date=date)))
        self.assertEqual(date_parts('2022-02-31'), ())

    def test_structured_version_is_not_lost(self):
        row = deezer_record(
            dict(
                id=1,
                title='Song',
                title_version='Live',
                artist={'name': 'Artist'},
                duration=200,
            ),
            '1',
            TRACK['source_url'],
        )
        self.assertEqual(rank_catalog(TRACK, [row]), [])
        self.assertIsNone(score_candidate(TRACK, dict(VIDEO, title_version='Live')))
        self.assertIsNotNone(
            score_candidate(
                dict(TRACK, title='Song Live'), dict(VIDEO, title_version='Live')
            )
        )

    def test_invalid_durations_do_not_match(self):
        for value in (float('nan'), float('inf'), True, -1, '200000'):
            self.assertIsNone(catalog_identity(dict(TRACK, duration_ms=value), TRACK))
            self.assertIsNone(score_candidate(dict(TRACK, duration_ms=value), VIDEO))

    def test_literal_title_word_does_not_hide_an_added_live_version(self):
        from matching import version_signature

        self.assertEqual(version_signature('Live Forever'), set())
        self.assertEqual(version_signature('Live Forever (Live)'), {'live'})
        self.assertIsNone(
            score_candidate(
                dict(TRACK, title='Live Forever'),
                dict(VIDEO, title='Artist - Live Forever (Live)'),
            )
        )

    def test_clean_conflict_is_symmetric(self):
        from search_evidence import explicit_conflict

        clean = dict(TRACK, title='Song (Clean)', explicit=None)
        explicit = dict(TRACK, explicit=True)
        self.assertTrue(explicit_conflict(clean, explicit))
        self.assertTrue(explicit_conflict(explicit, clean))

    def test_automatic_uses_best_validated_candidate(self):
        self.assertEqual(
            select_candidate(
                TRACK, [VIDEO, dict(VIDEO, id='other123456')], prefer_best=True
            )['id'],
            VIDEO['id'],
        )

    def test_duplicate_upload_id_does_not_create_ambiguity(self):
        self.assertEqual(
            select_candidate(TRACK, [VIDEO, dict(VIDEO)])['id'], VIDEO['id']
        )

    def test_revalidate_before_download(self):
        selected = select_candidate(TRACK, [VIDEO])
        self.assertEqual(revalidate_match(TRACK, selected, VIDEO), VIDEO)
        for changed in (
            dict(VIDEO, id='other123456'),
            dict(VIDEO, duration=300),
            dict(VIDEO, title='Artist Song Live'),
        ):
            with self.assertRaises(NoCompatibleMatch):
                revalidate_match(TRACK, selected, changed)

    def test_real_colette_official_visual_is_presentation_not_another_version(self):
        record = dict(
            TRACK, title='Colette', artists=['Piero Piccioni'], duration_ms=105000
        )
        video = dict(
            VIDEO,
            title='Piero Piccioni - Colette (Official Visual)',
            channel='Piero Piccioni',
            duration=106,
        )
        self.assertGreater(score_candidate(record, video), 0.94)
        self.assertIsNone(
            score_candidate(
                record, dict(video, title='Piero Piccioni - Colette Other Song')
            )
        )

    def test_manual_selection_is_revalidated_against_selected_version(self):
        current = dict(VIDEO, title='Artist Song Live', duration=300)
        selected = dict(current, selection='user')
        self.assertEqual(revalidate_match(TRACK, selected, current), current)
        with self.assertRaises(NoCompatibleMatch):
            revalidate_match(TRACK, selected, dict(current, duration=500))


class SearchTests(unittest.TestCase):
    def setUp(self):
        clear_cache()
        self.client = MetadataClient()
        self.addCleanup(self.client.close)

    def test_filters_and_exact_phrases(self):
        query = parse_query(
            '"Song" artista:"Artist" album:"Album" ano:2021-2023 duracao:3:00-4:00 exata:sim'
        )
        self.assertTrue(accepts(TRACK, query))
        for fields in (
            {'title': 'Other Song'},
            {'artists': ['Other']},
            {'duration_ms': 300000},
            {'release_date': '1999'},
        ):
            self.assertFalse(accepts(dict(TRACK, **fields), query))

    def test_invalid_filters_have_actionable_errors(self):
        for query in (
            'Song ano:tomorrow',
            'Song duracao:3:99',
            'Song exata:maybe',
            '"Song',
            'ano:2022',
        ):
            with self.subTest(query=query), self.assertRaises(MetadataError):
                parse_query(query)
        self.assertEqual(parse_query('7')['query'], '7')

    def test_version_filter_preserves_the_requested_edition(self):
        query = parse_query('Song versao:"Remastered 2022"')
        self.assertTrue(accepts(dict(TRACK, title='Song (Remastered 2022)'), query))
        self.assertFalse(accepts(dict(TRACK, title='Song (Remastered 2011)'), query))
        self.assertFalse(accepts(dict(TRACK, title='Song (Remastered)'), query))

    def test_pagination_uses_fixed_endpoint_and_stops_on_duplicate_page(self):
        page = {
            'data': [dict(id=1, title='Song', artist={'name': 'Artist'}, duration=200)],
            'next': 'https://untrusted.test/ignored',
        }
        with patch.object(self.client, 'get_json', return_value=page) as request:
            self.assertEqual(len(self.client.search('Song', limit=3)), 1)
        self.assertEqual(request.call_count, 2)
        self.assertTrue(
            all(
                call.args[0] == 'https://api.deezer.com/search'
                for call in request.call_args_list
            )
        )

    def test_http_retries_only_transient_failures(self):
        retry = Mock(status_code=503, headers={})
        good = Mock(status_code=200)
        with patch.object(
            self.client.session, 'request', side_effect=[retry, good]
        ) as request:
            self.assertIs(self.client.request('https://example.test'), good)
            self.assertEqual(request.call_count, 2)
            retry.close.assert_called_once()
        denied = Mock(status_code=401)
        with patch.object(
            self.client.session, 'request', return_value=denied
        ) as request:
            with self.assertRaises(MetadataError):
                self.client.request('https://example.test')
            request.assert_called_once()

    def test_parallel_providers_partial_failure_and_stable_results(self):
        barrier = threading.Barrier(2)

        def search(worker, query, provider, **kwargs):
            barrier.wait(timeout=3)
            if provider == 'Deezer':
                raise MetadataError('Falha temporária')
            return [dict(TRACK, platform='Apple / iTunes')]

        with patch.object(MetadataClient, 'search', search):
            result = search_music(self.client, 'Song', 'Todos')
        self.assertEqual(len(result['tracks']), 1)
        self.assertIn('Deezer', result['warnings'][0])

    def test_cache_is_defensive_refreshable_and_never_caches_failure(self):
        with patch.object(MetadataClient, 'search', return_value=[TRACK]) as search:
            result = search_music(self.client, 'Song')
            result['tracks'][0]['artists'].append('Mutated')
            second = search_music(self.client, 'Song')
            self.assertEqual(second['tracks'][0]['artists'], ['Artist'])
            self.assertEqual(search.call_count, 1)
            search_music(self.client, 'Song', refresh=True)
            self.assertEqual(search.call_count, 2)

    def test_fallback_is_bounded_and_reports_all_failures(self):
        with patch.object(
            MetadataClient, 'search', side_effect=MetadataError('offline')
        ) as search:
            with self.assertRaises(MetadataError):
                search_music(self.client, 'Song')
            self.assertEqual(search.call_count, 2)

    def test_cancel_prevents_requests(self):
        with patch.object(MetadataClient, 'search') as search:
            with self.assertRaises(SearchCancelled):
                search_music(self.client, 'Song', cancelled=lambda: True)
            search.assert_not_called()

    def test_cancel_after_request_prevents_results_and_cache(self):
        event = threading.Event()

        def search(*args, **kwargs):
            event.set()
            return [TRACK]

        with patch.object(MetadataClient, 'search', side_effect=search):
            with self.assertRaises(SearchCancelled):
                search_music(self.client, 'Song', cancelled=event.is_set)
        with patch.object(MetadataClient, 'search', return_value=[TRACK]) as search:
            search_music(self.client, 'Song')
            search.assert_called_once()

    def test_link_resolution_uses_existing_credentials_and_choice(self):
        with patch.object(self.client, 'resolve', return_value=TRACK) as resolve:
            result = search_music(self.client, TRACK['source_url'], automatic=True)
        self.assertEqual(result['tracks'], [TRACK])
        self.assertTrue(resolve.call_args.kwargs['automatic'])

    def test_grouping_preserves_different_albums_and_editions(self):
        records = [
            TRACK,
            dict(TRACK, source_url='second'),
            dict(TRACK, album='Compilation', source_url='third'),
            dict(TRACK, title='Song Live', source_url='fourth'),
        ]
        with patch.object(MetadataClient, 'search', return_value=records):
            rows = search_music(self.client, 'Song')['tracks']
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['equivalent_sources'][0]['source_url'], 'second')

    def test_typo_is_suggested_not_silently_rewritten(self):
        with patch.object(
            MetadataClient, 'search', return_value=[dict(TRACK, title='Sunshine')]
        ) as search:
            result = search_music(self.client, 'Sunshne')
        self.assertTrue(result['suggestions'])
        self.assertEqual(search.call_args.args[0], 'Sunshne')


class ChoiceTests(unittest.TestCase):
    def test_remember_reject_undo_and_expiry(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            store = ChoiceStore(Path(folder) / 'choices.sqlite')
            store.set(TRACK, 'abcdefghijk', True)
            self.assertTrue(store.get(TRACK)['abcdefghijk'])
            store.set(TRACK, 'abcdefghijk', False)
            self.assertFalse(store.get(TRACK)['abcdefghijk'])
            with patch('search_choices.time.time', return_value=99999999999):
                self.assertEqual(store.get(TRACK), {})
            store.clear(TRACK)
            self.assertEqual(store.get(TRACK), {})


if __name__ == '__main__':
    unittest.main()
