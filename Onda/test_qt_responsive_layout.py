"""Geometry regressions for desktop window resizing, without network/audio."""
import os
import unittest

@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt desktop tests')
class ResponsiveLayoutTests(unittest.TestCase):
    def setUp(self):
        from test_qt_playback_queue import PlaybackQueueDrawerTests
        self.case = PlaybackQueueDrawerTests()
        self.case.setUp()

    def tearDown(self):
        self.case.tearDown()

    def test_playback_controls_remain_visible_and_separate(self):
        from PySide6.QtCore import QObject
        self.case.ws.selectPage('jukebox')
        for sidebar in (160, 220, 420):
            self.case.ws.setSetting('sidebar_width', sidebar)
            for width in (920, 1100, 1360):
                with self.subTest(sidebar=sidebar, width=width):
                    self.case.window.setWidth(width)
                    self.case.window.setHeight(680)
                    for _ in range(5): self.case.settle()
                    bar = self.case.window.findChild(QObject, 'jukeboxPlaybackBar')
                    groups = [self.case.window.findChild(QObject, name) for name in
                              ('jukeboxPlaybackControlsTransport', 'unifiedPlaybackExtras')]
                    rectangles = []
                    for group in groups:
                        for item in group.childItems():
                            if not any(item.metaObject().indexOfProperty(key)>=0 for key in ('glyph','value','text')) or not item.isVisible():
                                continue
                            point = item.mapToItem(bar, 0, 0)
                            w, h = item.width(), item.height()
                            self.assertGreater(w, 0)
                            self.assertGreaterEqual(point.x(), 0)
                            self.assertLessEqual(point.x()+w, bar.width()+1)
                            self.assertLessEqual(point.y()+h, bar.height()-32)
                            for x,y,r,b in rectangles:
                                self.assertFalse(point.x()<r-1 and point.x()+w>x+1 and point.y()<b-1 and point.y()+h>y+1)
                            rectangles.append((point.x(),point.y(),point.x()+w,point.y()+h))
                    self.assertGreaterEqual(len(rectangles), 13)
                    field = self.case.window.findChild(QObject, 'playbackSearchField')
                    self.assertGreater(field.width(), 250)

    def test_search_image_and_compact_player_fit_narrow_content(self):
        from PySide6.QtCore import QObject
        self.case.window.setWidth(920)
        self.case.window.setHeight(680)
        self.case.ws.setSetting('sidebar_width', 420)
        self.case.bridge.update_state(playing=True, title='A long track title', artist='Artist')
        for page in ('catalog', 'images'):
            self.case.ws.selectPage(page)
            for _ in range(5): self.case.settle()
            name = 'libraryLoadButton' if page == 'catalog' else 'toolChooseFile'
            action = self.case.window.findChild(QObject, name)
            point = action.mapToItem(self.case.window.contentItem(), 0, 0)
            self.assertGreaterEqual(point.x(), 420)
            self.assertLessEqual(point.x()+action.width(), 920)
            if page == 'images':
                field = self.case.window.findChild(QObject, 'imageLinkInput')
                self.assertGreater(field.width(), 250)
            mini = self.case.window.findChild(QObject, 'jukeboxMiniPlayer')
            self.assertTrue(mini.isVisible())
            grid = next(item for item in mini.childItems() if 'GridLayout' in item.metaObject().className())
            for item in grid.childItems():
                if not item.isVisible(): continue
                self.assertGreaterEqual(item.x(), 0)
                self.assertLessEqual(item.x()+item.width(), grid.width()+1)
                self.assertLessEqual(item.y()+item.height(), grid.height()+1)

    def test_cover_and_track_text_stay_together_after_resizing(self):
        from PySide6.QtCore import QObject
        self.case.ws.selectPage('jukebox')
        self.case.bridge.update_state(title='Music Sounds Better With You', artist='Stardust')
        for width in (1800, 920, 1800, 1100, 1360):
            self.case.window.setWidth(width)
            for _ in range(4): self.case.settle()
            metadata = self.case.window.findChild(QObject, 'playbackMetadata')
            children = metadata.childItems()
            cover, details = children[:2]
            self.assertAlmostEqual(details.x()-(cover.x()+cover.width()), 12, delta=1)

    def test_collection_options_collapse_preserves_tracks_filters_and_selection(self):
        from PySide6.QtCore import QObject, QMetaObject
        self.case.ws.selectPage('playlists')
        self.case.ws.playlistModel.replace([
            dict(title=f'Track {i}', artists=['Artist'], checked=i==3)
            for i in range(50)
        ])
        self.case.ws.collectionFilterModel.setFilters('Track', '', '')
        for _ in range(4): self.case.settle()
        root = self.case.window
        button = root.findChild(QObject, 'collectionOptionsToggle')
        panel = root.findChild(QObject, 'collectionOptionsPanel')
        tracks = root.findChild(QObject, 'libraryScrollList')
        height = tracks.height()
        before = list(self.case.ws.collectionFilterModel.visible_rows())
        self.assertTrue(button.isVisible())
        self.assertGreaterEqual(button.width(), button.property('contentItem').implicitWidth()+24)
        self.assertTrue(QMetaObject.invokeMethod(button, 'click'))
        for _ in range(4): self.case.settle()
        self.assertFalse(panel.isVisible())
        self.assertTrue(root.findChild(QObject, 'collapsedCollectionCardSizeControl').isVisible())
        self.assertGreater(tracks.height(), height+150)
        self.assertEqual(self.case.ws.collectionFilterModel.visible_rows(), before)
        self.assertTrue(self.case.ws.playlistModel.rows[3]['checked'])
        self.assertIs(tracks, root.findChild(QObject, 'libraryScrollList'))
        self.assertTrue(QMetaObject.invokeMethod(button, 'click'))
        self.case.settle()
        self.assertTrue(panel.isVisible())
        self.assertEqual(self.case.ws.collectionFilterModel.filters['title'], 'Track')

    def test_very_small_cards_and_collapsed_size_control_share_header(self):
        from PySide6.QtCore import QObject, QMetaObject
        for key in ('catalog_card_size','playlist_card_size','history_card_size','queue_card_size'):
            self.case.ws.setSetting(key, 'Muito pequeno')
            self.assertEqual(self.case.ws.preferences[key], 'Muito pequeno')
        self.case.ws.store.save(self.case.ws.settings)
        saved = self.case.ws.store.load()
        for key in ('catalog_card_size','playlist_card_size','history_card_size','queue_card_size'):
            self.assertEqual(saved[key], 'Muito pequeno')
        self.case.ws.selectPage('playlists')
        self.case.ws.playlistModel.replace([dict(title='Track', artist='Artist', checked=False)])
        for _ in range(4): self.case.settle()
        root = self.case.window
        button = root.findChild(QObject, 'collectionOptionsToggle')
        QMetaObject.invokeMethod(button, 'click')
        for _ in range(4): self.case.settle()
        size = root.findChild(QObject, 'collapsedCollectionCardSizeControl')
        self.assertTrue(size.isVisible())
        self.assertLessEqual(size.x()+size.width(), button.x())
        self.assertAlmostEqual(size.y()+size.height()/2, button.y()+button.height()/2, delta=1)
        self.assertFalse(root.findChild(QObject,'collectionCardSizeControl').isVisible())
        view = root.findChild(QObject, 'libraryScrollList')
        cards = [item for item in view.property('contentItem').childItems() if item.objectName()=='libraryTrackCard']
        self.assertTrue(cards)
        self.assertLessEqual(cards[0].height(), 70)
