"""Optional miniplayer visuals follow the actual PCM and the master switch."""

from array import array
import os, sys, unittest
from pathlib import Path
import test_qt_playback_queue as fixtures


class AudioEnvelopeTests(unittest.TestCase):
    def test_pcm_envelope_tracks_silence_and_intensity_in_bounded_windows(self):
        from mini_player_effects import pcm_envelope

        samples = array('h', [0] * 160 + [8192] * 160 + [24576] * 160)
        if sys.byteorder != 'little':
            samples.byteswap()
        self.assertEqual(pcm_envelope(samples.tobytes(), rate=1000), [0.0, 0.25, 0.75])
        self.assertEqual(pcm_envelope(b''), [])


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt interface')
class MiniVisualEffectsTests(unittest.TestCase):
    setUp = fixtures.PlaybackQueueDrawerTests.setUp
    tearDown = fixtures.PlaybackQueueDrawerTests.tearDown
    settle = fixtures.PlaybackQueueDrawerTests.settle

    def test_album_background_crossfades_without_blanking_and_releases_old_cover(self):
        from PIL import Image
        from PySide6.QtCore import QObject, QMetaObject, QUrl

        first = Path(self.temp.name) / 'first.png'
        second = Path(self.temp.name) / 'second.png'
        Image.new('RGB', (768, 768), '#c06040').save(first)
        Image.new('RGB', (768, 768), '#305090').save(second)
        self.ws.setSetting('qt_animations', True)
        self.bridge.update_state(cover=QUrl.fromLocalFile(str(first)).toString())
        mini = self.window.findChild(QObject, 'miniPlayer')
        QMetaObject.invokeMethod(mini, 'show')
        for _ in range(12):
            self.settle()
        canvas = mini.findChild(QObject, 'miniBackgroundCanvas')
        self.assertTrue(canvas.property('loadedSource'))
        self.bridge.update_state(cover=QUrl.fromLocalFile(str(second)).toString())
        for _ in range(4):
            self.settle()
        self.assertTrue(canvas.property('previousSource'))
        self.assertGreater(canvas.property('blend'), 0)
        self.assertLess(canvas.property('blend'), 1)
        for _ in range(10):
            self.settle()
        self.assertAlmostEqual(canvas.property('blend'), 1)
        self.assertEqual(canvas.property('previousSource'), '')
        mini.grabWindow().save(
            str(Path.cwd() / 'Testes/auditoria-melhorias/miniplayer-all-effects.png')
        )

    def test_music_pulse_and_master_switch(self):
        from PySide6.QtCore import QObject, QMetaObject

        self.ws.setSetting('qt_animations', True)
        mini = self.window.findChild(QObject, 'miniPlayer')
        QMetaObject.invokeMethod(mini, 'show')
        for _ in range(4):
            self.settle()
        self.assertTrue(self.bridge._mini_active)
        self.bridge.update_state(playing=True, paused=False)
        self.bridge.handle_event(
            self.bridge.revision,
            'position',
            dict(index=0, phase=0.0, elapsed=1.0, jumps=0, edges=[], level=0.36),
        )
        for _ in range(4):
            self.settle()
        self.assertAlmostEqual(self.bridge.audioLevel, 0.36)
        self.assertAlmostEqual(mini.property('musicPulse'), 0.6, delta=0.02)
        backdrop = mini.findChild(QObject, 'miniSwirlBackdrop')
        self.ws.setSetting('translucent_effects', False)
        for _ in range(4):
            self.settle()
        self.assertFalse(mini.property('glassEnabled'))
        self.assertFalse(backdrop.property('active'))
        self.assertAlmostEqual(mini.property('musicPulse'), 0)
        self.assertEqual(backdrop.property('source').toString(), '')
        self.bridge.update_state(playing=False)
