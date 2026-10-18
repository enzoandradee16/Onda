"""Native Windows tray, balloon notifications and taskbar progress; no helper process."""
import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
import os,queue,uuid

class Guid(c.Structure):
    _fields_=[('data',c.c_ubyte*16)]
    @classmethod
    def value(cls,text):return cls((c.c_ubyte*16).from_buffer_copy(uuid.UUID(text).bytes_le))

class IconData(c.Structure):
    _fields_=[('size',w.DWORD),('window',w.HWND),('id',w.UINT),('flags',w.UINT),('message',w.UINT),('icon',w.HICON),('tip',w.WCHAR*128),('state',w.DWORD),('mask',w.DWORD),('info',w.WCHAR*256),('version',w.UINT),('title',w.WCHAR*64),('info_flags',w.DWORD),('guid',Guid),('balloon',w.HICON)]

class WindowsShell:
    MESSAGE=0x8000+43
    def __init__(self,root):
        self.root=root;self.events=queue.Queue();self.added=False;self.taskbar=c.c_void_p();self.closed=False;self.owns_icon=False
        self.user=c.WinDLL('user32',use_last_error=True);self.shell=c.WinDLL('shell32');self.ole=c.WinDLL('ole32')
        self.user.GetAncestor.argtypes=[w.HWND,w.UINT];self.user.GetAncestor.restype=w.HWND
        self.hwnd=self.user.GetAncestor(root.winfo_id(),2)
        self.user.RegisterWindowMessageW.argtypes=[w.LPCWSTR];self.user.RegisterWindowMessageW.restype=w.UINT
        self.button_message=self.user.RegisterWindowMessageW('TaskbarButtonCreated')
        self.restart_message=self.user.RegisterWindowMessageW('TaskbarCreated')
        self.user.IsWindowVisible.argtypes=[w.HWND];self.user.IsWindowVisible.restype=w.BOOL
        self.ready=bool(self.user.IsWindowVisible(self.hwnd))
        self.user.CallWindowProcW.argtypes=[c.c_void_p,w.HWND,w.UINT,w.WPARAM,w.LPARAM];self.user.CallWindowProcW.restype=c.c_ssize_t
        self.set_proc=self.user.SetWindowLongPtrW if c.sizeof(c.c_void_p)==8 else self.user.SetWindowLongW
        self.set_proc.argtypes=[w.HWND,c.c_int,c.c_void_p];self.set_proc.restype=c.c_void_p
        callback=c.WINFUNCTYPE(c.c_ssize_t,w.HWND,w.UINT,w.WPARAM,w.LPARAM)
        def window_proc(hwnd,message,wp,lp):
            if message==self.button_message:self.ready=True
            elif message==self.restart_message:self.added=False;self.ready=False;self.events.put('restart')
            elif message==self.MESSAGE:
                if lp in (0x202,0x203,0x405,0x400,0x401):self.events.put('open')
                elif lp in (0x205,0x7b):self.events.put('menu')
                return 0
            return self.user.CallWindowProcW(self.old_proc,hwnd,message,wp,lp)
        self.callback=callback(window_proc)
        self.old_proc=self.set_proc(self.hwnd,-4,c.cast(self.callback,c.c_void_p))
        if not self.old_proc:raise c.WinError(c.get_last_error())
        self.shell.Shell_NotifyIconW.argtypes=[w.DWORD,c.POINTER(IconData)];self.shell.Shell_NotifyIconW.restype=w.BOOL
        self.user.LoadImageW.argtypes=[w.HINSTANCE,w.LPCWSTR,w.UINT,c.c_int,c.c_int,w.UINT];self.user.LoadImageW.restype=w.HANDLE
        self.user.SendMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM];self.user.SendMessageW.restype=c.c_ssize_t
        self.user.DestroyIcon.argtypes=[w.HICON]
        base=Path(__file__).resolve().parent.parent
        candidates=[base/'onda.ico',base/'Portatil/onda.ico']
        if os.environ.get('ONDA_PACKAGED_ROOT'):candidates.insert(0,Path(os.environ['ONDA_PACKAGED_ROOT'])/'onda.ico')
        self.icon=None
        for path in candidates:
            if path.is_file():
                self.icon=self.user.LoadImageW(None,str(path),1,32,32,0x10)
                if self.icon:self.owns_icon=True;break
        if not self.icon:self.icon=self.user.SendMessageW(self.hwnd,0x7f,0,0) or self.user.SendMessageW(self.hwnd,0x7f,1,0)
        self.ole.CoInitializeEx.argtypes=[c.c_void_p,w.DWORD];self.ole.CoInitializeEx.restype=c.c_long
        self.com_initialized=self.ole.CoInitializeEx(None,2)>=0
        self.ole.CoCreateInstance.argtypes=[c.POINTER(Guid),c.c_void_p,w.DWORD,c.POINTER(Guid),c.POINTER(c.c_void_p)];self.ole.CoCreateInstance.restype=c.c_long
        if self.com_initialized:
            cls=Guid.value('56FDF344-FD6D-11D0-958A-006097C9A090');iid=Guid.value('EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF')
            if self.ole.CoCreateInstance(c.byref(cls),None,1,c.byref(iid),c.byref(self.taskbar))>=0:self.com(3,[])()

    def theme_icon(self,colors):
        key=tuple(colors.get(name) for name in ('accent','text','bg'))
        if getattr(self,'icon_colors',None)==key:return
        from io import BytesIO
        import struct
        from window_icons import draw_icon
        stream=BytesIO()
        draw_icon('onda',32,colors).save(stream,format='ICO',sizes=[(32,32)],bitmap_format='bmp')
        data=stream.getvalue()
        length,offset=struct.unpack_from('<II',data,14)
        resource=(c.c_ubyte*length).from_buffer_copy(data[offset:offset+length])
        create=self.user.CreateIconFromResourceEx
        create.argtypes=[c.POINTER(c.c_ubyte),w.DWORD,w.BOOL,w.DWORD,c.c_int,c.c_int,w.UINT]
        create.restype=w.HICON
        icon=create(resource,length,True,0x30000,32,32,0)
        if not icon:return
        previous,owned=self.icon,self.owns_icon
        self.icon=icon;self.owns_icon=True;self.icon_colors=key
        if self.added:
            value=self.data();value.flags=2
            self.shell.Shell_NotifyIconW(1,c.byref(value))
        if owned:self.user.DestroyIcon(previous)

    def com(self,index,args):
        table=c.cast(self.taskbar,c.POINTER(c.POINTER(c.c_void_p))).contents
        function=c.WINFUNCTYPE(c.c_long,c.c_void_p,*args)(table[index])
        return lambda *values:function(self.taskbar,*values)

    def data(self):
        value=IconData();value.size=c.sizeof(IconData);value.window=self.hwnd;value.id=1;value.message=self.MESSAGE;value.icon=self.icon;value.flags=7;value.tip='ONDA';return value

    def add(self,tip='ONDA'):
        data=self.data();data.tip=tip[:127]
        ok=bool(self.shell.Shell_NotifyIconW(1 if self.added else 0,c.byref(data)))
        self.added=ok;return ok

    def remove(self):
        if self.added:self.shell.Shell_NotifyIconW(2,c.byref(self.data()));self.added=False

    def notify(self,title,text):
        if not self.add():return False
        data=self.data();data.flags=0x10;data.title=title[:63];data.info=text[:255];data.info_flags=0x11
        return bool(self.shell.Shell_NotifyIconW(1,c.byref(data)))

    def progress(self,value=None,paused=False,enabled=True):
        if not self.taskbar or not self.ready:return False
        state=0 if not enabled or value is None else 8 if paused else 2
        result=self.com(10,[w.HWND,c.c_int])(self.hwnd,state)
        if state:self.com(9,[w.HWND,c.c_ulonglong,c.c_ulonglong])(self.hwnd,int(max(0,min(100,value))*100),10000)
        return result>=0

    def close(self):
        if self.closed:return
        self.progress(enabled=False);self.remove()
        self.set_proc(self.hwnd,-4,self.old_proc)
        if self.taskbar:self.com(2,[])();self.taskbar=c.c_void_p()
        if self.com_initialized:self.ole.CoUninitialize();self.com_initialized=False
        if self.owns_icon:self.user.DestroyIcon(self.icon)
        self.closed=True
