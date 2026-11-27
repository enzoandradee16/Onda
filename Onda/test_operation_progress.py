"""Generic tasks share one progress bar instead of global cancel buttons."""

import os, threading, unittest
import test_qt_playback_queue as fixtures


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt interface')
class OperationProgressTests(unittest.TestCase):
    setUp = fixtures.PlaybackQueueDrawerTests.setUp
    tearDown = fixtures.PlaybackQueueDrawerTests.tearDown
    settle = fixtures.PlaybackQueueDrawerTests.settle

    def test_settings_refresh_does_not_show_progress_over_playback(self):
        from PySide6.QtCore import QMetaObject, QObject
        from PySide6.QtTest import QTest
        from unittest.mock import patch

        self.ws.selectPage('jukebox')
        popup = self.window.findChild(QObject, 'settingsPopup')
        progress = self.window.findChild(QObject, 'globalOperationProgress')
        release = threading.Event()

        def perform(*args):
            release.wait(5)
            return {}

        with patch('qt_operations_ui.perform', side_effect=perform):
            try:
                QMetaObject.invokeMethod(popup, 'open')
                QTest.qWait(300)
                self.assertIn('tools_status', self.ws.tasks)
                popup.setProperty('category', 'Desempenho')
                self.settle()
                self.assertIn('cache_report', self.ws.tasks)
                QMetaObject.invokeMethod(popup, 'close')
                self.settle()
                self.assertFalse(progress.property('visible'))
            finally:
                release.set()
                self.settle()

    def test_progress_covers_generic_tasks_without_duplicating_existing_progress(self):
        from PySide6.QtCore import QObject

        progress = self.window.findChild(QObject, 'globalOperationProgress')
        self.assertFalse(progress.property('visible'))
        self.ws.selectPage('effects')
        for action in (
            'playback_input',
            'verify_tools',
            'cache_clear',
            'audio_read',
            'unknown_operation',
        ):
            self.ws.tasks = {action: threading.Event()}
            self.ws.statusChanged.emit()
            self.settle()
            self.assertTrue(progress.property('visible'), action)
            self.assertTrue(progress.property('indeterminate'))
        self.ws.tasks = {'first': threading.Event(), 'second': threading.Event()}
        self.ws.statusChanged.emit()
        self.settle()
        self.assertEqual(
            len(self.window.findChildren(QObject, 'globalOperationProgress')), 1
        )
        for action in ('prepare_tools', 'update_tools'):
            self.ws.tasks = {action: threading.Event()}
            self.ws.statusChanged.emit()
            self.settle()
            self.assertFalse(progress.property('visible'), action)
        self.ws.selectPage('catalog')
        self.ws.tasks = {'search': threading.Event()}
        self.ws.statusChanged.emit()
        self.settle()
        self.assertFalse(progress.property('visible'))
        self.ws.tasks = {}
        self.ws.statusChanged.emit()
        self.settle()
        self.assertFalse(progress.property('visible'))
