"""Warm-up ownership and per-track artwork regressions."""

import unittest
from unittest.mock import Mock, patch
from stream_warmup import prepare, take, keep


class StreamWarmupTests(unittest.TestCase):
    def tearDown(self):
        keep([])

    def test_prefix_is_ready_without_waiting_for_whole_song_and_is_transferred(self):
        cache = Mock(closed=False, error=None, complete=False, buffered_seconds=3)
        model = dict(_stream=dict(url='https://example.test/track'), duration=240)
        with patch('progressive_audio_cache.ProgressiveAudioCache', return_value=cache):
            prepare(model, {}, lambda: False, lambda _: None)
        self.assertIs(take(model), cache)
        keep([])
        cache.cancel.assert_not_called()
        cache.thread.join.assert_not_called()

    def test_playlist_cover_is_not_written_as_track_cover(self):
        from catalog_details import collection_artwork, track_artwork

        row = dict(
            source_url='https://open.spotify.com/track/' + 'A' * 22, title='Song'
        )
        result = collection_artwork(
            dict(kind='playlist', cover_url='https://mosaic.scdn.co/list', tracks=[row])
        )
        self.assertNotIn('cover_url', row)
        with patch('metadata.MetadataClient') as factory:
            factory.return_value.fetch.return_value = dict(
                cover_url='https://example.test/album.jpg'
            )
            completed = track_artwork(row, {})
        self.assertEqual(completed['cover_url'], 'https://example.test/album.jpg')
        self.assertEqual(completed['title'], 'Song')
        self.assertEqual(result['cover_url'], 'https://mosaic.scdn.co/list')
