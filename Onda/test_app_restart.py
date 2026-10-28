import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock,patch
from tool_status import display


class RestartEligibilityTests(unittest.TestCase):
    def test_restart_requires_a_complete_successful_check(self):
        good=dict(name='Python',version='3.11',status='Disponível')
        self.assertFalse(display({})['can_restart'])
        self.assertFalse(display({'tools':[good]})['can_restart'])
        self.assertTrue(display({'checked_at':'2026-10-27T23:00:00+00:00','tools':[good]})['can_restart'])
        self.assertFalse(display({'checked_at':'2026-10-27T23:00:00+00:00','tools':[good,dict(good,status='Indisponível')]})['can_restart'])

    @unittest.skipUnless(os.name=='nt','Windows handoff')
    def test_new_process_waits_until_the_parent_exits(self):
        from app_restart import schedule
        with tempfile.TemporaryDirectory(prefix='onda-restart-test-') as folder:
            marker=Path(folder)/'new-process.txt'
            parent=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)'],creationflags=0x08000000)
            helper=None
            try:
                helper=schedule(Path(folder)/'Onda',parent_pid=parent.pid,command=[sys.executable,'-c',f'import os;from pathlib import Path;Path({str(marker)!r}).write_text(str(os.getpid()))'])
                time.sleep(.25);self.assertFalse(marker.exists())
                parent.terminate();parent.wait(timeout=5);self.assertEqual(helper.wait(timeout=10),0)
                deadline=time.monotonic()+5
                while not marker.exists() and time.monotonic()<deadline:time.sleep(.05)
                child=int(marker.read_text())
                import ctypes
                kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                kernel.OpenProcess.restype=ctypes.c_void_p
                kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint]
                kernel.CloseHandle.argtypes=[ctypes.c_void_p]
                handle=kernel.OpenProcess(0x100000,False,child)
                if handle:
                    self.assertEqual(kernel.WaitForSingleObject(handle,5000),0);kernel.CloseHandle(handle)
            finally:
                if parent.poll() is None:parent.kill();parent.wait()
                if helper and helper.poll() is None:helper.kill();helper.wait()


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Qt restart flow')
class DesktopRestartTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture
    setUpClass=classmethod(Fixture.setUpClass.__func__)
    setUp=Fixture.setUp;tearDown=Fixture.tearDown

    def test_busy_restart_never_schedules_a_process(self):
        self.ws.active['busy']=Mock()
        try:
            with patch('tool_status.read',return_value={'checked_at':'now','tools':[dict(name='Python',status='Disponível')]}),patch('app_restart.schedule') as start:
                with self.assertRaisesRegex(ValueError,'operações'):self.ws.dispatch('restart_app',{})
                start.assert_not_called()
        finally:self.ws.active.clear()

    def test_idle_restart_saves_before_handoff_and_ignores_tray_close_mode(self):
        self.ws.settings['close_behavior']='Minimizar para a bandeja'
        with patch('tool_status.read',return_value={'checked_at':'now','tools':[dict(name='Python',status='Disponível')]}),patch('app_restart.schedule') as start,patch('qt_workspace_ui.QGuiApplication') as application:
            with patch.object(self.ws,'save_playback_session') as session,patch.object(self.ws,'save_queue') as queue:
                self.ws.dispatch('restart_app',{})
                session.assert_called_once();queue.assert_called_once();start.assert_called_once();application.exit.assert_called_once_with(0)

    def test_failed_session_write_blocks_handoff(self):
        with patch('tool_status.read',return_value={'checked_at':'now','tools':[dict(name='Python',version='3.11',status='Disponível')]}),patch('app_restart.schedule') as start,patch.object(self.ws,'save_playback_session',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.ws.dispatch('restart_app',{})
            start.assert_not_called()
