"""Download destination remains editable alongside the folder picker."""
import os,unittest
from unittest.mock import patch
import test_qt_playback_queue as fixtures

@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Qt interface')
class DestinationFieldTests(unittest.TestCase):
    setUp=fixtures.PlaybackQueueDrawerTests.setUp
    tearDown=fixtures.PlaybackQueueDrawerTests.tearDown
    settle=fixtures.PlaybackQueueDrawerTests.settle

    def test_destination_picker_manual_path_and_cancel(self):
        from PySide6.QtCore import QObject,QMetaObject,QPointF,Qt
        from PySide6.QtTest import QTest
        popup=self.window.findChild(QObject,'settingsPopup')
        popup.setProperty('category','Downloads');QMetaObject.invokeMethod(popup,'open')
        for _ in range(4):self.settle()
        def find(item,name):
            if item.objectName()==name:return item
            for child in item.childItems():
                found=find(child,name)
                if found is not None:return found
        content=popup.property('contentItem')
        field=find(content,'settingInput_folder');button=find(content,'changeDownloadDestination')
        self.assertTrue(button.property('visible'));self.assertFalse(field.property('readOnly'))
        chosen=str(self.ws.store.path.parent/'chosen')
        with patch('PySide6.QtWidgets.QFileDialog.getExistingDirectory',return_value=chosen) as picker:
            QTest.mouseClick(self.window,Qt.LeftButton,Qt.NoModifier,button.mapToScene(QPointF(button.width()/2,button.height()/2)).toPoint())
            self.settle();picker.assert_called_once()
        self.assertEqual(self.ws.settings['folder'],chosen);self.assertEqual(field.property('text'),chosen)
        manual=str(self.ws.store.path.parent/'manual')
        field.setProperty('text',manual);QMetaObject.invokeMethod(field,'editingFinished');self.settle()
        self.assertEqual(self.ws.settings['folder'],manual)
        with patch('PySide6.QtWidgets.QFileDialog.getExistingDirectory',return_value=''):
            QMetaObject.invokeMethod(button,'clicked');self.settle()
        self.assertEqual(self.ws.settings['folder'],manual)
