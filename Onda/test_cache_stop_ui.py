import os
import tempfile
import threading
import time
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Desktop integration')
class CacheStopTests(unittest.TestCase):
    def test_lists_operations_and_waits_for_worker_exit_before_cleaning(self):
        from PySide6.QtTest import QTest
        from qt_desktop_ui import create_application,close_application
        from preferences import PreferenceStore
        from qt_operations_ui import perform
        started,release,cancelled,cleaned=[threading.Event() for _ in range(4)]
        def operation(action,config,cancel,emit):
            if action=='cache_info':
                started.set()
                while not release.wait(.01):
                    if cancel.is_set():cancelled.set()
                return {'bytes':0}
            if action=='cache_clear':cleaned.set()
            return perform(action,config,cancel,emit)
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder,'ONDA_ALIAS_CACHE_ROOT':folder}),patch('qt_operations_ui.perform',side_effect=operation):
            PreferenceStore().save({'check_updates':False,'clipboard_links':False})
            app,engine,bridge=create_application(complete=False)
            def wait(condition):
                deadline=time.monotonic()+5
                while time.monotonic()<deadline:
                    app.processEvents()
                    if condition():return
                    time.sleep(.01)
                self.fail('Tempo limite no encerramento das operações.')
            try:
                workspace=engine.workspace
                workspace.run_task('cache_info');wait(started.is_set)
                workspace.dispatch('cache_clear',{})
                self.assertIn('Consulta ao cache',workspace.choice['message'])
                self.assertEqual(workspace.choice['confirm_label'],'Parar operações e continuar')
                workspace.replyChoice(workspace.choice['identity'],{'yes':True})
                wait(cancelled.is_set);self.assertFalse(cleaned.is_set())
                self.assertTrue(workspace.cache_blocking_operations())
                release.set()
                wait(lambda:workspace.choice.get('title')=='Limpar arquivos dispensáveis')
                self.assertFalse(cleaned.is_set())
                workspace.replyChoice(workspace.choice['identity'],{'yes':True})
                wait(cleaned.is_set)
            finally:release.set();close_application(engine,bridge)


if __name__=='__main__':unittest.main()
