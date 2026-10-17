import unittest
from unittest.mock import Mock,patch
from clipboard_links import recognize_link
from advanced_options import DEFAULTS
from preferences import PreferenceStore

URL='https://www.youtube.com/watch?v=dQw4w9WgXcQ'
class RecognitionTests(unittest.TestCase):
    def test_supported_links_and_embedded_text_without_network(self):
        urls=[URL,'https://instagram.com/p/test/','https://vm.tiktok.com/test/','https://kw.ai/test','https://example.com/image.jpg','https://open.spotify.com/track/2iUWwgpnvKT17EcbxHlq5n']
        with patch('requests.sessions.Session.request',side_effect=AssertionError('network before confirmation')):
            for url in urls:
                self.assertIsNotNone(recognize_link('Veja: '+url+'.'),url)
    def test_tracking_variants_deduplicate(self):
        self.assertEqual(recognize_link(URL+'&si=one')['key'],recognize_link('https://youtu.be/dQw4w9WgXcQ?si=two')['key'])
    def test_collections_use_existing_collection_flow(self):
        for url in ['https://open.spotify.com/playlist/4LIPss85VQYyuVdNMbdHkn','spotify:album:1234567890123456789012','https://www.deezer.com/playlist/123']:
            self.assertTrue(recognize_link(url)['collection'])
    def test_invalid_text_and_unsafe_urls_ignored(self):
        for text in ['',None,'hello','https://github.com/enzoandradee16/Onda','https://user:secret@youtube.com/watch?v=x','file:///x.mp4','https://instagram.com','https://open.spotify.com/playlist/bad','a'*16385]:
            self.assertIsNone(recognize_link(text),text)
    def test_default_and_persistence_cleaner(self):
        self.assertTrue(DEFAULTS['clipboard_links'])
        self.assertFalse(PreferenceStore.clean({'clipboard_links':False})['clipboard_links'])

class WatchTests(unittest.TestCase):
    def app(self):
        app=Mock();app.clipboard_links.get.return_value=True;app.grab_current.return_value=None;app.updating=False;app.clipboard_get.return_value=URL
        return app
    def test_confirmation_dedup_and_shutdown(self):
        from clipboard_watch import ClipboardWatch
        app=self.app();watch=ClipboardWatch(app)
        with patch('clipboard_watch.ctypes.windll.user32.GetClipboardSequenceNumber',side_effect=[1,2]),patch('clipboard_watch.messagebox.askyesno',return_value=False) as ask:
            watch.poll();watch.poll();ask.assert_called_once();app.download_clipboard_link.assert_not_called()
        watch.shutdown();self.assertTrue(watch.closed);app.after_cancel.assert_called_once()
    def test_download_only_after_explicit_confirmation(self):
        from clipboard_watch import ClipboardWatch
        app=self.app();watch=ClipboardWatch(app)
        with patch('clipboard_watch.ctypes.windll.user32.GetClipboardSequenceNumber',return_value=1),patch('clipboard_watch.messagebox.askyesno',return_value=True):watch.poll()
        app.download_clipboard_link.assert_called_once();watch.shutdown()
    def test_disabled_and_modal_do_not_read_clipboard(self):
        from clipboard_watch import ClipboardWatch
        app=self.app();watch=ClipboardWatch(app);app.clipboard_links.get.return_value=False
        watch.poll();app.clipboard_get.assert_not_called()
        app.clipboard_links.get.return_value=True;app.grab_current.return_value=object();watch.poll();app.clipboard_get.assert_not_called();watch.shutdown()
    def test_confirmed_routes_reuse_existing_downloads(self):
        from app import App
        app=Mock();app.add.return_value=['job']
        App.download_clipboard_link(app,{'url':URL,'collection':False});app.start.assert_called_once_with(only_item='job')
        App.download_clipboard_link(app,{'url':'https://open.spotify.com/playlist/4LIPss85VQYyuVdNMbdHkn','collection':True})
        app.playlist_page.load.assert_called_once_with(start_download=True)
