"""PC UI summaries, native progress and queue persistence stay bounded."""

from copy import deepcopy
from pathlib import Path
import os
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch
from queue_persistence import QueuePersistence


class QueuePersistenceTests(unittest.TestCase):
    def test_snapshots_are_owned_and_newer_save_finishes_after_older_write(self):
        started = threading.Event()
        release = threading.Event()
        writes = []
        threads = []
        caller = threading.get_ident()

        class Library:
            def save_queue(self, rows):
                threads.append(threading.get_ident())
                if not writes:
                    started.set()
                    release.wait(3)
                writes.append(deepcopy(rows))

        writer = QueuePersistence(Library())
        jobs = [
            dict(
                url='before',
                mode='mp3',
                state='Na fila',
                catalog_record={'artists': ['Artist']},
            )
        ]
        try:
            old = writer.submit(jobs)
            self.assertTrue(started.wait(2))
            jobs[0]['catalog_record']['artists'].append('Changed')
            jobs[0]['url'] = 'after'
            latest = writer.submit(jobs)
            release.set()
            old.result(timeout=3)
            latest.result(timeout=3)
            self.assertEqual(writes[0][0]['catalog_record']['artists'], ['Artist'])
            self.assertEqual(writes[-1][0]['url'], 'after')
            self.assertNotIn(caller, threads)
        finally:
            release.set()
            writer.close()

    def test_write_errors_remain_visible_to_synchronous_caller(self):
        library = Mock()
        library.save_queue.side_effect = OSError('fixture')
        writer = QueuePersistence(library)
        try:
            with self.assertRaisesRegex(OSError, 'fixture'):
                writer.submit([]).result(timeout=3)
        finally:
            writer.close()


class TaskbarTests(unittest.TestCase):
    def test_native_progress_is_sent_only_on_changes_and_retried_after_failure(self):
        from windows_shell import WindowsShell

        shell = WindowsShell.__new__(WindowsShell)
        shell.taskbar = True
        shell.ready = True
        shell.hwnd = 1
        calls = []
        fail = False

        def com(index, arguments):
            def invoke(*values):
                calls.append((index, values))
                return -1 if fail and index == 9 else 0

            return invoke

        shell.com = com
        self.assertTrue(shell.progress(25))
        self.assertEqual(len(calls), 2)
        self.assertTrue(shell.progress(25))
        self.assertEqual(len(calls), 2)
        shell.progress(25, paused=True)
        self.assertEqual(len(calls), 4)
        fail = True
        self.assertFalse(shell.progress(30))
        fail = False
        self.assertTrue(shell.progress(30))
        self.assertEqual(len(calls), 8)
        shell.progress(enabled=False)
        shell.progress(enabled=False)
        self.assertEqual(len(calls), 9)
        shell._progress_signature = None  # Explorer creates a fresh taskbar.
        shell.progress(enabled=False)
        self.assertEqual(len(calls), 10)


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt responsiveness paths')
class DesktopResponsivenessTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture

    setUpClass = classmethod(Fixture.setUpClass.__func__)
    setUp = Fixture.setUp
    tearDown = Fixture.tearDown

    def test_activity_fields_share_one_scan_and_do_not_read_hidden_logs(self):
        class Rows(list):
            scans = 0

            def __iter__(self):
                self.scans += 1
                return super().__iter__()

        class HiddenLogs(list):
            def __getitem__(self, key):
                raise AssertionError('Unrequested logs were copied')

        ws = self.ws
        ws.jobs = Rows(
            dict(id=str(i), state='Na fila', checked=i == 0) for i in range(1000)
        )
        ws.logs = HiddenLogs()
        ws.statusChanged.emit()
        for _ in range(20):
            self.assertEqual(ws.activityValue(ws.statusRevision, 'total'), 1000)
            self.assertEqual(ws.activityValue(ws.statusRevision, 'selected'), 1)
        self.assertEqual(ws.jobs.scans, 1)
        ws.jobs[0]['checked'] = False
        ws.statusChanged.emit()
        self.assertEqual(ws.activityValue(ws.statusRevision, 'selected'), 0)
        self.assertEqual(ws.jobs.scans, 2)
        ws.logs = []

    def test_scheduler_does_not_scan_a_full_queue_when_all_slots_are_busy(self):
        class Rows(list):
            def __iter__(self):
                raise AssertionError('Full scheduler scanned pending jobs')

        ws = self.ws
        ws.jobs = Rows()
        ws.running = True
        ws.manual_queue = True
        ws.settings['concurrent_downloads'] = 1
        ws.active = {'fixture': {}}
        try:
            ws.fill_queue()
        finally:
            ws.active.clear()
            ws.running = False
            ws.jobs = []

    def test_checkpoint_returns_without_waiting_for_disk_and_final_save_is_current(
        self,
    ):
        started = threading.Event()
        release = threading.Event()
        writes = []
        ws = self.ws
        ws.jobs = [
            dict(
                id='fixture',
                url='before',
                folder=str(self.root),
                mode='mp3',
                state='Na fila',
            )
        ]

        def save(rows):
            if not writes:
                started.set()
                release.wait(3)
            writes.append(deepcopy(rows))

        try:
            with patch.object(ws.library, 'save_queue', side_effect=save):
                ws.save_queue(background=True)
                self.assertTrue(started.wait(2))
                ws.jobs[0]['url'] = 'after'
                release.set()
                ws.save_queue()
                self.assertEqual(writes[-1][0]['url'], 'after')
        finally:
            release.set()

    def test_locked_database_does_not_freeze_qt_during_background_checkpoint(self):
        import time
        from PySide6.QtCore import QEventLoop, QTimer

        ws = self.ws
        ws.jobs = [
            dict(
                id='fixture',
                url='https://example.com/audio',
                folder=str(self.root),
                mode='mp3',
                state='Na fila',
            )
        ]
        ticks = []
        timer = QTimer()
        timer.setInterval(16)
        timer.timeout.connect(lambda: ticks.append(time.monotonic()))
        with ws.library.connect() as database:
            database.execute('BEGIN EXCLUSIVE')
            try:
                ws.save_queue(background=True)
                timer.start()
                QTimer.singleShot(300, database.rollback)
                loop = QEventLoop()
                QTimer.singleShot(600, loop.quit)
                loop.exec()
            finally:
                timer.stop()
                database.rollback()
        ws.save_queue()
        self.assertGreater(len(ticks), 15)
        gaps = [b - a for a, b in zip(ticks, ticks[1:])]
        self.assertLess(max(gaps), 0.25)
        self.assertEqual(ws.library.load_queue()[0]['url'], 'https://example.com/audio')
        print('Qt timer gap with locked database: %.1f ms' % (max(gaps) * 1000))

    def test_tool_progress_publishes_status_and_details_in_one_update(self):
        from PySide6.QtTest import QSignalSpy

        ws = self.ws
        ws.generations['prepare_tools'] = 1
        changes = QSignalSpy(ws.statusChanged)
        ws.on_event(
            'task_progress',
            dict(
                action='prepare_tools',
                revision=1,
                event=dict(message='Fixture', done=25, total=100),
            ),
        )
        self.assertEqual(changes.count(), 1)
        self.assertEqual(ws.activityValue(ws.statusRevision, 'tools')['done'], 25)
        self.assertEqual(ws.status, 'Fixture')
