import unittest
from unittest.mock import MagicMock, Mock, patch
import requests
from social_recovery import public_html, public_response, retry_metadata, script_json


class SocialRecoveryTests(unittest.TestCase):
    def test_transient_http_retries_once_and_closes_failed_response(self):
        first = Mock(status_code=503, headers={'Retry-After': '0'})
        first.raise_for_status.side_effect = requests.HTTPError(response=first)
        second = Mock(status_code=200)
        session = Mock()
        session.get.side_effect = [first, second]
        with patch('social_recovery.time.sleep') as sleep:
            self.assertIs(public_response(session, 'https://example.com'), second)
        self.assertEqual(session.get.call_count, 2)
        first.close.assert_called_once()
        sleep.assert_called_once_with(0.5)

    def test_auth_missing_post_and_long_retry_after_do_not_retry(self):
        for status, header in [
            (401, ''),
            (403, ''),
            (404, ''),
            (429, '3600'),
            (429, 'Wed, 01 Jan 2100 00:00:00 GMT'),
        ]:
            with self.subTest(status=status, header=header):
                response = Mock(status_code=status, headers={'Retry-After': header})
                response.raise_for_status.side_effect = requests.HTTPError(
                    response=response
                )
                session = Mock()
                session.get.return_value = response
                with (
                    patch('social_recovery.time.sleep') as sleep,
                    self.assertRaises(requests.HTTPError),
                ):
                    public_response(session, 'https://example.com')
                session.get.assert_called_once()
                sleep.assert_not_called()

    def test_timeout_is_bounded_and_wrapped_metadata_errors_are_supported(self):
        from yt_dlp.utils import ExtractorError

        operation = Mock(
            side_effect=ExtractorError(
                'metadata temporarily unavailable', cause=requests.Timeout()
            )
        )
        with (
            patch('social_recovery.time.sleep') as sleep,
            self.assertRaises(ExtractorError),
        ):
            retry_metadata(operation)
        self.assertEqual(operation.call_count, 2)
        sleep.assert_called_once()

    def test_structural_and_certificate_errors_are_not_blindly_retried(self):
        for error in (
            ValueError('invalid metadata'),
            requests.exceptions.SSLError('certificate verification failed'),
        ):
            operation = Mock(side_effect=error)
            with (
                patch('social_recovery.time.sleep') as sleep,
                self.assertRaises(type(error)),
            ):
                retry_metadata(operation)
            operation.assert_called_once()
            sleep.assert_not_called()

    def test_stream_failure_retries_without_concatenating_partial_html(self):
        first = MagicMock()
        first.__enter__.return_value = first

        def chunks(*args):
            yield b'partial'
            raise requests.ConnectionError('interrupted')

        first.iter_content.side_effect = chunks
        second = MagicMock()
        second.__enter__.return_value = second
        second.url = 'https://example.com/final'
        second.iter_content.return_value = [b'complete']
        session = Mock()
        session.get.side_effect = [first, second]
        with patch('social_recovery.time.sleep'):
            self.assertEqual(
                public_html(session, 'https://example.com', with_url=True),
                ('complete', 'https://example.com/final'),
            )
        self.assertEqual(session.get.call_count, 2)
        first.__exit__.assert_called_once()

    def test_page_limit_is_not_retried(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.iter_content.return_value = [b'12345']
        session = Mock()
        session.get.return_value = response
        with self.assertRaisesRegex(ValueError, 'limite'):
            public_html(session, 'https://example.com', max_bytes=4)
        session.get.assert_called_once()

    def test_script_attributes_entities_and_multiple_layouts(self):
        html = """<script id="api-data">broken</script><script type="application/json" id = 'api-data'>{"title":"A &amp; B","videoDetail":{"id":"123"}}</script>"""
        self.assertEqual(script_json(html, 'api-data')['title'], 'A &amp; B')
        self.assertIsNone(script_json(html, 'other'))
        self.assertEqual(script_json('<script id="x">[1,2]</script>', 'x'), [1, 2])
