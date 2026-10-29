"""History deletion is record-only; media filters and origin badges stay consistent."""

import os, tempfile, unittest
from pathlib import Path
from library import LibraryStore
from platform_info import history_kind, platform_info, platforms


class HistoryRecordsTests(unittest.TestCase):
    def test_remove_one_record_preserves_file_companions_and_duplicate_record(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Música.mp3'
            path.write_bytes(b'audio')
            cover = path.with_suffix('.jpg')
            cover.write_bytes(b'cover')
            store = LibraryStore(Path(folder) / 'history.db')
            for _ in range(2):
                store.add_history(path, 'mp3', 'https://vt.tiktok.com/example/')
            newest, older = store.history()
            store.remove_history(newest['id'])
            store.remove_history(
                newest['id']
            )  # Safe if a stale button is activated twice.
            self.assertEqual([r['id'] for r in store.history()], [older['id']])
            self.assertEqual(path.read_bytes(), b'audio')
            self.assertEqual(cover.read_bytes(), b'cover')
            self.assertIsNotNone(store.find_duplicate(newest['source'], 'mp3'))

    def test_media_filter_combines_with_search_and_original_container(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LibraryStore(Path(folder) / 'history.db')
            for name, mode in [
                ('Álbum.mp3', 'mp3'),
                ('Álbum.mp4', 'original'),
                ('Álbum.gif', 'photos'),
                ('Other.png', 'png'),
            ]:
                store.add_history(Path(folder) / name, mode)
            self.assertEqual(len(store.history(kind='Todos')), 4)
            for kind, ext in [
                ('Áudio', '.mp3'),
                ('Vídeo', '.mp4'),
                ('Imagens', '.gif'),
            ]:
                rows = store.history('ÁLBUM', kind)
                self.assertEqual(len(rows), 1)
                self.assertTrue(rows[0]['path'].endswith(ext))
            self.assertEqual(len(store.history(kind='Imagens')), 2)
            self.assertEqual(history_kind('original', 'movie.webm'), 'Vídeo')
            self.assertEqual(history_kind('original', 'song.flac'), 'Áudio')

    def test_filter_applied_before_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LibraryStore(Path(folder) / 'history.db')
            with store.connect() as db:
                db.executemany(
                    'INSERT INTO history(path,name,mode) VALUES(?,?,?)',
                    [(str(Path(folder) / 'old.avif'), 'old', 'photos')]
                    + [(f'{i}.mp3', str(i), 'mp3') for i in range(1001)],
                )
            self.assertEqual(len(store.history()), 1000)
            self.assertEqual(store.history(kind='Imagens')[0]['name'], 'old')


class PlatformIdentityTests(unittest.TestCase):
    def test_short_links_and_subdomains(self):
        for url, key in [
            ('https://vt.tiktok.com/ZSg9jRoa3/', 'tiktok'),
            ('https://vm.tiktok.com/x', 'tiktok'),
            ('https://k.kwai.com/p/HC4BlW9o', 'kwai'),
            ('https://kwai-video.com/p/BUZC05Uf', 'kwai'),
            ('https://www.instagram.com/reel/x/', 'instagram'),
            ('https://fb.watch/x', 'facebook'),
            ('https://x.com/user/status/123', 'twitter'),
            ('https://soundcloud.com/a/b', 'soundcloud'),
            ('spotify:track:123', 'spotify'),
        ]:
            with self.subTest(url=url):
                self.assertEqual(platform_info(url)['platform_key'], key)

    def test_metadata_priority_and_safe_unknown_fallback(self):
        self.assertEqual(
            platform_info('https://youtube.com/watch?v=x', 'Spotify')['platform_key'],
            'spotify',
        )
        self.assertEqual(
            platform_info('https://www.instagram.com.evil.example/x'),
            {'platform_key': 'link', 'platform': 'instagram.com.evil.example'},
        )
        for source in [
            '',
            r'C:\Music\song.mp3',
            'file:///song.mp3',
            'https://instagram.com@evil.example/x',
        ]:
            self.assertEqual(platform_info(source)['platform_key'], '')
        for alias in ['Apple / iTunes', 'AppleMusic', 'iTunes', 'Apple Music']:
            self.assertEqual(platform_info(name=alias)['platform_key'], 'apple_music')

    def test_every_catalog_platform_has_packaged_icons(self):
        root = Path(__file__).parent
        for row in platforms():
            self.assertTrue(
                (root / 'assets/platforms' / f"{row['key']}.png").is_file(), row['key']
            )
            self.assertTrue(
                (
                    root.parent
                    / 'Android/app/src/main/res/drawable'
                    / f"metadata_{row['key']}.png"
                ).is_file(),
                row['key'],
            )


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt desktop tests')
class DesktopHistoryTests(unittest.TestCase):
    def setUp(self):
        import test_qt_playback_queue as harness

        self.case = harness.PlaybackQueueDrawerTests()
        self.case.setUp()

    def tearDown(self):
        self.case.tearDown()

    def walk(self, node):
        yield node
        for child in node.childItems():
            yield from self.walk(child)

    def test_image_badge_keeps_domain_and_native_image_icon(self):
        ws = self.case.ws
        ws.library.add_history(
            Path(self.case.temp.name) / 'photo.png',
            'png',
            'https://images.example.com/photo.png',
        )
        ws.selectPage('history')
        self.case.settle()
        self.assertTrue(ws.models['history'].rows[0]['is_image'])
        self.assertEqual(ws.models['history'].rows[0]['platform'], 'images.example.com')
        icons = [
            n
            for n in self.walk(self.case.window.contentItem())
            if n.objectName() == 'imageMediaIcon' and n.isVisible()
        ]
        self.assertTrue(icons)
        self.assertTrue(
            ws.queue_record({'url': 'https://example.com/pic', 'mode': 'photos'})[
                'is_image'
            ]
        )
        self.assertFalse(
            ws.queue_record({'url': 'https://example.com/song', 'mode': 'mp3'})[
                'is_image'
            ]
        )

    def test_filtered_card_removal_by_button_and_context_keeps_files(self):
        from PySide6.QtCore import QMetaObject

        ws = self.case.ws
        for name, mode, url in [
            ('keep.mp4', 'mp4', 'https://k.kwai.com/p/test'),
            ('remove.mp3', 'mp3', 'https://vt.tiktok.com/test'),
        ]:
            path = Path(self.case.temp.name) / name
            path.write_bytes(b'fixture')
            ws.library.add_history(path, mode, url)
        ws.selectPage('history')
        ws.setOption('historyKind', 'Áudio')
        self.case.settle()
        self.assertEqual(len(ws.models['history'].rows), 1)
        self.assertEqual(ws.models['history'].rows[0]['platform_key'], 'tiktok')
        cards = [
            n
            for n in self.walk(self.case.window.contentItem())
            if n.objectName() == 'libraryTrackCard' and n.isVisible()
        ]
        self.assertTrue(cards)
        button = next(
            n for n in self.walk(cards[0]) if n.objectName() == 'removeHistoryButton'
        )
        self.assertTrue(QMetaObject.invokeMethod(button, 'clicked'))
        self.case.settle()
        self.assertEqual(len(ws.models['history'].rows), 0)
        ws.setOption('historyKind', 'Vídeo')
        self.case.settle()
        cards = [
            n
            for n in self.walk(self.case.window.contentItem())
            if n.objectName() == 'libraryTrackCard' and n.isVisible()
        ]
        menu = cards[0].findChild(
            __import__('PySide6.QtCore', fromlist=['QObject']).QObject,
            'removeHistoryContext',
        )
        self.assertTrue(QMetaObject.invokeMethod(menu, 'triggered'))
        self.case.settle()
        self.assertFalse(ws.library.history())
        for name in ['keep.mp4', 'remove.mp3']:
            self.assertTrue((Path(self.case.temp.name) / name).exists())
