import queue
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from engine import MODES
from metadata import MetadataClient, is_streaming_link
from playlist_import import load_playlist, load_text
from version_picker import duration_label


class PlaylistPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(0, 18, 0, 0))
        self.app = app
        self.url = tk.StringVar()
        self.status = tk.StringVar(value="Playlist pública Deezer, Spotify ou YouTube · até 100 itens.")
        self.confirm_version = tk.BooleanVar(value=True)
        self.records = {}
        self.events = queue.Queue()
        self.generation = 0
        self.closed = False
        self.busy = False
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        ttk.Label(self, text="Sua playlist na biblioteca.", font=("Segoe UI", 21, "bold"), anchor="center").grid(row=0, column=0, sticky="ew")
        row = ttk.Frame(self)
        row.grid(row=1, column=0, sticky="ew", pady=18)
        ttk.Entry(row, textvariable=self.url).pack(side="left", fill="x", expand=True)
        self.load_button = ttk.Button(row, text="Carregar playlist", command=self.load)
        self.load_button.pack(side="left", padx=8)
        ttk.Button(row, text="TXT / M3U", command=self.text_file).pack(side="left")
        ttk.Label(self, textvariable=self.status, style="Muted.TLabel", wraplength=790, anchor="center", justify="center").grid(row=2, column=0, sticky="ew", pady=(0, 12))
        panel = ttk.Frame(self)
        panel.grid(row=3, column=0, sticky="nsew")
        self.table = ttk.Treeview(panel, columns=("title", "artist", "duration", "match"), show="headings", selectmode="extended")
        for key, label, width in (("title", "MÚSICA", 270), ("artist", "ARTISTA", 170), ("duration", "DURAÇÃO", 85), ("match", "VERSÃO NO YOUTUBE", 270)):
            self.table.heading(key, text=label)
            self.table.column(key, width=width, minwidth=60, stretch=key in ("title", "match"))
        self.table.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(panel, command=self.table.yview).pack(side="right", fill="y")
        self.table.configure(yscrollcommand=panel.winfo_children()[-1].set)
        controls = ttk.Frame(self)
        controls.grid(row=4, column=0, sticky="ew", pady=12)
        ttk.Button(controls, text="Selecionar todas", command=lambda: self.table.selection_set(self.table.get_children())).pack(side="left")
        self.check_button = ttk.Button(controls, text="Conferir correspondências", command=self.check)
        self.check_button.pack(side="left", padx=8)
        self.add_button = ttk.Button(controls, text="Adicionar selecionadas", command=self.add, style="Accent.TButton")
        self.add_button.pack(side="right")
        ttk.Checkbutton(self, text="Confirmar a versão do YouTube de cada música antes de baixar", variable=self.confirm_version).grid(row=5, column=0, sticky="w", pady=6)
        ttk.Label(self, text="Selecione com Ctrl/Shift. O formato usa a escolha da tela Links e fila; a consulta é refeita ao baixar.", style="Muted.TLabel", wraplength=790).grid(row=6, column=0, sticky="w", pady=8)
        self.poll_id = self.after(100, self.poll)

    def set_busy(self, value):
        self.busy = value
        for button in (self.load_button, self.check_button, self.add_button):
            button.configure(state="disabled" if value else "normal")

    def load(self):
        if self.busy:
            return
        self.generation += 1
        generation, url = self.generation, self.url.get().strip()
        self.status.set("Carregando playlist…")
        self.set_busy(True)
        def worker():
            client = MetadataClient()
            try:
                self.events.put((generation, "loaded", load_playlist(url, client)))
            except Exception as exc:
                self.events.put((generation, "error", str(exc)))
            finally:
                client.close()
        threading.Thread(target=worker, daemon=True).start()

    def text_file(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(parent=self.app, filetypes=[("Listas", "*.txt *.m3u *.m3u8")])
        if path:
            try:
                from pathlib import Path
                if Path(path).stat().st_size > 1024 * 1024:
                    raise ValueError("A lista deve ter até 1 MB.")
                self.display(load_text(Path(path).read_text(encoding="utf-8-sig")))
            except (OSError, ValueError) as exc:
                self.status.set(str(exc))

    def display(self, result):
        self.table.delete(*self.table.get_children())
        self.records = {str(i): row for i, row in enumerate(result["tracks"])}
        for key, row in self.records.items():
            self.table.insert("", "end", iid=key, values=(row["title"], ", ".join(row.get("artists", [])),
                duration_label(row["duration_ms"] / 1000 if row.get("duration_ms") else None), "A consultar"))
        self.table.selection_set(self.table.get_children())
        self.status.set(f"{result['title']} · {len(self.records)} itens. {result['note']}")
        self.set_busy(False)

    def check(self):
        selected = [(key, self.records[key]) for key in self.table.selection()]
        if self.busy or not selected:
            return
        generation = self.generation
        credentials = self.app.spotify_client_id.get(), self.app.spotify_client_secret.get()
        self.set_busy(True)
        self.status.set("Conferindo versões das faixas selecionadas…")
        def worker():
            from catalog_match import CatalogChoiceRequired
            from matching import find_youtube, AmbiguousMatch
            class Quiet:
                def debug(self, _): pass
                def warning(self, _): pass
                def error(self, _): pass
            client = MetadataClient(*credentials)
            try:
                for key, row in selected:
                    if self.closed:
                        return
                    try:
                        if not is_streaming_link(row["source_url"]):
                            status = "Vídeo da própria playlist"
                        else:
                            record = client.resolve(row["source_url"])
                            match = find_youtube(record, Quiet())
                            status = match["title"]
                    except (CatalogChoiceRequired, AmbiguousMatch):
                        status = "Escolha necessária ao baixar"
                    except Exception as exc:
                        status = str(exc)
                    self.events.put((generation, "match", (key, status)))
            finally:
                client.close()
                self.events.put((generation, "checked", None))
        threading.Thread(target=worker, daemon=True).start()

    def add(self):
        if self.busy:
            return
        selected = [self.records[key] for key in self.table.selection()]
        count = 0
        for row in selected:
            added = self.app.add(lines=[row["source_url"]], overrides={"playlist": False, "confirm_version": self.confirm_version.get()})
            count += len(added or [])
        self.status.set(f"{count} itens adicionados. Confira o formato na fila antes de iniciar.")
        if count:
            self.app.pages.select(self.app.download_page)

    def poll(self):
        if self.closed:
            return
        for _ in range(40):
            try:
                generation, kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if generation != self.generation:
                continue
            if kind == "loaded":
                self.display(value)
            elif kind == "error":
                self.status.set(value)
                self.set_busy(False)
            elif kind == "match" and self.table.exists(value[0]):
                self.table.set(value[0], "match", value[1])
            elif kind == "checked":
                self.status.set("Consulta concluída. Versões incertas serão confirmadas ao baixar.")
                self.set_busy(False)
        self.poll_id = self.after(100, self.poll)

    def shutdown(self):
        self.closed = True
        self.generation += 1
        self.after_cancel(self.poll_id)
