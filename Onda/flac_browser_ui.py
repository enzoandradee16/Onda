"""Small non-blocking desktop handoff to the user's browser."""
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser
from flac_browser import INSTRUCTIONS, validate_flac


class FlacBrowserDialog(tk.Toplevel):
    def __init__(self, parent, event, on_select, on_cancel):
        super().__init__(parent)
        self.title("Onda • FLAC pelo navegador")
        self.transient(parent)
        self.geometry("620x320")
        self.minsize(520, 300)
        self.record = event["record"]
        self.url = event["url"]
        self.on_select = on_select
        body = ttk.Frame(self, padding=22)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="FLAC pelo navegador", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(body, text=" — ".join([", ".join(self.record.get("artists", [])), self.record["title"]]),
                  wraplength=540).pack(anchor="w", pady=12)
        ttk.Label(body, text=INSTRUCTIONS, wraplength=540).pack(anchor="w", pady=8)
        ttk.Label(body, text="O arquivo original será preservado. A fila aguarda sua seleção.",
                  wraplength=540, style="Muted.TLabel").pack(anchor="w", pady=8)
        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=16)
        ttk.Button(buttons, text="Abrir serviço", command=self.open_browser).pack(side="left")
        ttk.Button(buttons, text="Selecionar FLAC baixado", style="Accent.TButton", command=self.choose).pack(side="left", padx=8)
        ttk.Button(buttons, text="Cancelar", command=on_cancel).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", on_cancel)

    def open_browser(self):
        if not webbrowser.open(self.url):
            messagebox.showerror("Abrir serviço", "Não foi possível abrir o navegador.\n" + self.url, parent=self)

    def choose(self):
        path = filedialog.askopenfilename(parent=self, title="Selecionar FLAC baixado", filetypes=[("Áudio FLAC", "*.flac")])
        if not path:
            return
        try:
            validate_flac(path, self.record)
        except ValueError as exc:
            messagebox.showerror("Arquivo FLAC", str(exc), parent=self)
            return
        self.on_select({"path": path})
