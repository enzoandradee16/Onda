"""Scrollable category pages that adapt to window size and display scaling."""
import tkinter as tk
from tkinter import ttk


class SettingsCategory(ttk.Frame):
    def __init__(self, parent, background):
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg=background, highlightthickness=0, borderwidth=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=scroll.set)
        self.content = ttk.Frame(self.canvas, padding=16)
        self.content_window = self.canvas.create_window(0, 0, window=self.content, anchor="nw")
        self._content_width = None
        self._region = None
        self.canvas.bind("<Configure>", self.resize)
        self.content.bind("<Configure>", self.update_region)

    def resize(self, event):
        if event.width == self._content_width:
            return
        self._content_width = event.width
        self.canvas.itemconfigure(self.content_window, width=event.width)
        available = max(100, event.width - 32)
        for child in self.content.winfo_children():
            if isinstance(child, ttk.Label):
                child.configure(wraplength=available)
        self.update_region()

    def update_region(self, _=None):
        region = self.canvas.bbox("all")
        if region != self._region:
            self._region = region
            self.canvas.configure(scrollregion=region)

    def wheel(self, event):
        if isinstance(event.widget, (ttk.Combobox, ttk.Spinbox)):
            return
        first, last = self.canvas.yview()
        if last - first < .999 and event.delta:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
            return "break"
