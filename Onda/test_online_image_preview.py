"""Online gallery lookup never queues, publishes, or saves original images."""

import io, json, tempfile, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import online_image_preview as preview


class OnlineImagePreviewTests(unittest.TestCase):
    def test_preview_button_filters_audio_video_and_music_covers(self):
        self.assertTrue(
            preview.can_preview({'url': 'https://example.com/image.png', 'mode': 'mp3'})
        )
        self.assertTrue(
            preview.can_preview(
                {'url': 'https://instagram.com/p/carousel', 'mode': 'photos'}
            )
        )
        self.assertTrue(
            preview.can_preview(
                {'url': 'https://instagram.com/p/mixed', 'mode': 'social'}
            )
        )
        self.assertFalse(
            preview.can_preview({'url': 'https://instagram.com/p/music', 'mode': 'mp3'})
        )
        self.assertFalse(
            preview.can_preview(
                {'url': 'https://example.com/movie.mp4', 'mode': 'social'}
            )
        )
        self.assertFalse(
            preview.can_preview(
                {'url': 'https://example.com/song.flac', 'mode': 'photos'}
            )
        )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.requests = []
        content = io.BytesIO()
        Image.new('RGB', (1800, 600), 'red').save(content, 'PNG')
        self.image = content.getvalue()
        case = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                case.requests.append((self.path, self.headers.get('Referer')))
                if self.path == '/post':
                    body = b'<meta property="og:image" content="/one.png"><meta property="og:video" content="/video.mp4"><meta property="og:image" content="/two.png">'
                    mime = 'text/html'
                elif self.path == '/empty':
                    body = b'<html>No images</html>'
                    mime = 'text/html'
                else:
                    body = case.image
                    mime = 'image/png'
                self.send_response(200)
                self.send_header('Content-Type', mime)
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = 'http://127.0.0.1:' + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def discover(self, path='/post'):
        return preview.discover({'url': self.base + path, '_root': str(self.root)})

    def test_manifest_reads_metadata_only_then_fetches_each_image_lazily(self):
        with patch(
            'social_media.save_media', side_effect=AssertionError('No download/export')
        ):
            result = self.discover()
            self.assertEqual(len(result['images']), 2)
            self.assertEqual([r[0] for r in self.requests], ['/post'])
            self.assertFalse(list(self.root.rglob('*.png')))
            self.assertFalse(list(self.root.rglob('*.jpg')))
            first = preview.thumbnail(result['token'], 0)
            self.assertEqual([r[0] for r in self.requests], ['/post', '/one.png'])
            self.assertEqual(self.requests[-1][1], self.base + '/post')
            with Image.open(first['path']) as image:
                self.assertEqual(image.size, (1280, 427))
                self.assertEqual(image.format, 'JPEG')
            self.assertEqual(preview.thumbnail(result['token'], 0), first)
            self.assertEqual(len(self.requests), 2)
            second = preview.thumbnail(result['token'], 1)
            self.assertNotEqual(second['path'], first['path'])
            self.assertEqual(self.requests[-1][0], '/two.png')

    def test_direct_and_google_image_links_do_not_require_a_download(self):
        url = 'https://www.google.com/imgres?imgurl=' + self.base + '/one.png'
        result = preview.discover({'url': url, '_root': str(self.root)})
        self.assertEqual(result['source_url'], self.base + '/one.png')
        self.assertEqual(len(result['images']), 1)
        self.assertFalse(list(self.root.rglob('*.jpg')))

    def test_tiktok_carousel_uses_existing_extractor_and_ignores_videos(self):
        rows = [
            (self.base + '/one.png', {'title': 'Photo', 'extension': 'png'}),
            (self.base + '/video.mp4', {'extension': 'mp4'}),
        ]
        with patch('tiktok_media.tiktok_items', return_value=rows) as extract:
            result = preview.discover(
                {
                    'url': 'https://www.tiktok.com/@user/photo/123',
                    '_root': str(self.root),
                }
            )
        extract.assert_called_once()
        self.assertEqual(len(result['images']), 1)
        self.assertEqual(self.requests, [])

    def test_other_supported_galleries_use_instance_settings_without_downloading(self):
        from gallery_dl.extractor.common import Message
        import requests

        class Source:
            subcategory = 'gallery'
            session = requests.Session()

            def config(self, key, default=None):
                return default

            def __iter__(self):
                yield Message.Url, self_url, {'extension': 'png', 'title': 'Gallery'}

        self_url = self.base + '/one.png'
        source = Source()
        with (
            patch('gallery_dl.extractor.find', return_value=source),
            patch('gallery_dl.config.set') as global_settings,
        ):
            result = self.discover()
        self.assertEqual(len(result['images']), 1)
        self.assertEqual(source.config('timeout'), 20)
        global_settings.assert_not_called()
        self.assertEqual(self.requests, [])

    def test_thumbnail_is_in_cleanable_cache_and_originals_are_preserved(self):
        from cache_cleanup import clear_cache, cache_info

        original = self.root / 'original.png'
        original.write_bytes(self.image)
        result = self.discover()
        path = Path(preview.thumbnail(result['token'], 0)['path'])
        self.assertGreater(cache_info(self.root)['bytes'], 0)
        clear_cache(self.root)
        self.assertFalse(path.exists())
        self.assertEqual(original.read_bytes(), self.image)

    def test_cancelled_thumbnail_never_creates_a_file(self):
        result = self.discover()
        with self.assertRaises(InterruptedError):
            preview.thumbnail(result['token'], 0, lambda: True)
        self.assertFalse(list(self.root.rglob('*.jpg')))
        self.assertEqual(len(self.requests), 1)

    def test_no_images_and_multiple_links_have_clear_errors(self):
        with self.assertRaisesRegex(ValueError, 'Nenhuma imagem'):
            self.discover('/empty')
        with self.assertRaisesRegex(ValueError, 'um link por vez'):
            preview.discover(
                {
                    'url': self.base + '/post\n' + self.base + '/one.png',
                    '_root': str(self.root),
                }
            )

    def test_invalid_indices_tokens_and_expiration_do_not_access_files(self):
        result = self.discover()
        for token, index in [
            ('unknown', 0),
            (result['token'], -1),
            (result['token'], 2),
        ]:
            with self.assertRaises(ValueError):
                preview.thumbnail(token, index)
        with preview._lock:
            preview._sessions[result['token']]['created'] -= 901
        with self.assertRaisesRegex(ValueError, 'expirou'):
            preview.thumbnail(result['token'], 0)

    def test_size_limit_does_not_leave_partial_thumbnail(self):
        result = self.discover()
        with patch('online_image_preview.MAX_BYTES', 1):
            # read_limited has an explicit default; exercise the bounded reader directly.
            from types import SimpleNamespace

            with self.assertRaisesRegex(ValueError, 'limite'):
                preview.read_limited(
                    SimpleNamespace(iter_content=lambda _: iter([b'123'])),
                    lambda: False,
                    2,
                )
        self.assertFalse(list(self.root.rglob('*.jpg')))
