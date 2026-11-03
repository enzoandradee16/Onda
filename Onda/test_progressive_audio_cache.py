"""Growing PCM is playable before completion, seekable and disposable without secrets."""

import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock
from progressive_audio_cache import ProgressiveAudioCache, in_use, prune


class ProgressiveCacheTests(unittest.TestCase):
    def test_premature_eof_is_not_persisted_as_a_complete_song(self):
        from progressive_audio_cache import CacheReadError

        with tempfile.TemporaryDirectory() as root:
            source = Mock()
            source.read.side_effect = [b'\0' * (44100 * 4), b'']
            cache = ProgressiveAudioCache('truncated', 20, lambda _: source, root=root)
            cache.start()
            cache.thread.join(2)
            try:
                self.assertFalse(cache.complete)
                self.assertIsInstance(cache.error, CacheReadError)
                self.assertFalse((cache.folder / 'ready.json').exists())
            finally:
                cache.close()

    def test_damaged_packet_cache_can_fall_back_to_resolved_stream_for_effects(self):
        from unittest.mock import patch
        from online_audio import prepare_stream

        with tempfile.TemporaryDirectory() as root, patch(
            'jukebox.cache_root', return_value=Path(root)
        ), patch(
            'stream_file_cache.lookup',
            return_value={'path': str(Path(root) / 'bad.mka')},
        ), patch(
            'jukebox.prepare',
            side_effect=[ValueError('Damaged cache'), {'cache': 'fresh'}],
        ) as analyze, patch(
            'online_audio.NetworkAudio'
        ) as network:
            network.return_value.read.side_effect = [b'\0' * 17640, b'']
            model = dict(
                title='Recovered',
                duration=4,
                _stream=dict(url='https://example.com/audio'),
            )
            prepared = prepare_stream(model, {})
            self.assertEqual(prepared['title'], 'Recovered')
            self.assertEqual(analyze.call_count, 2)
            network.assert_called_once()

    def test_effect_preparation_reuses_complete_pcm_without_opening_network(self):
        import wave
        from online_audio import prepare_stream
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as root, patch(
            'jukebox.cache_root', return_value=Path(root)
        ):
            raw = b'\x01\x00\x01\x00' * (2 * 44100)
            source = Mock()
            source.read.side_effect = [raw, b'']
            cache = ProgressiveAudioCache(
                'https://example.com/song', 2, lambda _: source
            )
            cache.start()
            cache.thread.join(2)
            self.assertTrue(cache.complete)
            cache.close()
            model = dict(
                title='Cached song',
                duration=2,
                _stream=dict(
                    url='https://expired.example/audio',
                    source_url='https://example.com/song',
                ),
            )

            def analyze(path, *args):
                with wave.open(str(path), 'rb') as sound:
                    self.assertEqual(sound.readframes(sound.getnframes()), raw)
                return dict(cache='prepared')

            with patch(
                'online_audio.NetworkAudio', side_effect=AssertionError('No network')
            ), patch('jukebox.prepare', side_effect=analyze):
                prepared = prepare_stream(model, {})
            self.assertEqual(prepared['title'], 'Cached song')

    def test_prefix_can_play_before_full_track_then_full_cache_reuses_without_network(
        self,
    ):
        with tempfile.TemporaryDirectory() as root:
            release = threading.Event()
            blocked = threading.Event()

            class Source:
                count = 0

                def read(self):
                    self.count += 1
                    if self.count == 3:
                        blocked.set()
                        release.wait(2)
                    return bytes([self.count]) * 17640 if self.count <= 20 else b''

                def cancel(self):
                    release.set()

                def close(self):
                    pass

            cache = ProgressiveAudioCache(
                'https://example.com/song', 2, lambda _: Source(), root=root
            )
            cache.start()
            reader = cache.reader()
            self.assertEqual(reader.read(), bytes([1]) * 17640)
            self.assertTrue(blocked.wait(2))
            self.assertFalse(cache.complete)
            self.assertTrue(cache.covers(0.1))
            self.assertFalse(cache.covers(1))
            self.assertTrue(in_use(cache.folder / 'audio.pcm'))
            reader.close()
            release.set()
            cache.thread.join(2)
            self.assertTrue(cache.complete)
            reader = cache.reader(1.5)
            self.assertEqual(reader.read(), bytes([16]) * 17640)
            reader.close()
            cache.close()
            factory = Mock(side_effect=AssertionError('Should use disk'))
            reused = ProgressiveAudioCache(
                'https://example.com/song', 2, factory, root=root
            )
            self.assertTrue(reused.complete)
            reader = reused.reader(0.5)
            self.assertEqual(reader.read(), bytes([6]) * 17640)
            reader.close()
            reused.close()
            factory.assert_not_called()
            self.assertNotIn(
                'https://', next(Path(root).glob('*/ready.json')).read_text()
            )

    def test_cancel_unblocks_readers_and_removes_incomplete_data(self):
        with tempfile.TemporaryDirectory() as root:
            release = threading.Event()
            source = Mock()
            source.read.side_effect = lambda: (release.wait(2), b'')[1]
            source.cancel.side_effect = release.set
            cache = ProgressiveAudioCache('cancel', 2, lambda _: source, root=root)
            cache.start()
            reader = cache.reader()
            result = []
            worker = threading.Thread(target=lambda: result.append(reader.read()))
            worker.start()
            cache.cancel()
            worker.join(1)
            self.assertFalse(worker.is_alive())
            self.assertEqual(result, [b''])
            reader.close()
            cache.close()
            self.assertFalse(cache.folder.exists())

    def test_cleanup_preserves_active_entries(self):
        with tempfile.TemporaryDirectory() as root:
            source = Mock()
            source.read.side_effect = [b'x' * 17640, b'']
            cache = ProgressiveAudioCache('protected', 1, lambda _: source, root=root)
            cache.start()
            cache.thread.join(2)
            prune(root, reserve=256 * 1024 * 1024)
            self.assertTrue(cache.folder.exists())
            cache.close()
            prune(root, reserve=256 * 1024 * 1024)
            self.assertFalse(cache.folder.exists())

    @unittest.skipUnless(
        __import__('os').environ.get('ONDA_FFMPEG'), 'FFmpeg network integration'
    )
    def test_real_http_cache_allows_distant_seek_after_server_disconnects(self):
        import functools
        import http.server
        import os
        import wave
        from online_audio import NetworkAudio

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with wave.open(str(root / 'tone.wav'), 'wb') as sound:
                sound.setparams((2, 2, 44100, 0, 'NONE', ''))
                sound.writeframes(b'\x01\x00\x01\x00' * (120 * 44100))

            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *args):
                    pass

            server = http.server.ThreadingHTTPServer(
                ('127.0.0.1', 0), functools.partial(Handler, directory=directory)
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            cache = ProgressiveAudioCache(
                'local-http',
                120,
                lambda seconds: NetworkAudio(
                    dict(url=f'http://127.0.0.1:{server.server_port}/tone.wav'),
                    os.environ['ONDA_FFMPEG'],
                    seconds,
                ),
                root=root / 'cache',
            )
            try:
                began = time.monotonic()
                cache.start()
                reader = cache.reader()
                self.assertEqual(reader.read(), b'\x01\x00\x01\x00' * 4410)
                first = time.monotonic() - began
                reader.close()
                cache.thread.join(15)
                self.assertTrue(cache.complete)
                server.shutdown()
                server.server_close()
                thread.join(2)
                reader = cache.reader(100.25)
                self.assertEqual(reader.read(), b'\x01\x00\x01\x00' * 4410)
                reader.close()
                print(
                    f'PC cache: first PCM {first:.3f}s; offline seek to 100.25s succeeded'
                )
            finally:
                cache.close()
                server.shutdown()
                server.server_close()
                thread.join(2)

    def test_empty_stream_unblocks_reader_with_error(self):
        from progressive_audio_cache import CacheReadError

        with tempfile.TemporaryDirectory() as root:
            source = Mock()
            source.read.return_value = b''
            cache = ProgressiveAudioCache('empty', 2, lambda _: source, root=root)
            cache.start()
            cache.thread.join(2)
            reader = cache.reader()
            try:
                with self.assertRaises(CacheReadError):
                    reader.read()
            finally:
                reader.close()
                cache.close()

    @unittest.skipUnless(
        __import__('os').environ.get('ONDA_FFMPEG'), 'FFmpeg integration'
    )
    def test_packet_cache_reuses_original_audio_without_analysis_or_network(self):
        import functools, http.server, os, wave, json, subprocess
        from unittest.mock import patch
        from stream_file_cache import prepare
        from audio_tools import executable, process_options

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with wave.open(str(root / 'tone.wav'), 'wb') as sound:
                sound.setparams((2, 2, 44100, 0, 'NONE', ''))
                sound.writeframes(b'\x01\x00\x01\x00' * (4 * 44100))

            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *args):
                    pass

            server = http.server.ThreadingHTTPServer(
                ('127.0.0.1', 0), functools.partial(Handler, directory=directory)
            )
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            model = {
                '_stream': {'url': f'http://127.0.0.1:{server.server_port}/tone.wav'},
                'duration': 4,
            }
            config = {'ffmpeg': os.environ['ONDA_FFMPEG']}
            try:
                with (
                    patch('jukebox.cache_root', return_value=root / 'cache'),
                    patch(
                        'jukebox.prepare',
                        side_effect=AssertionError('No musical analysis'),
                    ),
                ):
                    first = prepare(model, config)
                    server.shutdown()
                    server.server_close()
                    worker.join(2)
                    second = prepare(model, config)
                self.assertEqual(first, second)
                result = subprocess.run(
                    [
                        executable('ffprobe', config['ffmpeg']),
                        '-v',
                        'error',
                        '-show_streams',
                        '-of',
                        'json',
                        first['path'],
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                    **process_options(),
                )
                stream = json.loads(result.stdout)['streams'][0]
                self.assertEqual(stream['codec_name'], 'pcm_s16le')
                self.assertEqual(stream['sample_rate'], '44100')
                from online_audio import prepare_stream

                with patch('jukebox.cache_root', return_value=root / 'cache'), patch(
                    'online_audio.NetworkAudio',
                    side_effect=AssertionError('No second audio download'),
                ):
                    analyzed = prepare_stream(
                        dict(model, title='Packet cached song'), config
                    )
                    self.assertTrue(
                        (Path(analyzed['cache']) / 'analysis.json').is_file()
                    )
            finally:
                server.shutdown()
                server.server_close()
                worker.join(2)
