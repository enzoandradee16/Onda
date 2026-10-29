import os, threading, unittest
from unittest.mock import patch
import test_qt_playback_queue as fixtures


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt interface')
class PlaybackPreparationVisualTests(unittest.TestCase):
    setUp = fixtures.PlaybackQueueDrawerTests.setUp
    tearDown = fixtures.PlaybackQueueDrawerTests.tearDown
    settle = fixtures.PlaybackQueueDrawerTests.settle

    def test_pure_black_toggle_applies_to_all_playback_cards_and_drawer(self):
        from PySide6.QtCore import QObject, QMetaObject
        from PySide6.QtQml import QQmlProperty

        self.window.resize(1360, 900)
        self.ws.selectPage('jukebox')
        self.bridge.setAppearance('Preto puro', 'Verde-Água', False)
        popup = self.window.findChild(QObject, 'appearancePopup')
        QMetaObject.invokeMethod(popup, 'open')
        self.settle()
        toggle = popup.findChild(QObject, 'appearanceBlackSeparators')
        self.assertTrue(toggle.property('visible'))
        self.assertEqual(
            toggle.property('text'), 'Mostrar bordas e separações no Preto puro'
        )
        cards = [
            self.window.findChild(QObject, name)
            for name in (
                'playbackTrackCard',
                'playbackEffectsCard',
                'playbackJukeboxCard',
                'unifiedQueuePanel',
            )
        ]
        for enabled in (False, True, False):
            self.ws.setSetting('pure_black_separators', enabled)
            for _ in range(3):
                self.settle()
            for card in cards:
                self.assertIsNotNone(card)
                self.assertEqual(card.property('color').name(), '#000000')
                self.assertEqual(
                    QQmlProperty(card, 'border.width').read(), int(enabled)
                )
        self.bridge.setAppearance('Escuro', 'Verde-Água', False)
        self.settle()
        self.assertFalse(toggle.property('visible'))

    def test_both_queues_show_visual_progress_without_resetting_their_cards(self):
        from PySide6.QtCore import QObject
        from PySide6.QtTest import QSignalSpy

        self.window.resize(1360, 900)
        self.ws.selectPage('jukebox')
        entry = dict(
            id='preparing',
            title='Preparing song',
            artist='Artist',
            analysis='preparing',
            preparation_progress=0,
        )
        self.bridge.playlist = [entry]
        owner = threading.Event()
        self.bridge._queue_cancel['preparing'] = owner
        self.bridge.queueChanged.emit()
        self.bridge.preparationChanged.emit()
        self.settle()
        inline = self.window.findChild(QObject, 'unifiedQueuePanel')
        self.ws.setOption('jukeboxQueueOpen', True)
        for _ in range(5):
            self.settle()
        drawer = self.window.findChild(QObject, 'jukeboxQueueDrawer')

        def find(item):
            if item.objectName() == 'queuePreparationProgress':
                return item
            for child in item.childItems():
                found = find(child)
                if found is not None:
                    return found

        bars = [find(inline), find(drawer.property('contentItem'))]
        for bar in bars:
            self.assertIsNotNone(bar)
            self.assertTrue(bar.property('visible'))
            self.assertTrue(bar.property('indeterminate'))
        signals = QSignalSpy(self.bridge.queueChanged)
        self.bridge.handle_event(
            0, 'queue_progress', dict(id='preparing', owner=owner, progress=58)
        )
        self.settle()
        self.assertEqual(signals.count(), 0)
        for bar in bars:
            self.assertEqual(bar.property('value'), 58)
            self.assertFalse(bar.property('indeterminate'))
            self.assertFalse(
                any(
                    'Text' in child.metaObject().className()
                    for child in bar.childItems()
                )
            )
        owner.set()
        self.bridge.handle_event(
            0, 'queue_progress', dict(id='preparing', owner=owner, progress=90)
        )
        self.settle()
        self.assertEqual(self.bridge.queuePreparation['preparing'], 58)
        entry['analysis'] = 'ready'
        self.bridge.queueChanged.emit()
        self.bridge.preparationChanged.emit()
        self.settle()
        for root in (inline, drawer.property('contentItem')):
            bar = find(root)
            self.assertIsNotNone(bar)
            self.assertFalse(bar.property('visible'))

    def test_catalog_preparation_progress_moves_forward_between_stages(self):
        values = []

        def fetch(config, record, cancelled, progress, *, stage_progress):
            for stage, value in [
                ('download', 0),
                ('download', 50),
                ('download', 100),
                ('analysis', 0),
                ('analysis', 85),
                ('analysis', 99),
            ]:
                stage_progress(stage, value)
            return {}

        with patch('qt_jukebox_ui.fetch_audio', side_effect=fetch):
            self.bridge.fetch_record(
                {'source_url': 'https://example.com/song'},
                {},
                threading.Event(),
                values.append,
            )
        self.assertEqual(values, sorted(values))
        self.assertEqual(values[0], 0)
        self.assertEqual(values[-1], 99)
