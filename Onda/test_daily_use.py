import os, tempfile, unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from advanced_options import DEFAULTS, clean_advanced, export_settings, import_settings
from daily_desktop import queue_progress


class DailyPolicyTests(unittest.TestCase):
    def test_defaults_validation_and_transfer(self):
        self.assertTrue(DEFAULTS['notification_controls'])
        self.assertFalse(DEFAULTS['wifi_only'])
        self.assertEqual(DEFAULTS['close_behavior'], 'Encerrar')
        valid = {
            'wifi_only': True,
            'wifi_loss': 'Concluir downloads ativos',
            'finish_action': 'Som',
            'close_behavior': 'Minimizar para a bandeja',
            'taskbar_progress': False,
            'notification_controls': False,
        }
        self.assertEqual(clean_advanced(valid), valid)
        self.assertEqual(
            clean_advanced(
                {
                    'finish_action': 'invalid',
                    'wifi_loss': 'invalid',
                    'close_behavior': 'invalid',
                }
            ),
            {},
        )
        self.assertEqual(
            import_settings(export_settings(valid, 'windows'), 'windows')[
                'finish_action'
            ],
            'Som',
        )

    def test_progress_respects_scope(self):
        app = SimpleNamespace(
            parallel=SimpleNamespace(
                attempted={'done', 'active'},
                scope={'done', 'active', 'pending'},
                workers={'active'},
            ),
            jobs={
                'done': {'state': 'Falhou'},
                'active': {'state': 'Em andamento', '_queue_percent': 50},
                'pending': {'state': 'Na fila'},
                'outside': {'state': 'Na fila'},
            },
        )
        self.assertEqual(queue_progress(app), 50)
        app.parallel.scope = None
        self.assertEqual(queue_progress(app), 37.5)


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'), 'Tk integration')
class DailyDesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name})
        self.env.start()
        from preferences import PreferenceStore

        PreferenceStore().save({'check_updates': False, 'finish_action': 'Nenhuma'})
        from app import App

        self.app = App(show_welcome=False)
        self.app.clipboard_watch.shutdown()
        self.app.update()

    def tearDown(self):
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()

    def test_native_tray_restore_and_explicit_exit(self):
        app = self.app
        native = app.daily.shell
        self.assertIsNotNone(native)
        self.assertTrue(native.taskbar.value)
        native.theme_icon(app.theme_manager.colors)
        first = native.icon
        colors = dict(app.theme_manager.colors, accent='#ff0000')
        native.theme_icon(colors)
        self.assertNotEqual(native.icon, first)
        themed = native.icon
        native.theme_icon(colors)
        self.assertEqual(native.icon, themed)
        app.close_behavior.set('Minimizar para a bandeja')
        app.close()
        app.update()
        self.assertEqual(app.state(), 'withdrawn')
        self.assertTrue(native.added)
        app.daily.restore()
        app.update()
        self.assertNotEqual(app.state(), 'withdrawn')
        self.assertTrue(native.ready)
        self.assertTrue(native.progress(25))
        native.progress(enabled=False)
        with patch.object(app, 'close') as close:
            app.daily.menu.invoke(app.daily.menu.index('end'))
            close.assert_called_once_with(force_exit=True)
        with patch.object(app, 'close') as close:
            app._applied_language = 'en'
            app.restart_app()
            close.assert_called_once_with(force_exit=True)

    def test_finish_notice_and_empty_run(self):
        app = self.app
        key = app.add(lines=['https://example.com/daily'])[0]
        app.jobs[key]['state'] = 'Concluído'
        native = app.daily.shell
        try:
            app.daily.shell = Mock()
            app.finish_action.set('Notificação')
            app.daily.finished(set())
            app.daily.shell.notify.assert_not_called()
            app.daily.finished({key})
            app.daily.shell.notify.assert_called_once()
            self.assertIn('1/1', app.daily.shell.notify.call_args.args[1])
        finally:
            app.daily.shell = native

    @patch('daily_desktop.subprocess.run')
    def test_shutdown_confirm_cancel_and_skip_failure(self, shutdown):
        app = self.app
        key = app.add(lines=['https://example.com/daily'])[0]
        app.finish_action.set('Desligar PC')
        with patch('daily_desktop.messagebox.askyesno', return_value=False) as confirm:
            app.jobs[key]['state'] = 'Falhou'
            app.daily.finished({key})
            confirm.assert_not_called()
            app.jobs[key]['state'] = 'Concluído'
            app.daily.finished({key})
            confirm.assert_called_once()
            self.assertIsNone(app.daily.shutdown_window)
        app.daily.begin_shutdown()
        self.assertIsNotNone(app.daily.shutdown_window)
        app.daily.cancel_shutdown()
        self.assertIsNone(app.daily.shutdown_window)
        shutdown.assert_not_called()
        with patch('daily_desktop.time.monotonic', side_effect=[100, 161]):
            app.daily.begin_shutdown()
        shutdown.assert_called_once()
        self.assertEqual(shutdown.call_args.args[0], ['shutdown.exe', '/s', '/t', '0'])
