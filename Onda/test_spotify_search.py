import os
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
from metadata import MetadataClient, MetadataError
from spotify_search import search_tracks, cached_record


def track(index):
    identity = f'{index:022d}'
    return {
        'id': identity,
        'name': f'Música {index}',
        'type': 'track',
        'artists': [{'name': 'Artista'}],
        'duration_ms': 180000,
        'album': {
            'name': 'Álbum',
            'images': [{'url': 'https://example.test/cover.jpg'}],
            'artists': [{'name': 'Artista'}],
        },
        'external_ids': {'isrc': 'TEST'},
        'preview_url': 'https://example.test/preview.mp3',
    }


class SpotifySearchTests(unittest.TestCase):
    def test_paginates_ten_at_a_time_and_normalizes_results(self):
        calls = []

        def get(path, params):
            calls.append((path, params.copy()))
            rows = [
                track(i)
                for i in range(params['offset'], params['offset'] + params['limit'])
            ]
            return {
                'tracks': {
                    'items': rows,
                    'next': (
                        'https://untrusted.test/ignored'
                        if params['offset'] < 20
                        else None
                    ),
                }
            }

        results = search_tracks('artista', get)
        self.assertEqual(len(results), 25)
        self.assertEqual([params['limit'] for _, params in calls], [10, 10, 5])
        self.assertEqual([params['offset'] for _, params in calls], [0, 10, 20])
        self.assertTrue(all(path == 'search' for path, _ in calls))
        self.assertEqual(results[0]['platform'], 'Spotify')
        self.assertEqual(results[0]['album'], 'Álbum')
        self.assertEqual(results[0]['preview_url'], 'https://example.test/preview.mp3')

    def test_optional_auth_methods_and_missing_auth_message(self):
        account = Mock(connected=True)
        account.get.return_value = {'tracks': {'items': [track(1)], 'next': None}}
        client = MetadataClient()
        try:
            self.assertEqual(
                client.search('music', 'Spotify', account=account)[0]['title'],
                'Música 1',
            )
            with self.assertRaisesRegex(MetadataError, 'Conectar Spotify'):
                client.search('music', 'Spotify')
        finally:
            client.close()
        client = MetadataClient('id', 'secret')
        try:
            with (
                patch.object(client, 'spotify_token', return_value='TOKEN'),
                patch.object(
                    client,
                    'get_json',
                    return_value={'tracks': {'items': [track(2)], 'next': None}},
                ) as get,
            ):
                self.assertEqual(
                    client.search('music', 'Spotify')[0]['title'], 'Música 2'
                )
                self.assertEqual(
                    get.call_args.kwargs['headers'], {'Authorization': 'Bearer TOKEN'}
                )
        finally:
            client.close()

    def test_invalid_results_and_cached_metadata_validation(self):
        with self.assertRaises(MetadataError):
            search_tracks('music', lambda *args: {'tracks': {}})
        self.assertEqual(
            search_tracks(
                'music',
                lambda *args: {
                    'tracks': {
                        'items': [None, {'id': 'bad'}, track(1), track(1)],
                        'next': None,
                    }
                },
            )[0]['title'],
            'Música 1',
        )
        result = search_tracks(
            'music', lambda *args: {'tracks': {'items': [track(1)], 'next': None}}
        )[0]
        result['access_token'] = 'must-not-persist'
        self.assertNotIn('access_token', cached_record(result, result['source_url']))
        with self.assertRaises(MetadataError):
            cached_record(result, 'https://open.spotify.com/track/' + f'{2:022d}')


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'), 'Tk integration')
class SpotifySearchUiTests(unittest.TestCase):
    def test_search_connection_button_queue_and_remember_provider(self):
        from app import App
        from preferences import PreferenceStore

        result = search_tracks(
            'music', lambda *args: {'tracks': {'items': [track(1)], 'next': None}}
        )[0]
        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, {'LOCALAPPDATA': folder}),
        ):
            app = App(show_welcome=False)
            try:
                app.folder.set(folder)
                pane = app.catalog_page
                pane.provider.set('Spotify')
                self.assertTrue(pane.spotify_connect_button.grid_info())
                with patch.object(app.playlist_page, 'connect_spotify') as connect:
                    pane.spotify_connect_button.invoke()
                    connect.assert_called_once()
                pane.query.set('artist music')
                with (
                    patch('catalog_ui.cover_png', return_value=None),
                    patch.object(
                        MetadataClient, 'search', return_value=[result]
                    ) as search,
                ):
                    pane.search()
                    for _ in range(100):
                        app.update()
                        if pane.records:
                            break
                        time.sleep(0.01)
                    self.assertEqual(
                        [
                            {
                                key: value
                                for key, value in row.items()
                                if key != 'search_score'
                            }
                            for row in pane.records
                        ],
                        [result],
                    )
                    self.assertEqual(search.call_args.args, ('artist music', 'Spotify'))
                    self.assertIs(
                        search.call_args.kwargs['account'],
                        app.playlist_page.spotify_account,
                    )
                app.queue_catalog(result, 'mp3', '192 kbps')
                saved = app.library.load_queue()[0]
                self.assertEqual(saved['catalog_record']['album'], 'Álbum')
                self.assertEqual(
                    saved['catalog_record']['source_url'], result['source_url']
                )
                app.remember_settings.set(True)
                app.persist_preferences()
                self.assertEqual(
                    PreferenceStore().load()['catalog_provider'], 'Spotify'
                )
            finally:
                app.destroy()
