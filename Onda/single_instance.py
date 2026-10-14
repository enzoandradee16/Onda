"""One Onda window per Windows session, shared by portable and installed copies."""
import ctypes
from ctypes import wintypes
import os

INSTANCE_NAME = r"Local\Onda.Desktop.C522DFD9-6BF4-4FE0-9CE4-5D3C5C88E470"


class SingleInstance:
    def __init__(self, name=INSTANCE_NAME):
        self.primary = True
        self.mutex = self.event = None
        self.root = self.after_id = None
        if os.name != "nt":
            return
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateMutexW.restype = wintypes.HANDLE
        self.kernel.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
        self.kernel.CreateEventW.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.kernel.CloseHandle.restype = wintypes.BOOL
        self.kernel.SetEvent.argtypes = [wintypes.HANDLE]
        self.kernel.SetEvent.restype = wintypes.BOOL
        self.kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.kernel.WaitForSingleObject.restype = wintypes.DWORD
        # Keep the event alive before creating the mutex so simultaneous launches
        # cannot lose a request to activate the first window during startup.
        self.event = self.kernel.CreateEventW(None, False, False, name + ".Activate")
        if not self.event:
            raise ctypes.WinError(ctypes.get_last_error())
        self.mutex = self.kernel.CreateMutexW(None, False, name + ".Mutex")
        error = ctypes.get_last_error()
        if not self.mutex:
            self.close()
            raise ctypes.WinError(error)
        self.primary = error != 183  # ERROR_ALREADY_EXISTS
        if not self.primary:
            # A duplicate warning must not keep the app locked if the original
            # instance exits while the user is still reading the warning.
            self.kernel.CloseHandle(self.mutex)
            self.mutex = None

    def notify(self):
        if self.event:
            user = ctypes.WinDLL("user32", use_last_error=True)
            user.AllowSetForegroundWindow.argtypes = [wintypes.DWORD]
            user.AllowSetForegroundWindow.restype = wintypes.BOOL
            user.AllowSetForegroundWindow(0xFFFFFFFF)
            self.kernel.SetEvent(self.event)

    def activation_requested(self):
        return bool(self.event and self.kernel.WaitForSingleObject(self.event, 0) == 0)

    def watch(self, root):
        self.root = root
        if self.event:
            self.after_id = root.after(150, self.poll)

    def poll(self):
        self.after_id = None
        try:
            if self.activation_requested():
                if self.root.state() in ("iconic", "withdrawn"):
                    self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
            self.after_id = self.root.after(150, self.poll)
        except Exception:
            # A pending callback may race with the user closing the main window.
            self.after_id = None

    def close(self):
        if self.root is not None and self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
        self.root = self.after_id = None
        for name in ("mutex", "event"):
            handle = getattr(self, name)
            if handle:
                self.kernel.CloseHandle(handle)
                setattr(self, name, None)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def already_open_message():
    from i18n import tr
    from preferences import PreferenceStore
    language = PreferenceStore().load_language()
    user = ctypes.WinDLL("user32", use_last_error=True)
    user.MessageBoxW.argtypes = [wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.UINT]
    user.MessageBoxW.restype = ctypes.c_int
    user.MessageBoxW(None, tr("O Onda já está aberto.\nUse a janela existente; uma nova janela não será criada.", language),
                     tr("Onda já está aberto", language), 0x40 | 0x10000)  # Information + foreground


def run_single_instance(factory):
    with SingleInstance() as guard:
        if not guard.primary:
            guard.notify()
            already_open_message()
            guard.notify()
            return 0
        while True:
            app = factory()
            guard.watch(app)
            app.mainloop()
            if getattr(app,"restart_requested",False) is not True:return 0
