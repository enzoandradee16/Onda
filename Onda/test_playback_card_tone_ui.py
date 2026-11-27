"""Main-card resizing and independent tone controls without network or audio output."""

import os
import unittest


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt desktop tests')
class PlaybackCardToneTests(unittest.TestCase):
    def test_tone_survives_silent_session_restore_without_a_legacy_source(self):
        from playback_session import save, restore

        self.ws.setOption('pitch_shift', -4)
        save(self.ws, strict=True)
        self.ws.setOption('pitch_shift', 0)
        restore(self.ws)
        self.assertEqual(self.ws.options['pitch_shift'], -4)
        self.assertFalse(self.case.bridge._state.get('playing'))

    def setUp(self):
        from test_qt_playback_queue import PlaybackQueueDrawerTests

        self.case = PlaybackQueueDrawerTests()
        self.case.setUp()
        self.addCleanup(self.case.tearDown)
        self.ws = self.case.ws
        self.ws.selectPage('jukebox')
        self.case.window.setWidth(1360)
        self.case.window.setHeight(1000)
        self.case.settle()

    def test_card_sizes_change_geometry_and_persist_without_hiding_metadata(self):
        from PySide6.QtCore import QObject, QMetaObject, Qt, Q_ARG

        window = self.case.window
        card = window.findChild(QObject, 'playbackTrackCard')
        artwork = window.findChild(QObject, 'playbackMainArtwork')
        selector = window.findChild(QObject, 'playbackTrackCardSize')
        default = artwork.width()
        self.assertEqual(self.ws.settings['playback_card_size'], 'Padrão')
        heights = []
        for index, label in [
            (0, 'Muito pequeno'),
            (1, 'Pequeno'),
            (2, 'Padrão'),
            (3, 'Grande'),
        ]:
            selector.setProperty('currentIndex', index)
            QMetaObject.invokeMethod(
                selector, 'activated', Qt.DirectConnection, Q_ARG(int, index)
            )
            self.case.settle()
            self.assertEqual(self.ws.settings['playback_card_size'], label)
            heights.append(card.height())
        self.assertGreater(artwork.width(), default)
        self.assertLess(heights[0], heights[1] * 0.65)
        self.assertLess(heights[1], heights[2])
        self.assertLess(heights[2], heights[3])
        self.ws.settings['remember_settings'] = False
        self.ws.persist()
        self.assertEqual(self.ws.store.load_display()['playback_card_size'], 'Grande')

    def test_tone_stays_enabled_with_slowed_disabled_and_reset_restores_streaming(self):
        from PySide6.QtCore import QObject, QMetaObject

        window = self.case.window
        self.ws.setOption('effectsEnabled', False)
        popup = window.findChild(QObject, 'playbackPitchPopup')
        QMetaObject.invokeMethod(popup, 'open')
        self.case.settle()
        tone = window.findChild(QObject, 'unifiedPitchSlider')
        speed = window.findChild(QObject, 'unifiedSpeedSlider')
        self.assertTrue(tone.property('enabled'))
        self.assertFalse(speed.property('enabled'))
        self.ws.setOption('pitch_shift', 5)
        self.case.settle()
        self.assertEqual(self.case.bridge._effects['pitch_shift'], 5)
        self.assertFalse(self.case.bridge.can_stream())
        reset = window.findChild(QObject, 'unifiedPitchReset')
        QMetaObject.invokeMethod(reset, 'click')
        self.case.settle()
        self.assertEqual(self.case.bridge._effects['pitch_shift'], 0)
        self.assertTrue(self.case.bridge.can_stream())

    def test_second_lyrics_click_closes_the_window(self):
        from PySide6.QtCore import QObject, QPointF, Qt
        from PySide6.QtTest import QTest

        window = self.case.window
        button = window.findChild(QObject, 'playbackLyricsButton')
        popup = window.findChild(QObject, 'lyricsWindow')
        point = button.mapToScene(QPointF(button.width() / 2, button.height() / 2))
        for visible in (True, False):
            QTest.mouseClick(window, Qt.MouseButton.LeftButton, pos=point.toPoint())
            self.case.settle()
            self.assertEqual(popup.property('visible'), visible)
