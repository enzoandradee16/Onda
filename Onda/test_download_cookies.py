import unittest
from download_defaults import download_cookies


class DownloadCookieTests(unittest.TestCase):
    def test_instagram_session_never_leaks_to_other_platforms(self):
        self.assertEqual(download_cookies('https://www.instagram.com/reel/1', 'social', 'youtube', 'instagram'), 'instagram')
        for url in ('https://www.tiktok.com/@a/video/1', 'https://kw.ai/1', 'https://instagram.com.example.org/'):
            self.assertEqual(download_cookies(url, 'social', 'youtube', 'instagram'), 'social')
        self.assertEqual(download_cookies('https://youtu.be/1', 'social', 'youtube', 'instagram'), 'youtube')
    def test_platform_sessions_are_independent(self):
        for url in (
            'https://instagram.com/p/1',
            'https://www.tiktok.com/@user/video/1',
            'https://kw.ai/123',
            'https://youtube.com.example.org/video',
        ):
            with self.subTest(url=url):
                self.assertEqual(download_cookies(url, 'social', 'youtube'), 'social')
        for url in (
            'https://youtu.be/123',
            'https://www.youtube.com/watch?v=123',
            'https://music.youtube.com/watch?v=123',
            'https://open.spotify.com/track/' + 'A' * 22,
            'https://www.deezer.com/track/1',
        ):
            with self.subTest(url=url):
                self.assertEqual(download_cookies(url, 'social', 'youtube'), 'youtube')

    def test_missing_files_preserve_fallback_without_using_youtube_on_social(self):
        self.assertEqual(
            download_cookies('https://youtu.be/123', 'social', ''), 'social'
        )
        self.assertEqual(
            download_cookies('https://instagram.com/p/1', '', 'youtube'), ''
        )
        self.assertEqual(download_cookies('https://youtu.be/123'), '')
