import os,unittest
from pathlib import Path
from unittest.mock import patch
import test_qt_playback_queue as fixtures

@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Qt interface')
class QueueAddFromRecentTests(unittest.TestCase):
    setUp=fixtures.PlaybackQueueDrawerTests.setUp
    tearDown=fixtures.PlaybackQueueDrawerTests.tearDown
    settle=fixtures.PlaybackQueueDrawerTests.settle

    def open_recent(self):
        from PySide6.QtCore import QObject
        self.window.resize(1600,900);self.ws.selectPage('jukebox')
        self.bridge.playlist=[dict(id=key,title=key,artist='Artist',analysis='ready') for key in ('past','current','future')]
        self.bridge.queue_index=1;self.bridge._queue_history=['past']
        self.bridge.queueChanged.emit();self.bridge.changed.emit()
        self.ws.setOption('jukeboxQueueOpen',True)
        for _ in range(5):self.settle()
        drawer=self.window.findChild(QObject,'jukeboxQueueDrawer');drawer.setProperty('recent',True)
        panel=self.window.findChild(QObject,'unifiedQueuePanel');panel.setProperty('recent',True)
        self.settle()
        return drawer,panel

    def test_search_add_returns_to_queue_and_does_not_start_playback(self):
        from PySide6.QtCore import QPointF,Qt
        from PySide6.QtTest import QTest
        drawer,panel=self.open_recent()
        record=dict(title='Added song',artists=['Artist'],source_url='https://example.com/added',_details_checked=True)
        self.ws.setOption('jukeboxQueueResults',[record]);self.settle()
        def find(item):
            if item.objectName()=='addQueueSearchResult0':return item
            for child in item.childItems():
                found=find(child)
                if found is not None:return found
        button=find(drawer.property('contentItem'));self.assertIsNotNone(button)
        with patch.object(self.bridge,'prepare_next_queued'),patch.object(self.bridge,'playQueued') as play:
            QTest.mouseClick(self.window,Qt.LeftButton,Qt.NoModifier,button.mapToScene(QPointF(button.width()/2,button.height()/2)).toPoint())
            for _ in range(4):self.settle()
            play.assert_not_called()
        self.assertEqual(len(self.bridge.playlist),4)
        self.assertEqual(self.bridge.playlist[2]['record']['source_url'],record['source_url'])
        self.assertFalse(drawer.property('recent'));self.assertFalse(panel.property('recent'))
        self.assertTrue(drawer.property('opened'));self.assertEqual(self.bridge.queue_index,1)
        self.assertEqual(self.bridge._queue_history,['past']);self.assertFalse(self.bridge.state['playing'])

    def test_files_and_playlist_links_show_added_tracks_but_empty_add_keeps_recent(self):
        from PySide6.QtCore import QUrl
        drawer,panel=self.open_recent()
        source=Path(self.temp.name)/'local.mp3';source.write_bytes(b'fixture')
        with patch.object(self.bridge,'prepare_next_queued'):
            self.bridge.enqueueFiles([QUrl.fromLocalFile(str(source))]);self.settle()
            self.assertFalse(drawer.property('recent'));self.assertEqual(Path(self.bridge.playlist[-1]['source']),source)
            drawer.setProperty('recent',True);panel.setProperty('recent',True)
            self.bridge.enqueueRecords([]);self.settle();self.assertTrue(drawer.property('recent'))
            with patch.object(self.ws,'run_task') as task:
                self.ws.dispatch('playback_queue_search',{'effects':False,'query':'https://example.com/playlist'})
                task.call_args.args[2](dict(is_collection=True,title='Playlist',tracks=[dict(title='Playlist song',source_url='https://example.com/list-song')]))
            self.settle();self.assertFalse(drawer.property('recent'));self.assertFalse(panel.property('recent'))
        self.assertFalse(self.bridge.state['playing']);self.assertEqual(self.bridge.queue_index,1)

    def test_add_uses_result_identity_even_if_its_index_has_changed(self):
        self.open_recent()
        chosen=dict(title='Chosen song',source_url='https://example.com/chosen')
        self.ws.setOption('jukeboxQueueResults',[dict(title='Other song',source_url='https://example.com/other'),chosen])
        with patch.object(self.bridge,'prepare_next_queued'):
            self.ws.dispatch('playback_queue_add',{'effects':False,'index':0,'source':chosen['source_url']})
        self.assertEqual(self.bridge.playlist[2]['record']['title'],'Chosen song')
