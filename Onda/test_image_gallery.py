"""Render and interact with real image files, including mixed download cards."""

import os, unittest, time
from pathlib import Path
import test_qt_playback_queue as fixture


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt desktop tests')
class ImageGalleryTests(unittest.TestCase):
    setUp = fixture.PlaybackQueueDrawerTests.setUp
    tearDown = fixture.PlaybackQueueDrawerTests.tearDown
    settle = fixture.PlaybackQueueDrawerTests.settle

    def test_image_preview_automatically_follows_link_and_background_option(self):
        from unittest.mock import patch
        from PySide6.QtTest import QTest

        with patch.object(self.ws, 'dispatch') as dispatch:
            self.ws.setOption('imageUrl', 'https://example.com/old.png')
            self.ws.setOption('imageUrl', 'https://example.com/current.png')
            QTest.qWait(500)
            dispatch.assert_called_once_with('image_preview', {})
            dispatch.reset_mock()
            self.ws.setSetting('image_remove_background', True)
            QTest.qWait(500)
            dispatch.assert_called_once_with('image_preview', {})
            dispatch.reset_mock()
            self.ws.setSetting('image_remove_background', False)
            self.ws.setOption('imageUrl', '')
            QTest.qWait(500)
            dispatch.assert_not_called()

        self.ws.options['imageSource'] = str(self.images()[0])
        self.ws.schedule_image_preview()
        self.wait(lambda: bool(self.ws.options.get('imageInfo')))
        self.assertTrue(self.ws.options['imagePreview'])

    def test_background_removal_switch_reaches_export_configuration(self):
        self.window.setWidth(1280)
        self.window.setHeight(900)
        self.ws.selectPage('images')
        self.settle()
        control = self.find('imageRemoveBackground')
        self.assertIsNotNone(control)
        self.click(control)
        self.assertTrue(self.ws.image_options()['remove_background'])
        self.click(control)
        self.assertFalse(self.ws.image_options()['remove_background'])

    def test_clipboard_image_and_queue_removal_undo(self):
        from PySide6.QtGui import QImage, QColor, QGuiApplication
        from unittest.mock import patch

        image = QImage(60, 40, QImage.Format_RGBA8888)
        image.fill(QColor('red'))
        QGuiApplication.clipboard().setImage(image)
        self.ws.dispatch('image_paste', {})
        self.wait(lambda: bool(self.ws.options.get('imageInfo')))
        self.assertTrue(Path(self.ws.options['imageSource']).is_file())
        self.assertTrue(self.ws.options.get('imageOriginalPreview'))
        self.bridge.playlist = [
            dict(id='a', title='Playing'),
            dict(id='b', title='Next'),
        ]
        self.bridge.queue_index = 0
        with patch.object(self.bridge, 'prepare_next_queued'):
            self.bridge.removeQueued(1)
            self.assertTrue(self.bridge.canUndoQueueRemoval)
            self.bridge.undoQueueRemoval()
            self.assertEqual(
                [row['title'] for row in self.bridge.playlist], ['Playing', 'Next']
            )
            self.assertEqual(self.bridge.queue_index, 0)
            self.assertFalse(self.bridge.canUndoQueueRemoval)
            self.assertNotEqual(self.bridge.playlist[1]['id'], 'b')

    def test_image_background_picker_keeps_exact_color_without_changing_theme(self):
        from PySide6.QtCore import QObject

        self.ws.selectPage('images')
        self.ws.setSetting('image_background', 'color')
        self.ws.setSetting('image_background_color', '#123456')
        before = self.bridge.accent
        self.settle()
        self.click(self.find('imageBackgroundColorButton'))
        picker = self.find('imageBackgroundColorPicker')
        self.assertTrue(picker.property('opened'))
        picker.findChild(QObject, 'customAccentHex').setProperty('text', '#FA0088')
        self.settle()
        self.click(picker.findChild(QObject, 'applyCustomAccent'))
        self.assertEqual(self.ws.settings['image_background_color'].upper(), '#FA0088')
        self.assertEqual(self.bridge.accent, before)

    def test_background_removal_survives_source_changes_without_opening_gallery(self):
        from unittest.mock import patch
        from PIL import Image
        from PySide6.QtCore import QUrl

        paths = self.images()
        self.ws.selectPage('images')
        self.ws.options.update(
            imageGallery=[
                dict(
                    path=str(paths[0]), url=QUrl.fromLocalFile(str(paths[0])).toString()
                )
            ],
            imageGalleryEmbedded=True,
        )

        def remove(image, emit):
            image.putalpha(100)
            return image

        with patch('image_background.remove_background', side_effect=remove):
            self.ws.setSetting('image_remove_background', True)
            previous = ''
            for path in paths:
                self.ws.accept_files('image', [str(path)])
                self.wait(
                    lambda: 'image_preview' not in self.ws.tasks
                    and self.ws.options['imagePreview']
                    != QUrl.fromLocalFile(str(path)).toString()
                )
                current = self.ws.options['imagePreview']
                self.assertNotEqual(current, previous)
                with Image.open(QUrl(current.split('?')[0]).toLocalFile()) as output:
                    self.assertEqual(output.getpixel((0, 0))[3], 100)
                self.assertFalse(self.find('imageGalleryPopup').property('opened'))
                previous = current
            self.ws.setSetting('image_remove_background', False)
            self.wait(lambda: self.ws.options['imagePreview'] != previous)
            self.assertFalse(self.find('imageGalleryPopup').property('opened'))

    def test_paste_accepts_explorer_file_urls_and_quoted_file_paths(self):
        from PySide6.QtCore import QMimeData, QUrl
        from PySide6.QtGui import QGuiApplication

        paths = self.images()
        self.ws.selectPage('images')
        clipboard = QGuiApplication.clipboard()
        data = QMimeData()
        data.setUrls([QUrl.fromLocalFile(str(paths[0]))])
        clipboard.setMimeData(data)
        self.assertTrue(self.ws.clipboardHasImage())
        self.ws.dispatch('image_paste', {})
        self.wait(lambda: bool(self.ws.options.get('imageInfo')))
        self.assertEqual(Path(self.ws.options['imageSource']), paths[0])
        clipboard.setText('"' + str(paths[1]) + '"')
        self.assertTrue(self.ws.clipboardHasImage())
        self.ws.dispatch('image_paste', {})
        self.wait(
            lambda: 'image_preview' not in self.ws.tasks
            and self.ws.options['imagePreview']
            != QUrl.fromLocalFile(str(paths[1])).toString()
        )
        self.assertEqual(Path(self.ws.options['imageSource']), paths[1])
        self.assertFalse(self.find('imageGalleryPopup').property('opened'))
        clipboard.clear()
        self.assertFalse(self.ws.clipboardHasImage())

    def images(self):
        from PIL import Image

        paths = [Path(self.temp.name) / ('image-' + str(i) + '.png') for i in range(2)]
        for path, color in zip(paths, ('red', 'blue')):
            Image.new('RGB', (12, 12), color).save(path)
        return paths

    def job(self, paths):
        job = dict(
            id='gallery',
            url='https://example.com/post',
            mode='social',
            state='Concluído',
            percent=100,
            checked=False,
            output_files=[str(p) for p in paths],
            display_name='Mixed publication',
        )
        self.ws.jobs = [job]
        self.ws.refresh_queue()
        return job

    def wait(self, predicate):
        until = time.monotonic() + 5
        while not predicate():
            self.assertLess(time.monotonic(), until)
            self.settle()

    def find(self, name):
        from PySide6.QtCore import QObject

        found = self.window.findChild(QObject, name)
        if found is not None:
            return found

        def walk(item):
            if item.objectName() == name:
                return item
            for child in item.childItems():
                result = walk(child)
                if result is not None:
                    return result

        return walk(self.window.contentItem())

    def click(self, item):
        from PySide6.QtCore import Qt, QPointF
        from PySide6.QtTest import QTest

        position = item.mapToScene(
            QPointF(item.width() / 2, item.height() / 2)
        ).toPoint()
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, position)
        self.settle()

    def test_completed_mixed_card_opens_decodes_navigates_and_shares_real_images(self):
        from PySide6.QtCore import QObject
        from PySide6.QtGui import QGuiApplication

        paths = self.images()
        self.job(paths)
        self.window.setWidth(1360)
        self.window.setHeight(900)
        self.ws.selectPage('queue')
        self.settle()
        row = self.ws.models['queue'].rows[0]
        self.assertTrue(row['has_images'])
        self.assertTrue(row['is_image'])
        self.assertTrue(row['track_cover'].endswith('image-0.png'))
        artwork = self.find('downloadQueueArtwork')
        self.assertIsNotNone(artwork)
        self.click(artwork)
        gallery = self.find('imageGalleryPopup')
        image = self.find('galleryImage')
        self.assertTrue(gallery.property('opened'))
        self.wait(lambda: image.property('imageReady'))
        self.assertEqual(len(self.ws.options['imageGallery']), 2)
        self.click(self.find('galleryNext'))
        self.wait(
            lambda: image.property('imageReady')
            and image.property('source').toString().endswith('image-1.png')
        )
        self.assertEqual(self.ws.options['imageGalleryIndex'], 1)
        self.click(self.find('galleryShare'))
        mime = QGuiApplication.clipboard().mimeData()
        self.assertTrue(mime.hasImage())
        self.assertTrue(mime.hasUrls())
        self.assertEqual(
            Path(mime.urls()[0].toLocalFile()).resolve(), paths[1].resolve()
        )
        self.click(self.find('galleryPrevious'))
        self.assertEqual(self.ws.options['imageGalleryIndex'], 0)
        self.click(self.find('galleryClose'))
        self.assertFalse(gallery.property('opened'))
        # Closing must not break reopening the same card.
        self.click(artwork)
        self.assertTrue(gallery.property('opened'))
        self.wait(lambda: image.property('imageReady'))

    def test_gallery_mouse_drag_and_keyboard_respect_boundaries(self):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtTest import QTest

        paths = self.images()
        self.window.setWidth(1360)
        self.window.setHeight(900)
        self.ws.local_gallery(
            [
                dict(
                    path=str(p),
                    url=__import__('PySide6.QtCore', fromlist=['QUrl'])
                    .QUrl.fromLocalFile(str(p))
                    .toString(),
                    name=p.name,
                )
                for p in paths
            ],
            0,
        )
        self.settle()
        image = self.find('galleryImage')
        self.wait(lambda: image.property('imageReady'))

        def drag(dx):
            start = image.mapToScene(
                QPointF(image.width() / 2, image.height() / 2)
            ).toPoint()
            end = start + __import__('PySide6.QtCore', fromlist=['QPoint']).QPoint(
                dx, 0
            )
            QTest.mousePress(self.window, Qt.LeftButton, Qt.NoModifier, start)
            QTest.mouseMove(self.window, end, 30)
            QTest.mouseRelease(self.window, Qt.LeftButton, Qt.NoModifier, end)
            self.settle()

        drag(-100)
        self.assertEqual(self.ws.options['imageGalleryIndex'], 1)
        drag(-100)
        self.assertEqual(self.ws.options['imageGalleryIndex'], 1)
        drag(100)
        self.assertEqual(self.ws.options['imageGalleryIndex'], 0)
        drag(-10)
        self.assertEqual(self.ws.options['imageGalleryIndex'], 0)
        QTest.keyClick(self.window, Qt.Key_Right)
        self.settle()
        self.assertEqual(self.ws.options['imageGalleryIndex'], 1)
        QTest.keyClick(self.window, Qt.Key_Left)
        self.settle()
        self.assertEqual(self.ws.options['imageGalleryIndex'], 0)
        self.click(self.find('galleryArrowNext'))
        self.assertEqual(self.ws.options['imageGalleryIndex'], 1)
        self.click(self.find('galleryArrowPrevious'))
        self.assertEqual(self.ws.options['imageGalleryIndex'], 0)

    def test_links_show_only_their_jobs_and_follow_queue_changes(self):
        from unittest.mock import patch

        self.ws.selectPage('downloads')
        with patch.object(self.ws.title_lookup, 'submit'):
            self.ws.options['links'] = 'https://example.com/linked.mp4'
            self.ws.dispatch('add_links', {})
            self.ws.enqueue(['https://example.com/other.mp4'])
        self.settle()
        model = self.ws.models['links']
        self.assertEqual(len(model.rows), 1)
        job = self.ws.jobs[0]
        self.assertEqual(model.rows[0]['id'], job['id'])
        self.assertEqual(self.ws.currentPage, 'downloads')
        self.assertTrue(self.find('downloadQueueList').property('visible'))
        job['state'] = 'Em andamento'
        self.ws.refresh_queue()
        self.ws.on_event(job['id'], {'type': 'progress', 'percent': 37})
        self.assertEqual(model.rows[0]['percent'], 37)
        self.ws.queue_action('remove', job['id'])
        self.assertEqual(len(model.rows), 0)
        self.assertEqual(len(self.ws.jobs), 1)

    def test_old_mixed_card_uses_history_when_output_paths_were_not_saved(self):
        paths = self.images()
        for path in paths:
            self.ws.library.add_history(path, 'png', 'https://example.com/post')
        self.ws.refresh_history()
        job = self.job([])
        self.ws.refresh_queue()
        self.assertTrue(self.ws.models['queue'].rows[0]['has_images'])
        self.ws.dispatch('download_preview', {'id': job['id']})
        self.assertEqual(
            [Path(r['path']).resolve() for r in self.ws.options['imageGallery']],
            [p.resolve() for p in paths],
        )

    def test_history_image_card_opens_from_title_area(self):
        from PySide6.QtCore import QObject, QPointF, Qt
        from PySide6.QtTest import QTest

        path = self.images()[0]
        self.ws.library.add_history(path, 'png', 'https://example.com/post')
        self.ws.refresh_history()
        self.ws.selectPage('history')
        self.settle()
        card = self.find('libraryTrackCard')
        point = card.mapToScene(QPointF(card.width() * 0.7, 22)).toPoint()
        QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, point)
        self.settle()
        self.assertTrue(self.find('imageGalleryPopup').property('opened'))
        self.wait(lambda: self.find('galleryImage').property('imageReady'))

    def test_online_preview_from_links_loads_lazily_without_queue_or_history(self):
        from unittest.mock import patch
        from PySide6.QtGui import QGuiApplication
        from test_online_image_preview import OnlineImagePreviewTests

        server = OnlineImagePreviewTests()
        server.setUp()
        try:
            self.window.setWidth(1360)
            self.window.setHeight(900)
            self.ws.selectPage('downloads')
            self.ws.setOption('links', server.base + '/post')
            self.ws.setSetting('mode', 'Fotos · todas do carrossel')
            self.settle()
            before = self.ws.library.history()
            with patch.object(self.ws, 'enqueue') as enqueue:
                self.click(self.find('previewLinksImages'))
                self.wait(lambda: bool(self.ws.options.get('imageGallery')))
                self.wait(lambda: self.find('galleryImage').property('imageReady'))
                self.assertTrue(self.find('imageGalleryPopup').property('online'))
                self.assertEqual([r[0] for r in server.requests], ['/post', '/one.png'])
                self.click(self.find('galleryNext'))
                self.wait(
                    lambda: self.find('galleryImage').property('imageReady')
                    and self.ws.options['imageGallery'][1].get('url')
                )
                self.assertEqual(server.requests[-1][0], '/two.png')
                self.click(self.find('galleryShare'))
                self.assertEqual(
                    QGuiApplication.clipboard().text(), server.base + '/post'
                )
                self.click(self.find('galleryClose'))
                enqueue.assert_not_called()
            self.assertEqual(self.ws.library.history(), before)
            self.assertEqual(self.ws.jobs, [])
        finally:
            server.tearDown()

    def test_online_download_button_uses_original_link_and_photo_mode(self):
        from unittest.mock import patch
        from test_online_image_preview import OnlineImagePreviewTests
        import online_image_preview

        server = OnlineImagePreviewTests()
        server.setUp()
        try:
            manifest = online_image_preview.discover(
                {'url': server.base + '/post', '_root': self.temp.name}
            )
            self.ws.online_gallery_loaded(manifest)
            self.wait(lambda: self.find('galleryImage').property('imageReady'))
            with patch.object(self.ws, 'enqueue') as enqueue:
                self.click(self.find('downloadPreviewImages'))
            self.assertEqual(enqueue.call_args.args[0], [server.base + '/post'])
            self.assertEqual(enqueue.call_args.kwargs['overrides']['mode'], 'photos')
            self.assertTrue(enqueue.call_args.kwargs['start'])
        finally:
            server.tearDown()
