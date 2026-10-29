import os, tempfile, time, unittest
from pathlib import Path
from unittest.mock import patch


class QualityImprovementsTests(unittest.TestCase):
    def test_automatic_cleanup_expires_only_disposable_old_files(self):
        from cache_cleanup import automatic_cleanup

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            now = time.time()
            keep = [
                'jukebox/track/audio.wav',
                '.onda-work/job/video.part',
                'settings.json',
                'image-preview/recent.png',
            ]
            remove = [
                'image-preview/expired.png',
                'online-image-preview/expired.jpg',
                'extractor-cache/old.json',
            ]
            for name in keep + remove:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'data')
                if name != 'image-preview/recent.png':
                    os.utime(path, (now - 9 * 86400, now - 9 * 86400))
            result = automatic_cleanup(root, now=now, max_bytes=0)
            self.assertEqual(result['removed'], 12)
            for name in keep:
                self.assertTrue((root / name).exists(), name)
            for name in remove:
                self.assertFalse((root / name).exists(), name)

    def test_size_limit_evicts_oldest_and_keeps_recent_lease(self):
        from cache_cleanup import automatic_cleanup

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cache = root / 'image-preview'
            cache.mkdir()
            now = time.time()
            for i in range(3):
                file = cache / str(i)
                file.write_bytes(b'1234')
                os.utime(file, (now - 7200 + i * 60, now - 7200 + i * 60))
            result = automatic_cleanup(root, now=now, max_bytes=8)
            self.assertEqual(result['removed'], 4)
            self.assertFalse((cache / '0').exists())
            self.assertTrue((cache / '2').exists())

    def test_recovery_keeps_work_id_progress_and_links_origin(self):
        from library import LibraryStore

        with tempfile.TemporaryDirectory() as folder:
            db = LibraryStore(Path(folder) / 'library.sqlite3')
            db.save_queue(
                [
                    dict(
                        url='https://example.com/video',
                        folder=folder,
                        mode='mp4',
                        state='Em andamento',
                        work_id='stable',
                        percent=42,
                        ui_origin='links',
                    )
                ]
            )
            row = db.load_queue()[0]
            self.assertEqual(row['work_id'], 'stable')
            self.assertEqual(row['percent'], 42)
            self.assertTrue(row['interrupted'])
            self.assertEqual(row['state'], 'Na fila')
            self.assertEqual(row['ui_origin'], 'links')

    def test_stable_update_ignores_prerelease_and_shows_details(self):
        from advanced_options import release_update

        def release(version, pre=False):
            return dict(
                tag_name=version,
                prerelease=pre,
                body='New features',
                assets=[
                    dict(
                        name='ONDA-Android-' + version + '-arm64-v8a.apk',
                        size=123,
                        browser_download_url='https://github.com/enzoandradee16/Onda/releases/download/'
                        + version
                        + '/app.apk',
                    )
                ],
            )

        releases = [release('1.2.4'), release('2.0.0-beta.1', True)]
        result = release_update('android', '1.2.3', releases, abi='arm64-v8a')
        self.assertEqual(result['version'], '1.2.4')
        self.assertEqual(result['size'], 123)
        self.assertEqual(result['notes'], 'New features')
        self.assertEqual(
            release_update('android', '1.2.3-beta.1', releases, abi='arm64-v8a')[
                'version'
            ],
            '2.0.0-beta.1',
        )

    def test_changed_http_validator_restarts_without_mixing_old_bytes(self):
        import hashlib, json, threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        import requests
        from social_media import save_media

        data = b'NEW_DATA'
        seen = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                range_value = self.headers.get('Range')
                seen.append((range_value, self.headers.get('If-Range')))
                offset = 4 if range_value else 0
                self.send_response(206 if offset else 200)
                self.send_header('Content-Type', 'image/png')
                self.send_header('ETag', '"new"')
                self.send_header('Content-Length', str(len(data) - offset))
                if offset:
                    self.send_header('Content-Range', 'bytes 4-7/8')
                self.end_headers()
                self.wfile.write(data[offset:])

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                config = dict(
                    url='https://example.com/post', mode='photos', folder=folder
                )
                identity = hashlib.sha256(
                    json.dumps(
                        {
                            key: config.get(key)
                            for key in (
                                'url',
                                'mode',
                                'audio_quality',
                                'height',
                                'fps',
                                'work_id',
                                '_identity',
                            )
                        },
                        sort_keys=True,
                    ).encode()
                ).hexdigest()[:20]
                staging = Path(folder) / '.onda-work' / identity
                staging.mkdir(parents=True)
                partial = staging / 'Author - Photo - 01.png.part'
                partial.write_bytes(b'OLD_')
                partial.with_suffix('.part.validator').write_text('"old"')
                with requests.Session() as session:
                    target = save_media(
                        session,
                        'http://127.0.0.1:' + str(server.server_port) + '/file.png',
                        dict(extension='png', user='Author', title='Photo'),
                        config,
                        lambda *a, **kw: None,
                        lambda *a: 'keep',
                        1,
                    )
                self.assertEqual(Path(target).read_bytes(), data)
                self.assertEqual(seen, [('bytes=4-', '"old"'), (None, None)])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt integration')
class QueueInteractionTests(unittest.TestCase):
    from test_qt_playback_queue import PlaybackQueueDrawerTests as Fixture

    setUp = Fixture.setUp
    tearDown = Fixture.tearDown
    settle = Fixture.settle
    seed = Fixture.seed

    def test_effects_move_inserts_and_keeps_active_track(self):
        self.seed()
        self.ws.dispatch('effects_queue_move', dict(index=0, direction=2))
        self.assertEqual(
            [r['source'] for r in self.ws.options['effectsQueue']],
            ['1.wav', '2.wav', '0.wav'],
        )
        self.assertEqual(self.ws.options['effectsQueueIndex'], 0)

    def test_download_reorder_respects_active_jobs_and_can_undo(self):
        self.ws.jobs = [
            dict(
                id=str(i),
                url='https://example.com/' + str(i),
                mode='mp4',
                state='Na fila',
                checked=False,
                percent=0,
            )
            for i in range(3)
        ]
        self.ws.refresh_queue()
        self.ws.dispatch('queue_reorder', dict(id='0', target='2'))
        self.assertEqual([r['id'] for r in self.ws.jobs], ['1', '2', '0'])
        self.ws.dispatch('undo_queue', {})
        self.assertEqual([r['id'] for r in self.ws.jobs], ['0', '1', '2'])
        self.ws.jobs[1]['state'] = 'Em andamento'
        self.ws.dispatch('queue_reorder', dict(id='0', target='1'))
        self.assertEqual([r['id'] for r in self.ws.jobs], ['0', '1', '2'])

    def test_download_drag_handle_mouse_and_keyboard(self):
        from PySide6.QtCore import Qt, QPointF
        from PySide6.QtTest import QTest

        self.ws.jobs = [
            dict(
                id=str(i),
                url='https://example.com/' + str(i),
                mode='mp4',
                state='Na fila',
                checked=False,
                percent=0,
            )
            for i in range(3)
        ]
        self.window.setWidth(1360)
        self.window.setHeight(1000)
        self.ws.refresh_queue()
        self.ws.selectPage('queue')
        self.settle()

        def walk(item):
            if item.objectName() == 'downloadQueueDrag':
                yield item
            for child in item.childItems():
                yield from walk(child)

        handles = list(walk(self.window.contentItem()))
        self.assertTrue(handles)
        handle = next(h for h in handles if h.property('rowIndex') == 0)
        card = handle.property('dragItem')
        view = handle.property('listView')
        neighbor = next(h for h in handles if h.property('rowIndex') == 1).property(
            'dragItem'
        )
        neighborY = neighbor.mapToScene(QPointF(0, 0)).y()
        before = card.mapToScene(QPointF(0, 0)).y()
        scroll = view.property('contentY')
        point = card.mapToScene(QPointF(card.width() / 2, 35)).toPoint()
        target = point + __import__('PySide6.QtCore', fromlist=['QPoint']).QPoint(
            0, int(card.height() + 8)
        )
        QTest.mousePress(self.window, Qt.LeftButton, Qt.NoModifier, point)
        QTest.mouseMove(self.window, target, 40)
        self.settle()
        for _ in range(3):
            self.settle()
        self.assertLess(neighbor.mapToScene(QPointF(0, 0)).y(), neighborY - 60)
        self.assertTrue(handle.property('dragging'))
        self.assertGreater(card.mapToScene(QPointF(0, 0)).y() - before, 80)
        self.assertAlmostEqual(view.property('contentY'), scroll, delta=1)
        QTest.mouseMove(self.window, point, 40)
        for _ in range(3):
            self.settle()
        self.assertAlmostEqual(
            neighbor.mapToScene(QPointF(0, 0)).y(), neighborY, delta=2
        )
        QTest.mouseMove(self.window, target, 40)
        for _ in range(3):
            self.settle()
        QTest.mouseRelease(self.window, Qt.LeftButton, Qt.NoModifier, target)
        self.settle()
        self.assertEqual([r['id'] for r in self.ws.jobs], ['1', '0', '2'])
        handle = next(
            h for h in walk(self.window.contentItem()) if h.property('rowIndex') == 0
        )
        handle.forceActiveFocus()
        QTest.keyClick(self.window, Qt.Key_Down)
        self.settle()
        self.assertEqual([r['id'] for r in self.ws.jobs], ['0', '1', '2'])

    def test_playback_card_body_follows_drag(self):
        from PySide6.QtCore import Qt, QPointF, QPoint
        from PySide6.QtTest import QTest

        self.seed()
        self.window.setWidth(1360)
        self.window.setHeight(900)
        for effects in (True, False):
            self.ws.setOption(
                'effectsQueueOpen' if effects else 'jukeboxQueueOpen', True
            )
            for _ in range(5):
                self.settle()

            def walk(item):
                if item.objectName() == 'playbackQueueDrag' and item.isVisible():
                    yield item
                for child in item.childItems():
                    yield from walk(child)

            handle = next(
                h
                for h in walk(self.window.contentItem())
                if h.property('rowIndex') == 0
            )
            card = handle.property('dragItem')
            view = handle.property('listView')
            scroll = view.property('contentY')
            neighbor = next(
                h
                for h in walk(self.window.contentItem())
                if h.property('rowIndex') == 1
            ).property('dragItem')
            neighborY = neighbor.mapToScene(QPointF(0, 0)).y()
            before = card.mapToScene(QPointF(0, 0)).y()
            point = card.mapToScene(QPointF(card.width() / 2, 25)).toPoint()
            target = point + QPoint(0, int(card.height() + 10))
            QTest.mousePress(self.window, Qt.LeftButton, Qt.NoModifier, point)
            QTest.mouseMove(self.window, target, 40)
            self.settle()
            for _ in range(3):
                self.settle()
            self.assertLess(neighbor.mapToScene(QPointF(0, 0)).y(), neighborY - 40)
            self.assertGreater(card.mapToScene(QPointF(0, 0)).y() - before, 60)
            self.assertAlmostEqual(view.property('contentY'), scroll, delta=1)
            QTest.mouseRelease(self.window, Qt.LeftButton, Qt.NoModifier, target)
            self.settle()
            rows = self.ws.options['effectsQueue'] if effects else self.bridge.playlist
            self.assertEqual(
                rows[1]['source'] if effects else rows[1]['id'],
                '0.wav' if effects else '0',
            )

            def buttons(item):
                if item.objectName() == 'playQueueTrack' and item.isVisible():
                    yield item
                for child in item.childItems():
                    yield from buttons(child)

            button = next(buttons(self.window.contentItem()))
            with patch.object(
                self.ws if effects else self.bridge,
                'play_effects_entry' if effects else 'playQueued',
            ) as play:
                center = button.mapToScene(
                    QPointF(button.width() / 2, button.height() / 2)
                ).toPoint()
                QTest.mouseClick(self.window, Qt.LeftButton, Qt.NoModifier, center)
                self.settle()
                play.assert_called_once_with(0)
            self.ws.setOption(
                'effectsQueueOpen' if effects else 'jukeboxQueueOpen', False
            )
            self.settle()
