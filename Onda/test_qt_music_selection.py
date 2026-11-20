"""Modifier selection and checkbox synchronization without network or audio."""

import os
import unittest


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt desktop tests')
class MusicSelectionTests(unittest.TestCase):
    def setUp(self):
        from test_qt_playback_queue import PlaybackQueueDrawerTests

        self.case = PlaybackQueueDrawerTests()
        self.case.setUp()
        self.ws = self.case.ws

    def tearDown(self):
        self.case.tearDown()

    def test_ctrl_shift_clicks_select_rows_and_checks_without_initial_highlight(self):
        from PySide6.QtCore import QObject, QMetaObject, Qt, QPoint, QPointF
        from PySide6.QtTest import QTest

        self.ws.selectPage('playlists')
        self.ws.setSetting('playlist_card_size', 'Muito pequeno')
        self.ws.playlistModel.replace(
            [dict(id=str(i), title=f'Track {i}', checked=True) for i in range(8)]
        )
        for _ in range(4):
            self.case.settle()
        root = self.case.window
        QMetaObject.invokeMethod(
            root.findChild(QObject, 'collectionOptionsToggle'), 'click'
        )
        for _ in range(4):
            self.case.settle()
        view = root.findChild(QObject, 'libraryScrollList')

        def row(index):
            return next(
                item
                for item in view.property('contentItem').childItems()
                if item.objectName() == 'libraryTrackCard'
                and item.property('index') == index
            )

        self.assertFalse(row(0).property('modifierSelected'))
        self.assertEqual(row(0).property('color').alpha(), 0)

        def click(index, modifiers):
            item = row(index)
            point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
            QTest.mouseClick(
                root,
                Qt.LeftButton,
                modifiers,
                QPoint(round(point.x()), round(point.y())),
            )
            self.case.settle()

        click(0, Qt.ControlModifier)
        self.assertEqual(
            [i for i, r in enumerate(self.ws.playlistModel.rows) if r['checked']], [0]
        )
        self.assertTrue(row(0).property('modifierSelected'))
        click(2, Qt.ControlModifier)
        self.assertEqual(
            [i for i, r in enumerate(self.ws.playlistModel.rows) if r['checked']],
            [0, 2],
        )
        click(4, Qt.ShiftModifier)
        self.assertEqual(
            [i for i, r in enumerate(self.ws.playlistModel.rows) if r['checked']],
            [2, 3, 4],
        )
        self.ws.toggle_row('playlists', 3, False)
        self.case.settle()
        self.assertFalse(row(3).property('modifierSelected'))
        self.ws.toggle_row('playlists', 0, True)
        self.case.settle()
        self.assertFalse(row(0).property('modifierSelected'))

    def test_filtered_order_preserves_hidden_checks_and_uses_source_rows(self):
        from PySide6.QtCore import Qt

        rows = [
            dict(id=str(i), title=t, checked=True)
            for i, t in enumerate(['Hidden', 'C', 'A', 'B'])
        ]
        self.ws.playlistModel.replace(rows)
        self.ws.collectionFilterModel.setFilters('', '', '')
        self.ws.collectionFilterModel.setOrdering('title', False)
        self.ws.selectMusicRows('playlists', 0, Qt.ControlModifier.value)
        self.ws.selectMusicRows('playlists', 2, Qt.ShiftModifier.value)
        self.assertEqual(
            [r['title'] for r in self.ws.playlistModel.rows if r['checked']],
            ['C', 'A', 'B'],
        )
        self.ws.collectionFilterModel.setFilters('Hidden', '', '')
        self.ws.selectMusicRows('playlists', 0, Qt.ControlModifier.value)
        self.assertTrue(self.ws.playlistModel.rows[0]['checked'])
        self.assertTrue(self.ws.playlistModel.rows[1]['checked'])

    def test_all_models_and_download_links_sync_job_and_other_view(self):
        from PySide6.QtCore import Qt

        for name in ('catalog', 'history', 'queue', 'links'):
            self.ws.models[name].replace(
                [
                    dict(id='one', title='One', checked=True),
                    dict(id='two', title='Two', checked=True),
                ]
            )
        self.ws.jobs = [dict(id='one', checked=True), dict(id='two', checked=True)]
        for name in ('catalog', 'history', 'queue', 'links'):
            self.ws.selectMusicRows(name, 0, Qt.ControlModifier.value)
            self.assertTrue(self.ws.models[name].rows[0]['checked'])
            self.assertFalse(self.ws.models[name].rows[1]['checked'])
            self.assertTrue(self.ws.musicRowSelected(0, name, 0))
        self.assertFalse(self.ws.jobs[1]['checked'])
        self.assertFalse(self.ws.queueModel.rows[1]['checked'])
        self.ws.dispatch('check_all', dict(model='links', checked=True))
        self.assertFalse(self.ws.musicRowSelected(0, 'links', 0))
        self.assertTrue(self.ws.queueModel.rows[1]['checked'])
        self.ws.catalogModel.replace([dict(id='new', checked=True)])
        self.assertFalse(self.ws.musicRowSelected(0, 'catalog', 0))

    def test_download_clicks_work_on_drag_surface_and_survive_refresh(self):
        from PySide6.QtCore import QObject, Qt, QPoint, QPointF
        from PySide6.QtTest import QTest

        self.ws.enqueue(
            [
                'https://example.com/a.mp3',
                'https://example.com/b.mp3',
                'https://example.com/c.mp3',
            ]
        )
        self.ws.selectPage('queue')
        self.ws.setSetting('queue_card_size', 'Muito pequeno')
        for _ in range(4):
            self.case.settle()
        root = self.case.window
        view = root.findChild(QObject, 'downloadQueueList')

        def click(index, modifier):
            item = next(
                item
                for item in view.property('contentItem').childItems()
                if item.objectName() == 'downloadQueueCard'
                and item.property('index') == index
            )
            point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
            QTest.mouseClick(
                root,
                Qt.LeftButton,
                modifier,
                QPoint(round(point.x()), round(point.y())),
            )
            self.case.settle()

        click(0, Qt.ControlModifier)
        self.assertEqual(
            [bool(j.get('checked')) for j in self.ws.jobs], [True, False, False]
        )
        click(2, Qt.ShiftModifier)
        self.assertTrue(all(j['checked'] for j in self.ws.jobs))
        self.ws.refresh_queue()
        self.case.settle()
        self.assertTrue(self.ws.musicRowSelected(0, 'queue', 2))
