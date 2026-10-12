import os
import tempfile
import unittest
from unittest.mock import Mock, patch

from queue_titles import record_name, resolve_name


class QueueNameTests(unittest.TestCase):
    def test_youtube_metadata_lookup_never_downloads_media(self):
        with patch('yt_dlp.YoutubeDL') as downloader:
            downloader.return_value.__enter__.return_value.extract_info.return_value = {'title': 'Song'}
            self.assertEqual(resolve_name('https://youtu.be/abcdefghijk', ('', ''), ''), 'Song')
            self.assertTrue(downloader.call_args.args[0]['skip_download'])
            downloader.return_value.__enter__.return_value.extract_info.assert_called_once_with(
                'https://youtu.be/abcdefghijk', download=False)

    def test_imported_plain_links_are_not_mislabeled_as_song_titles(self):
        self.assertIsNone(record_name({'title': 'https://example.com/song'}))
        self.assertEqual(record_name({'title': 'Song', 'artists': ['Artist', 'Guest']}), 'Artist, Guest - Song')


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'), 'Tk integration')
class QueueNameUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name})
        self.env.start()
        from app import App
        self.app = App(show_welcome=False)
        self.app.withdraw()
        self.app.folder.set(self.temp.name)

    def tearDown(self):
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def test_playlist_and_album_names_appear_before_download_and_survive_restart(self):
        app = self.app
        page = app.playlist_page
        with patch.object(app.title_lookup, 'submit') as lookup:
            page.display({'title': 'Album', 'note': '', 'tracks': [
                {'title': 'Song', 'artists': ['Artist'], 'source_url': 'https://www.deezer.com/track/1'},
                {'title': 'Video title', 'artists': ['Channel'], 'source_url': 'https://youtu.be/abcdefghijk'}]})
            page.add()
            lookup.assert_not_called()
        self.assertEqual([app.tree.set(item, 'name') for item in app.jobs], ['Artist - Song', 'Channel - Video title'])
        self.assertFalse(app.running)
        app.destroy()
        from app import App
        self.app = App(show_welcome=False)
        self.app.withdraw()
        self.assertEqual([self.app.tree.set(item, 'name') for item in self.app.jobs], ['Artist - Song', 'Channel - Video title'])

    def test_search_name_is_saved_before_starting(self):
        self.app.queue_catalog({'title': 'Song', 'artists': ['Artist'], 'source_url': 'https://www.deezer.com/track/1'}, 'mp3')
        job = next(iter(self.app.jobs.values()))
        self.assertEqual(job['display_name'], 'Artist - Song')
        self.assertEqual(self.app.library.load_queue()[0]['display_name'], 'Artist - Song')

    def test_direct_link_updates_async_and_deleted_or_active_items_are_ignored(self):
        app = self.app
        url = 'https://youtu.be/abcdefghijk'
        app.urls.insert('1.0', url)
        with patch.object(app.title_lookup, 'submit') as lookup:
            key = app.add()[0]
            lookup.assert_called_once()
        self.assertEqual(app.tree.set(key, 'name'), url)
        app.events.put((key, {'type': 'queue_title', 'url': url, 'title': 'Song'}))
        app.after_cancel(app._poll_after)
        app.poll_events()
        self.assertEqual(app.tree.set(key, 'name'), 'Song')
        self.assertEqual(app.library.load_queue()[0]['display_name'], 'Song')
        app.events.put(('missing', {'type': 'queue_title', 'url': url, 'title': 'Ignored'}))
        app.jobs[key]['state'] = 'Em andamento'
        app.events.put((key, {'type': 'queue_title', 'url': url, 'title': 'Other version'}))
        app.after_cancel(app._poll_after)
        app.poll_events()
        self.assertEqual(app.tree.set(key, 'name'), 'Song')
