"""Qt preview integration: isolated preferences, no network or audible playback."""

import threading
import os, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
TOOLS = Path(
    os.environ.get(
        'ONDA_FFMPEG',
        str(Path(os.environ.get('LOCALAPPDATA', '')) / 'Onda/tools/ffmpeg/9.0.2'),
    )
)
import sys

packages = ROOT.parent / '.venv/qt-packages'
if packages.is_dir():
    sys.path.insert(0, str(packages))
try:
    from PySide6.QtCore import (
        QUrl,
        QTimer,
        QObject,
        QMetaObject,
        QEventLoop,
        qInstallMessageHandler,
    )
    from PySide6.QtGui import QGuiApplication

    QT = True
except ImportError:
    QT = False


@unittest.skipUnless(
    QT and os.environ.get('ONDA_QT_TESTS'), 'Optional Qt preview tests'
)
class QtJukeboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QGuiApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {
                'LOCALAPPDATA': self.temp.name,
                'ONDA_ALIAS_CACHE_ROOT': str(Path(self.temp.name) / 'cache'),
            },
        )
        self.env.start()
        from preferences import PreferenceStore

        self.store = PreferenceStore()
        self.store.save(
            {
                'check_updates': False,
                'clipboard_links': False,
                'theme_mode': 'Claro',
                'theme_accent': 'Vermelho',
                'mp3_quality': '192 kbps',
            }
        )
        self.bridges = []

    def tearDown(self):
        for bridge in self.bridges:
            bridge.shutdown()
        self.app.processEvents()
        self.env.stop()
        self.temp.cleanup()

    def bridge(self):
        from qt_jukebox_ui import JukeboxBridge

        bridge = JukeboxBridge(self.store)
        bridge.setParams(45, 35, 80, False)
        bridge.config_provider = lambda: {
            'ffmpeg': str(TOOLS),
            'spotify_client_id': '',
            'spotify_client_secret': '',
        }
        self.bridges.append(bridge)
        return bridge

    def wait(self, milliseconds):
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec()

    def wait_for(self, predicate, timeout=6000):
        deadline = time.monotonic() + timeout / 1000
        while time.monotonic() < deadline:
            if predicate():
                return
            self.wait(10)
        self.fail('Qt operation did not finish before timeout')

    def test_preferences_preserve_existing_values_and_preset(self):
        bridge = self.bridge()
        bridge.applyPreset('Rock')
        bridge.setAppearance('Escuro', 'Azul', False)
        bridge.save_preferences()
        saved = self.store.load()
        self.assertEqual(saved['mp3_quality'], '192 kbps')
        self.assertFalse(saved['qt_animations'])
        other = self.bridge()
        self.assertEqual(other.presetName, 'Rock')
        self.assertEqual(other.theme, 'Escuro')
        self.assertFalse(other.animations)
        self.assertFalse(bridge.state['playing'])

    def test_remember_disabled_keeps_equalizer_session_only(self):
        self.store.forget()
        bridge = self.bridge()
        bridge.applyPreset('Vocais')
        bridge.save_preferences()
        self.assertEqual(bridge.presetName, 'Vocais')
        self.assertIsNone(self.store.load())

    def test_stale_results_do_not_replace_current_model(self):
        bridge = self.bridge()
        revision = bridge.revision
        bridge.stop()
        bridge.handle_event(revision, 'result', {'tracks': [{'title': 'Stale'}]})
        self.assertEqual(bridge.state['results'], [])
        self.assertFalse(bridge.state['busy'])

    def test_normal_mode_hides_possible_links_without_erasing_flow(self):
        bridge = self.bridge()
        bridge.model = {'neighbors': [[12] for _ in range(32)]}
        bridge.flow = [(1, 12)]
        bridge.setParams(0, 35, 80, False)
        self.assertTrue(bridge.graph['links'])
        bridge.setParams(0, 35, 80, True)
        self.assertFalse(bridge.graph['links'])
        self.assertEqual(bridge.graph['flow'], [(1, 12)])

    def test_marker_progress_reuses_graph_until_links_or_flow_change(self):
        bridge = self.bridge()
        bridge.model = {'neighbors': [[12] for _ in range(32)]}
        bridge.update_graph()
        graph = bridge.graph
        bridge.handle_event(
            bridge.revision,
            'position',
            {'index': 3, 'phase': 0.5, 'elapsed': 1.5, 'jumps': 0, 'edges': []},
        )
        self.assertIs(bridge.graph, graph)
        self.assertEqual(bridge.graph['links'], [(i, 12) for i in range(32)])
        self.assertEqual(bridge.position, 3.5)
        graph = bridge.graph
        bridge.handle_event(
            bridge.revision,
            'position',
            {'index': 3, 'phase': 0.6, 'elapsed': 0.6, 'jumps': 0, 'edges': []},
        )
        self.assertIs(bridge.graph, graph)
        bridge.handle_event(
            bridge.revision,
            'position',
            {'index': 12, 'phase': 0, 'elapsed': 2.0, 'jumps': 1, 'edges': [(3, 12)]},
        )
        self.assertIsNot(bridge.graph, graph)
        self.assertEqual(bridge.graph['flow'], [(3, 12)])
        self.assertEqual(bridge.graph['used'], [(3, 12)])

    def test_used_connections_remain_highlighted_after_recent_trail_expires(self):
        bridge = self.bridge()
        bridge.model = {'neighbors': [[12] for _ in range(32)]}
        for i in range(30):
            bridge.handle_event(
                bridge.revision,
                'position',
                {
                    'index': i,
                    'phase': 0,
                    'elapsed': float(i),
                    'jumps': i,
                    'edges': [(i, 12)],
                },
            )
        self.assertEqual(len(bridge.graph['flow']), 24)
        self.assertEqual(len(bridge.graph['used']), 30)
        self.assertIn((0, 12), bridge.graph['used'])

    def test_variation_filters_connections_by_similarity(self):
        bridge = self.bridge()
        bridge.model = {'neighbors': [[12, 14, 16, 18, 20] for _ in range(32)]}
        bridge.setParams(0, 35, 80, False)
        low = bridge.graph
        bridge.setParams(100, 35, 80, False)
        high = bridge.graph
        self.assertTrue(set(low['links']) < set(high['links']))
        self.assertEqual(len(low['links']), 32)
        self.assertEqual(len(high['links']), 160)
        self.assertEqual(low['variation'], 0)
        self.assertEqual(high['variation'], 100)

    def test_dense_graph_is_bounded_and_topology_is_reused_during_playback(self):
        from jukebox import variation_neighbors

        bridge = self.bridge()
        rows = [list(range(80)) for _ in range(2000)]
        bridge.model = {'neighbors': rows}
        bridge.setParams(100, 35, 80, False)
        with patch(
            'jukebox.variation_neighbors', wraps=variation_neighbors
        ) as topology:
            first = bridge.graph
            self.assertLessEqual(len(first['links']), 1800)
            bridge.handle_event(
                bridge.revision,
                'position',
                {
                    'index': 3,
                    'phase': 0,
                    'elapsed': 2.0,
                    'jumps': 1,
                    'edges': [(3, 12)],
                },
            )
            second = bridge.graph
            self.assertIs(first['links'], second['links'])
            self.assertEqual(topology.call_count, 1)
            self.assertEqual(sum(map(len, rows)), 160000)
            self.assertEqual(second['flow'], [(3, 12)])

    def test_graph_static_image_is_reused_for_new_trail(self):
        from qt_graph_ui import BeatGraph
        from PySide6.QtGui import QImage, QPainter

        graph = BeatGraph()
        graph.setWidth(400)
        graph.setHeight(320)
        graph.graphData = {
            'count': 32,
            'links': [(0, 12), (3, 15)],
            'used': [],
            'flow': [],
        }
        image = QImage(400, 320, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        try:
            graph.paint(painter)
            base = graph._base_image
            graph.graphData = {
                'count': 32,
                'links': [(0, 12), (3, 15)],
                'used': [(3, 15)],
                'flow': [(3, 15)],
            }
            graph.paint(painter)
            self.assertIs(graph._base_image, base)
            graph.setWidth(420)
            graph.paint(painter)
            self.assertIsNot(graph._base_image, base)
        finally:
            painter.end()

    def test_search_returns_choices_without_downloading(self):
        bridge = self.bridge()
        records = [
            {
                'title': 'Choice',
                'artists': ['Artist'],
                'source_url': 'https://www.deezer.com/track/1',
            }
        ]
        with (
            patch('music_search.search_music', return_value={'tracks': records}),
            patch('qt_jukebox_ui.fetch_audio') as download,
        ):
            bridge.search('Choice')
            self.wait_for(lambda: not bridge.state['busy'])
            self.assertEqual(
                [
                    {key: row[key] for key in ('title', 'artist', 'album', 'cover')}
                    for row in bridge.state['results']
                ],
                [{'title': 'Choice', 'artist': 'Artist', 'album': '', 'cover': ''}],
            )
            self.assertEqual(
                bridge.state['results'][0]['source_url'], records[0]['source_url']
            )
            download.assert_not_called()
            self.assertFalse(bridge.state['playing'])

    def prepare_model(self, bridge):
        from test_jukebox import song

        tools = TOOLS
        if not tools.is_dir():
            self.skipTest('FFmpeg is required for the local audio integration test')
        source = Path(self.temp.name) / 'Teste local.wav'
        song(source)
        with patch.object(bridge, 'config', return_value={'ffmpeg': str(tools)}):
            bridge.openFile(QUrl.fromLocalFile(str(source)))
            self.wait_for(lambda: not bridge.state['busy'], 10000)
        self.assertTrue(bridge.state['ready'], bridge.state['status'])
        self.assertEqual(bridge.state['title'], 'Teste local')
        bridge.clearPlaybackQueue()  # Opening a source now also inserts its shared queue entry.
        return bridge.model

    def test_playback_queue_reordering_next_and_autoplay(self):
        bridge = self.bridge()
        model = self.prepare_model(bridge)
        source = Path(self.temp.name) / 'Teste local.wav'
        bridge.enqueueFiles(
            [QUrl.fromLocalFile(str(source)), QUrl.fromLocalFile(str(source))]
        )
        self.assertEqual(len(bridge.playback['queue']), 2)
        with (
            patch.object(bridge, 'config', return_value={'ffmpeg': str(TOOLS)}),
            patch('qt_jukebox_ui.prepare', return_value=model),
            patch.object(bridge, 'playPause') as play,
        ):
            bridge.playQueued(0)
            self.wait_for(lambda: play.call_count == 1)
            play.assert_called_once()
            self.assertEqual(bridge.queue_index, 0)
            bridge.nextTrack()
            self.wait_for(lambda: play.call_count == 2)
            self.assertEqual(play.call_count, 2)
            self.assertEqual(bridge.queue_index, 1)
            bridge.moveQueued(1, -1)
            self.assertEqual(bridge.queue_index, 0)
            bridge.removeQueued(1)
            self.assertEqual(len(bridge.playback['queue']), 1)
        bridge.setTrackMinutes(3)
        with patch.object(bridge, 'nextTrack') as next_track:
            bridge.handle_event(
                bridge.revision,
                'position',
                {'index': 0, 'phase': 0, 'elapsed': 180, 'jumps': 0, 'edges': []},
            )
            next_track.assert_called_once()

    def test_sleep_timer_stops_without_altering_user_volume(self):
        bridge = self.bridge()
        now = [0.0]
        bridge.sleep.clock = lambda: now[0]
        bridge.setSleep(1)
        volume = bridge._params[2]
        bridge.update_state(playing=True)
        now[0] = 55
        self.assertAlmostEqual(bridge.sleep.gain(), 0.5)
        now[0] = 60
        bridge.tick_sleep()
        self.assertFalse(bridge.playback['sleepActive'])
        self.assertFalse(bridge.state['playing'])
        self.assertEqual(bridge._params[2], volume)
        self.assertEqual(bridge.sleep.gain(), 1)

    def test_search_can_add_next_music_without_stopping_playback(self):
        bridge = self.bridge()
        bridge.update_state(playing=True)
        cancel = bridge.cancelled
        with patch(
            'music_search.search_music',
            return_value={
                'tracks': [
                    {
                        'title': 'Next',
                        'artists': [],
                        'source_url': 'https://www.deezer.com/track/1',
                    }
                ]
            },
        ):
            bridge.search('Next')
            self.wait_for(lambda: not bridge.state['busy'])
        self.assertFalse(cancel.is_set())
        self.assertTrue(bridge.state['playing'])
        with patch.object(
            bridge, 'fetch_record', return_value={'title': 'Next', 'links': 0}
        ):
            bridge.enqueueResult(0)
            self.wait_for(lambda: bridge.queuedTracks[0]['analysis'] == 'ready')
        self.assertEqual(bridge.playback['queue'][0]['title'], 'Next')

    def test_failed_queue_item_does_not_autoplay_previous_model(self):
        bridge = self.bridge()
        self.prepare_model(bridge)
        source = Path(self.temp.name) / 'Teste local.wav'
        with (
            patch.object(bridge, 'config', return_value={'ffmpeg': str(TOOLS)}),
            patch('qt_jukebox_ui.prepare', side_effect=ValueError('Falha na análise')),
            patch.object(bridge, 'playPause') as play,
        ):
            bridge.enqueueFiles([QUrl.fromLocalFile(str(source))])
            bridge.playQueued(0)
            self.wait_for(lambda: bridge.queuedTracks[0]['analysis'] == 'error')
            play.assert_not_called()
            self.assertEqual(bridge.state['status'], 'Falha na análise')

    def test_timer_crossfade_keeps_one_audio_output(self):
        bridge = self.bridge()
        model = self.prepare_model(bridge)
        source = Path(self.temp.name) / 'Teste local.wav'

        class Output:
            instances = []

            def __init__(self, progress):
                self.progress = progress
                self.frames = 0
                self.instances.append(self)

            def write(self, data, cancelled, paused):
                while paused() and not cancelled():
                    time.sleep(0.002)
                if cancelled():
                    return
                self.frames += len(data) // 4
                self.progress(self.frames)
                time.sleep(0.002)

            def close(self):
                pass

        with (
            patch.object(bridge, 'prepare_local', return_value=model),
            patch('jukebox_audio.PcmOutput', Output),
        ):
            bridge.enqueueFiles(
                [QUrl.fromLocalFile(str(source)), QUrl.fromLocalFile(str(source))]
            )
            self.wait_for(
                lambda: all(row['analysis'] == 'ready' for row in bridge.playlist)
            )
            bridge.setTrackMinutes(1)
            bridge.setSleep(30)
            bridge.playQueued(0)
            cancel = bridge.cancelled
            self.wait_for(lambda: bridge.queue_index == 1, 10000)
            self.assertEqual(len(Output.instances), 1)
            self.assertFalse(cancel.is_set())
            self.assertTrue(bridge.playback['sleepActive'])
            self.assertEqual(bridge.track_minutes, 1)
            bridge.stop()
            self.wait_for(lambda: all(not t.is_alive() for t in bridge.workers))

    def test_normal_crossfade_with_effects_needs_no_timer_or_second_output(self):
        bridge = self.bridge()
        model = self.prepare_model(bridge)
        source = Path(self.temp.name) / 'Teste local.wav'
        from playback_effects import prepare

        effects = dict(enabled=True, speed=85, reverb=25, keep_pitch=False)
        self.assertEqual(prepare(model['cache'], effects), '')
        bridge.setEffects(effects)
        bridge.setParams(45, 35, 80, True)

        class Output:
            instances = []

            def __init__(self, progress):
                self.progress = progress
                self.frames = 0
                self.buffers = []
                self.instances.append(self)

            def write(self, data, cancelled, paused):
                self.frames += len(data) // 4
                self.progress(self.frames)
                time.sleep(0.01)

            def close(self):
                pass

        with (
            patch.object(bridge, 'prepare_local', return_value=model),
            patch('jukebox_audio.PcmOutput', Output),
        ):
            bridge.enqueueFiles(
                [QUrl.fromLocalFile(str(source)), QUrl.fromLocalFile(str(source))]
            )
            self.wait_for(
                lambda: all(row['analysis'] == 'ready' for row in bridge.playlist)
            )
            self.assertEqual(bridge.track_minutes, 0)
            self.assertIsNone(bridge.sleep.deadline)
            bridge.playQueued(0)
            cancel = bridge.cancelled
            self.wait_for(lambda: bridge.queue_index == 1, 10000)
            self.assertEqual(len(Output.instances), 1)
            self.assertFalse(cancel.is_set())
            bridge.stop()
            self.wait_for(lambda: all(not t.is_alive() for t in bridge.workers))

    def test_close_search_keeps_audio_queue_and_timers(self):
        bridge = self.bridge()
        bridge.update_state(playing=True, results=[{'title': 'Found'}])
        bridge.records = [{'title': 'Found'}]
        bridge.playlist = [{'id': 'queued', 'title': 'Queued'}]
        bridge.setSleep(30)
        bridge.setTrackMinutes(5)
        cancelled = bridge.cancelled
        bridge.closeSearch()
        self.assertEqual(bridge.records, [])
        self.assertEqual(bridge.state['results'], [])
        self.assertTrue(bridge.state['playing'])
        self.assertFalse(cancelled.is_set())
        self.assertEqual(len(bridge.playlist), 1)
        self.assertTrue(bridge.playback['sleepActive'])
        self.assertEqual(bridge.track_minutes, 5)

    def test_cancel_search_preserves_playback_and_sleep_timer(self):
        bridge = self.bridge()
        bridge.update_state(playing=True)
        bridge.setSleep(15)
        release = threading.Event()

        def search(*args, **kwargs):
            release.wait(2)
            return {'tracks': []}

        with patch('music_search.search_music', side_effect=search):
            bridge.search('Next')
            self.assertTrue(bridge.state['busy'])
            bridge.cancelOperation()
            release.set()
            self.wait_for(
                lambda: all(not worker.is_alive() for worker in bridge.workers)
            )
        self.assertTrue(bridge.state['playing'])
        self.assertTrue(bridge.playback['sleepActive'])
        self.assertFalse(bridge.cancelled.is_set())
        self.assertEqual(bridge.state['results'], [])

    def test_local_queue_loads_tags_and_cover_before_playback(self):
        import io
        from PIL import Image
        from mutagen.wave import WAVE
        from mutagen.id3 import TIT2, TPE1, TALB, APIC
        from test_jukebox import song

        source = Path(self.temp.name) / 'local.wav'
        song(source)
        cover = io.BytesIO()
        Image.new('RGB', (64, 64), 'red').save(cover, format='PNG')
        audio = WAVE(source)
        audio.add_tags()
        audio.tags.add(TIT2(encoding=3, text=['Track']))
        audio.tags.add(TPE1(encoding=3, text=['Artist']))
        audio.tags.add(TALB(encoding=3, text=['Album']))
        audio.tags.add(
            APIC(
                encoding=3,
                mime='image/png',
                type=3,
                desc='Front',
                data=cover.getvalue(),
            )
        )
        audio.save()
        bridge = self.bridge()
        bridge.enqueueFiles([QUrl.fromLocalFile(str(source))])
        self.wait_for(lambda: bool(bridge.queuedTracks[0].get('cover')))
        entry = bridge.queuedTracks[0]
        self.assertEqual(entry['title'], 'Track')
        self.assertEqual(entry['artist'], 'Artist')
        self.assertEqual(entry['album'], 'Album')
        self.assertTrue(entry['cover'].startswith('data:image/png;base64,'))
        self.assertFalse(bridge.state['playing'])

    def test_local_analysis_and_pcm_controls_use_existing_engine(self):
        bridge = self.bridge()
        self.prepare_model(bridge)

        class Output:
            instances = []

            def __init__(self, progress):
                self.progress = progress
                self.frames = 0
                self.closed = False
                self.instances.append(self)

            def write(self, data, cancelled, paused):
                while paused() and not cancelled():
                    time.sleep(0.005)
                if cancelled():
                    return
                time.sleep(0.008)
                count = len(data) // 4
                self.progress(self.frames + count // 2)
                self.frames += count
                self.progress(self.frames)

            def close(self):
                self.closed = True

        with patch('jukebox_audio.PcmOutput', Output):
            bridge.playPause()
            self.wait_for(lambda: bridge._elapsed > 0)
            self.assertTrue(bridge.state['playing'])
            bridge.playPause()
            self.assertTrue(bridge.state['paused'])
            bridge.playPause()
            self.assertFalse(bridge.state['paused'])
            bridge.seek(3)
            bridge.stop()
            bridge.shutdown()
            self.assertTrue(all(output.closed for output in Output.instances))
            self.assertTrue(all(not worker.is_alive() for worker in bridge.workers))
            self.assertFalse(bridge.state['playing'])

    def test_queue_prepares_serially_and_plays_without_a_second_analysis(self):
        bridge = self.bridge()
        model = self.prepare_model(bridge)
        source = Path(self.temp.name) / 'Teste local.wav'
        release = threading.Event()
        calls = []
        active = [0, 0]

        def prepare_entry(*args):
            calls.append(args[0])
            active[0] += 1
            active[1] = max(active)
            release.wait(2)
            active[0] -= 1
            return dict(model)

        bridge.update_state(playing=True)
        with (
            patch.object(bridge, 'prepare_local', side_effect=prepare_entry),
            patch.object(bridge, 'playPause') as play,
        ):
            bridge.enqueueFiles(
                [QUrl.fromLocalFile(str(source)), QUrl.fromLocalFile(str(source))]
            )
            self.assertTrue(bridge.state['playing'])
            self.assertEqual(len(calls), 1)
            release.set()
            self.wait_for(
                lambda: all(row.get('analysis') == 'ready' for row in bridge.playlist)
            )
            self.assertEqual(len(calls), 2)
            self.assertEqual(active[1], 1)
            bridge.update_state(playing=False)
            bridge.setSleep(30)
            bridge.setTrackMinutes(5)
            bridge.playQueued(0)
            play.assert_called_once()
            self.assertEqual(len(calls), 2)
            self.assertTrue(bridge.playback['sleepActive'])
            self.assertEqual(bridge.track_minutes, 5)

    def test_manual_and_timer_switches_request_overlap_without_stopping_audio(self):
        bridge = self.bridge()
        model = self.prepare_model(bridge)
        bridge.playlist = [
            {'id': 'first', 'analysis': 'ready'},
            {'id': 'second', 'analysis': 'ready'},
        ]
        bridge._prepared = {'first': model, 'second': model}
        bridge.queue_index = 0
        bridge.update_state(playing=True)
        bridge._elapsed = 10
        bridge.setSleep(30)
        bridge.setTrackMinutes(5)
        bridge.setTransitionSeconds(4)
        cancelled = bridge.cancelled
        with patch.object(bridge, 'playPause') as play:
            bridge.nextTrack()
            play.assert_not_called()
            self.assertFalse(cancelled.is_set())
            self.assertEqual(bridge._switch_requests.get(), (str(model['cache']), 4))
            bridge.handle_event(bridge.revision, 'track_started', str(model['cache']))
            self.assertEqual(bridge.queue_index, 1)
            self.assertFalse(cancelled.is_set())
            self.assertTrue(bridge.playback['sleepActive'])
            self.assertEqual(bridge.track_minutes, 5)
            self.assertEqual(bridge.playback_gain(), 1)
        self.assertEqual(
            self.store.clean({'jukebox_transition_seconds': '4'})[
                'jukebox_transition_seconds'
            ],
            4,
        )

    def test_disabled_gradual_requests_zero_overlap(self):
        bridge = self.bridge()
        model = self.prepare_model(bridge)
        bridge.playlist = [{'id': 'next', 'analysis': 'ready'}]
        bridge._prepared = {'next': model}
        bridge.update_state(playing=True)
        bridge.setGradualTransition(False)
        with patch.object(bridge, 'playPause') as play:
            bridge.playQueued(0)
            play.assert_not_called()
            self.assertEqual(bridge._switch_requests.get(), (str(model['cache']), 0))

    def test_timers_pause_and_can_be_disabled_independently(self):
        bridge = self.bridge()
        now = [0.0]
        bridge.sleep.clock = lambda: now[0]
        bridge.update_state(playing=True)
        bridge.setSleep(2)
        bridge.setTrackMinutes(1)
        bridge._elapsed = 30
        now[0] = 30
        bridge.tick_sleep()
        self.assertEqual(bridge.playback['remaining'], 90)
        self.assertEqual(bridge.playback['switchRemaining'], 30)
        bridge.paused.set()
        now[0] = 60
        bridge.tick_sleep()
        self.assertEqual(bridge.playback['remaining'], 90)
        bridge.setTrackMinutes(0)
        self.assertTrue(bridge.playback['sleepActive'])
        bridge.setTrackMinutes(2)
        bridge.setSleep(0)
        self.assertEqual(bridge.track_minutes, 2)

    def test_gradual_preference_persists_and_marker_follows_jump_curve(self):
        bridge = self.bridge()
        bridge.setGradualTransition(False)
        bridge.save_preferences()
        self.assertFalse(self.bridge().playback['gradual'])
        bridge.model = {'neighbors': [[] for _ in range(32)]}
        bridge._beat_index = 4
        bridge._position = 4.95
        bridge._next_index = 20
        bridge._jump_blend = 0.5
        self.assertAlmostEqual(bridge.cursor['x'], 0)
        self.assertAlmostEqual(bridge.cursor['y'], 0)

    def test_qml_popups_resizing_themes_and_clean_shutdown(self):
        from qt_desktop_ui import create_application, close_application

        warnings = []
        old = qInstallMessageHandler(lambda t, c, msg: warnings.append(msg))
        app, engine, bridge = create_application(complete=False)
        window = engine.rootObjects()[0]
        try:
            self.wait(100)
            sidebar = window.findChild(QObject, 'sidebar')
            self.assertIsNotNone(sidebar)
            toggle = window.findChild(QObject, 'sidebarToggle')
            self.assertIsNotNone(toggle)
            toggle_x = toggle.x()
            toggle_width = toggle.width()
            sidebar.setProperty('collapsed', True)
            self.wait_for(lambda: sidebar.width() < 100)
            self.assertEqual(toggle.x(), toggle_x)
            self.assertEqual(toggle.width(), toggle_width)
            sidebar.setProperty('collapsed', False)
            self.wait_for(lambda: sidebar.width() > 200)
            for size in ((1000, 740), (1360, 900)):
                window.resize(*size)
                self.wait(80)
                self.assertFalse(window.grabWindow().isNull())
            for mode in ('Escuro', 'Preto puro', 'Alto contraste', 'Claro'):
                bridge.setAppearance(mode, 'Vermelho', False)
                self.wait(30)
                self.assertEqual(window.color().name(), bridge.palette['bg'])
            workspace = engine.rootContext().contextProperty('workspace')
            from PySide6.QtCore import Qt

            workspace.selectPage('jukebox')
            workspace.setSetting('playback_tab_order', 'Jukebox infinito primeiro')
            self.wait(30)
            tabs = window.findChild(QObject, 'playbackTabsLayout')
            self.assertIsNone(tabs)
            self.assertIsNone(window.findChild(QObject, 'effectsTab'))
            self.assertEqual(workspace.currentPage, 'jukebox')
            workspace.persist()
            self.assertEqual(
                workspace.store.load()['playback_tab_order'],
                'Jukebox infinito primeiro',
            )
            workspace.setSetting('playback_tab_order', 'Efeitos primeiro')
            self.wait(30)
            self.assertIsNone(window.findChild(QObject, 'playbackTabsLayout'))
            workspace.selectPage('effects')
            self.assertEqual(workspace.currentPage, 'jukebox')
            bridge.update_state(
                playing=True, title='Mini player test', artist='Artist', album='Album'
            )
            workspace.selectPage('catalog')
            self.wait(40)
            mini = window.findChild(QObject, 'jukeboxMiniPlayer')
            self.assertTrue(mini.property('visible'))
            self.assertTrue(bridge.state['playing'])
            for size in ((920, 680), (1360, 900)):
                window.resize(*size)
                self.wait(40)
                self.assertGreater(mini.width(), 400)
            from PySide6.QtTest import QTest
            from PySide6.QtCore import QPointF

            target = window.findChild(QObject, 'openJukeboxFromMiniPlayer')
            point = target.mapToScene(QPointF(30, 30)).toPoint()
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
            self.wait(40)
            self.assertEqual(workspace.currentPage, 'jukebox')
            self.assertTrue(bridge.state['playing'])
            timers = window.findChild(QObject, 'jukeboxTimers')
            self.assertIsNotNone(timers)
            QMetaObject.invokeMethod(timers, 'open')
            self.wait(40)
            self.assertTrue(timers.property('opened'))
            QMetaObject.invokeMethod(timers, 'close')
            bridge.update_state(playing=False)
            popup = window.findChild(QObject, 'equalizerPopup')
            self.assertIsNotNone(popup)
            QMetaObject.invokeMethod(popup, 'open')
            self.wait(80)
            self.assertTrue(popup.property('opened'))
            bridge.applyPreset('Rock')
            self.assertEqual(bridge.presetName, 'Rock')
            QMetaObject.invokeMethod(popup, 'close')
            self.wait(30)
        finally:
            close_application(engine, bridge)
            qInstallMessageHandler(old)
        self.assertEqual(warnings, [])

    def test_current_interface_accepts_qt_preferences(self):
        bridge = self.bridge()
        bridge.setAppearance('Claro', 'Vermelho', False)
        bridge.save_preferences()
        from app import App

        app = App(show_welcome=False)
        app.withdraw()
        try:
            self.assertFalse(app.qt_animations.get())
            app.update()
        finally:
            app.destroy()


if __name__ == '__main__':
    unittest.main()
