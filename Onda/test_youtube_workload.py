import unittest
from unittest.mock import MagicMock, patch

from engine import Logger, build_options
from matching import find_youtube, AmbiguousMatch
from parallel_queue import ParallelQueue
from test_dynamic_downloads import App
from youtube_workload import uses_youtube


class YouTubeWorkloadTests(unittest.TestCase):
    def test_catalog_and_direct_jobs_respect_configured_concurrency(self):
        app = App(5)
        app.jobs['first'].update(url='https://open.spotify.com/track/test', mode='mp3')
        app.jobs['second'].update(url='https://youtu.be/abcdefghijk', mode='mp3')
        app.jobs['unrequested'].update(
            url='https://example.org/media.mp4', mode='video'
        )
        scheduler = ParallelQueue(app)
        with patch('parallel_queue.threading.Thread'):
            scheduler.start(None)
            self.assertEqual(scheduler.workers, {'first', 'second', 'unrequested'})
            self.assertEqual(app.jobs['second']['state'], 'Em andamento')
            scheduler.finish('first', {'success': True, 'cancelled': False})
            self.assertEqual(scheduler.workers, {'second', 'unrequested'})

    def test_youtube_limit_increases_and_decreases_without_interrupting_active_jobs(
        self,
    ):
        app = App(1)
        for job in app.jobs.values():
            job.update(url='https://youtu.be/abcdefghijk', mode='mp3')
        scheduler = ParallelQueue(app)
        with patch('parallel_queue.threading.Thread'):
            scheduler.start(None)
            self.assertEqual(len(scheduler.workers), 1)
            app.concurrent_downloads.set(2)
            scheduler.fill()
            self.assertEqual(len(scheduler.workers), 2)
            app.concurrent_downloads.set(1)
            scheduler.fill()
            self.assertEqual(len(scheduler.workers), 2)
            scheduler.finish('first', {'success': True, 'cancelled': False})
            self.assertEqual(scheduler.workers, {'second'})
            self.assertEqual(app.jobs['unrequested']['state'], 'Na fila')
            scheduler.finish('second', {'success': True, 'cancelled': False})
            self.assertEqual(scheduler.workers, {'unrequested'})

    def test_lossless_catalog_and_unrelated_hosts_are_independent(self):
        for url in (
            'https://youtube.com.evil.test/video',
            'https://example.org/a',
            'invalid',
        ):
            self.assertFalse(uses_youtube({'url': url, 'mode': 'mp3'}))
        self.assertFalse(
            uses_youtube({'url': 'https://www.deezer.com/track/1', 'mode': 'flac'})
        )
        self.assertTrue(
            uses_youtube(
                {'url': 'https://music.youtube.com/watch?v=abcdefghijk', 'mode': 'flac'}
            )
        )

    def test_youtube_has_no_forced_wait_or_fragment_reduction(self):
        base = {'folder': '.', 'mode': 'mp3'}
        self.assertNotIn(
            'sleep_interval', build_options(dict(base, url='https://example.org/song'))
        )
        options = build_options(dict(base, url='https://open.spotify.com/track/test'))
        self.assertEqual(options['concurrent_fragment_downloads'], 2)
        self.assertNotIn('sleep_interval_requests', options)
        self.assertNotIn('sleep_interval', options)

    def test_alternative_queries_reuse_extractor_and_session(self):
        record = {'title': 'Song', 'artists': ['Artist'], 'duration_ms': 120000}
        video = {
            'id': 'abcdefghijk',
            'title': 'Song',
            'channel': 'Artist - Topic',
            'duration': 120,
        }
        factory = MagicMock()
        downloader = factory.return_value.__enter__.return_value
        downloader.extract_info.side_effect = [{'entries': []}, {'entries': [video]}]
        logger = Logger({'cookies_file': 'explicit-session.txt'})
        with patch('yt_dlp.YoutubeDL', factory):
            result = find_youtube(record, logger, prefer_best=True)
        self.assertEqual(result['id'], video['id'])
        factory.assert_called_once()
        self.assertEqual(downloader.extract_info.call_count, 2)
        self.assertEqual(
            factory.call_args.args[0]['cookiefile'], 'explicit-session.txt'
        )
        self.assertNotIn('sleep_interval_requests', factory.call_args.args[0])
        self.assertIs(logger.youtube_cookiejar, downloader.cookiejar)

    def test_manual_choice_retains_search_session(self):
        factory = MagicMock()
        downloader = factory.return_value.__enter__.return_value
        logger = Logger()
        with (
            patch('yt_dlp.YoutubeDL', factory),
            patch('matching._find_youtube', side_effect=AmbiguousMatch([])),
        ):
            with self.assertRaises(AmbiguousMatch):
                find_youtube({'title': 'Song', 'artists': ['Artist']}, logger)
        self.assertIs(logger.youtube_cookiejar, downloader.cookiejar)


if __name__ == '__main__':
    unittest.main()
