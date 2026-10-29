"""Shared source, original analysis, actual FFmpeg effects and one playback UI."""

import json, os, time, unittest, wave
from pathlib import Path
from unittest.mock import patch
import test_jukebox as fixtures


class CombinedAudioTests(unittest.TestCase):
    setUp = fixtures.JukeboxTests.setUp
    tearDown = fixtures.JukeboxTests.tearDown

    def test_prepared_queue_reference_restores_without_decode_and_rejects_deleted_cache(
        self,
    ):
        from playback_session import prepared_reference, restored_prepared

        model = dict(
            self.model,
            cache=str(self.base),
            source=str(self.base / 'audio.wav'),
            media_title='Track',
            media_artist='Artist',
        )
        reference = prepared_reference(model)
        self.assertNotIn('beats', reference)
        restored = restored_prepared(reference)
        self.assertEqual(restored['beats'], model['beats'])
        self.assertEqual(restored['media_title'], 'Track')
        (self.base / 'audio.wav').unlink()
        self.assertIsNone(restored_prepared(reference))

    def test_normal_crossfade_cannot_run_past_outgoing_track_end(self):
        from jukebox_stream import Stream
        from jukebox import RATE

        stream = Stream(str(self.base))
        try:
            for _ in range(31):
                stream.chunk(45, 0, 100, True)
            stream.switch(str(self.base), 10)
            self.assertEqual(stream.fade_frames, RATE // 4)
            frames = 0
            while stream.transitioning:
                frames += len(stream.chunk(45, 0, 100, True)['pcm']) // 4
            self.assertEqual(frames, RATE // 4)
        finally:
            stream.close()

    def test_effects_preserve_original_analysis_and_scale_audio_duration(self):
        from jukebox import Session

        player = Session(self.base)
        original = (self.base / 'analysis.json').read_bytes()
        effect = dict(enabled=True, speed=85, reverb=25, keep_pitch=True)
        try:
            initial = player.chunk(45, 0, 100, True, effects=effect)
            self.assertTrue(initial['effects_pending'])
            deadline = time.monotonic() + 30
            while player.effects.thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertFalse(player.effects.error, player.effects.error)
            player.seek(0)
            pieces = [
                player.chunk(100, 0, 100, True, effects=effect) for _ in range(32)
            ]
            self.assertEqual((self.base / 'analysis.json').read_bytes(), original)
            self.assertAlmostEqual(
                sum(p['seconds'] for p in pieces), 8 / 0.85, delta=0.01
            )
            self.assertTrue(pieces[-1]['finished'])
            self.assertFalse(pieces[0]['finished'])
            self.assertFalse(pieces[0]['effects_pending'])
            player.seek(4)
            player.story_until = 0
            player.since_jump = 32
            player.model['neighbors'][4] = [20]
            player._variation = None
            with (
                patch('jukebox.loop_boundary', return_value=None),
                patch.object(player.random, 'random', return_value=0),
            ):
                part = player.chunk(100, 35, 100, False, effects=effect)
            self.assertTrue(part['jumped'])
            self.assertFalse(part['finished'])
            player.seek(0)
            dry = player.chunk(45, 0, 100, True, effects=dict(enabled=False))
            self.assertIsNone(player.effect_key)
            self.assertAlmostEqual(dry['seconds'], 0.25)
        finally:
            player.close()
            if player.effects.thread:
                player.effects.thread.join(5)

    def test_invalid_effect_values_are_clamped_and_closed_worker_cancels(self):
        from playback_effects import clean, PreparedEffects

        self.assertEqual(clean(dict(enabled=True, speed=999, reverb=-4))['speed'], 150)
        effects = PreparedEffects(self.base)
        effects.configure(dict(enabled=True, speed=80, reverb=20))
        effects.close()
        if effects.thread:
            effects.thread.join(10)
            self.assertFalse(effects.thread.is_alive())


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt interface')
class UnifiedDesktopTests(unittest.TestCase):
    def test_stale_preparation_cannot_replace_current_worker_or_model(self):
        import threading

        old = threading.Event()
        old.set()
        current = threading.Event()
        self.bridge.playlist = [dict(id='track', title='Track', analysis='preparing')]
        self.bridge._queue_cancel['track'] = current
        self.bridge._queue_preparing = True
        with patch.object(self.bridge, 'prepare_next_queued') as prepare:
            self.bridge.handle_event(
                0, 'queue_prepared', dict(id='track', owner=old, error='old failure')
            )
            self.assertIs(self.bridge._queue_cancel['track'], current)
            self.assertTrue(self.bridge._queue_preparing)
            self.assertEqual(self.bridge.playlist[0]['analysis'], 'preparing')
            prepare.assert_not_called()

    def test_cancelled_preparation_returns_to_pending_instead_of_recording_an_error(
        self,
    ):
        import threading

        owner = threading.Event()
        owner.set()
        self.bridge.playlist = [dict(id='track', title='Track', analysis='preparing')]
        self.bridge._queue_cancel['track'] = owner
        self.bridge._queue_preparing = True
        with patch.object(self.bridge, 'prepare_next_queued') as prepare:
            self.bridge.handle_event(
                0, 'queue_prepared', dict(id='track', owner=owner, error='cancelled')
            )
            self.assertEqual(self.bridge.playlist[0]['analysis'], 'pending')
            self.assertFalse(self.bridge._queue_preparing)
            prepare.assert_called_once()

    from test_qt_workspace import NativeDesktopTests as Fixture

    setUpClass = classmethod(Fixture.setUpClass.__func__)
    setUp = Fixture.setUp
    tearDown = Fixture.tearDown
    settle = Fixture.settle

    def test_closing_queue_search_preserves_queue_and_open_drawer(self):
        self.ws.setOption('jukeboxQueueOpen', True)
        self.ws.setOption('jukeboxQueueResults', [dict(title='Search result')])
        self.bridge.playlist = [dict(id='kept', title='Queued song')]
        with patch.object(self.ws, 'cancel_task') as cancel:
            self.ws.dispatch('playback_queue_close_search', {})
        cancel.assert_called_once_with('playback_input')
        self.assertEqual(self.ws.options['jukeboxQueueResults'], [])
        self.assertTrue(self.ws.options['jukeboxQueueOpen'])
        self.assertEqual(len(self.bridge.playlist), 1)

    def test_played_song_leaves_upcoming_but_previous_and_recent_keep_it(self):
        self.bridge.playlist = [
            dict(id=str(i), title=str(i), analysis='pending') for i in range(4)
        ]
        self.bridge.queue_index = 0
        self.bridge.remember_current()
        self.bridge.queue_index = 1
        self.assertEqual([r['id'] for r in self.bridge.upcomingTracks], ['1', '2', '3'])
        self.assertEqual([r['id'] for r in self.bridge.recentTracks], ['0'])
        with patch.object(self.bridge, 'playQueued') as play:
            self.bridge.previousTrack()
        play.assert_called_once_with(0)

    def test_shuffle_restores_original_order_and_does_not_shuffle_again_on_restore(
        self,
    ):
        from playback_session import save, restore

        self.bridge.playlist = [
            dict(
                id=str(i),
                kind='catalog',
                record=dict(title=str(i)),
                title=str(i),
                analysis='pending',
            )
            for i in range(8)
        ]
        self.bridge.queue_index = 0
        with (
            patch.object(self.bridge, 'prepare_next_queued'),
            patch('random.shuffle', side_effect=lambda rows: rows.reverse()) as shuffle,
        ):
            self.bridge.setQueueShuffle(True)
            self.assertEqual(
                [r['id'] for r in self.bridge.playlist],
                ['0', '7', '6', '5', '4', '3', '2', '1'],
            )
            save(self.ws)
            restore(self.ws)
            self.assertEqual(shuffle.call_count, 1)
            self.bridge.setQueueShuffle(False)
            self.assertEqual(
                [r['id'] for r in self.bridge.playlist], list(map(str, range(8)))
            )
            self.assertEqual(self.bridge.queue_index, 0)
            self.bridge.setQueueShuffle(True)
            self.assertEqual(shuffle.call_count, 2)

    def test_manual_addition_takes_priority_without_deleting_playlist(self):
        self.bridge.playlist = [dict(id='a', title='A'), dict(id='b', title='B')]
        self.bridge.queue_index = 0
        with patch.object(self.bridge, 'prepare_next_queued'):
            self.bridge.enqueueRecord(
                dict(title='Manual', artists=[], source_url='https://example.com/song')
            )
        self.assertEqual(
            [r['title'] for r in self.bridge.playlist], ['A', 'Manual', 'B']
        )
        with patch.object(self.bridge, 'prepare_next_queued'):
            self.bridge.clearManualQueue()
        self.assertEqual([r['title'] for r in self.bridge.playlist], ['A', 'B'])
        self.assertEqual(self.bridge.queue_index, 0)

    def test_rapid_next_uses_pending_identity_after_queue_reorder(self):
        models = {}
        for identity in ('a', 'b', 'c'):
            cache = self.root / identity
            cache.mkdir()
            (cache / 'analysis.json').write_text('{}')
            models[identity] = dict(
                cache=str(cache),
                source=str(cache / 'audio.wav'),
                title=identity,
                media_title=identity,
                beats=[0, 1, 2],
                neighbors=[[], []],
                duration=2,
                links=0,
            )
        self.bridge.playlist = [
            dict(id=i, title=i, kind='catalog', record={'title': i}, analysis='ready')
            for i in models
        ]
        self.bridge._prepared = dict(models)
        self.bridge.model = models['a']
        self.bridge.queue_index = 0
        self.bridge.update_state(playing=True)
        with patch.object(self.bridge, 'prepare_next_queued'):
            self.bridge.nextTrack()
            self.assertEqual(self.bridge._switch_pending, 'b')
            self.bridge.nextTrack()
            self.assertEqual(self.bridge._switch_after, 'c')
            self.bridge.moveQueued(2, -2)
            self.bridge.handle_event(
                self.bridge.revision, 'track_started', models['b']['cache']
            )
        self.assertEqual(self.bridge.playlist[self.bridge.queue_index]['id'], 'b')
        self.assertEqual(self.bridge._switch_pending, 'c')

    def test_rapid_next_advances_past_tracks_still_being_prepared(self):
        self.bridge.playlist = [
            dict(id=i, title=i, analysis='pending') for i in ('a', 'b', 'c', 'd', 'e')
        ]
        self.bridge.queue_index = 0
        self.bridge._switch_pending = 'b'
        with patch.object(self.bridge, 'prepare_next_queued'):
            self.bridge.nextTrack()
            self.assertEqual(self.bridge._autoplay_entry, 'c')
            self.bridge.nextTrack()
            self.assertEqual(self.bridge._autoplay_entry, 'd')
            self.bridge.nextTrack()
            self.assertEqual(self.bridge._autoplay_entry, 'e')

    def test_manual_lyrics_offers_choices_while_automatic_keeps_best_match(self):
        self.bridge.model = dict(
            source='song.wav', media_title='Song', media_artist='Artist', duration=200
        )
        original = [(0, 'Current lyric')]
        self.ws._jukebox_lyrics = list(original)
        with (
            patch.object(self.ws, 'run_task') as task,
            patch.object(self.ws, 'present_choice') as chooser,
        ):
            self.ws.dispatch('lyrics_online', {})
            self.assertTrue(task.call_args.args[1]['alternatives'])
            candidate = dict(
                id='42',
                title='Other recording',
                lines=[(0, 'Other lyric')],
                synced=True,
            )
            task.call_args.args[2](dict(candidates=[candidate]))
            self.assertEqual(self.ws._jukebox_lyrics, original)
            chooser.call_args.args[2](dict(cancel=True))
            self.assertEqual(self.ws._jukebox_lyrics, original)
            chooser.call_args.args[2](dict(selected_id='42'))
            self.assertEqual(self.ws._jukebox_lyrics, candidate['lines'])
            self.ws.dispatch('lyrics_online', dict(automatic=True))
            self.assertFalse(task.call_args.args[1]['alternatives'])

    def test_generic_cache_name_never_replaces_catalog_metadata(self):
        record = dict(
            title='One More Time',
            artists=['Daft Punk'],
            album='Discovery',
            cover_url='https://example.org/cover.jpg',
        )
        entry = dict(
            id='track',
            kind='file',
            source='audio.wav',
            title='One More Time',
            record=record,
        )
        self.bridge.playlist = [entry]
        self.bridge.queue_index = 0
        model = dict(
            title='audio',
            media_title='audio',
            source='audio.wav',
            duration=320,
            beats=[0, 1],
            neighbors=[[]],
            links=0,
        )
        with patch.object(self.bridge, 'prepare_next_queued'):
            self.bridge.handle_event(0, 'queue_prepared', dict(id='track', model=model))
        self.assertEqual(entry['title'], 'One More Time')
        self.assertEqual(entry['cover'], record['cover_url'])
        self.bridge.handle_event(
            self.bridge.revision, 'result', self.bridge._prepared['track']
        )
        self.assertEqual(self.bridge.state['title'], 'One More Time')
        self.assertEqual(self.bridge.state['artist'], 'Daft Punk')
        self.assertEqual(self.bridge.state['cover'], record['cover_url'])
        genuine = self.bridge.retain_media_metadata(
            dict(media_title='Different tagged edition'), entry
        )
        self.assertEqual(genuine['media_title'], 'Different tagged edition')

    def test_both_navigation_entries_and_destinations_use_one_queue(self):
        self.ws.selectPage('effects')
        self.assertEqual(self.ws.currentPage, 'jukebox')
        self.ws.models['catalog'].replace(
            [
                dict(
                    title='Track',
                    artists=['Artist'],
                    source_url='https://example.org/a',
                )
            ]
        )
        with patch.object(self.bridge, 'prepare_next_queued'):
            self.ws.dispatch('effects_add', dict(index=0))
        self.assertEqual(len(self.bridge.playlist), 1)
        self.assertEqual(self.ws.options['effectsQueue'], [])
        self.ws.setOption('effectsQueueOpen', True)
        self.assertTrue(self.ws.options['jukeboxQueueOpen'])
        self.ws.setOption('effectsEnabled', True)
        self.ws.setOption('speed', 90)
        self.assertTrue(self.bridge._effects['enabled'])
        self.assertEqual(self.bridge._effects['speed'], 90)

    def test_large_collection_is_added_as_one_bounded_batch(self):
        rows = [
            dict(
                title='Track', artists=['Artist'], source_url=f'https://example.com/{i}'
            )
            for i in range(6000)
        ]
        with (
            patch.object(self.bridge, 'prepare_next_queued') as prepare,
            patch.object(self.bridge, 'queueChanged') as changed,
        ):
            self.assertEqual(self.bridge.enqueueRecords(rows), 5000)
            self.assertEqual(len(self.bridge.playlist), 5000)
            prepare.assert_called_once()
            changed.emit.assert_called_once()
            self.assertEqual(self.bridge.enqueueRecords(rows), 0)

    def test_large_queue_keeps_only_nearby_analysis_in_memory(self):
        self.bridge.playlist = [
            dict(
                id=str(i),
                title='Track',
                kind='file',
                source='track.wav',
                analysis='ready',
            )
            for i in range(5000)
        ]
        self.bridge._prepared = {
            str(i): dict(cache='cache/' + str(i), source='track.wav')
            for i in range(5000)
        }
        self.bridge.queue_index = 0
        with patch.object(self.bridge, 'start_worker') as worker:
            self.bridge.prepare_next_queued()
            worker.assert_not_called()
        self.assertEqual(set(self.bridge._prepared), {'0', '1', '2'})
        self.assertIn('prepared_cache', self.bridge.playlist[-1])

    def test_preparation_setting_changes_the_live_window_without_starting_audio(self):
        self.bridge.playlist = [
            dict(
                id=str(i),
                title='Track',
                kind='file',
                source='track.wav',
                analysis='ready',
            )
            for i in range(10)
        ]
        self.bridge.queue_index = 0
        for ahead in (1, 2, 3, 5):
            self.bridge._prepared = {
                str(i): dict(cache='cache/' + str(i), source='track.wav')
                for i in range(10)
            }
            with (
                patch.object(self.bridge, 'start_worker') as worker,
                patch.object(self.bridge, 'playPause') as play,
            ):
                self.ws.setSetting('playback_prepare_ahead', ahead)
                worker.assert_not_called()
                play.assert_not_called()
            self.assertEqual(len(self.bridge._prepared), ahead + 1)
            self.assertEqual(self.ws.settings['playback_prepare_ahead'], ahead)

    def test_migration_is_once_and_never_starts_audio(self):
        from playback_session import save, restore

        source = self.root / 'source.wav'
        from test_jukebox import song

        song(source)
        self.ws.options.update(
            effectsSource=str(source),
            duration=8,
            position=2,
            effectsQueue=[
                dict(source=str(source), record=dict(title='Old effects'), duration=8)
            ],
        )
        save(self.ws)
        target = self.store.path.with_name('playback-session.json')
        data = json.loads(target.read_text())
        data.pop('unified')
        target.write_text(json.dumps(data))
        with patch.object(self.bridge, 'playPause') as play:
            restore(self.ws)
            self.assertEqual(len(self.bridge.playlist), 1)
            play.assert_not_called()
            save(self.ws)
            restore(self.ws)
            self.assertEqual(len(self.bridge.playlist), 1)
        self.assertEqual(self.ws.options['position'], 2)

    def test_restore_keeps_prepared_tracks_ready_and_advances_interrupted_preparation(
        self,
    ):
        from playback_session import save, restore

        source = self.root / 'queue-source.wav'
        fixtures.song(source)
        cache = self.root / 'prepared-cache'
        cache.mkdir()
        fixtures.song(cache / 'audio.wav')
        model = dict(
            version=1,
            duration=8,
            bpm=120,
            beats=[i * 0.25 for i in range(33)],
            neighbors=[[] for _ in range(32)],
            links=0,
            cache=str(cache),
            source=str(source),
            title='Prepared',
        )
        (cache / 'analysis.json').write_text(json.dumps(model))
        self.bridge.playlist = [
            dict(
                id='ready',
                kind='file',
                source=str(source),
                title='Prepared',
                analysis='ready',
            ),
            dict(
                id='interrupted',
                kind='file',
                source=str(source),
                title='Next',
                analysis='preparing',
            ),
        ]
        self.bridge._prepared = {'ready': model}
        save(self.ws)
        self.bridge._prepared.clear()
        self.bridge.playlist = []
        with (
            patch.object(self.bridge, 'playPause') as play,
            patch.object(self.bridge, 'start_worker') as worker,
        ):
            restore(self.ws)
            self.assertEqual(
                [row['analysis'] for row in self.bridge.playlist], ['ready', 'pending']
            )
            self.bridge.prepare_next_queued()
            self.assertEqual(
                [row['analysis'] for row in self.bridge.playlist],
                ['ready', 'preparing'],
            )
            self.assertEqual(set(self.bridge._queue_cancel), {'interrupted'})
            worker.assert_called_once()
            play.assert_not_called()

    def test_unified_qml_loads_without_errors(self):
        from qt_desktop_ui import create_application, close_application
        from PySide6.QtGui import QFontDatabase

        QFontDatabase.addApplicationFont('C:/Windows/Fonts/segoeui.ttf')
        app, engine, bridge = create_application(complete=False)
        self.assertTrue(engine.rootObjects())
        warnings = []
        engine.warnings.connect(
            lambda values: warnings.extend(v.toString() for v in values)
        )
        try:
            engine.workspace.selectPage('effects')
            ws = engine.workspace
            bridge.setAppearance('Preto puro', 'Verde-Água', False)
            ws.setSetting('pure_black_separators', True)
            source = self.root / 'sample.wav'
            fixtures.song(source)
            from PySide6.QtGui import QImage, QPainter, QColor, QFont
            from PySide6.QtCore import QBuffer, QIODevice

            cover = QImage(256, 256, QImage.Format_RGB32)
            cover.fill(QColor('#112640'))
            painter = QPainter(cover)
            painter.setPen(QColor('#ddba69'))
            painter.drawRect(8, 8, 239, 239)
            painter.setFont(QFont('Segoe UI', 22, QFont.Bold))
            painter.drawText(30, 136, 'STARDUST')
            painter.end()
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            cover.save(buffer, 'PNG')
            bridge.handle_event(
                bridge.revision,
                'result',
                dict(
                    title='Music Sounds Better With You',
                    media_title='Music Sounds Better With You',
                    media_artist='Stardust',
                    album='Music Sounds Better With You',
                    source=str(source),
                    cache=str(self.root),
                    duration=265,
                    beats=list(range(33)),
                    neighbors=[[] for _ in range(32)],
                    links=0,
                    _cover=bytes(buffer.data()),
                ),
            )
            ws._lyric_source = str(source)
            ws._jukebox_lyrics = []
            with patch.object(bridge, 'prepare_next_queued'):
                bridge.enqueueRecord(
                    dict(
                        title='One More Time',
                        artists=['Daft Punk'],
                        album='Discovery',
                        source_url='https://example.org/one',
                    )
                )
                bridge.enqueueRecord(
                    dict(
                        title='Digital Love',
                        artists=['Daft Punk'],
                        album='Discovery',
                        source_url='https://example.org/two',
                    )
                )
            ws.options['effectsEnabled'] = True
            ws.optionsChanged.emit()
            bridge.setParams(45, 35, 80, False)
            for _ in range(4):
                self.settle()
            self.assertEqual(engine.workspace.currentPage, 'jukebox')
            root = engine.rootObjects()[0]
            root.setWidth(1550)
            root.setHeight(950)
            self.settle()
            output = (
                Path(__file__).resolve().parents[1]
                / 'Testes/auditoria-melhorias/unified-pc.png'
            )
            root.grabWindow().save(str(output))

            def find(name):
                def walk(item):
                    if item.objectName() == name:
                        return item
                    for child in item.childItems():
                        found = walk(child)
                        if found is not None:
                            return found

                return walk(root.contentItem())

            from PySide6.QtTest import QTest
            from PySide6.QtCore import Qt, QPointF, QMetaObject
            from PySide6.QtCore import QObject

            equalizer = find('playbackEqualizerButton')
            self.assertIsNotNone(equalizer)
            self.assertEqual(equalizer.property('glyph'), 'equalizer')
            QMetaObject.invokeMethod(equalizer, 'clicked')
            self.settle()
            opened = [
                p
                for p in root.findChildren(QObject, 'equalizerPopup')
                if p.property('opened')
            ]
            self.assertTrue(opened)
            for popup in opened:
                QMetaObject.invokeMethod(popup, 'close')
            self.settle()
            repeat = find('playbackRepeatButton')
            bridge.setQueueRepeat('Desativada')
            for mode in ('Todas', 'Uma', 'Desativada'):
                QMetaObject.invokeMethod(repeat, 'clicked')
                self.settle()
                self.assertEqual(bridge.queueRepeat, mode)
                self.assertEqual(
                    repeat.property('glyph'),
                    'repeat-one' if mode == 'Uma' else 'repeat',
                )
            first = find('unifiedQueueTrack0')
            last = find('unifiedQueueTrack2')
            self.assertIsNotNone(first)
            self.assertIsNotNone(last)
            start = first.mapToScene(
                QPointF(first.width() * 0.7, first.height() / 2)
            ).toPoint()
            end = last.mapToScene(
                QPointF(last.width() * 0.7, last.height() / 2)
            ).toPoint()
            QTest.mousePress(root, Qt.LeftButton, Qt.NoModifier, start)
            QTest.mouseMove(root, end, 40)
            self.settle()
            self.assertTrue(find('unifiedQueueDrag0').property('dragging'))
            self.assertNotEqual(find('unifiedQueueDrag1').property('cardOffset'), 0)
            QTest.mouseRelease(root, Qt.LeftButton, Qt.NoModifier, end)
            self.settle()
            self.assertEqual(
                bridge.playlist[-1]['title'], 'Music Sounds Better With You'
            )
            self.assertEqual(bridge.queue_index, 2)
            root.resize(920, 720)
            self.settle()
            transport = find('jukeboxPlaybackControlsTransport')
            extras = find('unifiedPlaybackExtras')
            transport_end = transport.mapToScene(QPointF(transport.width(), 0)).x()
            extras_start = extras.mapToScene(QPointF(0, 0)).x()
            self.assertLessEqual(transport_end, extras_start)
            root.grabWindow().save(str(output.with_name('unified-pc-compact.png')))
            self.assertFalse([w for w in warnings if 'Error' in w], warnings)
        finally:
            close_application(engine, bridge)
