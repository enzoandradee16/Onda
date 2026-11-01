"""Different scripts can be equivalent spellings, not evidence of another recording."""

import json
import threading
import unittest
from unittest.mock import MagicMock, patch
from matching import words, version_signature
from text_search import normalize, equivalent, variants, romanize_kana, contains_terms
from lyrics_service import best_recording, fetch_lyrics


class ScriptNormalizationTests(unittest.TestCase):
    def test_kana_width_script_and_composition_are_equivalent(self):
        for value in ('ガラス', 'がらす', 'ｶﾞﾗｽ', 'カ\u3099ラス'):
            self.assertEqual(words(value), words('がらす'))
        self.assertNotEqual(words('ガラス'), words('カラス'))
        self.assertNotEqual(words('パパ'), words('ババ'))

    def test_non_latin_signs_are_not_destroyed(self):
        self.assertNotEqual(words('й'), words('и'))
        self.assertNotEqual(words('ё'), words('е'))
        self.assertNotEqual(words('माल'), words('मल'))
        self.assertFalse(equivalent('माल', 'मल'))
        self.assertEqual(words('한글'), words('한글'))
        self.assertEqual(words('Άλφα'), words('Α\u0301λφα'))
        self.assertEqual(words('Beyoncé'), words('Beyonce'))
        self.assertEqual(words('İstanbul'), words('Istanbul'))
        self.assertEqual(words('ＦＲＩＤＡＹ'), words('Friday'))
        self.assertTrue(contains_terms('Αλφα', 'Άλφα'))
        self.assertTrue(contains_terms('Елка', 'Ёлка'))
        self.assertTrue(contains_terms('قلب', 'قَلْب'))

    def test_kana_romanization_and_bounded_queries(self):
        self.assertTrue(equivalent('サヨナラ', 'Sayonara'))
        self.assertTrue(equivalent('とうきょう', 'Tōkyō'))
        self.assertTrue(equivalent('トーキョー', 'Tōkyō'))
        self.assertFalse(equivalent('おばさん', 'おばあさん'))
        self.assertEqual(romanize_kana('キット'), 'kitto')
        self.assertEqual(romanize_kana('ミュージック'), 'myuujikku')
        self.assertIsNone(romanize_kana('真夜中のドア'))
        self.assertIn('サヨナラ', variants('ｻﾖﾅﾗ'))
        self.assertEqual(variants('Test'), ['Test'])
        self.assertIn('Αλφα', variants('Άλφα'))
        self.assertLessEqual(len(variants('サヨナラ')), 5)

    def test_localized_version_labels_are_not_original_recordings(self):
        self.assertEqual(version_signature('Song (ライブ)'), {'live'})
        self.assertEqual(version_signature('Song (リミックス)'), {'remix'})
        self.assertEqual(version_signature('Song (라이브)'), {'live'})
        self.assertEqual(version_signature('Song (ремикс)'), {'remix'})


class MultilingualLyricsTests(unittest.TestCase):
    def row(self, title='サヨナラ', artist='Artist', duration=200):
        return dict(
            id=1,
            trackName=title,
            artistName=artist,
            duration=duration,
            plainLyrics='Fixture',
        )

    def test_script_variants_keep_artist_duration_and_version_checks(self):
        row = self.row()
        self.assertIs(best_recording([row], 'さよなら', 'Artist', duration=200), row)
        self.assertIs(best_recording([row], 'Sayonara', 'Artist', duration=200), row)
        self.assertIsNone(best_recording([row], 'Sayonara', 'Other', duration=200))
        self.assertIsNone(best_recording([row], 'Sayonara', 'Artist', duration=250))
        self.assertIsNone(
            best_recording(
                [self.row('サヨナラ (ライブ)')], 'さよなら', 'Artist', duration=200
            )
        )
        self.assertIsNone(
            best_recording([self.row('カラス')], 'ガラス', 'Artist', duration=200)
        )

    def test_kanji_title_can_use_a_catalog_verified_alternate_name(self):
        session = MagicMock()
        calls = []

        def get(url, **kwargs):
            params = kwargs['params']
            calls.append(params)
            payload = (
                [self.row('Alternate title')]
                if params.get('track_name') == 'Alternate title'
                else []
            )
            response = MagicMock()
            response.status_code = 200
            response.iter_content.return_value = [json.dumps(payload).encode()]
            manager = MagicMock()
            manager.__enter__.return_value = response
            return manager

        session.get.side_effect = get
        alias = dict(
            title='Alternate title',
            artists=['Artist'],
            duration_ms=200000,
            identity_evidence='isrc',
        )
        with (
            patch('lyrics_service.read_audio', side_effect=ValueError),
            patch('catalog_aliases.alternate_records', return_value=[alias]) as lookup,
        ):
            result = fetch_lyrics(
                'missing.wav',
                dict(
                    title='真夜中',
                    artists=['Artist'],
                    duration=200,
                    isrc='JPABC1200001',
                ),
                session=session,
            )
        self.assertEqual(result['lines'], [(0, 'Fixture')])
        lookup.assert_called_once()
        self.assertTrue(
            any(call.get('track_name') == 'Alternate title' for call in calls)
        )

    def test_failed_lookup_retries_another_script(self):
        session = MagicMock()
        calls = []

        def get(url, **kwargs):
            calls.append(kwargs['params'])
            response = MagicMock()
            response.status_code = 404 if len(calls) < 3 else 200
            response.iter_content.return_value = [json.dumps([self.row()]).encode()]
            manager = MagicMock()
            manager.__enter__.return_value = response
            return manager

        session.get.side_effect = get
        with patch('lyrics_service.read_audio', side_effect=ValueError):
            result = fetch_lyrics(
                'missing.wav',
                dict(title='さよなら', artists=['Artist'], duration=200),
                session=session,
            )
        self.assertEqual(result['lines'], [(0, 'Fixture')])
        self.assertTrue(
            any(
                (call.get('track_name') or call.get('q')) == 'サヨナラ'
                for call in calls
            )
        )
        self.assertLessEqual(len(calls), 5)


class MultilingualCatalogTests(unittest.TestCase):
    def test_partial_japanese_title_and_script_equivalent_filters_rank_correctly(self):
        from music_search import _rank, parse_query, accepts

        row = dict(
            title='サヨナラの季節',
            artists=['Artist'],
            source_url='https://example.com/1',
        )
        self.assertTrue(accepts(row, parse_query('title:さよなら')))
        self.assertGreater(
            _rank([row], parse_query('さよなら'), 10)[0]['search_score'], 0.8
        )
        row['title'] = 'サヨナラ'
        self.assertEqual(
            _rank([row], parse_query('Sayonara'), 10)[0]['search_score'], 1.0
        )

    def test_empty_local_catalog_can_retry_japanese_region(self):
        from metadata import MetadataClient
        from music_search import search_music, clear_cache

        clear_cache()
        calls = []

        def search(client, text, provider, **kwargs):
            calls.append((text, provider, kwargs.get('country')))
            if provider == 'Apple / iTunes' and kwargs.get('country') == 'jp':
                return [
                    dict(
                        title='真夜中',
                        artists=['Artist'],
                        source_url='https://example.com/track',
                    )
                ]
            return []

        client = MetadataClient()
        try:
            with patch.object(MetadataClient, 'search', search):
                result = search_music(client, '真夜中', 'Deezer')
            self.assertEqual(len(result['tracks']), 1)
            self.assertIn(('真夜中', 'Apple / iTunes', 'jp'), calls)
            self.assertLessEqual(len(calls), 5)
        finally:
            client.close()
