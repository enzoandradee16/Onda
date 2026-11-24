"""Keep native Android network audio verified, bounded and cancellable."""

import sys
import unittest
from unittest.mock import MagicMock, patch

from audio_tools import network_input_options
from stream_file_cache import _download_android_hls


class AndroidHttpsAudioTests(unittest.TestCase):
    def test_android_trust_store_is_explicit_and_verification_stays_on(self):
        with patch.object(sys, 'getandroidapilevel', return_value=30, create=True):
            with patch('certifi.where', return_value='/private/cacert.pem'):
                self.assertEqual(
                    network_input_options('https://example.com/a'),
                    ['-ca_file', '/private/cacert.pem', '-tls_verify', '1'],
                )
                self.assertEqual(network_input_options('/private/audio.wav'), [])

    def test_native_hls_enforces_cache_limit_and_cancellation(self):
        from jukebox import Cancelled

        for cancelled, value, error in [
            (lambda: False, {'downloaded_bytes': 1025}, ValueError),
            (lambda: True, {'downloaded_bytes': 1}, Cancelled),
        ]:
            native = MagicMock()
            native.download.side_effect = lambda *args: (
                native.add_progress_hook.call_args.args[0](value),
                True,
            )
            with patch('yt_dlp.YoutubeDL') as ydl, patch(
                'yt_dlp.downloader.hls.HlsFD', return_value=native
            ), self.assertRaises(error):
                _download_android_hls(
                    {'url': 'https://example.com/a.m3u8'}, 'unused', 1024, cancelled
                )
            self.assertNotIn('nocheckcertificate', ydl.call_args.args[0])
