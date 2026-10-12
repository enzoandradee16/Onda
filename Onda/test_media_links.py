import http.server
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path
from media_links import unwrap_google, prepare_link
from engine import validate_url


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        paths = {
            '/photo': ('image/png', b'\x89PNG\r\n\x1a\noriginal-image'),
            '/video': ('video/mp4', b'video'),
            '/audio': ('audio/mpeg', b'audio'),
            '/page': ('text/html', b'<video><source src="/video"></video>'),
            '/image-page': ('text/html', b'<meta property="og:image" content="/photo">'),
            '/empty': ('text/html', b'<html>No media</html>'),
        }
        mime, data = paths[self.path]
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class MediaLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def resolve(self, route, mode='mp4'):
        self.events=[]
        self.config={'url':self.base+route,'mode':mode,'folder':self.folder,'duplicate_policy':'keep'}
        return prepare_link(self.config,lambda event,**data:self.events.append((event,data)),None)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder=self.temp.name

    def test_google_wrappers_validate_destination(self):
        self.assertEqual(validate_url('https://www.google.com/imgres?imgurl=https%3A%2F%2Fexample.com%2Fpic.png'),'https://example.com/pic.png')
        self.assertEqual(unwrap_google('https://www.google.com.br/url?q=https%3A%2F%2Fexample.com%2Fmovie.mp4'),'https://example.com/movie.mp4')
        with self.assertRaises(ValueError):
            validate_url('https://google.com/url?q=https%3A%2F%2Fuser%3Asecret%40example.com%2Fa')
        search='https://google.com/search?q=cats'
        self.assertEqual(unwrap_google(search),search)

    def test_image_without_extension_downloads_original_and_reports(self):
        self.assertTrue(self.resolve('/photo')[0])
        files=list(Path(self.folder).glob('*.png'))
        self.assertEqual(len(files),1)
        self.assertEqual(files[0].read_bytes(),b'\x89PNG\r\n\x1a\noriginal-image')
        self.assertIn('done',[event for event,_ in self.events])
        self.assertIn('file',[event for event,_ in self.events])
        self.assertIn('progress',[event for event,_ in self.events])

    def test_embedded_video_and_automatic_format(self):
        self.assertEqual(self.resolve('/page','photos'),(False,self.base+'/video'))
        self.assertEqual(self.config['mode'],'mp4')
        self.assertEqual(self.resolve('/audio','social'),(False,self.base+'/audio'))
        self.assertEqual(self.config['mode'],'original')

    def test_page_image_only_when_photo_mode(self):
        self.assertEqual(self.resolve('/image-page'),(False,self.base+'/image-page'))
        self.assertTrue(self.resolve('/image-page','photos')[0])
        with self.assertRaisesRegex(ValueError,'Não foi encontrada'):
            self.resolve('/empty','photos')

    def test_worker_finishes_image_without_ffmpeg_or_video_extractor(self):
        from engine import run_worker
        events=[]
        config={'url':self.base+'/photo','mode':'mp3','folder':self.folder,'duplicate_policy':'keep'}
        with patch('engine.emit',side_effect=lambda event,**data:events.append((event,data))), patch('engine.binaries',return_value=False):
            self.assertEqual(run_worker(config),0)
        self.assertEqual(events[-1][0],'done')
        self.assertTrue(Path(events[-1][1]['files'][0]).is_file())


if __name__=='__main__':
    unittest.main()
