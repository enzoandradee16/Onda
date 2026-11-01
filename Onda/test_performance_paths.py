"""Performance boundaries preserve identity, latest state and lightweight clocks."""

import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from session_writer import SessionWriter


class SessionWriterTests(unittest.TestCase):
    def test_encoding_is_off_caller_thread_and_latest_snapshot_wins(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'session.json'
            writer = SessionWriter(target)
            caller = threading.get_ident()
            threads = []
            original = json.dumps

            def encode(*args, **kwargs):
                threads.append(threading.get_ident())
                return original(*args, **kwargs)

            try:
                with patch('session_writer.json.dumps', side_effect=encode):
                    for index in range(50):
                        writer.submit(dict(position=index))
                    writer.submit(dict(position=99)).result(timeout=5)
                self.assertEqual(json.loads(target.read_text())['position'], 99)
                self.assertTrue(threads)
                self.assertNotIn(caller, threads)
                self.assertFalse(list(Path(folder).glob('*.tmp')))
            finally:
                writer.close()


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt performance paths')
class ModelPermutationTests(unittest.TestCase):
    def test_large_shuffle_preserves_persistent_indexes_without_reset(self):
        from qt_models_ui import RowsModel
        from PySide6.QtCore import QPersistentModelIndex
        from PySide6.QtTest import QSignalSpy

        model = RowsModel()
        rows = [dict(id=str(i)) for i in range(5000)]
        model.replace(rows)
        selected = QPersistentModelIndex(model.index(123))
        resets = QSignalSpy(model.modelReset)
        layouts = QSignalSpy(model.layoutChanged)
        model.replace(list(reversed(rows)))
        self.assertEqual(resets.count(), 0)
        self.assertEqual(layouts.count(), 1)
        self.assertEqual(selected.row(), 5000 - 124)
        self.assertEqual(model.rows[selected.row()]['id'], '123')


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt lyric clock')
class LyricsClockTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture

    setUpClass = classmethod(Fixture.setUpClass.__func__)
    setUp = Fixture.setUp
    tearDown = Fixture.tearDown

    def test_clock_does_not_transfer_document_and_revision_changes_only_with_lyrics(
        self,
    ):
        self.ws._lyric_source = ''
        self.ws._jukebox_lyrics = [(0.0, 'First'), (1.0, 'Second')]
        first = self.ws.lyricsClock(True)
        second = self.ws.lyricsClock(True)
        self.assertNotIn('lines', first)
        self.assertEqual(first['revision'], second['revision'])
        self.assertEqual(len(self.ws.lyricsDocument()), 2)
        self.ws._jukebox_lyrics = [(0.0, 'Changed')]
        changed = self.ws.lyricsClock(True)
        self.assertGreater(changed['revision'], first['revision'])


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt queue performance')
class PlaybackQueueProjectionTests(unittest.TestCase):
    def test_large_embedded_artwork_is_referenced_and_native_roles_survive_shuffle(
        self,
    ):
        import base64
        from qt_queue_rows_ui import presentation_rows
        from qt_models_ui import QueueRowsModel
        from PySide6.QtCore import Qt, QPersistentModelIndex

        cover = 'data:image/png;base64,' + base64.b64encode(b'x' * 1000000).decode()
        rows = [
            dict(
                id=str(i),
                title='Track',
                cover=cover,
                record=dict(cover_url=cover, unused='x' * 1000),
                group='Next',
            )
            for i in range(994)
        ]
        projected = presentation_rows(rows)
        self.assertLess(len(json.dumps(projected)), 500000)
        self.assertEqual(
            Path(projected[0]['cover'].removeprefix('file:///')).read_bytes(),
            b'x' * 1000000,
        )
        model = QueueRowsModel()
        model.setRows(projected)
        selected = QPersistentModelIndex(model.index(7))
        model.setRows(list(reversed(projected)))
        self.assertEqual(model.data(selected, Qt.UserRole + 1)['id'], '7')
        self.assertEqual(model.data(selected, Qt.UserRole + 2), 'Next')
        self.assertNotIn('unused', model.data(selected, Qt.UserRole + 1)['record'])


class SessionEncodingTests(unittest.TestCase):
    def test_position_checkpoints_reuse_queue_encoding_and_keep_valid_json(self):
        with tempfile.TemporaryDirectory() as folder:
            writer = SessionWriter(Path(folder) / 'session.json')
            rows = [dict(id='1', title='日本語', cover='x' * 1000000)]
            first = dict(version=1, jukebox=dict(queue=rows, seconds=1))
            try:
                writer.submit(first).result(timeout=5)
                encoded_queue = writer._queue_json
                second = dict(version=1, jukebox=dict(queue=rows, seconds=2))
                writer.submit(second).result(timeout=5)
                self.assertIs(encoded_queue, writer._queue_json)
                self.assertEqual(
                    json.loads(writer.target.read_text(encoding='utf-8')), second
                )
                changed = dict(jukebox=dict(queue=[dict(id='2')]))
                writer.submit(changed).result(timeout=5)
                self.assertEqual(json.loads(writer.target.read_text()), changed)
            finally:
                writer.close()


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt performance paths')
class QueueCacheTests(unittest.TestCase):
    from test_qt_jukebox import QtJukeboxTests as Fixture

    setUpClass = classmethod(Fixture.setUpClass.__func__)
    setUp = Fixture.setUp
    tearDown = Fixture.tearDown
    bridge = Fixture.bridge

    def test_queue_presentations_are_reused_until_queue_changes(self):
        from qt_jukebox_ui import JukeboxBridge

        bridge = self.bridge()
        try:
            bridge.playlist = [dict(id='1', title='Track', record={})]
            first = bridge.visibleQueuedTracks
            self.assertIs(first, bridge.visibleQueuedTracks)
            bridge.playlist[0]['title'] = 'Updated'
            bridge.queueChanged.emit()
            self.assertEqual(bridge.visibleQueuedTracks[0]['title'], 'Updated')
            self.assertIsNot(first, bridge.visibleQueuedTracks)
            old_cancel = bridge._effect_prepare_cancel
            bridge.prewarm_effects()
            self.assertTrue(old_cancel.is_set())
        finally:
            bridge.shutdown()


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt performance paths')
class PlaylistBatchTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture

    setUpClass = classmethod(Fixture.setUpClass.__func__)
    setUp = Fixture.setUp
    tearDown = Fixture.tearDown

    def test_playlist_download_queue_is_published_and_saved_once(self):
        ws = self.ws
        records = [
            dict(
                title='Track ' + str(i),
                artists=['Artist'],
                source_url='https://www.deezer.com/track/' + str(i + 1),
            )
            for i in range(300)
        ]
        ws.settings['detect_duplicates'] = False
        with (
            patch.object(ws, 'refresh_queue') as refresh,
            patch.object(ws, 'save_queue') as save,
            patch.object(ws, 'notify') as notify,
            patch.object(ws, 'config', wraps=ws.config) as config,
        ):
            added = ws.enqueue_tracks(records)
            self.assertEqual(len(added), 300)
            refresh.assert_called_once()
            save.assert_called_once()
            notify.assert_called_once()
            config.assert_called_once()

    def test_batch_keeps_duplicate_protection_and_flushes_partial_input(self):
        ws = self.ws
        ws.settings['detect_duplicates'] = True
        row = dict(
            title='Track',
            artists=['Artist'],
            source_url='https://www.deezer.com/track/1',
        )
        with (
            patch.object(ws, 'refresh_queue') as refresh,
            patch.object(ws, 'save_queue') as save,
        ):
            self.assertEqual(len(ws.enqueue_tracks([row, row])), 1)
            refresh.assert_called_once()
            save.assert_called_once()
        with (
            patch.object(ws, 'refresh_queue') as refresh,
            patch.object(ws, 'save_queue') as save,
        ):
            with self.assertRaises(KeyError):
                ws.enqueue_tracks(
                    [dict(row, source_url='https://www.deezer.com/track/2'), {}]
                )
            refresh.assert_called_once()
            save.assert_called_once()
            self.assertEqual(len(ws.jobs), 2)
