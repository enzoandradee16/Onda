import ctypes as c
import os
import queue
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from windows_shell import WindowsShell, ThumbnailButton


class ThumbnailToolbarTests(unittest.TestCase):
    def shell(self):
        shell = WindowsShell.__new__(WindowsShell)
        shell.closed, shell.ready, shell.taskbar, shell.hwnd = False, True, 1, 1
        shell._thumbnail_added, shell._thumbnail_signature = False, None
        shell._thumbnail_icons = dict(previous=1, play=2, pause=3, next=4)
        shell.calls = []
        def com(index, args):
            def call(hwnd, count, buttons):
                shell.calls.append((index, [(b.identity, b.icon, b.flags, b.tip) for b in buttons]))
                return 0
            return call
        shell.com = com
        return shell

    def test_hidden_initially_and_updates_pause_navigation_and_unload(self):
        shell = self.shell()
        self.assertTrue(shell.thumbnail(False))
        self.assertEqual(shell.calls, [])
        shell.thumbnail(True, playing=True, previous=True, next=False)
        self.assertEqual(shell.calls[-1][0], 15)
        self.assertEqual([b[2] for b in shell.calls[-1][1]], [0, 0, 1])
        self.assertEqual(shell.calls[-1][1][1][1], 3)
        shell.thumbnail(True, playing=True, previous=True, next=False)
        self.assertEqual(len(shell.calls), 1)
        shell.thumbnail(True, playing=False, previous=True, next=True)
        self.assertEqual(shell.calls[-1][0], 16)
        self.assertEqual(shell.calls[-1][1][1][1], 2)
        shell.thumbnail(False)
        self.assertTrue(all(b[2] & 8 for b in shell.calls[-1][1]))

    def test_waits_until_shell_is_ready_and_recovers_after_taskbar_recreation(self):
        shell = self.shell()
        shell.ready = False
        self.assertFalse(shell.thumbnail(True))
        self.assertEqual(shell.calls, [])
        shell.ready = True
        shell.thumbnail(True)
        shell._thumbnail_added, shell._thumbnail_signature = False, None
        shell.thumbnail(True)
        self.assertEqual([call[0] for call in shell.calls], [15, 15])

    @unittest.skipUnless(os.name == 'nt', 'Windows structure layout')
    def test_native_structure_layout_matches_windows_sdk(self):
        self.assertEqual(c.sizeof(ThumbnailButton), 552 if c.sizeof(c.c_void_p) == 8 else 540)
        self.assertEqual(ThumbnailButton.icon.offset, 16 if c.sizeof(c.c_void_p) == 8 else 12)


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt controller')
class TaskbarRoutingTests(unittest.TestCase):
    def test_only_loaded_reproduction_enables_and_receives_commands(self):
        from qt_workspace_ui import DesktopWorkspace
        shell = SimpleNamespace(thumbnail_events=queue.SimpleQueue(), thumbnail=Mock())
        bridge = SimpleNamespace(model=None, _state={'playing': False}, paused=threading.Event(),
                                 normal_next_index=Mock(return_value=1), previousTrack=Mock(), playPause=Mock(), nextTrack=Mock())
        workspace = SimpleNamespace(shell=shell, bridge=bridge,
                                    options={'effectsSource': 'metadata-preview.wav'})
        shell.thumbnail_events.put('toggle')
        DesktopWorkspace.sync_taskbar_media(workspace)
        self.assertFalse(shell.thumbnail.call_args.args[0])
        bridge.playPause.assert_not_called()
        bridge.model = {'cache': 'loaded'}
        bridge._state['playing'] = True
        for command in ('previous', 'toggle', 'next'):
            shell.thumbnail_events.put(command)
        DesktopWorkspace.sync_taskbar_media(workspace)
        bridge.previousTrack.assert_called_once()
        bridge.playPause.assert_called_once()
        bridge.nextTrack.assert_called_once()
        self.assertTrue(shell.thumbnail.call_args.kwargs['playing'])
        bridge.paused.set()
        bridge.normal_next_index.return_value = None
        shell.thumbnail_events.put('next')
        DesktopWorkspace.sync_taskbar_media(workspace)
        bridge.nextTrack.assert_called_once()
        self.assertFalse(shell.thumbnail.call_args.kwargs['playing'])
        self.assertFalse(shell.thumbnail.call_args.kwargs['next'])
        bridge.model = None
        DesktopWorkspace.sync_taskbar_media(workspace)
        self.assertFalse(shell.thumbnail.call_args.args[0])


@unittest.skipUnless(os.name == 'nt' and os.environ.get('ONDA_UI_TESTS'), 'Native taskbar integration')
class NativeTaskbarTests(unittest.TestCase):
    def test_real_com_buttons_native_click_and_resource_cleanup(self):
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QWindow
        from PySide6.QtTest import QTest
        app = QApplication.instance() or QApplication([])
        window = QWindow()
        window.setTitle('ONDA · verificação dos controles')
        window.resize(320, 200)
        window.show()
        shell = None
        try:
            QTest.qWait(200)
            shell = WindowsShell(SimpleNamespace(winfo_id=lambda: int(window.winId())))
            self.assertTrue(shell.thumbnail(False))
            self.assertFalse(shell._thumbnail_added)
            for _ in range(20):
                if shell.thumbnail(True, playing=True, previous=True, next=True):
                    break
                QTest.qWait(100)
            self.assertTrue(shell._thumbnail_added)
            self.assertEqual(len(shell._thumbnail_icons), 4)
            shell.user.SendMessageW(shell.hwnd, 0x111, (0x1800 << 16) | 0x5102, 0)
            self.assertEqual(shell.thumbnail_events.get_nowait(), 'toggle')
            self.assertTrue(shell.thumbnail(True, playing=False, previous=True))
            self.assertTrue(shell.thumbnail(False))
            shell.close()
            self.assertEqual(shell._thumbnail_icons, {})
        finally:
            if shell:
                shell.close()
            window.close()
            window.destroy()
