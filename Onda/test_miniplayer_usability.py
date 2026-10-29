import os,unittest
from pathlib import Path
import test_qt_playback_queue as fixtures

@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Qt interface')
class MiniUsabilityTests(unittest.TestCase):
    setUp=fixtures.PlaybackQueueDrawerTests.setUp
    tearDown=fixtures.PlaybackQueueDrawerTests.tearDown
    settle=fixtures.PlaybackQueueDrawerTests.settle

    def test_repeated_expansion_keeps_controls_stable_and_queue_artwork_visible(self):
        from PIL import Image
        from PySide6.QtCore import QObject,QMetaObject,QUrl
        cover=Path(self.temp.name)/'cover.png';Image.new('RGB',(200,200),'blue').save(cover)
        url=QUrl.fromLocalFile(str(cover)).toString()
        self.bridge.playlist=[dict(id=str(i),title=f'Track {i}',artist='Artist',cover=url,record={'cover_url':url},analysis='ready') for i in range(80)]
        self.bridge.queue_index=0;self.bridge.queueChanged.emit();self.bridge.changed.emit()
        mini=self.window.findChild(QObject,'miniPlayer');QMetaObject.invokeMethod(mini,'show')
        for _ in range(4):self.settle()
        play=mini.findChild(QObject,'miniPlayPause');top=play.mapToScene(play.boundingRect().center()).y()
        for mode in ('lyricsVisible','queueVisible','lyricsVisible','queueVisible'):
            mini.setProperty(mode,True)
            for _ in range(5):self.settle()
            self.assertGreaterEqual(mini.height(),450)
            self.assertAlmostEqual(play.mapToScene(play.boundingRect().center()).y(),top,delta=4)
            mini.setProperty(mode,False)
            for _ in range(5):self.settle()
            self.assertEqual(mini.height(),290)
        mini.setProperty('queueVisible',True)
        for _ in range(5):self.settle()
        listing=mini.findChild(QObject,'miniPlayerQueue')
        def find(item):
            if item.objectName()=='miniQueueArtwork':return item
            for child in item.childItems():
                found=find(child)
                if found is not None:return found
        artwork=find(listing)
        self.assertIsNotNone(artwork);self.assertEqual(artwork.property('status'),1)
        mini.grabWindow().save(str(Path.cwd()/'Testes/auditoria-melhorias/miniplayer-expanded-queue.png'))

    def test_wheel_scroll_and_glass_preference(self):
        from PySide6.QtCore import QObject,QMetaObject,QPoint,QPointF,Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication
        from preferences import PreferenceStore
        self.assertIs(self.ws.defaults['translucent_effects'],True)
        self.bridge.playlist=[dict(id=str(i),title=f'Track {i}',artist='Artist') for i in range(80)]
        self.bridge.queueChanged.emit()
        mini=self.window.findChild(QObject,'miniPlayer');QMetaObject.invokeMethod(mini,'show');mini.setProperty('queueVisible',True)
        for _ in range(5):self.settle()
        listing=mini.findChild(QObject,'miniPlayerQueue')
        point=listing.mapToScene(QPointF(listing.width()/2,listing.height()/2))
        event=QWheelEvent(point,mini.mapToGlobal(point.toPoint()).toPointF(),QPoint(),QPoint(0,-120),Qt.NoButton,Qt.NoModifier,Qt.NoScrollPhase,False)
        QApplication.sendEvent(mini,event);self.settle()
        self.assertAlmostEqual(listing.property('contentY'),84,delta=2)
        self.assertTrue(mini.property('scrolling'))
        self.ws.setSetting('translucent_effects',False);self.settle()
        self.assertFalse(mini.property('glassEnabled'))
        backdrop=mini.findChild(QObject,'miniSwirlBackdrop');self.assertFalse(backdrop.property('active'))
        self.ws.persist();self.assertIs(self.ws.store.load()['translucent_effects'],False)
        self.ws.setSetting('translucent_effects',True);self.settle();self.assertTrue(mini.property('glassEnabled'))

    def test_manual_lyrics_scroll_does_not_jump_to_the_current_verse(self):
        from PySide6.QtCore import QObject,QMetaObject,QPoint,QPointF,Qt
        from PySide6.QtGui import QWheelEvent
        from PySide6.QtWidgets import QApplication
        self.bridge.model={'source':'fixture.wav','beats':list(range(301)),'neighbors':[[] for _ in range(300)],'duration':300}
        self.ws._lyric_source='fixture.wav';self.ws._jukebox_lyrics=[(float(i),f'Verse {i}') for i in range(300)]
        first=self.ws.lyricsFrame(True)['lines'];self.assertIs(first,self.ws.lyricsFrame(True)['lines'])
        mini=self.window.findChild(QObject,'miniPlayer');QMetaObject.invokeMethod(mini,'show');mini.setProperty('lyricsVisible',True)
        for _ in range(5):self.settle()
        listing=mini.findChild(QObject,'miniPlayerLyrics')
        point=listing.mapToScene(QPointF(listing.width()/2,listing.height()/2))
        event=QWheelEvent(point,mini.mapToGlobal(point.toPoint()).toPointF(),QPoint(),QPoint(0,-120),Qt.NoButton,Qt.NoModifier,Qt.NoScrollPhase,False)
        QApplication.sendEvent(mini,event);self.settle();position=listing.property('contentY')
        self.assertGreater(position,0)
        self.bridge._position=100
        for _ in range(3):self.settle()
        self.assertAlmostEqual(listing.property('contentY'),position,delta=2)
