import os
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk


class HistoryPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(0, 18, 0, 0))
        self.app = app
        self.query = tk.StringVar()
        self.rows = {}
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        ttk.Label(self, text="Sua biblioteca de downloads.", font=("Segoe UI", 21, "bold"), anchor="center").grid(row=0, column=0, sticky="ew")
        search = ttk.Frame(self)
        search.grid(row=1, column=0, sticky="ew", pady=18)
        ttk.Entry(search, textvariable=self.query).pack(side="left", fill="x", expand=True)
        ttk.Button(search, text="Pesquisar", command=self.refresh).pack(side="left", padx=8)
        ttk.Button(search, text="Limpar histórico", command=self.clear).pack(side="right")
        self.query.trace_add("write", lambda *_: self.refresh())
        panel = ttk.Frame(self)
        panel.grid(row=2, column=0, sticky="nsew")
        self.table = ttk.Treeview(panel, columns=("name", "mode", "date"), show="headings", selectmode="browse")
        for key, label, width in (("name", "ARQUIVO", 480), ("mode", "FORMATO", 100), ("date", "DATA", 200)):
            self.table.heading(key, text=label)
            self.table.column(key, width=width, minwidth=80, stretch=key == "name")
        self.table.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(panel, command=self.table.yview)
        scroll.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scroll.set)
        self.table.bind("<Double-1>", lambda _: self.open())
        controls = ttk.Frame(self)
        controls.grid(row=3, column=0, sticky="ew", pady=16)
        ttk.Button(controls, text="Abrir arquivo", command=self.open).pack(side="left")
        ttk.Button(controls, text="Abrir pasta", command=lambda: self.open(True)).pack(side="left", padx=8)
        ttk.Button(controls, text="Usar nos efeitos", style="Accent.TButton", command=self.effects).pack(side="right")
        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status, style="Muted.TLabel").grid(row=4, column=0, sticky="w")
        self.refresh()

    def refresh(self):
        if not hasattr(self, "table"):
            return
        selected = self.table.selection()
        self.table.delete(*self.table.get_children())
        try:
            self.rows = {str(row["id"]): row for row in self.app.library.history(self.query.get())}
        except Exception:
            self.status.set("Não foi possível ler o histórico.")
            return
        for key, row in self.rows.items():
            self.table.insert("", "end", iid=key, values=(row["name"], row["mode"], row["date"][:19].replace("T", " ")))
        if selected and selected[0] in self.rows:
            self.table.selection_set(selected[0])
        self.status.set(f"{len(self.rows)} registros · até 1000 resultados por pesquisa.")

    def current(self):
        selected = self.table.selection()
        if not selected:
            return None
        path = Path(self.rows[selected[0]]["path"])
        if not path.is_file():
            self.status.set("O arquivo foi movido ou removido do computador.")
            return None
        return path

    def open(self, folder=False):
        path = self.current()
        if not path:
            return
        path = path.parent if folder else path
        try:
            if os.name == "nt":
                os.startfile(str(path))
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])
        except OSError as exc:
            self.status.set(str(exc))

    def effects(self):
        path = self.current()
        if path:
            self.app.effects_page.use_file(path)
            self.app.pages.select(self.app.effects_page)

    def clear(self):
        if messagebox.askyesno("Histórico", "Remover os registros do histórico? Os arquivos serão preservados.", parent=self.app):
            self.app.library.clear_history()
            self.refresh()
