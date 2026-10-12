import os
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from window_position import centered_position


class WindowPositionTests(unittest.TestCase):
    def test_work_area_and_negative_monitor_coordinates(self):
        self.assertEqual(centered_position((0, 0, 1920, 1040), 980, 780), (470, 130))
        self.assertEqual(centered_position((-1920, -200, 0, 840), 800, 600), (-1360, 20))

    def test_large_window_stays_at_work_area_origin(self):
        self.assertEqual(centered_position((0, 20, 800, 600), 980, 780), (0, 20))


@unittest.skipUnless(os.environ.get("ONDA_UI_TESTS") and os.name == "nt", "Windows Tk integration")
class CenteredWindowsUiTests(unittest.TestCase):
    def assert_centered(self, window):
        import ctypes
        from ctypes import wintypes
        class MonitorInfo(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                        ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]
        user32 = ctypes.WinDLL("user32")
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        user32.GetAncestor.restype = wintypes.HWND
        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.MonitorFromWindow.restype = wintypes.HANDLE
        user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
        handle = user32.GetAncestor(window.winfo_id(), 2)
        rectangle, info = wintypes.RECT(), MonitorInfo()
        info.cbSize = ctypes.sizeof(info)
        self.assertTrue(user32.GetWindowRect(handle, ctypes.byref(rectangle)))
        self.assertTrue(user32.GetMonitorInfoW(user32.MonitorFromWindow(handle, 2), ctypes.byref(info)))
        area = info.rcWork
        expected = centered_position((area.left, area.top, area.right, area.bottom),
                                     rectangle.right - rectangle.left, rectangle.bottom - rectangle.top)
        self.assertAlmostEqual(rectangle.left, expected[0], delta=1)
        self.assertAlmostEqual(rectangle.top, expected[1], delta=1)

    def test_startup_reopening_and_child_widgets(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, {"LOCALAPPDATA": folder}):
            from app import App
            app = App()
            try:
                app.update()
                self.assert_centered(app)
                for show, window in ((app.show_settings, app.settings_window), (app.show_log, app.log_window)):
                    show()
                    app.update()
                    self.assert_centered(window)
                    window.geometry("+20+20")
                    app.update()
                    window.withdraw()
                    app.update()
                    show()
                    app.update()
                    self.assert_centered(window)
                    window.withdraw()
                app.help()
                app.update()
                help_window = next(w for w in app.winfo_children() if isinstance(w, tk.Toplevel) and w.title() == "Sobre o Onda")
                self.assert_centered(help_window)
                help_window.destroy()
                dialog = tk.Toplevel(app)
                dialog.geometry("400x240")
                dialog.transient(app)
                app.update()
                self.assert_centered(dialog)
                dialog.destroy()
                app.geometry("+50+50")
                app.update()
                position = app.winfo_rootx(), app.winfo_rooty()
                label = tk.Label(app, text="Map de um controle")
                label.place(x=0, y=0)
                app.update()
                self.assertEqual((app.winfo_rootx(), app.winfo_rooty()), position)
            finally:
                app.destroy()


if __name__ == "__main__":
    unittest.main()
