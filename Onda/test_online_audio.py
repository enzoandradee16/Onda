"""Online resolution never downloads media; decoding uses a bounded PCM pipe."""

import functools
import http.server
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import wave
from unittest.mock import Mock, patch

from online_audio import resolve, NetworkAudio


class OnlineResolveTests(unittest.TestCase):
    def test_direct_url_is_resolved_without_downloading_or_postprocessing(self):
        downloader = Mock()
        downloader.extract_info.return_value = dict(
            url='https://cdn.example/audio',
            duration=20,
            http_headers={'Referer': 'https://example.com/', 'Bad': 'x\r\ny'},
        )
        with patch('yt_dlp.YoutubeDL') as factory:
            factory.return_value.__enter__.return_value = downloader
            model = resolve(
                dict(folder='.', mode='original'),
                dict(
                    title='Track',
                    artists=['Artist'],
                    source_url='https://example.com/song',
                ),
            )
        self.assertFalse(downloader.extract_info.call_args.kwargs['download'])
        self.assertTrue(factory.call_args.args[0]['skip_download'])
        self.assertNotIn('postprocessors', factory.call_args.args[0])
        self.assertNotIn('Bad', model['_stream']['headers'])
        self.assertEqual(model['duration'], 20)
        self.assertEqual(model['cache'], '')

    def test_stream_credentials_are_not_in_persisted_cache_reference(self):
        from playback_session import prepared_reference

        model = dict(
            _stream=dict(
                url='https://example.com/private', headers={'Cookie': 'secret'}
            )
        )
        self.assertEqual(prepared_reference(model), {})

    def test_unknown_duration_and_non_network_streams_are_rejected(self):
        for url, duration in [
            ('file:///tmp/audio', 10),
            ('https://example.com/audio', None),
        ]:
            with (
                self.subTest(url=url, duration=duration),
                patch('yt_dlp.YoutubeDL') as factory,
            ):
                factory.return_value.__enter__.return_value.extract_info.return_value = dict(
                    url=url, duration=duration
                )
                with self.assertRaises(ValueError):
                    resolve(
                        dict(folder='.'),
                        dict(source_url='https://example.com/song', title='Track'),
                    )


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt streaming controls')
class OnlineControlsTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture

    setUpClass = classmethod(Fixture.setUpClass.__func__)
    setUp = Fixture.setUp
    tearDown = Fixture.tearDown

    def streamed_model(self):
        return dict(
            _stream=dict(
                url='https://example.com/audio?secret=token',
                headers={'Cookie': 'secret'},
            ),
            title='Online',
            media_title='Online',
            duration=30,
            cache='',
            source='',
            beats=[0.0, 30.0],
            neighbors=[[]],
            links=0,
        )

    def test_stream_controls_use_source_time_and_native_transport(self):
        bridge = self.bridge
        bridge.model = self.streamed_model()
        bridge.online.position = 12
        self.assertEqual(bridge.sourcePosition, 12)
        with patch.object(bridge.online, 'start') as start:
            bridge.playPause()
            start.assert_called_once()
        bridge.update_state(playing=True, paused=False)
        bridge.playPause()
        self.assertTrue(bridge.paused.is_set())
        bridge.playPause()
        self.assertFalse(bridge.paused.is_set())
        with patch.object(bridge.online, 'start') as start:
            bridge.seekSeconds(8)
            self.assertEqual(bridge.sourcePosition, 8)
            start.assert_called_once()

    def begin_preparation(self):
        bridge = self.bridge
        bridge.model = self.streamed_model()
        bridge.online.position = 12
        bridge.update_state(playing=True, paused=False)
        with patch.object(bridge, 'start_worker') as worker:
            bridge.setEffects(dict(enabled=True, speed=85, reverb=0))
            worker.assert_called_once()
        return bridge._stream_preparation

    def test_enabling_effects_keeps_stream_live_and_deduplicates_jobs(self):
        job = self.begin_preparation()
        bridge = self.bridge
        self.assertTrue(bridge._state['playing'])
        self.assertFalse(bridge.cancelled.is_set())
        self.assertFalse(bridge._state['busy'])
        self.assertTrue(bridge._state['effects_pending'])
        self.assertEqual(bridge.sourcePosition, 12)
        with patch.object(bridge, 'start_worker') as worker:
            bridge.setEffects(dict(enabled=True, speed=75, reverb=20))
            worker.assert_not_called()
        self.assertIs(bridge._stream_preparation, job)

    def test_completed_preparation_switches_at_latest_position(self):
        job = self.begin_preparation()
        job.model = dict(job.source, cache='prepared-cache')
        job.model.pop('_stream')
        bridge = self.bridge
        bridge.online.position = 17
        with patch.object(bridge, 'playPause') as play:
            bridge.handle_event(0, 'stream_prepared', job)
            play.assert_called_once()
        self.assertFalse(bridge._state['effects_pending'])
        self.assertAlmostEqual(bridge.sourcePosition, 17)
        self.assertNotIn('_stream', bridge.model)

    def test_disabling_all_effects_cancels_preparation_without_stopping_audio(self):
        job = self.begin_preparation()
        bridge = self.bridge
        bridge.setEffects(dict(enabled=False, speed=85, reverb=0))
        self.assertTrue(job.cancelled.is_set())
        self.assertTrue(bridge._state['playing'])
        self.assertIs(bridge.model, job.source)
        self.assertFalse(bridge._state['effects_pending'])
        bridge.handle_event(0, 'stream_prepared', job)
        self.assertIs(bridge.model, job.source)

    def test_preparation_error_keeps_original_and_allows_retry(self):
        job = self.begin_preparation()
        bridge = self.bridge
        bridge.handle_event(0, 'stream_prepare_error', (job, 'Network error'))
        self.assertTrue(bridge._state['playing'])
        self.assertIs(bridge.model, job.source)
        self.assertFalse(bridge._state['effects_pending'])
        with patch.object(bridge, 'start_worker') as worker:
            bridge.setEffects(dict(enabled=True, speed=90, reverb=0))
            worker.assert_called_once()

    def test_disabling_slowed_keeps_preparing_until_jukebox_is_also_disabled(self):
        job = self.begin_preparation()
        bridge = self.bridge
        bridge.setParams(45, 35, 80, False)
        bridge.setEffects(dict(enabled=False))
        self.assertFalse(job.cancelled.is_set())
        self.assertTrue(bridge._state['playing'])
        bridge.setParams(45, 35, 80, True)
        self.assertTrue(job.cancelled.is_set())
        self.assertTrue(bridge._state['playing'])
        self.assertFalse(bridge._state['effects_pending'])

    def test_latest_slider_settings_are_ready_before_handoff(self):
        job = self.begin_preparation()
        job.effects = dict(enabled=True, speed=75, reverb=0, keep_pitch=False)
        job.retry = Mock()
        with patch.object(self.bridge, 'start_worker') as worker:
            self.bridge.handle_event(0, 'stream_prepared', job)
            worker.assert_called_once_with(job.retry)
        self.assertIs(self.bridge.model, job.source)
        self.assertTrue(self.bridge._state['playing'])
        self.assertTrue(self.bridge._state['effects_pending'])

    def test_old_song_preparation_cannot_replace_new_song(self):
        job = self.begin_preparation()
        bridge = self.bridge
        other = self.streamed_model()
        bridge.handle_event(bridge.revision, 'result', other)
        self.assertTrue(job.cancelled.is_set())
        bridge.handle_event(0, 'stream_prepared', job)
        self.assertIs(bridge.model, other)

    @unittest.skipUnless(os.environ.get('ONDA_FFMPEG'), 'Native FFmpeg/output')
    def test_native_stream_keeps_playing_until_real_effects_are_ready(self):
        import time
        from PySide6.QtCore import QTimer
        from test_jukebox import song
        from test_qt_workspace import NativeDesktopTests

        bridge = self.bridge
        bridge.config_provider = lambda: dict(ffmpeg=os.environ['ONDA_FFMPEG'])
        source = self.root / 'online.wav'
        song(source, seconds=16)

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        server = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), functools.partial(Handler, directory=str(self.root))
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        timer = QTimer()
        ticks = []
        timer.timeout.connect(lambda: ticks.append(time.monotonic()))
        timer.start(16)
        from qt_models_ui import QueueRowsModel
        from qt_queue_rows_ui import presentation_rows
        import base64

        # Exercise both queue views while native HTTP audio and effects run.
        cover = 'data:image/png;base64,' + base64.b64encode(b'x' * 4096).decode()
        rows = [
            dict(id=str(i), title='Track', cover=cover, record=dict(cover_url=cover))
            for i in range(994)
        ]
        queue_models = [QueueRowsModel(), QueueRowsModel()]
        queue_updates = QTimer()

        def update_queues():
            rows.append(rows.pop(0))
            projected = presentation_rows(rows)
            for queue_model in queue_models:
                queue_model.setRows(projected)

        queue_updates.timeout.connect(update_queues)
        queue_updates.start(100)
        try:
            model = self.streamed_model()
            model['_stream'] = dict(
                url=f'http://127.0.0.1:{server.server_port}/online.wav'
            )
            model['duration'] = 16
            model['beats'] = [0.0, 16.0]
            bridge.model = model
            bridge._params = (45.0, 35.0, 0.0, True)
            bridge.update_state(ready=True, streaming=True)
            bridge.playPause()
            NativeDesktopTests.wait_for(
                self, lambda: bridge.sourcePosition > 0.3, 10000
            )
            original_cancel = bridge.cancelled
            bridge.setEffects(dict(enabled=True, speed=85, reverb=25))
            self.assertFalse(original_cancel.is_set())
            self.assertTrue(bridge._state['playing'])
            NativeDesktopTests.wait_for(self, lambda: bridge.model is not model, 30000)
            self.assertTrue(original_cancel.is_set())
            self.assertTrue(bridge._state['playing'])
            self.assertNotIn('_stream', bridge.model)
            self.assertFalse(bridge._state['effects_pending'])
            self.assertGreater(bridge.sourcePosition, 0.3)
            self.assertEqual(bridge._state.get('effects_error', ''), '')
            gaps = [b - a for a, b in zip(ticks, ticks[1:])]
            self.assertGreater(len(ticks), 10)
            self.assertLess(max(gaps), 0.25, f'UI heartbeat stalled: {max(gaps):.3f}s')
            print(
                f'Native streaming/effects UI maximum timer gap: {max(gaps)*1000:.1f} ms'
            )
        finally:
            timer.stop()
            queue_updates.stop()
            bridge.stop()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_snapshot_does_not_save_expiring_urls_or_headers(self):
        from playback_session import save

        bridge = self.bridge
        bridge.model = self.streamed_model()
        bridge.playlist = [
            dict(
                id='song',
                kind='catalog',
                title='Online',
                record=dict(title='Online', source_url='https://example.com/song'),
            )
        ]
        bridge.queue_index = 0
        bridge._prepared['song'] = bridge.model
        bridge.online.position = 12
        save(self.ws, strict=True)
        raw = self.ws.store.path.with_name('playback-session.json').read_text(
            encoding='utf-8'
        )
        self.assertNotIn('secret', raw)
        self.assertEqual(json.loads(raw)['jukebox']['seconds'], 12)


@unittest.skipUnless(os.environ.get('ONDA_FFMPEG'), 'FFmpeg network integration')
class OnlineDecodeTests(unittest.TestCase):
    def test_real_http_audio_starts_as_pcm_and_supports_seeking_without_output_file(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'tone.wav'
            with wave.open(str(source), 'wb') as sound:
                sound.setparams((2, 2, 44100, 0, 'NONE', ''))
                sound.writeframes(b'\x01\x00\x01\x00' * (3 * 44100))

            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, *args):
                    pass

            server = http.server.ThreadingHTTPServer(
                ('127.0.0.1', 0), functools.partial(Handler, directory=directory)
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for start in (0, 2):
                    reader = NetworkAudio(
                        dict(url=f'http://127.0.0.1:{server.server_port}/tone.wav'),
                        os.environ['ONDA_FFMPEG'],
                        start,
                    )
                    try:
                        first = reader.read()
                        self.assertEqual(len(first), 4410 * 4)
                        total = len(first)
                        while True:
                            part = reader.read()
                            if not part:
                                break
                            total += len(part)
                        self.assertAlmostEqual(total / 4 / 44100, 3 - start, delta=0.02)
                    finally:
                        reader.close()
                self.assertEqual([p.name for p in root.iterdir()], ['tone.wav'])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
