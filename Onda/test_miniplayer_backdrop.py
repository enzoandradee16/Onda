import io,os,unittest
from pathlib import Path
import test_qt_playback_queue as fixtures

@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Qt interface')
class MiniBackdropTests(unittest.TestCase):
    setUp=fixtures.PlaybackQueueDrawerTests.setUp
    tearDown=fixtures.PlaybackQueueDrawerTests.tearDown
    settle=fixtures.PlaybackQueueDrawerTests.settle

    def test_temporary_artwork_failure_is_not_cached(self):
        from unittest.mock import patch
        from PIL import Image
        from qt_backdrop_ui import blurred_artwork
        stream=io.BytesIO();Image.new('RGB',(16,16),'red').save(stream,'PNG')
        url='https://example.invalid/transient-artwork.png'
        blurred_artwork.cache_clear()
        with patch('tagging.fetch_cover',side_effect=[None,(stream.getvalue(),'image/png')]) as fetch:
            with self.assertRaises(OSError):blurred_artwork(url)
            self.assertTrue(blurred_artwork(url))
            self.assertEqual(fetch.call_count,2)

    def test_background_is_blurred_at_full_resolution(self):
        from PIL import Image,ImageDraw
        from qt_backdrop_ui import blurred_artwork
        source=Path(self.temp.name)/'blocks.png'
        image=Image.new('RGB',(124,124),'black');draw=ImageDraw.Draw(image)
        draw.rectangle((62,0,123,123),fill='white');image.save(source)
        result=Image.open(io.BytesIO(blurred_artwork(str(source))))
        self.assertEqual(result.size,(768,768))
        self.assertGreater(result.getpixel((370,384))[0],30)
        self.assertLess(result.getpixel((398,384))[0],225)

    def test_swirl_changes_rendered_pixels_and_stops_when_hidden(self):
        from PIL import Image,ImageDraw
        from PySide6.QtCore import QObject,QMetaObject,QUrl
        source=Path(self.temp.name)/'cover.png';image=Image.new('RGB',(768,768),'#152745');draw=ImageDraw.Draw(image)
        draw.ellipse((50,30,370,340),fill='#de8b80');draw.rectangle((450,280,700,700),fill='#448f9a');image.save(source)
        self.bridge.persist({'qt_animations':True});self.bridge.appearanceChanged.emit()
        self.bridge.update_state(cover=QUrl.fromLocalFile(str(source)).toString())
        mini=self.window.findChild(QObject,'miniPlayer');QMetaObject.invokeMethod(mini,'show')
        for _ in range(16):self.settle()
        backdrop=mini.findChild(QObject,'miniSwirlBackdrop')
        self.assertIsNotNone(backdrop)
        phase=backdrop.property('phase')
        for _ in range(4):self.settle()
        self.assertGreater(backdrop.property('phase'),phase)
        backdrop.setProperty('animated',False);backdrop.setProperty('phase',0);self.settle()
        first=mini.grabWindow()
        backdrop.setProperty('phase',1.5);self.settle()
        second=mini.grabWindow();self.assertFalse(first==second)
        backdrop.setProperty('animated',True);mini.hide();self.settle()
        phase=backdrop.property('phase')
        for _ in range(3):self.settle()
        self.assertEqual(backdrop.property('phase'),phase)
        second.save(str(Path.cwd()/'Testes/auditoria-melhorias/miniplayer-soft-swirl.png'))
