import unittest
from history_origin import history_origin


class HistoryOriginTests(unittest.TestCase):
    def test_recorded_identities(self):
        for source, url in [
            ('spotify:track:abc', 'https://open.spotify.com/track/abc'),
            ('deezer:track:123', 'https://www.deezer.com/track/123'),
            ('youtube:video:abc-123', 'https://www.youtube.com/watch?v=abc-123'),
            ('youtube:playlist:PL123', 'https://www.youtube.com/playlist?list=PL123'),
        ]:
            self.assertEqual(history_origin(source), url)

    def test_web_links_and_missing_or_unsafe_sources(self):
        self.assertEqual(
            history_origin('https://music.apple.com/br/song/123'),
            'https://music.apple.com/br/song/123',
        )
        for source in (
            '',
            'file:///C:/x',
            'javascript:alert(1)',
            'C:/Downloads/a.mp3',
            'https://',
            'https://user:password@example.com',
        ):
            self.assertEqual(history_origin(source), '')
