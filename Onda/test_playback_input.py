"""Input routing and metadata regressions shared by PC and Android."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from playback_input import collection_url, resolve_input


class PlaybackInputTests(unittest.TestCase):
    def test_collection_links_include_localized_catalogs_and_spotify_uri(self):
        urls = [
            'https://open.spotify.com/intl-pt/playlist/' + 'a' * 22,
            'https://www.deezer.com/br/album/123',
            'https://music.apple.com/br/album/song/123',
            'https://www.youtube.com/watch?v=abcdefghijk&list=PL123',
        ]
        for url in urls:
            self.assertEqual(collection_url(url), url)
        self.assertEqual(
            collection_url('spotify:playlist:' + 'a' * 22),
            'https://open.spotify.com/playlist/' + 'a' * 22,
        )
        self.assertFalse(collection_url('https://example.com/playlist/1'))

    def test_catalog_track_links_bypass_the_direct_download_restriction(self):
        for url in [
            'https://open.spotify.com/track/' + 'a' * 22,
            'https://music.apple.com/us/album/song/1?i=2',
            'https://www.deezer.com/track/1',
        ]:
            with patch(
                'music_search.search_music',
                return_value={'tracks': [{'title': 'Selected'}]},
            ) as search:
                result = resolve_input(url, Mock())
            self.assertFalse(result['is_collection'])
            self.assertEqual(search.call_args.args[1], url)

    def test_collection_uses_collection_loader_and_fallback_artwork(self):
        url = 'https://open.spotify.com/playlist/' + 'a' * 22
        with (
            patch(
                'playlist_import.load_playlist',
                return_value={
                    'tracks': [{'title': 'Song'}],
                    'cover_url': 'https://example.com/cover.jpg',
                },
            ) as load,
            patch('music_search.search_music') as search,
        ):
            result = resolve_input(url, Mock(), {'playlist_limit': 400})
        self.assertTrue(result['is_collection'])
        self.assertEqual(
            result['tracks'][0]['cover_url'], 'https://example.com/cover.jpg'
        )
        self.assertEqual(load.call_args.kwargs['limit'], 400)
        search.assert_not_called()

    def test_direct_url_keeps_source_and_does_not_search_catalog(self):
        url = 'https://www.youtube.com/watch?v=abcdefghijk'
        with patch('music_search.search_music') as search:
            result = resolve_input(url, Mock())
        self.assertEqual(result['tracks'][0]['source_url'], url)
        self.assertTrue(result['tracks'][0]['_jukebox_direct'])
        search.assert_not_called()

    def test_google_redirect_is_resolved_before_catalog_routing(self):
        url = (
            'https://www.google.com/url?q=https%3A%2F%2Fopen.spotify.com%2Ftrack%2F'
            + 'a' * 22
        )
        with patch('music_search.search_music', return_value={'tracks': []}) as search:
            resolve_input(url, Mock())
        self.assertEqual(
            search.call_args.args[1], 'https://open.spotify.com/track/' + 'a' * 22
        )

    def test_short_link_resolves_to_collection_before_loading(self):
        client = Mock()
        client.request.return_value.__enter__ = Mock(
            return_value=SimpleNamespace(
                is_redirect=True,
                headers={'Location': 'https://open.spotify.com/playlist/' + 'a' * 22},
            )
        )
        client.request.return_value.__exit__ = Mock(return_value=False)
        with patch(
            'playlist_import.load_playlist', return_value={'tracks': []}
        ) as load:
            result = resolve_input('https://spotify.link/short', client)
        self.assertTrue(result['is_collection'])
        load.assert_called_once()

    def test_deezer_short_playlist_does_not_go_through_track_only_resolver(self):
        client = Mock()
        client.request.return_value.__enter__ = Mock(
            return_value=SimpleNamespace(
                is_redirect=True,
                headers={'Location': 'https://www.deezer.com/br/playlist/123'},
            )
        )
        client.request.return_value.__exit__ = Mock(return_value=False)
        with patch(
            'playlist_import.load_playlist', return_value={'tracks': []}
        ) as load:
            result = resolve_input('https://link.deezer.com/short', client)
        self.assertTrue(result['is_collection'])
        self.assertEqual(
            load.call_args.args[0], 'https://www.deezer.com/br/playlist/123'
        )

    def test_short_link_rejects_redirect_outside_its_catalog(self):
        client = Mock()
        client.request.return_value.__enter__ = Mock(
            return_value=SimpleNamespace(
                is_redirect=True,
                headers={'Location': 'https://example.com/not-spotify'},
            )
        )
        client.request.return_value.__exit__ = Mock(return_value=False)
        with self.assertRaises(ValueError):
            resolve_input('https://spotify.link/short', client)

    def test_android_adapter_uses_same_resolver_for_both_search_actions(self):
        import importlib.util, json

        path = (
            Path(__file__).resolve().parent.parent
            / 'Android/app/src/main/python/mobile_backend.py'
        )
        spec = importlib.util.spec_from_file_location('input_test_backend', path)
        backend = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend)
        callback = SimpleNamespace(onEvent=lambda _: None)
        for action in ('effects_search', 'playback_input'):
            with (
                patch.object(backend, 'client', return_value=Mock()),
                patch.object(backend, 'account', return_value=None),
                patch(
                    'playback_input.resolve_input',
                    return_value={'tracks': [{'title': 'Song'}], 'is_collection': True},
                ) as resolve,
            ):
                result = json.loads(
                    backend.run(
                        'input-test',
                        action,
                        json.dumps({'query': 'collection'}),
                        callback,
                    )
                )
            self.assertTrue(result['is_collection'])
            self.assertEqual(resolve.call_args.args[0], 'collection')

    def test_cancelled_input_does_no_network(self):
        client = Mock()
        with self.assertRaises(InterruptedError):
            resolve_input('Song', client, cancelled=lambda: True)
        self.assertEqual(client.mock_calls, [])

    def test_url_with_credentials_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_input(
                'https://user:pass@open.spotify.com/track/' + 'a' * 22, Mock()
            )

    def test_metadata_completion_preserves_recording_identity_and_selection(self):
        from catalog_details import complete_record, _cache

        _cache.clear()
        client = Mock()
        client.fetch.return_value = {
            'title': 'Wrong title',
            'artists': ['Wrong artist'],
            'cover_url': 'https://example.com/cover.jpg',
            'release_date': '1998-07-20',
            'album': 'Album',
        }
        record = {
            'source_url': 'https://www.deezer.com/track/991',
            'title': 'Chosen',
            'artists': ['Artist'],
            'checked': True,
        }
        result = complete_record(record, client)
        self.assertEqual(result['title'], 'Chosen')
        self.assertEqual(result['artists'], ['Artist'])
        self.assertTrue(result['checked'])
        self.assertEqual(result['release_date'], '1998-07-20')
        self.assertNotIn('release_date', record)
        self.assertEqual(
            complete_record(record, client)['cover_url'],
            'https://example.com/cover.jpg',
        )
        self.assertEqual(client.fetch.call_count, 1)

    def test_metadata_lookup_failure_preserves_fallback_cover(self):
        from catalog_details import complete_record, _cache

        _cache.clear()
        client = Mock()
        client.fetch.side_effect = OSError('offline')
        result = complete_record(
            {
                'source_url': 'https://www.deezer.com/track/992',
                'title': 'Song',
                'cover_url': 'fallback',
            },
            client,
        )
        self.assertEqual(result['cover_url'], 'fallback')
        self.assertNotIn('release_date', result)
        self.assertTrue(result['_details_checked'])

    def test_direct_audio_uses_extractor_metadata_without_catalog_matching(self):
        import jukebox

        with tempfile.TemporaryDirectory() as folder:

            def download(url, options, configure, saved):
                processors = []
                configure(
                    SimpleNamespace(
                        add_post_processor=lambda processor, **_: processors.append(
                            processor
                        )
                    )
                )
                path = Path(options['outtmpl'].replace('%(ext)s', 'wav'))
                path.write_bytes(b'audio')
                processors[0]._progress_hooks = []
                processors[0].run(
                    {
                        'filepath': str(path),
                        'title': 'Actual song',
                        'artist': 'Artist',
                        'album': 'Album',
                        'thumbnail': 'https://example.com/cover.jpg',
                        'duration': 200,
                    }
                )
                return 0

            with (
                patch('jukebox.cache_root', return_value=Path(folder)),
                patch('engine.download_with_recovery', side_effect=download),
                patch('matching.resolve_youtube') as match,
            ):
                result = jukebox.fetch_audio(
                    {},
                    {
                        'source_url': 'https://example.com/song.wav',
                        'title': 'URL placeholder',
                    },
                    analyze=False,
                )
            match.assert_not_called()
            self.assertTrue(Path(result['source']).is_file())
            self.assertEqual(result['record']['title'], 'Actual song')
            self.assertEqual(result['record']['artists'], ['Artist'])
            self.assertEqual(result['record']['duration_ms'], 200000)


if __name__ == '__main__':
    unittest.main()
