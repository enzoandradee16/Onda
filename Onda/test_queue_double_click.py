import os,unittest
from unittest.mock import patch
import test_qt_playback_queue as fixtures

@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Qt interface')
class QueueDoubleClickTests(unittest.TestCase):
    setUp=fixtures.PlaybackQueueDrawerTests.setUp
    tearDown=fixtures.PlaybackQueueDrawerTests.tearDown
    settle=fixtures.PlaybackQueueDrawerTests.settle

    def find(self,item,name):
        if item.objectName()==name:return item
        for child in item.childItems():
            found=self.find(child,name)
            if found is not None:return found

    def test_only_double_click_switches_song_in_all_three_playback_queues(self):
        from PySide6.QtCore import QObject,QMetaObject,QPointF,Qt
        from PySide6.QtTest import QTest
        self.window.resize(1600,900);self.ws.selectPage('jukebox')
        self.bridge.playlist=[dict(id=str(i),title=f'Track {i}',artist='Artist',analysis='ready') for i in range(4)]
        self.bridge.queue_index=0;self.bridge.queueChanged.emit();self.bridge.changed.emit()
        for _ in range(4):self.settle()
        drawer=self.window.findChild(QObject,'jukeboxQueueDrawer')
        mini=self.window.findChild(QObject,'miniPlayer')
        for kind in ('inline','drawer','mini'):
            if kind=='inline':
                host=self.window;root=self.window.contentItem();name='unifiedQueueTrack1'
            elif kind=='drawer':
                self.ws.setOption('jukeboxQueueOpen',True)
                for _ in range(5):self.settle()
                host=self.window;root=drawer.property('contentItem');name='playbackQueueTrack1'
            else:
                self.ws.setOption('jukeboxQueueOpen',False)
                QMetaObject.invokeMethod(mini,'show');mini.setProperty('queueVisible',True)
                for _ in range(5):self.settle()
                host=mini;root=mini.contentItem();name='miniQueueTrack1'
            row=self.find(root,name);self.assertIsNotNone(row,kind)
            point=row.mapToScene(QPointF(120,row.height()/2)).toPoint()
            with patch.object(self.bridge,'playQueued') as play:
                QTest.mouseClick(host,Qt.LeftButton,Qt.NoModifier,point);self.settle();play.assert_not_called()
                QTest.qWait(self.app.styleHints().mouseDoubleClickInterval()+30)
                QTest.mouseDClick(host,Qt.LeftButton,Qt.NoModifier,point);self.settle()
                play.assert_called_once_with(1)
