"""Reopen only after the old process releases its single-instance lock."""
from pathlib import Path
import json
import os
import subprocess
import sys

WAIT_AND_START = r'''
import ctypes,json,subprocess,sys
pid=int(sys.argv[1]);command=json.loads(sys.argv[2]);cwd=sys.argv[3]
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.OpenProcess.argtypes=[ctypes.c_uint,ctypes.c_int,ctypes.c_uint]
kernel.OpenProcess.restype=ctypes.c_void_p
kernel.WaitForSingleObject.argtypes=[ctypes.c_void_p,ctypes.c_uint]
kernel.CloseHandle.argtypes=[ctypes.c_void_p]
handle=kernel.OpenProcess(0x100000,False,pid)
if handle:
    result=kernel.WaitForSingleObject(handle,30000)
    kernel.CloseHandle(handle)
    if result!=0:sys.exit(1)
elif ctypes.get_last_error() not in (87,1168):sys.exit(2)
subprocess.Popen(command,cwd=cwd,creationflags=0x08000000)
'''


def schedule(root, *, parent_pid=None, command=None):
    root=Path(root).resolve()
    if command is None:
        launcher=root.parent/'Onda.exe'
        command=[str(launcher)] if launcher.is_file() else [sys.executable,str(root/'qt_desktop_ui.py')]
    return subprocess.Popen([sys.executable,'-c',WAIT_AND_START,str(parent_pid or os.getpid()),json.dumps(command),str(root.parent)],
                            cwd=root.parent,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                            close_fds=True,creationflags=0x00000008|0x00000200|0x08000000)
