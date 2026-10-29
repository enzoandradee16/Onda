"""Queue drawer follows the pointer while resizing and remembers its width."""

import os, unittest
import test_qt_playback_queue as fixtures


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt interface')
class QueueResizeTests(unittest.TestCase):
    setUp = fixtures.PlaybackQueueDrawerTests.setUp
    tearDown = fixtures.PlaybackQueueDrawerTests.tearDown
    settle = fixtures.PlaybackQueueDrawerTests.settle

    def test_drag_resizes_live_and_preserves_width_after_reopening(self):
        from PySide6.QtCore import QObject, QPointF, QPoint, Qt
        from PySide6.QtTest import QTest

        self.window.resize(1200, 800)
        self.ws.setOption('jukeboxQueueOpen', True)
        for _ in range(5):
            self.settle()
        drawer = self.window.findChild(QObject, 'jukeboxQueueDrawer')
        handle = drawer.findChild(QObject, 'playbackQueueResizeHandle')
        listing = drawer.findChild(QObject, 'playbackQueueList')
        initial = drawer.property('width')
        list_width = listing.width()
        start = handle.mapToScene(QPointF(4, 120)).toPoint()
        QTest.mousePress(self.window, Qt.LeftButton, Qt.NoModifier, start)
        for delta in (40, 90, 130, 60, -70, 130):
            QTest.mouseMove(self.window, start - QPoint(delta, 0))
            self.settle()
            self.assertAlmostEqual(drawer.property('width'), initial + delta, delta=2)
            self.assertAlmostEqual(listing.width(), list_width + delta, delta=2)
            self.assertTrue(handle.property('pressed'))
        QTest.mouseRelease(
            self.window, Qt.LeftButton, Qt.NoModifier, start - QPoint(130, 0)
        )
        self.settle()
        self.assertAlmostEqual(
            self.ws.settings['playback_queue_width'], initial + 130, delta=2
        )
        self.ws.persist()
        self.assertEqual(
            self.ws.store.load()['playback_queue_width'],
            self.ws.settings['playback_queue_width'],
        )
        self.ws.setOption('jukeboxQueueOpen', False)
        for _ in range(4):
            self.settle()
        self.ws.setOption('jukeboxQueueOpen', True)
        for _ in range(4):
            self.settle()
        self.assertAlmostEqual(drawer.property('width'), initial + 130, delta=2)
        self.window.resize(600, 800)
        self.settle()
        self.assertLessEqual(drawer.property('width'), self.window.width() * 0.95 + 1)

    def test_width_preferences_are_bounded(self):
        from preferences import PreferenceStore

        for requested, expected in ((1, 360), (470, 470), (5000, 900)):
            self.assertEqual(
                PreferenceStore.clean({'playback_queue_width': requested})[
                    'playback_queue_width'
                ],
                expected,
            )
        self.assertNotIn(
            'playback_queue_width',
            PreferenceStore.clean({'playback_queue_width': float('nan')}),
        )
