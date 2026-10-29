import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from album_import import spotify_public_album
from playlist_import import load_playlist
from metadata import MetadataError

ALBUM = 'A' * 22


class AlbumTests(unittest.TestCase):
    def test_spotify_api_paginates_and_preserves_edition(self):
        meta = {
            'id': ALBUM,
            'name': 'Original Edition',
            'total_tracks': 3,
            'images': [{'url': 'https://example.com/cover.jpg'}],
        }

        def get(path, params=None):
            if params is None:
                return meta
            offset = params['offset']
            return {
                'items': [
                    {
                        'id': str(offset + 1) * 22,
                        'name': 'Song',
                        'artists': [{'name': 'Artist'}],
                        'track_number': offset + 1,
                        'disc_number': 1,
                    }
                ],
                'next': offset < 2,
            }

        account = SimpleNamespace(connected=True, get=Mock(side_effect=get))
        result = load_playlist('spotify:album:' + ALBUM, Mock(), account=account)
        self.assertEqual(len(result['tracks']), 3)
        self.assertEqual(result['tracks'][2]['album'], 'Original Edition')
        self.assertEqual(result['tracks'][2]['track_number'], 3)
        self.assertEqual(
            [c.args[1]['offset'] for c in account.get.call_args_list[1:]], [0, 1, 2]
        )

    def test_public_album_largest_cover_and_artist_names(self):
        entity = {
            'type': 'album',
            'id': ALBUM,
            'title': 'Edition',
            'trackList': [
                {
                    'uri': 'spotify:track:' + 'B' * 22,
                    'title': 'Song',
                    'subtitle': 'Artist,\ufffdGuest',
                    'duration': 123000,
                }
            ],
            'visualIdentity': {
                'image': [
                    {'url': 'small', 'maxHeight': 64},
                    {'url': 'large', 'maxHeight': 640},
                ]
            },
        }
        html = (
            '<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(
                {'props': {'pageProps': {'state': {'data': {'entity': entity}}}}}
            )
            + '</script>'
        )
        row = spotify_public_album(html, ALBUM, 100)['tracks'][0]
        self.assertEqual(row['artists'], ['Artist', 'Guest'])
        self.assertEqual(row['cover_url'], 'large')
        with self.assertRaises(MetadataError):
            spotify_public_album(html, 'C' * 22, 100)

    def test_deezer_pages_and_album_metadata(self):
        client = Mock()
        client.get_json.side_effect = [
            {'title': 'Album', 'nb_tracks': 2, 'cover_xl': 'cover'},
            {
                'data': [{'id': 1, 'title': 'First', 'artist': {'name': 'Artist'}}],
                'next': True,
            },
            {'data': [{'id': 2, 'title': 'Second', 'artist': {'name': 'Artist'}}]},
        ]
        result = load_playlist('https://www.deezer.com/pt/album/12', client)
        self.assertEqual(
            [row['title'] for row in result['tracks']], ['First', 'Second']
        )
        self.assertTrue(all(row['album'] == 'Album' for row in result['tracks']))
        self.assertEqual(client.get_json.call_args.kwargs['params']['index'], 1)
        with self.assertRaises(MetadataError):
            load_playlist(
                'https://www.deezer.com/album/12', client, cancelled=lambda: True
            )

    def test_apple_region_disc_order_and_excludes_other_album(self):
        client = Mock()

        def song(identity, disc, track, album=12):
            return {
                'kind': 'song',
                'trackId': identity,
                'collectionId': album,
                'trackName': 'Song',
                'artistName': 'Artist',
                'collectionName': 'Album',
                'discNumber': disc,
                'trackNumber': track,
            }

        client.get_json.return_value = {
            'results': [
                {
                    'wrapperType': 'collection',
                    'collectionId': 12,
                    'collectionName': 'Album',
                    'trackCount': 2,
                    'artistName': 'Various Artists',
                },
                song(2, 2, 1),
                song(99, 1, 1, 99),
                song(1, 1, 1),
            ]
        }
        result = load_playlist('https://music.apple.com/br/album/album/12', client)
        self.assertEqual([row['id'] for row in result['tracks']], ['1', '2'])
        self.assertEqual(client.get_json.call_args.kwargs['params']['country'], 'br')
        self.assertEqual(result['folder_title'], 'Various Artists - Album')


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'), 'Tk integration')
class AlbumUiTests(unittest.TestCase):
    def test_queue_preserves_public_spotify_album_metadata(self):
        from app import App
        from metadata import base_record

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(os.environ, {'LOCALAPPDATA': folder}),
        ):
            app = App()
            app.withdraw()
            try:
                row = base_record(
                    'Spotify',
                    'B' * 22,
                    'https://open.spotify.com/track/' + 'B' * 22,
                    'Spotify Embed público',
                )
                row.update(
                    title='Song', artists=['Artist'], album='Edition', track_number=2
                )
                from album_import import finish

                result = finish('Edition', [row], 1, 100, '', album_artists=['Artist'])
                app.playlist_page.display(result)
                app.playlist_page.add()
                job = next(iter(app.jobs.values()))
                self.assertEqual(job['playlist_title'], 'Artist - Edition')
                self.assertEqual(job['catalog_record']['album'], 'Edition')
                self.assertEqual(
                    app.library.load_queue()[0]['catalog_record']['track_number'], 2
                )
            finally:
                app.destroy()
