"""Account playlist pages expose metadata only and reuse existing track workflows."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from spotify_account import SpotifyAccount
from metadata import MetadataError

ID = 'A' * 22
TRACK = dict(
    title='Song',
    artists=['Artist'],
    album='Album',
    duration_ms=200000,
    source_url='https://open.spotify.com/track/' + 'B' * 22,
)


class SpotifyLibraryTests(unittest.TestCase):
    def test_metadata_page_skips_bad_rows_and_never_follows_next_url(self):
        account = SimpleNamespace(
            get=Mock(
                return_value=dict(
                    items=[
                        None,
                        dict(id='invalid'),
                        dict(
                            id=ID,
                            name='Private playlist',
                            owner=dict(display_name='Owner'),
                            items=dict(total=5),
                            images=[
                                dict(url='file:///secret'),
                                dict(url='https://i.scdn.co/image/cover'),
                            ],
                        ),
                    ],
                    next='https://untrusted.example/next',
                )
            )
        )
        result = SpotifyAccount.playlists(account)
        self.assertEqual(result['next_offset'], 3)
        self.assertEqual(len(result['playlists']), 1)
        row = result['playlists'][0]
        self.assertEqual(row['count'], 5)
        self.assertEqual(row['source_url'], 'https://open.spotify.com/playlist/' + ID)
        self.assertTrue(row['cover_url'].startswith('https://'))
        self.assertNotIn('tracks', row)
        account.get.assert_called_once_with('me/playlists', dict(offset=0, limit=50))

    def test_legacy_track_counts_empty_pages_and_cancellation(self):
        account = SimpleNamespace(
            get=Mock(
                return_value=dict(items=[dict(id=ID, tracks=dict(total=10))], next=None)
            )
        )
        self.assertEqual(SpotifyAccount.playlists(account)['playlists'][0]['count'], 10)
        account.get.reset_mock()
        with self.assertRaises(MetadataError):
            SpotifyAccount.playlists(account, cancelled=lambda: True)
        account.get.assert_not_called()
        with self.assertRaises(MetadataError):
            SpotifyAccount.playlists(account, offset=-1)
        account.get.return_value = dict(items=[], next=None)
        self.assertEqual(SpotifyAccount.playlists(account)['next_offset'], -1)


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt Spotify library')
class DesktopSpotifyLibraryTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture

    setUpClass = classmethod(Fixture.setUpClass.__func__)
    setUp = Fixture.setUp
    tearDown = Fixture.tearDown

    def connect_fixture(self):
        self.ws.account.client_id = 'a' * 32
        self.ws.account.refresh_token = 'fixture'
        self.ws.options['spotifyPlaylists'] = [
            dict(
                id=ID,
                title='Playlist',
                source_url='https://open.spotify.com/playlist/' + ID,
            )
        ]

    def test_account_listing_merges_pages_without_duplicate_cards(self):
        self.connect_fixture()
        with patch.object(self.ws, 'run_task') as task:
            self.ws.load_spotify_playlists()
            self.assertEqual(task.call_args.args[0], 'spotify_playlists')
            task.call_args.args[2](
                dict(playlists=[dict(id=ID, title='Playlist')], next_offset=50)
            )
            self.ws.load_spotify_playlists(True)
            self.assertEqual(task.call_args.args[1]['offset'], 50)
            task.call_args.args[2](
                dict(playlists=[dict(id=ID, title='Updated')], next_offset=-1)
            )
        self.assertEqual(len(self.ws.options['spotifyPlaylists']), 1)
        self.assertEqual(self.ws.options['spotifyPlaylistsNext'], -1)

    def test_playlist_actions_load_before_reusing_playback_or_download_queue(self):
        self.connect_fixture()
        for action in (
            'spotify_playlist_playback',
            'spotify_playlist_add',
            'spotify_playlist_download',
        ):
            with (
                patch.object(self.ws, 'run_task') as task,
                patch.object(self.ws, 'enqueue_tracks') as download,
                patch.object(self.bridge, 'enqueueRecords', return_value=1) as enqueue,
                patch.object(self.bridge, 'playQueued') as play,
            ):
                self.ws.dispatch(action, dict(id=ID))
                self.assertEqual(task.call_args.args[0], 'collection')
                task.call_args.args[2](dict(title='Playlist', tracks=[TRACK]))
                if action.endswith('playback'):
                    enqueue.assert_called_once()
                    play.assert_called_once()
                    download.assert_not_called()
                else:
                    download.assert_called_once_with(
                        [TRACK], start=action.endswith('download')
                    )
                    enqueue.assert_not_called()

    def test_disconnected_account_opens_account_settings_without_a_request(self):
        with patch.object(self.ws, 'run_task') as task:
            self.ws.load_spotify_playlists()
            task.assert_not_called()
