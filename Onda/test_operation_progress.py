"""Generic tasks share one progress bar instead of global cancel buttons."""

import os, threading, unittest
import test_qt_playback_queue as fixtures


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt interface')
class OperationProgressTests(unittest.TestCase):
    setUp = fixtures.PlaybackQueueDrawerTests.setUp
    tearDown = fixtures.PlaybackQueueDrawerTests.tearDown
    settle = fixtures.PlaybackQueueDrawerTests.settle

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
