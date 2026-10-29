import os, unittest
import test_qt_playback_queue as fixtures


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt interface')
class QueueStyleTests(unittest.TestCase):
    setUp = fixtures.PlaybackQueueDrawerTests.setUp
    tearDown = fixtures.PlaybackQueueDrawerTests.tearDown
    settle = fixtures.PlaybackQueueDrawerTests.settle
    seed = fixtures.PlaybackQueueDrawerTests.seed
    drawer = fixtures.PlaybackQueueDrawerTests.drawer

    def test_history_menu_shrinks_to_visible_items_in_each_theme(self):
        from PySide6.QtCore import QObject, QMetaObject

        self.window.show()
        for theme in ('Escuro', 'Claro', 'Preto puro', 'Alto contraste'):
            self.bridge.setAppearance(theme, 'Verde-Água', False)
            self.ws.selectPage('history')
            self.settle()
            menu = self.window.findChild(QObject, 'collectionActionsMenu')
            self.assertIsNotNone(menu)
            QMetaObject.invokeMethod(menu, 'open')
            self.settle()
            short = menu.property('height')
            self.assertGreater(short, 30)
            self.assertLess(short, 65)
            self.assertGreaterEqual(menu.property('width'), 168)
            QMetaObject.invokeMethod(menu, 'close')
            self.ws.selectPage('playlists')
            self.settle()
            QMetaObject.invokeMethod(menu, 'open')
            self.settle()
            self.assertGreater(menu.property('height'), short * 3)
            QMetaObject.invokeMethod(menu, 'close')

    def test_more_actions_opens_below_its_button(self):
        from PySide6.QtCore import QObject, QPointF, Qt
        from PySide6.QtTest import QTest

        self.window.show()
        self.ws.selectPage('playlists')
        self.settle()
        button = self.window.findChild(QObject, 'openCollectionActions')
        QTest.mouseClick(
            self.window,
            Qt.LeftButton,
            Qt.NoModifier,
            button.mapToScene(
                QPointF(button.width() / 2, button.height() / 2)
            ).toPoint(),
        )
        self.settle()
        menu = self.window.findChild(QObject, 'collectionActionsMenu')
        self.assertTrue(menu.property('opened'))
        self.assertIs(menu.property('parent'), button)
        self.assertGreaterEqual(menu.property('y'), button.height())

    def test_history_exports_directly_without_opening_a_menu(self):
        from unittest.mock import patch
        from PySide6.QtCore import QObject, QMetaObject

        self.ws.selectPage('history')
        self.settle()
        button = self.window.findChild(QObject, 'openCollectionActions')
        self.assertEqual(button.property('text'), 'Exportar histórico')
        with patch.object(self.ws, 'settings_file_action') as export:
            QMetaObject.invokeMethod(button, 'clicked')
            export.assert_called_once_with('export_history')
        self.assertFalse(
            self.window.findChild(QObject, 'collectionActionsMenu').property('opened')
        )

    def test_queue_tabs_animate_content_and_indicator_and_respect_animation_setting(
        self,
    ):
        from PySide6.QtCore import QObject

        self.ws.setSetting('qt_animations', True)
        self.ws.setOption('jukeboxQueueOpen', True)
        for _ in range(5):
            self.settle()
        drawer = self.drawer(False)
        tabs = drawer.findChild(QObject, 'playbackQueueTabs')
        indicator = tabs.findChild(QObject, 'queueTabIndicator')
        listing = drawer.findChild(QObject, 'playbackQueueList')
        self.assertGreater(indicator.width(), 10)
        slide = drawer.findChild(QObject, 'queueTabSlide')
        start = indicator.x()
        drawer.setProperty('recent', True)
        self.settle()
        self.assertGreater(slide.property('x'), 0)
        middle = indicator.x()
        self.assertGreater(middle, start)
        self.assertLess(listing.opacity(), 1)
        for _ in range(3):
            self.settle()
        self.assertGreater(indicator.x(), middle)
        self.assertAlmostEqual(listing.opacity(), 1)
        self.assertAlmostEqual(slide.property('x'), 0)
        drawer.setProperty('recent', False)
        self.settle()
        self.assertLess(slide.property('x'), 0)
        for _ in range(3):
            self.settle()
        drawer.setProperty('recent', True)
        for _ in range(4):
            self.settle()
        self.ws.setSetting('qt_animations', False)
        drawer.setProperty('recent', False)
        self.settle()
        self.assertAlmostEqual(indicator.x(), start)
        self.assertAlmostEqual(listing.opacity(), 1)
        self.assertAlmostEqual(slide.property('x'), 0)

    def test_modern_font_is_bundled_and_legacy_can_be_selected_live(self):
        from PySide6.QtGui import QFontDatabase, QFontInfo

        self.assertIn('Inter', QFontDatabase.families())
        self.assertEqual(self.bridge.interfaceFamily, 'Inter')
        self.ws.setSetting('interface_font', 'ONDA Legacy')
        self.settle()
        self.assertEqual(self.bridge.interfaceFamily, 'Segoe UI')
        self.ws.setSetting('interface_font', 'ONDA Modern')
        self.settle()
        self.assertEqual(QFontInfo(self.app.font()).family(), 'Inter')

    def test_drag_moves_only_card_and_keeps_section_heading_in_place(self):
        from PySide6.QtCore import QObject, QPointF

        self.seed()
        self.window.show()
        self.ws.setOption('jukeboxQueueOpen', True)
        self.settle()
        for _ in range(5):
            self.settle()
        drawer = self.drawer(False)
        header = drawer.findChild(QObject, 'playbackQueueSectionTocando agora')

        def visual_handle(item):
            if item.objectName() == 'playbackQueueDrag':
                return item
            for child in item.childItems():
                found = visual_handle(child)
                if found is not None:
                    return found

        handle = visual_handle(drawer.property('contentItem'))
        self.assertIsNotNone(header)
        self.assertIsNotNone(handle)
        self.assertFalse(handle.property('showIndicator'))
        position = header.mapToScene(QPointF(0, 0))
        handle.setProperty('dragging', True)
        handle.setProperty('offsetY', 35)
        self.settle()
        self.assertEqual(header.mapToScene(QPointF(0, 0)), position)
        handle.setProperty('dragging', False)
        handle.setProperty('offsetY', 0)

    def test_search_icon_opens_field_and_escape_closes_without_clearing_queue(self):
        from PySide6.QtCore import QObject, Qt, QPointF
        from PySide6.QtTest import QTest

        self.seed()
        self.window.show()
        self.ws.setOption('jukeboxQueueOpen', True)
        self.settle()
        drawer = self.drawer(False)
        field = drawer.findChild(QObject, 'playbackQueueSearch')
        self.assertFalse(field.property('visible'))
        button = drawer.findChild(QObject, 'togglePlaybackQueueSearch')
        position = button.mapToScene(
            QPointF(button.width() / 2, button.height() / 2)
        ).toPoint()
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, position)
        self.settle()
        self.assertTrue(field.property('visible'))
        field.setProperty('text', 'Test query')
        QTest.keyClick(self.window, Qt.Key_Escape)
        self.settle()
        self.assertFalse(field.property('visible'))
        self.assertEqual(field.property('text'), '')
        self.assertEqual(len(self.bridge.playlist), 3)
        self.assertTrue(drawer.property('opened'))
