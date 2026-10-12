"""Optional first-launch setup; edits remain local until the user applies them."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, ttk

from engine import MODES
from playlist_options import PLAYLIST_LIMITS
from settings_scroll import SettingsCategory


class WelcomeWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.title("Onda • Boas-vindas")
        self.configure(bg="#101419")
        self.geometry("650x650")
        self.minsize(580, 520)
        self.transient(app)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.folder = tk.StringVar(value=app.folder.get())
        self.mode = tk.StringVar(value=app.mode.get())
        self.provider = tk.StringVar(value=app.catalog_provider.get())
        self.limit = tk.StringVar(value=app.playlist_limit.get())
        self.remember = tk.BooleanVar(value=True)
        self.status = tk.StringVar()
        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Bem-vindo ao Onda", font=("Segoe UI", 22, "bold"), anchor="center").pack(fill="x")
        ttk.Label(body, text="Ajuste o básico para começar. Você pode fechar esta janela e configurar tudo depois.",
                  style="Muted.TLabel", wraplength=520, anchor="center", justify="center").pack(fill="x", pady=(8, 16))
        footer = ttk.Frame(body)
        footer.pack(side="bottom", fill="x", pady=(14, 0))
        ttk.Button(footer, text="Agora não", command=self.destroy).pack(side="left")
        ttk.Button(footer, text="Aplicar e começar", style="Accent.TButton", command=self.apply).pack(side="right")
        self.page = SettingsCategory(body, "#101419")
        self.page.pack(fill="both", expand=True)
        self.bind("<MouseWheel>", self.page.wheel)
        form = self.page.content
        ttk.Label(form, text="Pasta de destino", style="Muted.TLabel").pack(anchor="w")
        row = ttk.Frame(form)
        row.pack(fill="x", pady=(6, 14))
        ttk.Entry(row, textvariable=self.folder).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="Escolher", command=self.choose_folder).pack(side="right", padx=(8, 0))
        for label, variable, values in (("Formato padrão", self.mode, tuple(MODES)),
                                        ("Catálogo para pesquisar músicas", self.provider, ("Deezer", "Apple / iTunes", "Spotify")),
                                        ("Máximo de itens por playlist", self.limit, PLAYLIST_LIMITS)):
            ttk.Label(form, text=label, style="Muted.TLabel").pack(anchor="w")
            ttk.Combobox(form, textvariable=variable, values=values, state="readonly").pack(fill="x", pady=(6, 14))
        ttk.Checkbutton(form, text="Lembrar estas configurações nas próximas aberturas", variable=self.remember).pack(anchor="w", pady=(0, 10))
        ttk.Label(form, text="Mais opções em Configurações. O Spotify é opcional; você pode começar sem configurar uma API.",
                  style="Muted.TLabel", wraplength=490).pack(anchor="w")
        ttk.Label(form, textvariable=self.status, style="Muted.TLabel", wraplength=490).pack(anchor="w", pady=(8, 0))

    def choose_folder(self):
        path = filedialog.askdirectory(parent=self, title="Pasta dos downloads", initialdir=self.folder.get())
        if path:
            self.folder.set(path)

    def apply(self):
        folder = self.folder.get().strip()
        if not folder or "\x00" in folder:
            self.status.set("Escolha uma pasta de destino.")
            return
        if self.mode.get() not in MODES or self.limit.get() not in PLAYLIST_LIMITS or self.provider.get() not in ("Deezer", "Apple / iTunes", "Spotify"):
            self.status.set("Escolha uma opção válida em cada campo.")
            return
        try:
            folder = str(Path(folder).expanduser().resolve())
        except (OSError, ValueError):
            self.status.set("Escolha uma pasta de destino válida.")
            return
        self.app.remember_settings.set(self.remember.get())
        self.app.folder.set(folder)
        self.app.mode.set(self.mode.get())
        self.app.catalog_provider.set(self.provider.get())
        self.app.playlist_limit.set(self.limit.get())
        self.app.mode_changed()
        self.app.toggle_remember_settings()
        self.destroy()
