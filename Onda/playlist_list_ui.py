"""A separate, read-only view of the loaded playlist."""
import tkinter as tk
from tkinter import ttk

from version_picker import duration_label


class PlaylistListWindow(tk.Toplevel):
    def __init__(self, page):
        super().__init__(page.app)
        self.transient(page.app)
        self.geometry("800x580")
        self.minsize(520, 320)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        panel = ttk.Frame(self, padding=12)
        panel.grid(row=0, column=0, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)
        self.table = ttk.Treeview(panel, columns=("number", "title", "artist", "duration"),
                                  show="headings", selectmode="browse")
        for key, label, width, minimum in (("number", "Nº", 50, 40), ("title", "MÚSICA", 350, 180),
                                            ("artist", "ARTISTA", 220, 140), ("duration", "DURAÇÃO", 85, 75)):
            self.table.heading(key, text=label)
            self.table.column(key, width=width, minwidth=minimum, stretch=key in ("title", "artist"),
                              anchor="center" if key in ("number", "duration") else "w")
        self.table.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(panel, orient="vertical", command=self.table.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(panel, orient="horizontal", command=self.table.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.bind("<Escape>", lambda _: self.destroy())
        self.refresh(page)

    def refresh(self, page):
        self.title(f"Lista da playlist · {page.playlist_title} · {len(page.records)} itens")
        children = self.table.get_children()
        if children:
            self.table.delete(*children)
        for number, row in enumerate(page.records.values(), 1):
            duration = row.get("duration_ms")
            self.table.insert("", "end", values=(number, row.get("title") or row["source_url"],
                              ", ".join(row.get("artists", [])), duration_label(duration / 1000 if duration else None)))
