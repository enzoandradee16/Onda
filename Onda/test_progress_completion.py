import os
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'), 'Tk integration')
class ProgressCompletionTests(unittest.TestCase):
    def setUp(self):
        from app import App

        self.folder = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {'LOCALAPPDATA': self.folder.name})
        self.environment.start()
        self.app = App(show_welcome=False)
        self.app.withdraw()
        self.app.folder.set(self.folder.name)
        self.app.concurrent_downloads.set('2')
        self.app.add(
            ['https://example.com/first.mp3', 'https://example.com/second.mp3']
        )
        self.ids = list(self.app.jobs)

    def tearDown(self):
        self.app.parallel.workers.clear()
        self.app.active = None
        self.app.destroy()
        self.environment.stop()
        self.folder.cleanup()

    def event(self, identity, kind, **values):
        self.app.after_cancel(self.app._poll_after)
        self.app.events.put((identity, dict(type=kind, **values)))
        self.app.poll_events()

    def test_done_stops_animation_before_process_exit_and_late_events_cannot_restart_it(
        self,
    ):
        app = self.app
        with (
            patch('parallel_queue.threading.Thread'),
            patch('app.binaries', return_value=True),
        ):
            app.start(only_item=self.ids[0])
        self.event(
            self.ids[0], 'stage', message='Gravando metadados e capa no arquivo…'
        )
        self.assertEqual(str(app.bar['mode']), 'indeterminate')
        self.event(self.ids[0], 'done', files=['fixture.mp3'])
        self.assertEqual(str(app.bar['mode']), 'determinate')
        self.assertEqual(float(app.bar['value']), 100)
        self.event(self.ids[0], 'processing')
        self.assertEqual(str(app.bar['mode']), 'determinate')
        self.event(self.ids[0], 'exited', success=True, cancelled=False)
        self.assertEqual(app.jobs[self.ids[0]]['state'], 'Concluído')
        self.assertFalse(app.running)
        self.assertEqual(str(app.bar['mode']), 'determinate')
        self.assertEqual(app.status.get(), 'Fila finalizada')

    def test_one_finished_item_does_not_hide_other_active_download(self):
        app = self.app
        with (
            patch('parallel_queue.threading.Thread'),
            patch('app.binaries', return_value=True),
        ):
            app.start(only_items=self.ids)
        self.event(self.ids[0], 'done', files=['first.mp3'])
        self.assertEqual(str(app.bar['mode']), 'indeterminate')
        self.assertIn('1 download', app.status.get())
        self.event(self.ids[1], 'done', files=['second.mp3'])
        self.assertEqual(str(app.bar['mode']), 'determinate')
        for identity in self.ids:
            self.event(identity, 'exited', success=True, cancelled=False)
        self.assertFalse(app.running)
        self.assertEqual(float(app.bar['value']), 100)


if __name__ == '__main__':
    unittest.main()
