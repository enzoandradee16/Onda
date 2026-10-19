"""Scrollable category pages that adapt to window size and display scaling."""
import tkinter as tk
from tkinter import ttk


class SettingsCategory(ttk.Frame):
    def __init__(self, parent, background, *, fill_viewport=False, padding=16):
        super().__init__(parent)
        self.fill_viewport = fill_viewport
        self._onda_scroller = self
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg=background, highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.content = ttk.Frame(self.canvas, padding=padding)
        self.content_window = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self._content_width = None
        self._region = None
        self._refresh_id = None
        self.canvas.bind("<Configure>", self.resize)
        self.content.bind("<Configure>", self.update_region)

    def destroy(self):
        if self._refresh_id is not None:
            self.after_cancel(self._refresh_id)
            self._refresh_id = None
        super().destroy()

    def resize(self, event):
        if event.width != self._content_width:
            self._content_width = event.width
            self.canvas.itemconfigure(self.content_window, width=event.width)
        available = max(100, event.width - 32)
        for child in self.content.winfo_children():
            if isinstance(child, ttk.Label) and int(str(child.cget('wraplength')) or '0') != available:
                child.configure(wraplength=available)
        self.update_region()

    def update_region(self, _=None):
        if self.fill_viewport:
            height=max(self.content.winfo_reqheight(),self.canvas.winfo_height())
            if int(float(self.canvas.itemcget(self.content_window,"height") or 0)) != height:
                self.canvas.itemconfigure(self.content_window,height=height)
        region = self.canvas.bbox("all")
        if region != self._region:
            self._region = region
            self.canvas.configure(scrollregion=region)

    def refresh_when_idle(self):
        # Child requests can change while the canvas window keeps its old size.
        if self._refresh_id is None:
            self._refresh_id = self.after_idle(self._refresh_layout)

    def _refresh_layout(self):
        self._refresh_id = None
        self.update_region()

    def wheel(self, event):
        if isinstance(event.widget, (ttk.Combobox, ttk.Spinbox, ttk.Treeview, tk.Text, tk.Listbox, ttk.Scale, tk.Scale)):
            return
        first, last = self.canvas.yview()
        if last - first < .999 and event.delta:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
            return "break"


def scroll_page(event):
    """Route only the current page's wheel; lists keep their own scrolling."""
    widget=event.widget
    while widget is not None:
        scroller=vars(widget).get('_onda_scroller')
        if scroller is not None:return scroller.wheel(event)
        widget=getattr(widget,'master',None)


def refresh_page_layout(event):
    """Recalculate the whole page when dynamic cards or controls change size."""
    widget = event.widget
    while widget is not None:
        scroller = vars(widget).get("_onda_scroller")
        if scroller is not None:
            scroller.refresh_when_idle()
            return
        widget = getattr(widget, "master", None)
