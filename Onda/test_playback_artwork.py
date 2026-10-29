import os, unittest
import test_qt_playback_queue as fixtures


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt interface')
class PlaybackArtworkTests(unittest.TestCase):
    setUp = fixtures.PlaybackQueueDrawerTests.setUp
    tearDown = fixtures.PlaybackQueueDrawerTests.tearDown
    settle = fixtures.PlaybackQueueDrawerTests.settle

    def test_original_artwork_falls_back_and_recovers_on_track_change(self):
        from pathlib import Path
        from PIL import Image
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlComponent

        folder = Path(self.temp.name)
        cover = folder / 'cover.png'
        Image.new('RGB', (768, 768), 'blue').save(cover)
        component = QQmlComponent(
            self.engine,
            QUrl.fromLocalFile(str(Path(__file__).parent / 'qml/RoundedArtwork.qml')),
        )
        artwork = component.create(self.engine.rootContext())
        self.assertIsNotNone(artwork)
        try:
            artwork.setProperty('fallbackSource', QUrl.fromLocalFile(str(cover)))
            artwork.setProperty(
                'source', QUrl.fromLocalFile(str(folder / 'missing.png'))
            )
            for _ in range(5):
                self.settle()
            self.assertTrue(artwork.property('primaryFailed'))
            self.assertEqual(artwork.property('status'), 1)
            artwork.setProperty('source', QUrl.fromLocalFile(str(cover)))
            for _ in range(3):
                self.settle()
            self.assertFalse(artwork.property('primaryFailed'))
            self.assertEqual(artwork.property('status'), 1)
        finally:
            artwork.deleteLater()
