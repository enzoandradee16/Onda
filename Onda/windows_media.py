"""Native Windows SMTC session for the existing Jukebox PCM output; no helper player."""
import ctypes as c
from ctypes import wintypes as w
import base64
from pathlib import Path
from urllib.parse import urlparse,unquote
import queue
import uuid
from windows_shell import Guid

P=c.c_void_p
HRESULT=c.c_long

def method(pointer,index,*types):
    table=c.cast(pointer,c.POINTER(c.POINTER(P))).contents
    return c.WINFUNCTYPE(HRESULT,P,*types)(table[index])

def checked(result):
    if result<0:raise OSError('Windows media session: HRESULT 0x%08x'%(result & 0xffffffff))

def release(pointer):
    if pointer:method(pointer,2)(pointer)

class MediaControls:
    def __init__(self,root):
        self.controls=P();self.updater=P();self.music=P();self.token=c.c_longlong();self.events=queue.SimpleQueue();self.signature=None
        self.runtime=c.WinDLL('combase')
        self.runtime.WindowsCreateString.argtypes=[w.LPCWSTR,w.UINT,c.POINTER(P)]
        self.runtime.WindowsDeleteString.argtypes=[P]
        self.runtime.RoGetActivationFactory.argtypes=[P,c.POINTER(Guid),c.POINTER(P)]
        self.runtime.RoGetActivationFactory.restype=HRESULT
        self.runtime.RoInitialize.argtypes=[w.UINT];self.runtime.RoInitialize.restype=HRESULT
        result=self.runtime.RoInitialize(0);self.initialized=result>=0
        if result<0 and result!=-2147417850:checked(result)
        factory=P()
        try:
            name=self.string('Windows.Media.SystemMediaTransportControls')
            try:checked(self.runtime.RoGetActivationFactory(name,c.byref(Guid.value('ddb0472d-c911-4a1f-86d9-dc3d71a95f5a')),c.byref(factory)))
            finally:self.runtime.WindowsDeleteString(name)
            user=c.WinDLL('user32');user.GetAncestor.argtypes=[w.HWND,w.UINT];user.GetAncestor.restype=w.HWND
            hwnd=user.GetAncestor(root.winfo_id(),2)
            checked(method(factory,6,w.HWND,c.POINTER(Guid),c.POINTER(P))(factory,hwnd,c.byref(Guid.value('99fa3ff4-1742-42a6-902e-087d41f965ec')),c.byref(self.controls)))
            checked(method(self.controls,8,c.POINTER(P))(self.controls,c.byref(self.updater)))
            checked(method(self.updater,7,c.c_int)(self.updater,1))
            checked(method(self.updater,12,c.POINTER(P))(self.updater,c.byref(self.music)))
            for index in (13,15,17):checked(method(self.controls,index,c.c_bool)(self.controls,True))
            self.delegate=self.make_delegate()
            checked(method(self.controls,32,P,c.POINTER(c.c_longlong))(self.controls,c.byref(self.delegate),c.byref(self.token)))
        except Exception:
            self.close();raise
        finally:release(factory)
    def string(self,value):
        result=P();checked(self.runtime.WindowsCreateString(value,len(value.encode('utf-16-le'))//2,c.byref(result)));return result
    def make_delegate(self):
        signature='pinterface({9de1c534-6ae1-11e0-84e1-18a905bcc53f};rc(Windows.Media.SystemMediaTransportControls;{99fa3ff4-1742-42a6-902e-087d41f965ec});rc(Windows.Media.SystemMediaTransportControlsButtonPressedEventArgs;{b7f47116-a56f-4dc8-9e11-92031f4a87c2}))'
        typed=uuid.uuid5(uuid.UUID('11f47ad5-7b73-42c0-abae-878b1e16adee'),signature).bytes_le
        allowed={typed,uuid.UUID('00000000-0000-0000-c000-000000000046').bytes_le,uuid.UUID('94ea2b94-e9cc-49e0-c0ff-ee64ca8f5b90').bytes_le}
        self.refs=1
        def query(this,iid,out):
            if c.string_at(iid,16) not in allowed:out[0]=None;return -2147467262
            out[0]=this;self.refs+=1;return 0
        def add(this):self.refs+=1;return self.refs
        def drop(this):self.refs=max(0,self.refs-1);return self.refs
        def invoke(this,sender,args):
            try:
                button=c.c_int();checked(method(args,6,c.POINTER(c.c_int))(args,c.byref(button)))
                self.events.put(button.value)
                return 0
            except Exception:return -2147467259
        self.callbacks=(c.WINFUNCTYPE(HRESULT,P,c.POINTER(Guid),c.POINTER(P))(query),c.WINFUNCTYPE(w.ULONG,P)(add),c.WINFUNCTYPE(w.ULONG,P)(drop),c.WINFUNCTYPE(HRESULT,P,P,P)(invoke))
        self.vtable=(P*4)(*[c.cast(fn,P) for fn in self.callbacks])
        class Delegate(c.Structure):_fields_=[('vtable',c.POINTER(P))]
        return Delegate(self.vtable)
    def set_cover(self,cover):
        """Publish the already loaded artwork, without fetching images on the UI thread."""
        reference=P();stream=P();random=P();factory=P()
        try:
            data=b''
            if cover.startswith('data:image/'):
                header,separator,payload=cover.partition(',')
                if not separator or ';base64' not in header or len(payload)>12*1024*1024:raise ValueError('Invalid artwork data')
                data=base64.b64decode(payload,validate=True)
            elif cover:
                path=Path(unquote(urlparse(cover).path.lstrip('/'))) if cover.startswith('file:') else Path(cover)
                if path.is_file() and path.stat().st_size<=8*1024*1024:data=path.read_bytes()
            if data and len(data)<=8*1024*1024:
                shell=c.WinDLL('shlwapi');shell.SHCreateMemStream.argtypes=[P,w.UINT];shell.SHCreateMemStream.restype=P
                buffer=c.create_string_buffer(data);stream=P(shell.SHCreateMemStream(buffer,len(data)))
                if not stream:raise OSError('Unable to create artwork stream')
                interop=c.WinDLL('shcore');interop.CreateRandomAccessStreamOverStream.argtypes=[P,w.DWORD,c.POINTER(Guid),c.POINTER(P)];interop.CreateRandomAccessStreamOverStream.restype=HRESULT
                checked(interop.CreateRandomAccessStreamOverStream(stream,0,c.byref(Guid.value('905a0fe1-bc53-11df-8c49-001e4fc686da')),c.byref(random)))
                name=self.string('Windows.Storage.Streams.RandomAccessStreamReference')
                try:checked(self.runtime.RoGetActivationFactory(name,c.byref(Guid.value('857309dc-3fbf-4e7d-986f-ef3b1a07a964')),c.byref(factory)))
                finally:self.runtime.WindowsDeleteString(name)
                checked(method(factory,8,P,c.POINTER(P))(factory,random,c.byref(reference)))
            checked(method(self.updater,11,P)(self.updater,reference))
        finally:
            release(reference);release(factory);release(random);release(stream)
    def update(self,title,artist,playing,paused,cover=''):

        signature=(title,artist,playing,paused,cover)
        if signature==self.signature:return
        if self.signature is None or cover!=self.signature[4]:
            try:self.set_cover(cover)
            except (OSError,ValueError):
                checked(method(self.updater,11,P)(self.updater,None))
        for index,value in ((7,title),(11,artist)):
            text=self.string(value)
            try:checked(method(self.music,index,P)(self.music,text))
            finally:self.runtime.WindowsDeleteString(text)
        checked(method(self.updater,17)(self.updater))
        checked(method(self.controls,7,c.c_int)(self.controls,2 if not playing else 4 if paused else 3))
        checked(method(self.controls,11,c.c_bool)(self.controls,playing))
        self.signature=signature
    def close(self):
        if self.controls:
            if self.token.value:method(self.controls,33,c.c_longlong)(self.controls,self.token);self.token.value=0
            method(self.controls,11,c.c_bool)(self.controls,False)
        release(self.music);release(self.updater);release(self.controls)
        self.music=P();self.updater=P();self.controls=P()
        if getattr(self,'initialized',False):self.runtime.RoUninitialize();self.initialized=False
