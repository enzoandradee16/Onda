"""Windows OLE drop target using system APIs; no optional Tk extension."""

import ctypes as c
from ctypes import wintypes as w
import os
import queue


class WindowsDrop:
    def __init__(self, root, receive):
        self.root = root
        self.receive = receive
        self.registered = False
        self.timer = None
        self.events = queue.Queue()
        self.callbacks = []
        self.refs = 1
        if os.name != 'nt':
            return
        self.ole = c.OleDLL('ole32')
        self.user = c.WinDLL('user32')
        self.kernel = c.WinDLL('kernel32')
        self.shell = c.WinDLL('shell32')
        self.ole.OleInitialize.argtypes = [c.c_void_p]
        self.ole.OleInitialize.restype = c.c_long
        result = self.ole.OleInitialize(None)
        self.initialized = result >= 0
        if not self.initialized:
            return
        self.user.GetAncestor.argtypes = [w.HWND, w.UINT]
        self.user.GetAncestor.restype = w.HWND
        self.user.RegisterClipboardFormatW.argtypes = [w.LPCWSTR]
        self.user.RegisterClipboardFormatW.restype = w.UINT
        self.kernel.GlobalLock.argtypes = [w.HGLOBAL]
        self.kernel.GlobalLock.restype = c.c_void_p
        self.kernel.GlobalSize.argtypes = [w.HGLOBAL]
        self.kernel.GlobalSize.restype = c.c_size_t
        self.kernel.GlobalUnlock.argtypes = [w.HGLOBAL]
        self.shell.DragQueryFileW.argtypes = [w.HANDLE, w.UINT, w.LPWSTR, w.UINT]
        self.shell.DragQueryFileW.restype = w.UINT
        self.ole.ReleaseStgMedium.argtypes = [c.c_void_p]
        self.ole.RegisterDragDrop.argtypes = [w.HWND, c.c_void_p]
        self.ole.RegisterDragDrop.restype = c.c_long
        self.ole.RevokeDragDrop.argtypes = [w.HWND]
        self.url_format = self.user.RegisterClipboardFormatW('UniformResourceLocatorW')
        self.formats = (15, self.url_format, 13)
        self.hwnd = self.user.GetAncestor(root.winfo_id(), 2)
        self.build_target()
        result = self.ole.RegisterDragDrop(self.hwnd, c.byref(self.instance))
        self.registered = result >= 0
        if not self.registered:
            self.ole.OleUninitialize()
            self.initialized = False
            raise OSError('RegisterDragDrop: ' + hex(result & 0xFFFFFFFF))
        self.timer = root.after(100, self.poll)

    def build_target(self):
        HRESULT = c.c_long
        PTR = c.c_void_p
        DWORD = w.DWORD

        class Point(c.Structure):
            _fields_ = [('x', c.c_long), ('y', c.c_long)]

        signatures = [
            (HRESULT, [PTR, PTR, c.POINTER(PTR)]),
            (w.ULONG, [PTR]),
            (w.ULONG, [PTR]),
            (HRESULT, [PTR, PTR, DWORD, Point, c.POINTER(DWORD)]),
            (HRESULT, [PTR, DWORD, Point, c.POINTER(DWORD)]),
            (HRESULT, [PTR]),
            (HRESULT, [PTR, PTR, DWORD, Point, c.POINTER(DWORD)]),
        ]

        def query(this, iid, out):
            # IUnknown and IDropTarget only.
            import uuid

            allowed = (
                uuid.UUID('00000000-0000-0000-C000-000000000046').bytes_le,
                uuid.UUID('00000122-0000-0000-C000-000000000046').bytes_le,
            )
            if c.string_at(iid, 16) not in allowed:
                out[0] = None
                return -2147467262
            out[0] = c.addressof(self.instance)
            self.refs += 1
            return 0

        def add(this):
            self.refs += 1
            return self.refs

        def release(this):
            self.refs = max(0, self.refs - 1)
            return self.refs

        def enter(this, data, keys, point, effect):
            try:
                self.accepted = self.supported(data)
            except Exception:
                self.accepted = False
            effect[0] = 1 if self.accepted and effect[0] & 1 else 0
            return 0

        def over(this, keys, point, effect):
            effect[0] = 1 if getattr(self, 'accepted', False) and effect[0] & 1 else 0
            return 0

        def leave(this):
            self.accepted = False
            return 0

        def drop(this, data, keys, point, effect):
            try:
                payload = self.read(data)
                effect[0] = 1 if payload else 0
                if payload:
                    self.events.put(payload)
            except Exception:
                effect[0] = 0
            return 0

        for (result, args), function in zip(
            signatures, (query, add, release, enter, over, leave, drop)
        ):
            self.callbacks.append(c.WINFUNCTYPE(result, *args)(function))
        self.vtable = (PTR * 7)(*[c.cast(callback, PTR) for callback in self.callbacks])

        class Target(c.Structure):
            _fields_ = [('vtable', c.POINTER(PTR))]

        self.instance = Target(self.vtable)

    def format(self, identity):
        class Format(c.Structure):
            _fields_ = [
                ('format', w.WORD),
                ('target', c.c_void_p),
                ('aspect', w.DWORD),
                ('index', c.c_long),
                ('medium', w.DWORD),
            ]

        return Format(identity, None, 1, -1, 1)

    def supported(self, data):
        table = c.cast(data, c.POINTER(c.POINTER(c.c_void_p))).contents
        query = c.WINFUNCTYPE(c.c_long, c.c_void_p, c.c_void_p)(table[5])
        return any(
            query(data, c.byref(self.format(identity))) == 0
            for identity in self.formats
        )

    def read(self, data):
        class Medium(c.Structure):
            _fields_ = [
                ('type', w.DWORD),
                ('handle', c.c_void_p),
                ('owner', c.c_void_p),
            ]

        table = c.cast(data, c.POINTER(c.POINTER(c.c_void_p))).contents
        get = c.WINFUNCTYPE(c.c_long, c.c_void_p, c.c_void_p, c.c_void_p)(table[3])
        for identity in self.formats:
            medium = Medium()
            if get(data, c.byref(self.format(identity)), c.byref(medium)) != 0:
                continue
            try:
                if medium.type != 1 or not medium.handle:
                    continue
                if identity == 15:
                    count = self.shell.DragQueryFileW(
                        medium.handle, 0xFFFFFFFF, None, 0
                    )
                    if count > 1000:
                        continue
                    paths = []
                    for index in range(count):
                        size = self.shell.DragQueryFileW(medium.handle, index, None, 0)
                        buffer = c.create_unicode_buffer(size + 1)
                        self.shell.DragQueryFileW(
                            medium.handle, index, buffer, size + 1
                        )
                        paths.append(buffer.value)
                    if paths:
                        return {'files': paths}
                else:
                    size = self.kernel.GlobalSize(medium.handle)
                    if size > 1024 * 1024 or size < 2:
                        continue
                    pointer = self.kernel.GlobalLock(medium.handle)
                    if pointer:
                        try:
                            text = (
                                c.string_at(pointer, size)
                                .decode('utf-16-le', errors='replace')
                                .split('\0', 1)[0]
                            )
                        finally:
                            self.kernel.GlobalUnlock(medium.handle)
                        if text.strip():
                            return {'text': text}
            finally:
                self.ole.ReleaseStgMedium(c.byref(medium))
        return None

    def poll(self):
        self.timer = None
        try:
            for _ in range(10):
                try:
                    payload = self.events.get_nowait()
                except queue.Empty:
                    break
                self.receive(payload)
        finally:
            if self.registered:
                self.timer = self.root.after(100, self.poll)

    def shutdown(self):
        if self.timer:
            self.root.after_cancel(self.timer)
            self.timer = None
        if self.registered:
            self.ole.RevokeDragDrop(self.hwnd)
            self.registered = False
        if getattr(self, 'initialized', False):
            self.ole.OleUninitialize()
            self.initialized = False
