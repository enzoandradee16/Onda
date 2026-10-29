"""Desktop category order controls operate on the same model as the sidebar."""

import os, unittest
import test_qt_playback_queue as fixtures


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt interface')
class NavigationGroupTests(unittest.TestCase):
    setUp = fixtures.PlaybackQueueDrawerTests.setUp
    tearDown = fixtures.PlaybackQueueDrawerTests.tearDown
    settle = fixtures.PlaybackQueueDrawerTests.settle

    def test_settings_category_buttons_reorder_the_sidebar(self):
        from PySide6.QtCore import QObject, QMetaObject, QPointF, Qt
        from PySide6.QtTest import QTest

        popup = self.window.findChild(QObject, 'settingsPopup')
        popup.setProperty('category', 'Aparência')
        QMetaObject.invokeMethod(popup, 'open')
        for _ in range(4):
            self.settle()

        def find_button(item):
            if item.objectName() == 'moveCategoryUp_tools':
                return item
            for child in item.childItems():
                found = find_button(child)
                if found is not None:
                    return found

        button = find_button(popup.property('contentItem'))
        self.assertIsNotNone(button)
        self.assertTrue(button.property('enabled'))
        ancestor = button.parentItem()
        while ancestor is not None:
            if ancestor.metaObject().indexOfProperty('contentY') >= 0:
                y = button.mapToItem(ancestor, QPointF(0, 0)).y() + ancestor.property(
                    'contentY'
                )
                ancestor.setProperty('contentY', max(0, y - ancestor.height() / 2))
                break
            ancestor = ancestor.parentItem()
        self.settle()
        QTest.mouseClick(
            self.window,
            Qt.LeftButton,
            Qt.NoModifier,
            button.mapToScene(
                QPointF(button.width() / 2, button.height() / 2)
            ).toPoint(),
        )
        self.settle()
        self.assertEqual(
            [row['groupKey'] for row in self.ws.navigation if row.get('group')],
            ['tools', 'library'],
        )
        button = find_button(popup.property('contentItem'))
        self.assertFalse(button.property('enabled'))
