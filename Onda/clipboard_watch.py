"""One lightweight clipboard timer, stopped with the desktop window."""
import ctypes
import tkinter as tk
from tkinter import messagebox
from i18n import tr
from clipboard_links import recognize_link

class ClipboardWatch:
    def __init__(self,app):
        self.app=app;self.timer=None;self.sequence=None;self.seen=set();self.closed=False
        self.timer=app.after(1500,self.poll)
    def poll(self):
        self.timer=None
        if self.closed:return
        try:
            if self.app.clipboard_links.get() and self.app.grab_current() is None and not self.app.updating:
                sequence=ctypes.windll.user32.GetClipboardSequenceNumber()
                if sequence!=self.sequence:
                    try:text=self.app.clipboard_get()
                    except tk.TclError:return
                    self.sequence=sequence
                    candidate=recognize_link(text)
                    if candidate and candidate['key'] not in self.seen:
                        self.seen.add(candidate['key'])
                        if messagebox.askyesno(tr('Link copiado'),tr('Foi encontrado um link compatível. Deseja iniciar o download?')+'\n\n'+candidate['url'],parent=self.app):
                            self.app.download_clipboard_link(candidate)
        finally:
            if not self.closed:self.timer=self.app.after(1500,self.poll)
    def shutdown(self):
        self.closed=True
        if self.timer is not None:
            self.app.after_cancel(self.timer);self.timer=None
