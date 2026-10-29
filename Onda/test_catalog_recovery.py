import unittest
from unittest.mock import Mock, patch
import requests
from catalog_recovery import download_recording
from matching import NoCompatibleMatch
from tagging import fetch_cover, optional_cover


class RecoveryTests(unittest.TestCase):
    def test_cover_retries_transient_failure(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.iter_content.return_value = [b"\xff\xd8\xffimage"]
        with (
            patch('requests.get', side_effect=[requests.Timeout(), response]) as get,
            patch('time.sleep'),
        ):
            self.assertEqual(fetch_cover('https://example.com/cover')[1], 'image/jpeg')
            self.assertEqual(get.call_count, 2)

    def test_cover_outage_is_optional_and_bounded(self):
        emit = Mock()
        with (
            patch('requests.get', side_effect=requests.Timeout()) as get,
            patch('time.sleep'),
        ):
            self.assertIsNone(optional_cover('https://example.com/cover', emit))
            self.assertEqual(get.call_count, 3)
        emit.assert_called_once()

    def test_cover_http404_not_retried(self):
        error = requests.HTTPError()
        error.response = Mock(status_code=404)
        with patch('requests.get', side_effect=error) as get:
            self.assertIsNone(optional_cover('https://example.com/cover', Mock()))
            self.assertEqual(get.call_count, 1)

    def test_revalidation_and_age_failures_try_another_candidate(self):
        for error in [
            NoCompatibleMatch('invalid'),
            RuntimeError('Sign in to confirm your age'),
        ]:
            logger = Mock()
            logger.excluded_youtube_ids = ()
            download = Mock(side_effect=[error, 0])

            def resolve(*args, **kwargs):
                self.assertEqual(logger.excluded_youtube_ids, {'first'})
                return {'id': 'second'}

            with patch('matching.resolve_youtube', side_effect=resolve):
                self.assertEqual(
                    download_recording(
                        {},
                        {'id': 'first'},
                        logger,
                        Mock(),
                        download,
                        [],
                        automatic=True,
                    ),
                    0,
                )
            self.assertEqual(logger.excluded_youtube_ids, ())

    def test_manual_saved_and_unrelated_failures_not_retried(self):
        for selected, saved, error in [
            ({'id': 'first', 'selection': 'user'}, [], NoCompatibleMatch('invalid')),
            ({'id': 'first'}, ['done.mp3'], NoCompatibleMatch('invalid')),
            ({'id': 'first'}, [], OSError('disk full')),
            ({'id': 'first'}, [], RuntimeError('HTTP Error 403')),
        ]:
            with patch('matching.resolve_youtube') as resolve:
                with self.assertRaises(type(error)):
                    download_recording(
                        {},
                        selected,
                        Mock(excluded_youtube_ids=()),
                        Mock(),
                        Mock(side_effect=error),
                        saved,
                    )
                resolve.assert_not_called()

    def test_recovery_is_bounded(self):
        logger = Mock(excluded_youtube_ids=())
        download = Mock(side_effect=NoCompatibleMatch('invalid'))
        with patch(
            'matching.resolve_youtube', side_effect=[{'id': 'second'}, {'id': 'third'}]
        ) as resolve:
            with self.assertRaises(NoCompatibleMatch):
                download_recording({}, {'id': 'first'}, logger, Mock(), download, [])
            self.assertEqual(download.call_count, 3)
            self.assertEqual(resolve.call_count, 2)

    def test_search_excludes_failed_ids(self):
        from matching import _find_youtube

        downloader = Mock()
        downloader.extract_info.return_value = {
            'entries': [{'id': 'bad'}, {'id': 'good'}]
        }
        with patch('matching.select_candidate', return_value={'id': 'good'}) as select:
            _find_youtube(
                {'artists': ['Artist'], 'title': 'Track'},
                downloader,
                excluded_ids={'bad'},
            )
            self.assertEqual(select.call_args.args[1], [{'id': 'good'}])
