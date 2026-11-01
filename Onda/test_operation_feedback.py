"""Messages describe results without leaking internal dictionaries to dialogs."""

import os
import unittest
from unittest.mock import patch
from operation_feedback import cache_message


class CacheFeedbackTests(unittest.TestCase):
    def test_cache_summary_formats_bytes_and_partial_failures(self):
        text = cache_message(dict(bytes=16384, removed=2938162050, failed=2))
        self.assertIn('2802.05 MB', text)
        self.assertIn('0.02 MB', text)
        self.assertIn('não puderam ser removidos', text)
        self.assertNotIn('"removed"', text)

    def test_size_only_and_empty_cache_are_readable(self):
        self.assertEqual(cache_message(dict(bytes=0)), 'Cache em disco: 0.00 MB.')
        self.assertNotIn(
            'não puderam', cache_message(dict(bytes=0, removed=0, failed=0))
        )


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt feedback')
class DesktopFeedbackTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture

    setUpClass = classmethod(Fixture.setUpClass.__func__)
    setUp = Fixture.setUp
    tearDown = Fixture.tearDown

    def test_cache_dialog_and_other_structured_results_do_not_show_json(self):
        messages = []
        self.ws.message.connect(lambda title, text: messages.append(text))
        self.ws.show_result(
            dict(bytes=16384, removed=1048576, failed=0), notification=False
        )
        self.assertIn('1.00 MB', messages[-1])
        self.ws.show_result(dict(internal_count=3), notification=False)
        self.assertEqual(messages[-1], 'Concluído')
        self.assertTrue(any('internal_count' in line for line in self.ws.logs))
        for result in (None, [{'internal': True}], {}):
            self.ws.show_result(result, notification=False)
            self.assertEqual(messages[-1], 'Concluído')

    def test_empty_searches_warn_without_starting_any_worker(self):
        messages = []
        self.ws.message.connect(lambda title, text: messages.append(text))
        with (
            patch.object(self.ws, 'run_task') as task,
            patch.object(self.bridge, 'task') as playback,
        ):
            self.ws.setOption('query', '   ')
            self.ws.invoke('search', {})
            self.ws.invoke('playback_queue_search', dict(query='  '))
            self.ws.setOption('effectsQuery', '')
            self.ws.invoke('effects_search', {})
            self.bridge.search('   ')
            task.assert_not_called()
            playback.assert_not_called()
        self.assertEqual(len(messages), 4)
        self.assertTrue(all('Informe uma música' in message for message in messages))
