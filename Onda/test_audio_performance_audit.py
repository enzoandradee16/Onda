"""Audio work is bounded, bit-exact and independent of network read jitter."""

from array import array
import threading
import os
import unittest
from unittest.mock import Mock, patch

from online_audio import NetworkAudio, ReadAheadAudio
from jukebox_equalizer import Equalizer, gain_table


class EqualizerLookupTests(unittest.TestCase):
    def test_all_signed_samples_match_original_rounding_and_clipping(self):
        raw = array('h', range(-32768, 32768))
        for gain in (0, 0.25, 0.5011872336272722, 0.75, 1.75, 4):
            equalizer = Equalizer()
            equalizer.gain = gain
            expected = array(
                'h', (max(-32768, min(32767, round(x * gain))) for x in raw)
            )
            self.assertEqual(equalizer.process(raw.tobytes()), expected.tobytes())
        self.assertLessEqual(gain_table.cache_info().currsize, 8)


class ReadAheadTests(unittest.TestCase):
    def test_preserves_order_end_and_read_errors(self):
        reader = Mock()
        reader.read.side_effect = [b'a', b'b', b'']
        buffered = ReadAheadAudio(reader, blocks=2)
        try:
            self.assertEqual(
                [buffered.read() for _ in range(4)], [b'a', b'b', b'', b'']
            )
        finally:
            buffered.close()
        self.assertFalse(buffered.thread.is_alive())
        reader = Mock()
        reader.read.side_effect = [b'a', ValueError('fixture')]
        buffered = ReadAheadAudio(reader)
        try:
            self.assertEqual(buffered.read(), b'a')
            with self.assertRaisesRegex(ValueError, 'fixture'):
                buffered.read()
            self.assertEqual(buffered.read(), b'')
        finally:
            buffered.close()

    def test_reserve_can_play_while_network_is_blocked_and_cancel_unblocks_it(self):
        blocked = threading.Event()
        release = threading.Event()

        class Reader:
            count = 0

            def read(self):
                self.count += 1
                if self.count <= 3:
                    return bytes([self.count])
                blocked.set()
                release.wait(3)
                return b''

            def cancel(self):
                release.set()

            def close(self):
                release.set()

        buffered = ReadAheadAudio(Reader(), blocks=3)
        try:
            self.assertTrue(blocked.wait(2))
            self.assertEqual(
                [buffered.read() for _ in range(3)], [b'\x01', b'\x02', b'\x03']
            )
            self.assertFalse(release.is_set())
        finally:
            buffered.close()
        self.assertFalse(buffered.thread.is_alive())

    def test_full_reserve_is_bounded_and_cancellation_stops_producer(self):
        calls = []
        enough = threading.Event()
        reader = Mock()

        def read():
            calls.append(1)
            if len(calls) == 3:
                enough.set()
            return b'x' * 17640

        reader.read.side_effect = read
        buffered = ReadAheadAudio(reader, blocks=2)
        try:
            self.assertTrue(enough.wait(2))
            self.assertLessEqual(len(calls), 3)
            self.assertLessEqual(buffered.blocks.qsize(), 2)
        finally:
            buffered.close()
        self.assertFalse(buffered.thread.is_alive())
        self.assertEqual(buffered.read(), b'')

    def test_network_seek_is_an_input_seek(self):
        with (
            patch('online_audio.subprocess.Popen') as process,
            patch('audio_tools.executable', return_value='ffmpeg'),
        ):
            reader = NetworkAudio(
                dict(url='https://example.com/fixture.m4a'), start=123
            )
            try:
                command = process.call_args.args[0]
                self.assertLess(command.index('-ss'), command.index('-i'))
                self.assertEqual(command[command.index('-ss') + 1], '123.0')
            finally:
                reader.close()


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt history work')
class VisibleHistoryTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture

    setUpClass = classmethod(Fixture.setUpClass.__func__)
    setUp = Fixture.setUp
    tearDown = Fixture.tearDown

    def test_history_loads_only_requested_cards_in_bounded_batches(self):
        rows = [
            dict(
                id=i + 1,
                path=str(self.root / (str(i) + '.mp3')),
                name='Track',
                mode='mp3',
                source='',
                date='2026-11-01',
            )
            for i in range(1000)
        ]
        with (
            patch.object(self.ws.library, 'history', return_value=rows),
            patch.object(self.ws, 'run_task') as run,
        ):
            self.ws.selectPage('history')
            self.assertEqual(self.ws.models['history'].count, 1000)
            run.assert_not_called()
            for identity in range(1, 21):
                self.ws.request_history_details(identity)
            self.ws.history_timer.stop()
            self.ws.flush_history_details()
            self.assertEqual(len(run.call_args.args[1]['rows']), 16)
            self.assertEqual(len(self.ws.history_requests), 4)
            self.ws.history_details_loaded(
                [
                    dict(
                        id=1,
                        title='Loaded',
                        artist='Artist',
                        album='Album',
                        cover_url='',
                    )
                ]
            )
            self.assertTrue(self.ws.models['history'].rows[0]['_details_checked'])
            self.ws.request_history_details(1)
            self.assertNotIn(1, self.ws.history_requests)

    def test_background_metadata_does_not_block_closing_but_exports_still_do(self):
        cancel = threading.Event()
        self.ws.tasks['history_details'] = cancel
        self.ws.background_tasks.add('history_details')
        with (
            patch('qt_workspace_ui.QGuiApplication.exit') as exit_app,
            patch.object(self.ws, 'notify') as notice,
        ):
            self.ws.requestClose(True)
            self.assertTrue(cancel.is_set())
            exit_app.assert_called_once_with(0)
            notice.assert_not_called()
        self.ws.tasks['convert'] = threading.Event()
        with (
            patch('qt_workspace_ui.QGuiApplication.exit') as exit_app,
            patch.object(self.ws, 'notify') as notice,
        ):
            self.ws.requestClose(True)
            exit_app.assert_not_called()
            notice.assert_called_once()

    def test_leaving_history_cancels_unneeded_metadata(self):
        self.ws._page = 'history'
        cancel = threading.Event()
        self.ws.tasks['history_details'] = cancel
        self.ws.background_tasks.add('history_details')
        self.ws.history_requests[1] = dict(id=1, path='fixture.mp3')
        self.ws.selectPage('catalog')
        self.assertTrue(cancel.is_set())
        self.assertEqual(self.ws.history_requests, {})

    def test_progress_updates_each_card_once_and_keeps_indexes_after_reorder(self):
        from PySide6.QtTest import QSignalSpy

        rows = [dict(id=str(i), percent=0, download_detail='') for i in range(1000)]
        self.ws.jobs = [
            dict(
                id=row['id'],
                state='Em andamento',
                percent=0,
                url='https://example.com/audio',
            )
            for row in rows
        ]
        for name in ('queue', 'links'):
            self.ws.models[name].replace(rows)
        spies = [
            QSignalSpy(self.ws.models[name].dataChanged) for name in ('queue', 'links')
        ]
        with patch.object(self.ws, 'save_queue'):
            self.ws.on_event('999', dict(type='progress', downloaded=50, total=100))
        self.assertEqual([spy.count() for spy in spies], [1, 1])
        for name in ('queue', 'links'):
            model = self.ws.models[name]
            self.assertEqual(model.rows[model.index_for_id('999')]['percent'], 50)
            model.replace(list(reversed(model.rows)))
            self.assertEqual(model.index_for_id('999'), 0)
            model.update(0, id='changed')
            self.assertEqual(model.index_for_id('999'), -1)
            self.assertEqual(model.index_for_id('changed'), 0)

    def test_bulk_model_changes_use_ranges_and_preserve_existing_selection(self):
        from qt_models_ui import RowsModel
        from PySide6.QtCore import QPersistentModelIndex
        from PySide6.QtTest import QSignalSpy

        model = RowsModel()
        inserted = QSignalSpy(model.rowsInserted)
        removed = QSignalSpy(model.rowsRemoved)
        rows = [dict(id=str(i)) for i in range(5000)]
        model.replace(rows)
        self.assertEqual(inserted.count(), 1)
        selected = QPersistentModelIndex(model.index(2500))
        model.replace(rows + [dict(id='next')])
        self.assertEqual(inserted.count(), 2)
        self.assertTrue(selected.isValid())
        model.replace([rows[0], rows[2500], rows[-1]])
        self.assertEqual(model.index_for_id('2500'), 1)
        self.assertEqual(selected.row(), 1)
        self.assertLessEqual(removed.count(), 3)
