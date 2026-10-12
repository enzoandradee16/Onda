"""Center application windows whenever they become visible."""
import os
import tkinter as tk


def centered_position(bounds, width, height):
    left, top, right, bottom = bounds
    return (left + max(0, (right - left - width) // 2),
            top + max(0, (bottom - top - height) // 2))


def _center_windows(window):
    import ctypes
    from ctypes import wintypes

    class MonitorInfo(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.MonitorFromWindow.argtypes = [wintypes.HWND, wintypes.DWORD]
    user32.MonitorFromWindow.restype = wintypes.HANDLE
    user32.GetMonitorInfoW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MonitorInfo)]
    user32.GetMonitorInfoW.restype = wintypes.BOOL
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect.restype = wintypes.BOOL
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int,
                                  ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
    user32.SetWindowPos.restype = wintypes.BOOL
    handle = user32.GetAncestor(window.winfo_id(), 2)  # GA_ROOT: include frame/title bar.
    parent = window.master.winfo_toplevel() if window.master else window
    reference = user32.GetAncestor(parent.winfo_id(), 2)
    monitor = user32.MonitorFromWindow(reference, 2)  # Nearest monitor, including negative coordinates.
    info, rectangle = MonitorInfo(), wintypes.RECT()
    info.cbSize = ctypes.sizeof(info)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)) or not user32.GetWindowRect(handle, ctypes.byref(rectangle)):
        raise OSError("Não foi possível consultar a área da tela.")
    area = info.rcWork  # Exclude taskbar.
    x, y = centered_position((area.left, area.top, area.right, area.bottom),
                             rectangle.right - rectangle.left, rectangle.bottom - rectangle.top)
    if not user32.SetWindowPos(handle, None, x, y, 0, 0, 0x0001 | 0x0004 | 0x0010):
        raise OSError("Não foi possível centralizar a janela.")


def center_window(window):
    if window.state() != "normal":
        return
    if os.name == "nt":
        try:
            _center_windows(window)
            return
        except OSError:
            pass
    x, y = centered_position((0, 0, window.winfo_screenwidth(), window.winfo_screenheight()),
                             window.winfo_width(), window.winfo_height())
    window.geometry(f"+{x}+{y}")


def install_window_centering(root):
    def on_map(event):
        # Map also fires for labels, tabs and menus; only move actual windows.
        if isinstance(event.widget, (tk.Tk, tk.Toplevel)):
            from window_icons import apply_window_icon
            apply_window_icon(event.widget)
            center_window(event.widget)
    root.bind_all("<Map>", on_map, add="+")
