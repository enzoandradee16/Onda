import os
import unittest


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt desktop tests')
class EqualizerBandsTests(unittest.TestCase):
    from test_qt_playback_queue import PlaybackQueueDrawerTests as Fixture

    setUp = Fixture.setUp
    tearDown = Fixture.tearDown
    settle = Fixture.settle

    def test_popup_resizes_presets_and_selected_band_without_qml_warnings(self):
        from PySide6.QtCore import QObject, QMetaObject, Qt

        warnings = []
        self.engine.warnings.connect(
            lambda rows: warnings.extend(row.toString() for row in rows)
        )
        popup = self.window.findChild(QObject, 'equalizerPopup')
        self.assertIsNotNone(popup)
        QMetaObject.invokeMethod(popup, 'open', Qt.ConnectionType.DirectConnection)
        self.settle()
        self.bridge.applyPreset('Rock')
        for count in (15, 5, 10):
            self.bridge.setEqualizerBandCount(count)
            self.assertEqual(self.bridge.presetName, 'Rock')
        for count in (15, 5, 10, 15):
            popup.setProperty('selectedBand', 14)
            self.bridge.setEqualizerBandCount(count)
            self.settle()
            self.assertLess(popup.property('selectedBand'), count)
            self.assertEqual(len(self.bridge.equalizer['bands']), count)
            self.bridge.applyPreset('Rock')
            self.assertEqual(self.bridge.presetName, 'Rock')
            self.assertEqual(self.bridge.equalizer['band_count'], count)
            self.bridge.setBand(count - 1, 16000, -4, 2)
            self.assertEqual(self.bridge.equalizer['bands'][-1]['gain'], -4)
            self.bridge.resetEqualizer()
            self.assertEqual(self.bridge.equalizer['band_count'], count)
            self.assertTrue(all(b['gain'] == 0 for b in self.bridge.equalizer['bands']))
        self.assertFalse(warnings, '\n'.join(warnings))
