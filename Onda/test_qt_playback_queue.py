"""Regression coverage for the shared playback drawer; no network or audio output."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt desktop tests')
class PlaybackQueueDrawerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {'LOCALAPPDATA': self.temp.name, 'ONDA_ALIAS_CACHE_ROOT': self.temp.name},
        )
        self.env.start()
        from qt_desktop_ui import create_application

        self.app, self.engine, self.bridge = create_application(complete=False)
        self.ws = self.engine.workspace
        self.window = self.engine.rootObjects()[0]
        self.settle()

    def tearDown(self):
        from qt_desktop_ui import close_application

        close_application(self.engine, self.bridge)
        self.env.stop()
        self.temp.cleanup()

    def test_manual_tracks_and_files_are_next_before_collection(self):
        from PySide6.QtCore import QUrl

        self.bridge.playlist = [
            dict(id='current', title='Current'),
            dict(id='collection', title='Collection', manual=False),
        ]
        self.bridge.queue_index = 0
        with (
            patch.object(self.bridge, 'prepare_next_queued'),
            patch.object(self.bridge, 'queue_info'),
        ):
            self.bridge.enqueueRecords([dict(title='Manual')])
            self.bridge.enqueueFiles(
                [
                    QUrl.fromLocalFile(str(Path(self.temp.name) / 'one.wav')),
                    QUrl.fromLocalFile(str(Path(self.temp.name) / 'two.wav')),
                ]
            )
        self.assertEqual(
            [row['title'] for row in self.bridge.playlist],
            ['Current', 'Manual', 'one', 'two', 'Collection'],
        )
        self.assertEqual(self.bridge.queue_index, 0)

    def test_end_of_last_track_keeps_lyrics_and_allows_seek(self):
        self.seed()
        bridge = self.bridge
        bridge.queue_index = len(bridge.playlist) - 1
        bridge.model = {'beats': [0.0, 10.0, 20.0], 'duration': 20.0, 'links': 0,
                        'source': 'retained-song.wav', 'neighbors': [[], []], 'cache': 'test-cache'}
        bridge.update_state(ready=True, playing=True)
        self.ws._lyric_source = 'retained-song.wav'
        self.ws._jukebox_lyrics = [(1.0, 'first'), (12.0, 'last'), (20.0, '')]
        bridge.handle_event(bridge.revision, 'finished', None)
        frame = self.ws.lyricsFrame(True)
        self.assertEqual(frame['position'], 20.0)
        self.assertEqual(frame['text'], 'last')
        self.assertEqual(len(frame['lines']), 3)
        self.ws.seekLyrics(10.0, True)
        self.assertEqual(bridge._position, 1)
        self.assertTrue(bridge._state['ready'])

    def test_search_selection_prepares_without_stopping_current_track(self):
        self.seed()
        bridge = self.bridge
        bridge.records = [{'title': 'Search result', 'source_url': 'https://example.com/track'}]
        bridge.refreshSearchResults()
        bridge.update_state(playing=True)
        current_index = bridge.queue_index
        current = bridge.playlist[current_index]
        with patch.object(bridge, 'prepare_next_queued') as prepare, patch.object(bridge, 'stop') as stop:
            bridge.selectResult(0)
            prepare.assert_called_once()
            stop.assert_not_called()
        self.assertIs(bridge.playlist[bridge.queue_index], current)
        selected = bridge.playlist[current_index + 1]
        self.assertEqual(bridge._autoplay_entry, selected['id'])
        self.assertTrue(bridge._state['results'])
        bridge.handle_event(bridge.revision, 'stream_position', 1.0)
        self.assertTrue(bridge._state['results'])
        bridge.queue_index += 1
        bridge.handle_event(bridge.revision, 'stream_position', 1.0)
        self.assertFalse(bridge._state['results'])

    def test_opening_local_file_keeps_stream_alive_until_preparation_finishes(self):
        from PySide6.QtCore import QUrl

        self.bridge.playlist = [dict(id='playing', title='Playing', analysis='ready')]
        self.bridge.queue_index = 0
        self.bridge.model = dict(
            _stream={'url': 'https://example.test/audio'},
            duration=120,
            beats=[0, 120],
            neighbors=[[]],
            title='Playing',
            links=0,
        )
        self.bridge.online.position = 45
        self.bridge._state.update(playing=True, paused=False)
        with (
            patch.object(self.bridge, 'prepare_next_queued'),
            patch.object(self.bridge, 'stop') as stop,
        ):
            self.bridge.openFile(
                QUrl.fromLocalFile(str(Path(self.temp.name) / 'new.wav'))
            )
            stop.assert_not_called()
            self.assertEqual(self.bridge.queue_index, 0)
            self.assertEqual(self.bridge.online.position, 45)
            self.assertEqual(self.bridge._autoplay_entry, self.bridge.playlist[1]['id'])
        self.bridge._state['playing'] = False
        self.bridge._autoplay_entry = None

    def test_upcoming_track_cannot_disappear_behind_current_when_reordered(self):
        self.bridge.playlist = [
            dict(id='playing', title='Playing'),
            dict(id='a', title='A'),
            dict(id='b', title='B'),
        ]
        self.bridge.queue_index = 0
        with patch.object(self.bridge, 'prepare_next_queued'):
            self.bridge.moveQueued(2, -2)
        self.assertEqual([r['id'] for r in self.bridge.playlist], ['playing', 'b', 'a'])
        self.assertEqual(self.bridge.queue_index, 0)

    def test_new_next_prepares_without_waiting_for_an_uncooperative_old_job(self):
        import threading, time
        from jukebox import Cancelled

        gate = threading.Event()
        started = threading.Event()

        def fetch(record, config, cancel, progress):
            if record['title'] == 'Old':
                started.set()
                gate.wait(5)
                raise Cancelled()
            return dict(
                _stream={'url': 'https://example.test/new'},
                duration=120,
                beats=[0, 120],
                neighbors=[[]],
                title='New',
                links=0,
            )

        self.bridge.playlist = [
            dict(
                id=name,
                title=name,
                kind='catalog',
                analysis='pending',
                record=dict(title=title),
            )
            for name, title in [('current', 'Current'), ('old', 'Old'), ('new', 'New')]
        ]
        self.bridge.queue_index = 0
        self.bridge._prepared['current'] = dict(
            _stream={'url': 'https://example.test/current'},
            duration=120,
            beats=[0, 120],
            neighbors=[[]],
            title='Current',
            links=0,
        )
        with (
            patch.object(self.bridge, 'fetch_record', side_effect=fetch),
            patch('online_audio.prefetch_stream'),
        ):
            try:
                self.bridge.prepare_next_queued()
                end = time.monotonic() + 2
                while not started.is_set() and time.monotonic() < end:
                    self.settle()
                self.assertTrue(started.is_set())
                self.bridge.moveQueued(2, -1)
                end = time.monotonic() + 2
                while 'new' not in self.bridge._prepared and time.monotonic() < end:
                    self.settle()
                self.assertIn('new', self.bridge._prepared)
                self.assertEqual(self.bridge.playlist[1]['id'], 'new')
            finally:
                gate.set()
                self.settle()

    def test_stalled_preparation_becomes_retryable_error_without_stopping_current(self):
        import threading

        owner = threading.Event()
        self.bridge.playlist = [
            dict(id='current', title='Current', analysis='ready'),
            dict(id='next', title='Next', analysis='preparing'),
        ]
        self.bridge.queue_index = 0
        self.bridge._state.update(playing=True, paused=False)
        self.bridge._queue_preparing = True
        self.bridge._queue_cancel = {'next': owner}
        self.bridge._queue_current = ('next', owner)
        self.bridge._autoplay_entry = 'next'
        with patch.object(self.bridge, 'prepare_next_queued'):
            self.bridge.expire_queue_preparation()
        self.assertTrue(owner.is_set())
        self.assertEqual(self.bridge.playlist[1]['analysis'], 'error')
        self.assertIsNone(self.bridge._autoplay_entry)
        self.assertFalse(self.bridge._queue_preparing)
        self.assertTrue(self.bridge._state['playing'])
        self.bridge._state['playing'] = False

    def settle(self):
        from PySide6.QtCore import QEventLoop, QTimer

        loop = QEventLoop()
        QTimer.singleShot(80, loop.quit)
        loop.exec()

    def drawer(self, effects):
        from PySide6.QtCore import QObject

        return self.window.findChild(
            QObject, 'effectsQueueDrawer' if effects else 'jukeboxQueueDrawer'
        )

    def call(self, drawer, name, *args):
        from PySide6.QtCore import QMetaObject, Q_ARG

        self.assertTrue(
            QMetaObject.invokeMethod(
                drawer, name, *(Q_ARG('QVariant', x) for x in args)
            )
        )
        self.settle()

    def seed(self):
        self.ws.setOption(
            'effectsQueue',
            [
                {
                    'source': f'{i}.wav',
                    'record': {
                        'title': f'Effect {i}',
                        'artists': ['Artist'],
                        'album': 'Album',
                    },
                    'duration': 120,
                    'cover_url': '',
                }
                for i in range(3)
            ],
        )
        self.ws.setOption('effectsQueueIndex', 1)
        self.bridge.playlist = [
            {
                'id': str(i),
                'title': f'Jukebox {i}',
                'artist': 'Artist',
                'album': 'Album',
                'duration': 120,
                'cover': '',
                'analysis': 'ready',
            }
            for i in range(3)
        ]
        self.bridge.queue_index = 1
        self.bridge.queueChanged.emit()
        self.bridge.changed.emit()
        self.settle()

    def test_collection_playback_uses_all_visible_when_none_are_selected(self):
        rows = [
            dict(title='First', source_url='https://example.com/1', checked=False),
            dict(title='Second', source_url='https://example.com/2', checked=False),
        ]
        with (
            patch.object(self.ws.collection_filter, 'visible_rows', return_value=rows),
            patch.object(self.bridge, 'enqueueRecords', return_value=2) as enqueue,
            patch.object(self.bridge, 'playQueued'),
            patch.object(self.ws, 'selectPage'),
        ):
            self.ws.dispatch('playlist_playback', {})
            self.assertEqual(
                [r['title'] for r in enqueue.call_args.args[0]], ['First', 'Second']
            )
            rows[1]['checked'] = True
            self.ws.dispatch('playlist_playback', {})
            self.assertEqual(
                [r['title'] for r in enqueue.call_args.args[0]], ['Second']
            )

    def test_stream_selection_records_history_and_prepares_successors(self):
        self.bridge.playlist = [
            dict(id='first', title='First'),
            dict(id='second', title='Second'),
        ]
        self.bridge.queue_index = 0
        self.bridge._prepared['second'] = {
            '_stream': {'url': 'https://example.com/audio'},
            'duration': 30,
        }
        with (
            patch.object(self.bridge, 'can_stream', return_value=True),
            patch.object(self.bridge, 'stop'),
            patch.object(self.bridge, 'handle_event'),
            patch.object(self.bridge, 'playPause'),
            patch.object(self.bridge, 'prepare_next_queued') as prepare,
        ):
            self.bridge.playQueued(1)
            prepare.assert_called_once()
        self.assertEqual(self.bridge._queue_history, ['first'])
        self.assertEqual(self.bridge.queue_index, 1)

    def test_both_drawers_open_close_without_changing_tab_or_other_queue(self):
        self.seed()
        # Both playback modes now share one drawer, accessible from any page.
        self.assertIsNone(self.drawer(True))
        for page in ('search', 'images', 'jukebox'):
            self.ws.selectPage(page)
            self.settle()
            key = 'jukeboxQueueOpen'
            drawer = self.drawer(False)
            self.assertIsNotNone(drawer)
            original = self.ws.currentPage
            self.ws.setOption(key, True)
            self.settle()
            self.assertTrue(drawer.property('visible'))
            self.assertEqual(self.ws.currentPage, original)
            self.assertEqual(
                [row['id'] for row in drawer.property('tracks')], ['1', '2']
            )
            from PySide6.QtCore import QMetaObject

            QMetaObject.invokeMethod(drawer, 'close')
            self.settle()
            self.assertFalse(self.ws.values[key])
        self.assertEqual(len(self.bridge.playlist), 3)
        self.assertEqual(len(self.ws.values['effectsQueue']), 3)

    def test_reordering_and_removing_preserve_active_identity_and_isolation(self):
        self.seed()
        self.bridge.moveQueued(1, -1)
        self.settle()
        self.call(self.drawer(False), 'remove', 1)
        self.assertEqual(self.bridge.queue_index, 0)
        self.assertEqual([row['id'] for row in self.bridge.playlist], ['1', '2'])
        self.assertEqual(self.ws.values['effectsQueueIndex'], 1)
        self.assertEqual(len(self.ws.values['effectsQueue']), 3)

    def test_queue_drawer_accepts_selection_clicks_and_shortcuts(self):
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtQuick import QQuickItem
        from PySide6.QtTest import QTest

        self.seed()
        self.bridge.queue_index = -1
        self.bridge.queueChanged.emit()
        self.ws.setOption('jukeboxQueueOpen', True)
        self.window.show()
        QTest.qWait(450)
        view = self.drawer(False).findChild(QQuickItem, 'playbackQueueList')
        children = view.property('contentItem').childItems()
        rows = sorted(
            (row for row in children if row.metaObject().indexOfProperty('selected') >= 0),
            key=lambda row: row.property('index'),
        )
        self.assertEqual(len(rows), 3)

        def click(index, modifier=Qt.NoModifier):
            position = rows[index].mapToScene(QPoint(85, 25)).toPoint()
            QTest.mouseClick(self.window, Qt.LeftButton, modifier, position)

        click(0)
        click(1, Qt.ControlModifier)
        start = rows[0].mapToScene(QPoint(85, 25)).toPoint()
        end = rows[2].mapToScene(QPoint(85, 25)).toPoint()
        QTest.mousePress(self.window, Qt.LeftButton, Qt.NoModifier, start)
        QTest.mouseMove(self.window, end, 20)
        handles = [row.findChild(QQuickItem, 'playbackQueueDrag') for row in rows]
        self.assertGreater(handles[0].property('cardOffset'), 0)
        self.assertEqual(handles[1].property('cardOffset'), handles[0].property('cardOffset'))
        self.assertEqual(handles[2].property('cardOffset'), -2 * (rows[2].height() + view.property('spacing')))
        QTest.mouseRelease(self.window, Qt.LeftButton, Qt.NoModifier, end)
        self.assertEqual([row['id'] for row in self.bridge.playlist], ['2', '0', '1'])
        self.settle()
        rows.sort(key=lambda row: row.property('index'))
        click(0)
        click(2, Qt.ControlModifier)
        self.assertEqual([row.property('selected') for row in rows], [True, False, True])
        click(0, Qt.ShiftModifier)
        self.assertTrue(all(row.property('selected') for row in rows))
        click(1)
        QTest.keyClick(self.window, Qt.Key_A, Qt.ControlModifier)
        self.assertTrue(all(row.property('selected') for row in rows))
        QTest.keyClick(self.window, Qt.Key_Delete)
        self.assertFalse(self.bridge.playlist)

    def test_group_queue_move_remove_and_undo(self):
        self.seed()
        self.bridge.queue_index = 0
        self.bridge.playlist.extend(
            dict(self.bridge.playlist[-1], id=identity) for identity in ('4', '5')
        )
        with patch.object(self.bridge, 'prepare_next_queued') as prepare:
            self.bridge.moveQueuedGroup([2, 4], 1, False)
            self.assertEqual([row['id'] for row in self.bridge.playlist], ['0', '2', '5', '1', '4'])
            self.assertEqual(self.bridge.queue_index, 0)
            prepare.assert_called_once()
            self.bridge.removeQueuedGroup([1, 3])
            self.assertEqual([row['id'] for row in self.bridge.playlist], ['0', '5', '4'])
            self.bridge.undoQueueRemoval()
            self.assertEqual(len(self.bridge.playlist), 5)
            self.assertEqual(self.bridge.playlist[2]['id'], '5')
            self.assertEqual(self.bridge.queue_index, 0)

    def test_play_routes_to_corresponding_transport(self):
        self.seed()
        with (
            patch.object(self.ws, 'play_effects_entry') as effects,
            patch.object(self.bridge, 'playQueued') as jukebox,
        ):
            self.call(self.drawer(False), 'play', 1)
            jukebox.assert_called_once_with(2)
            effects.assert_not_called()

    def test_collapsing_adjustments_keeps_queue_and_playback_parameters(self):
        from PySide6.QtCore import QObject, QMetaObject
        self.ws.selectPage('jukebox')
        self.settle()
        params = dict(self.bridge.playbackParams)
        queue = list(self.bridge.playlist)
        toggle = self.window.findChild(QObject, 'playbackAdjustmentsToggle')
        effects = self.window.findChild(QObject, 'playbackEffectsCard')
        self.assertIsNotNone(toggle)
        QMetaObject.invokeMethod(toggle, 'clicked')
        self.settle()
        self.assertFalse(effects.property('visible'))
        self.assertEqual(params, self.bridge.playbackParams)
        self.assertEqual(queue, self.bridge.playlist)
        QMetaObject.invokeMethod(toggle, 'clicked')
        self.settle()
        self.assertTrue(effects.property('visible'))

    def test_ready_selection_starts_when_previous_audio_worker_has_exited(self):
        cache = Path(self.temp.name) / 'ready-track'
        cache.mkdir()
        (cache / 'analysis.json').write_text('{}', encoding='utf8')
        model = dict(cache=str(cache), title='Selected')
        self.bridge.playlist = [dict(id='selected', title='Selected')]
        self.bridge._prepared['selected'] = model
        self.bridge.model = dict(cache='previous', beats=[0, 20], neighbors=[[]])
        self.bridge._state.update(playing=True, paused=False)
        self.bridge._pcm_worker = None
        with patch.object(self.bridge, 'activate_queued') as activate:
            self.bridge.playQueued(0)
            activate.assert_called_once_with(0, model, auto_play=True)
        self.assertIsNone(self.bridge._switch_pending)
        self.bridge._state['playing'] = False

    def test_retry_from_playback_drawer_keeps_play_intent(self):
        self.seed()
        with patch.object(self.bridge, 'playQueued') as play:
            self.call(self.drawer(False), 'retry', 1)
            play.assert_called_once_with(2)

    def test_clear_only_affects_selected_drawer(self):
        self.seed()
        from PySide6.QtCore import QObject, QMetaObject

        button = self.drawer(False).findChild(QObject, 'clearPlaybackQueue')
        self.assertTrue(button.property('enabled'))
        self.assertTrue(QMetaObject.invokeMethod(button, 'triggered'))
        self.settle()
        self.assertEqual(len(self.bridge.playlist), 0)
        self.assertEqual(self.bridge.queue_index, -1)
        self.assertEqual(len(self.drawer(False).property('tracks')), 0)
        self.assertEqual(len(self.ws.values['effectsQueue']), 3)

    def test_repeat_does_not_change_other_transport(self):
        self.seed()
        self.ws.options.update(effectsQueueIndex=2, effectsRepeat='Todas')
        with patch.object(self.ws, 'play_effects_entry') as play:
            self.ws.advance_effects()
            play.assert_called_once_with(0)
        self.assertEqual(self.bridge.queueRepeat, 'Desativada')
        self.ws.options.update(effectsRepeat='Desativada')
        with patch.object(self.ws, 'play_effects_entry') as play:
            self.ws.advance_effects()
            play.assert_not_called()

    def test_shuffle_is_an_icon_in_each_bar_and_keeps_queues_independent(self):
        from PySide6.QtCore import QObject, QMetaObject

        buttons = [
            item
            for item in self.window.findChildren(QObject)
            if item.property('glyph') == 'shuffle'
        ]
        self.assertTrue(buttons)
        button = buttons[0]
        self.assertEqual(button.property('text'), '')
        self.assertTrue(QMetaObject.invokeMethod(button, 'clicked'))
        self.settle()
        self.assertTrue(self.bridge.queueShuffle)
        self.assertFalse(self.ws.options['effectsShuffle'])
        self.assertTrue(QMetaObject.invokeMethod(button, 'clicked'))
        self.settle()
        self.assertFalse(self.bridge.queueShuffle)

    def test_session_restores_jukebox_identity_position_and_settings_without_playing(
        self,
    ):
        from playback_session import save, restore

        source = Path(self.temp.name) / 'music.wav'
        source.write_bytes(b'fixture')
        cache = Path(self.temp.name) / 'analysis'
        cache.mkdir()
        self.bridge.playlist = [
            dict(id='missing', kind='file', source=str(source.with_name('gone.wav'))),
            dict(id='current', kind='file', source=str(source)),
        ]
        self.bridge.queue_index = 1
        self.bridge.model = dict(
            cache=str(cache),
            title='Restored',
            source=str(source),
            beats=[0, 1, 2, 3],
            neighbors=[[1], [2], [0]],
            links=3,
            duration=3,
        )
        import json
        from jukebox import VERSION

        self.bridge.model['version'] = VERSION
        (cache / 'audio.wav').write_bytes(b'fixture')
        (cache / 'analysis.json').write_text(
            json.dumps(self.bridge.model), encoding='utf-8'
        )
        self.bridge._position = 1
        self.bridge._phase = 0.4
        self.bridge._params = (30.0, 20.0, 75.0, True)
        save(self.ws)
        # An older graph cursor/index must not override the saved source time/identity.
        session_path = self.ws.store.path.with_name('playback-session.json')
        snapshot = json.loads(session_path.read_text(encoding='utf-8'))
        snapshot['jukebox'].update(index=0, position=0, phase=0)
        session_path.write_text(json.dumps(snapshot), encoding='utf-8')
        self.bridge.playlist = []
        self.bridge.queue_index = -1
        self.bridge.model = None
        self.bridge._position = 0
        with (
            patch.object(self.ws.player, 'play') as effects,
            patch.object(self.bridge, 'playPause') as juke,
        ):
            restore(self.ws)
            effects.assert_not_called()
            juke.assert_not_called()
        self.assertEqual(self.bridge.queue_index, 0)
        self.assertEqual(self.bridge.playlist[0]['id'], 'current')
        self.assertAlmostEqual(self.bridge.sourcePosition, 1.4)
        self.assertAlmostEqual(self.bridge.phase, 0.4)
        self.assertFalse(self.bridge.state['playing'])
        self.assertEqual(self.bridge._params, (30.0, 20.0, 75.0, True))

    def test_session_keeps_resume_seconds_when_prepared_cache_is_missing(self):
        from playback_session import save, restore

        source = Path(self.temp.name) / 'resume.wav'
        source.write_bytes(b'fixture')
        cache = Path(self.temp.name) / 'missing-cache'
        model = dict(
            cache=str(cache),
            title='Resume',
            source=str(source),
            beats=[0, 10, 20, 30],
            neighbors=[[1], [2], [0]],
            duration=30,
            links=3,
        )
        self.bridge.playlist = [
            dict(id='resume', kind='file', source=str(source), title='Resume')
        ]
        self.bridge.queue_index = 0
        self.bridge.model = model
        self.bridge._position = 1.5
        self.bridge._phase = 0.5
        save(self.ws)
        self.bridge.model = None
        self.bridge.playlist = []
        self.bridge.queue_index = -1
        with patch.object(self.bridge, 'playPause') as play:
            restore(self.ws)
            play.assert_not_called()
        self.assertEqual(self.bridge.playlist[0]['restore_seconds'], 15)
        self.assertTrue(self.bridge.state['ready'])
        self.assertEqual(self.bridge.state['title'], 'Resume')
        self.assertEqual(self.bridge.sourcePosition, 15)
        self.assertFalse(self.bridge.state['playing'])
        save(self.ws)
        self.bridge.playlist = []
        restore(self.ws)
        self.assertEqual(self.bridge.playlist[0]['restore_seconds'], 15)
        cache.mkdir()
        (cache / 'analysis.json').write_text('{}')
        with (
            patch.object(self.bridge, 'playPause') as play,
            patch.object(self.bridge, 'prepare_next_queued'),
        ):
            self.bridge.activate_queued(0, model)
            play.assert_called_once()
        self.assertEqual(self.bridge.sourcePosition, 15)
        self.assertNotIn('restore_seconds', self.bridge.playlist[0])

    def test_session_recovers_missing_download_from_original_record(self):
        from playback_session import save, restore

        self.bridge.playlist = [
            dict(
                id='recoverable',
                kind='file',
                source=str(Path(self.temp.name) / 'expired.wav'),
                title='Recovered',
                record=dict(
                    title='Recovered',
                    source_url='https://example.com/track',
                    artists=['Artist'],
                    duration_ms=90000,
                ),
                restore_seconds=25,
            )
        ]
        self.bridge.queue_index = 0
        self.bridge.model = None
        save(self.ws)
        restore(self.ws)
        self.assertEqual(self.bridge.playlist[0]['kind'], 'catalog')
        self.assertEqual(self.bridge.sourcePosition, 25)
        self.assertEqual(self.bridge.sourceDuration, 90)
        self.assertEqual(self.bridge.state['artist'], 'Artist')
        self.assertTrue(self.bridge.state['ready'])
        self.assertFalse(self.bridge.state['playing'])

    def test_streaming_session_restores_identity_and_position_without_expired_url(self):
        from playback_session import save, restore

        self.bridge.playlist = [
            dict(
                id='stream',
                kind='catalog',
                title='Stream track',
                artist='Artist',
                duration=120,
                record=dict(
                    title='Stream track',
                    artists=['Artist'],
                    source_url='https://example.com/song',
                    duration_ms=120000,
                ),
            )
        ]
        self.bridge.queue_index = 0
        self.bridge.model = dict(
            _stream=dict(url='https://temporary.example/expired'), duration=120
        )
        self.bridge.online.position = 42
        save(self.ws)
        self.bridge.model = None
        self.bridge.playlist = []
        with patch.object(self.bridge, 'start_worker') as worker:
            restore(self.ws)
            worker.assert_not_called()
        self.assertTrue(self.bridge.state['ready'])
        self.assertEqual(self.bridge.state['title'], 'Stream track')
        self.assertEqual(self.bridge.sourcePosition, 42)
        self.assertEqual(self.bridge.sourceDuration, 120)
        self.assertIsNone(self.bridge.model)
        save(self.ws)
        restore(self.ws)
        self.assertEqual(self.bridge.sourcePosition, 42)
        self.assertEqual(
            self.bridge.playlist[0]['record']['source_url'], 'https://example.com/song'
        )

    def test_restored_track_accepts_seek_before_preparation_and_checkpoints_quickly(
        self,
    ):
        import json
        from PySide6.QtTest import QTest
        from playback_session import restore

        self.bridge.playlist = [
            dict(
                id='resume',
                kind='catalog',
                title='Resume',
                duration=120,
                record=dict(
                    title='Resume',
                    source_url='https://example.com/track',
                    duration_ms=120000,
                ),
                restore_seconds=12,
            )
        ]
        self.bridge.queue_index = 0
        self.bridge.model = None
        self.bridge.seekSeconds(42.25)
        self.assertEqual(self.bridge.sourcePosition, 42.25)
        self.assertTrue(self.ws.session_seek_timer.isActive())
        QTest.qWait(450)
        path = self.ws.store.path.with_name('playback-session.json')
        saved = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(saved['jukebox']['seconds'], 42.25)
        self.assertEqual(saved['jukebox']['current_id'], 'resume')
        self.bridge.playlist = []
        restore(self.ws)
        self.assertEqual(self.bridge.sourcePosition, 42.25)
        self.assertFalse(self.bridge.state['playing'])

    def test_old_local_clock_message_does_not_undo_a_new_seek(self):
        self.bridge.model = dict(
            cache='fixture', beats=[0, 1, 2, 3], neighbors=[[], [], []], duration=3
        )
        old_serial = self.bridge._seek_serial
        self.bridge.seekSeconds(1.75)
        self.bridge.handle_event(
            self.bridge.revision,
            'position',
            dict(
                seek_serial=old_serial,
                index=0,
                phase=0.2,
                elapsed=0.2,
                jumps=0,
                edges=[],
            ),
        )
        self.assertEqual(self.bridge.sourcePosition, 1.75)
        self.bridge.handle_event(
            self.bridge.revision,
            'position',
            dict(
                seek_serial=self.bridge._seek_serial,
                index=1,
                phase=0.8,
                elapsed=1.8,
                jumps=0,
                edges=[],
            ),
        )
        self.assertEqual(self.bridge.sourcePosition, 1.8)

    def test_image_gallery_remains_complete_under_history_search_filter(self):
        for name in ['first.png', 'second.png']:
            self.ws.library.add_history(
                Path(self.temp.name) / name, 'png', 'https://example.com/post'
            )
        self.ws.setOption('historyQuery', 'first')
        self.ws.refresh_history()
        row = self.ws.models['history'].rows[0]
        self.ws.dispatch('history_preview', {'id': row['id']})
        self.assertEqual(
            [r['name'] for r in self.ws.values['imageGallery']], ['first', 'second']
        )

    def test_session_restores_position_without_audio(self):
        from playback_session import save, restore

        source = Path(self.temp.name) / 'music.wav'
        source.write_bytes(b'test')
        self.ws.options.update(
            effectsSource=str(source),
            duration=100,
            position=42,
            effectsQueue=[dict(source=str(source), duration=100, record={})],
            effectsQueueIndex=0,
        )
        save(self.ws)
        self.ws.options.update(effectsSource='', position=0, effectsQueue=[])
        with (
            patch.object(self.ws.player, 'play') as play,
            patch.object(self.bridge, 'playPause') as juke,
        ):
            restore(self.ws)
            play.assert_not_called()
            juke.assert_not_called()
        self.assertEqual(self.ws.options['position'], 42)
        self.assertEqual(self.ws.options['effectsQueueIndex'], 0)
        self.assertFalse(self.ws.options['previewActive'])

    def test_image_gallery_groups_only_same_origin(self):
        for name, source in [
            ('first.png', 'https://example.com/post'),
            ('second.png', 'https://example.com/post'),
            ('other.png', 'https://example.com/other'),
        ]:
            self.ws.library.add_history(Path(self.temp.name) / name, 'png', source)
        self.ws.refresh_history()
        row = next(
            row for row in self.ws.models['history'].rows if row['name'] == 'first'
        )
        self.ws.dispatch('history_preview', {'id': row['id']})
        self.assertEqual(
            {r['name'] for r in self.ws.values['imageGallery']}, {'first', 'second'}
        )
        self.assertEqual(
            self.ws.values['imageGallery'][self.ws.values['imageGalleryIndex']]['name'],
            'first',
        )

    def test_expired_undo_cannot_restore_removed_record(self):
        self.ws.library.add_history(Path(self.temp.name) / 'old.png', 'png')
        row = self.ws.library.history()[0]
        self.ws.dispatch('history_remove', {'id': row['id']})
        self.assertTrue(self.ws.values['historyUndo'])
        self.ws.expire_history_undo()
        self.ws.dispatch('history_undo', {})
        self.assertEqual(self.ws.library.history(), [])
