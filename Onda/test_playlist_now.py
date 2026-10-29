import os
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(
    os.environ.get('ONDA_UI_TESTS') and os.environ.get('ONDA_FFMPEG'),
    'Tk and FFmpeg integration',
)
class PlaylistDownloadNowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.profile = patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name})
        self.profile.start()
        from app import App

        self.app = App()
        self.app.withdraw()
        self.app.folder.set(self.temp.name)
        self.app.ffmpeg.set(os.environ['ONDA_FFMPEG'])

    def tearDown(self):
        self.app.set_progress(0)
        self.app.destroy()
        self.profile.stop()
        self.temp.cleanup()

    def test_now_uses_own_format_and_downloads_only_visible_selection(self):
        app = self.app
        old = app.add(
            lines=['https://www.deezer.com/track/99'], overrides={'mode': 'mp3'}
        )[0]
        page = app.playlist_page
        page.display(
            {
                'title': 'Album',
                'folder_title': 'Artist - Album',
                'note': '',
                'tracks': [
                    {
                        'title': 'Song One',
                        'source_url': 'https://www.deezer.com/track/1',
                    },
                    {'title': 'Hidden', 'source_url': 'https://www.deezer.com/track/2'},
                    {
                        'title': 'Song Two',
                        'source_url': 'https://www.deezer.com/track/3',
                    },
                ],
            }
        )
        app.playlist_mode.set('Áudio · MP3 (320 kbps)')
        app.playlist_mp3_quality.set('192 kbps')
        app.mp3_quality.set('96 kbps')
        page.filter_text.set('Song')
        page.table.selection_set(page.table.get_children())
        with patch('app.threading.Thread') as thread:
            page.download_now_button.invoke()
            chosen = [key for key in app.jobs if key != old]
            self.assertEqual(len(chosen), 2)
            self.assertEqual(app.parallel.scope, set(chosen))
            self.assertEqual(app.active, chosen[0])
            for key in chosen:
                self.assertEqual(app.jobs[key]['audio_quality'], '192 kbps')
                self.assertEqual(app.jobs[key]['playlist_title'], 'Artist - Album')
                self.assertEqual(app.jobs[key]['mode'], 'mp3')
                app.parallel.finish(key, {'success': True, 'cancelled': False})
            self.assertEqual(thread.call_count, 2)
        self.assertFalse(app.running)
        self.assertIsNone(app.immediate_item)
        self.assertEqual(app.jobs[old]['state'], 'Na fila')

    def test_reuses_selected_pending_items_and_busy_guard(self):
        app = self.app
        page = app.playlist_page
        page.display(
            {
                'title': 'Playlist',
                'note': '',
                'tracks': [
                    {'title': 'Song', 'source_url': 'https://www.deezer.com/track/1'}
                ],
            }
        )
        page.add()
        self.assertEqual(len(app.jobs), 1)
        with patch('app.threading.Thread'):
            page.add(start=True)
        self.assertEqual(len(app.jobs), 1)
        with patch.object(app.parallel, 'extend') as extend:
            page.add(start=True)
            extend.assert_called_once()
        self.assertTrue(app.running)

    def test_button_disabled_during_load_and_empty_selection_does_not_start(self):
        page = self.app.playlist_page
        page.set_busy(True)
        self.assertEqual(str(page.download_now_button['state']), 'disabled')
        page.set_busy(False)
        with patch.object(self.app, 'start') as start:
            page.add(start=True)
            start.assert_not_called()
