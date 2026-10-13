"""Independent catalog window; all network work stays off the Tk thread."""
import json
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser

from metadata import MetadataClient, MetadataError


class MetadataWindow(tk.Toplevel):
    def __init__(self, parent, links=()):
        super().__init__(parent)
        self.title("Onda • Metadados de músicas")
        self.geometry("960x740")
        self.minsize(780, 680)
        self.configure(bg="#10151e")
        self.records = []
        self.messages = queue.Queue()
        self.stop = threading.Event()
        self.busy = False
        self.client_id = parent.spotify_client_id
        self.client_secret = parent.spotify_client_secret
        self.status = tk.StringVar(value="Cole links de músicas do Deezer, Spotify ou Apple Music/iTunes.")
        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(5, weight=1)
        body.rowconfigure(6, weight=1)
        ttk.Label(body, text="Metadados das músicas", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(body, text="Consulta avulsa de faixas • Para baixar áudio com tags, adicione o link à fila da janela principal.",
                  style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 10))
        self.links = tk.Text(body, height=3, bg="#1a2230", fg="#eef3fa", insertbackground="white", relief="flat")
        self.links.grid(row=2, column=0, sticky="ew")
        self.links.bind("<Return>", self.enter_fetch)
        self.links.bind("<KP_Enter>", self.enter_fetch)
        self.links.insert("1.0", "\n".join(links))
        auth = ttk.LabelFrame(body, text="Spotify API (opcional)", padding=8)
        auth.grid(row=3, column=0, sticky="ew", pady=10)
        auth.columnconfigure(1, weight=1)
        auth.columnconfigure(3, weight=1)
        ttk.Label(auth, text="Client ID").grid(row=0, column=0, padx=5)
        ttk.Entry(auth, textvariable=self.client_id).grid(row=0, column=1, sticky="ew")
        ttk.Label(auth, text="Client Secret").grid(row=0, column=2, padx=8)
        ttk.Entry(auth, textvariable=self.client_secret, show="•").grid(row=0, column=3, sticky="ew")
        save_row = ttk.Frame(auth)
        save_row.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 0))
        ttk.Button(save_row, text="Salvar neste computador", command=parent.save_spotify_credentials).pack(side="left")
        ttk.Button(save_row, text="Esquecer credenciais", command=parent.forget_spotify_credentials).pack(side="left", padx=8)
        ttk.Label(auth, textvariable=parent.credential_status, style="Muted.TLabel", wraplength=820).grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        row = ttk.Frame(body)
        row.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.fetch_button = ttk.Button(row, text="Consultar metadados", style="Accent.TButton", command=self.fetch)
        self.fetch_button.pack(side="left")
        self.cancel_button = ttk.Button(row, text="Cancelar consulta", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=8)
        self.export_button = ttk.Button(row, text="Exportar JSON", command=self.export, state="disabled")
        self.export_button.pack(side="right")
        table = ttk.Frame(body)
        table.grid(row=5, column=0, sticky="nsew")
        self.table = ttk.Treeview(table, columns=("platform", "title", "artist", "album"), show="headings", height=4)
        for name, label, width in (("platform", "FONTE", 110), ("title", "TÍTULO", 260),
                                    ("artist", "ARTISTA", 210), ("album", "ÁLBUM", 220)):
            self.table.heading(name, text=label)
            self.table.column(name, width=width, minwidth=80)
        self.table.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.table.yview)
        scroll.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scroll.set)
        self.table.bind("<<TreeviewSelect>>", self.select)
        self.details = tk.Text(body, height=10, bg="#1a2230", fg="#eef3fa", relief="flat", wrap="word", state="disabled")
        self.details.grid(row=6, column=0, sticky="nsew", pady=10)
        actions = ttk.Frame(body)
        actions.grid(row=7, column=0, sticky="ew")
        self.source_button = ttk.Button(actions, text="Abrir na plataforma", command=lambda: self.open_url("source_url"), state="disabled")
        self.source_button.pack(side="left")
        self.cover_button = ttk.Button(actions, text="Abrir capa", command=lambda: self.open_url("cover_url"), state="disabled")
        self.cover_button.pack(side="left", padx=8)
        ttk.Button(actions, text="Configurar API Spotify", command=lambda: webbrowser.open(
            "https://developer.spotify.com/dashboard")).pack(side="right")
        ttk.Label(body, textvariable=self.status, style="Muted.TLabel", wraplength=850).grid(row=8, column=0, sticky="ew", pady=(10, 0))
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after_id = self.after(100, self.poll)

    def enter_fetch(self, _event=None):
        self.fetch()
        return "break"

    def fetch(self):
        if self.busy:
            return
        links = list(dict.fromkeys(line.strip() for line in self.links.get("1.0", "end").splitlines() if line.strip()))
        if not links:
            return
        if len(links) > 100:
            messagebox.showwarning("Muitos links", "Consulte até 100 músicas por vez.", parent=self)
            return
        self.records.clear()
        self.table.delete(*self.table.get_children())
        self.set_details("")
        for button in (self.export_button, self.source_button, self.cover_button, self.fetch_button):
            button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.status.set("Consultando…")
        self.busy = True
        self.stop.clear()
        threading.Thread(target=self.worker, args=(links, self.client_id.get(), self.client_secret.get()), daemon=True).start()

    def worker(self, links, client_id, secret):
        client = MetadataClient(client_id, secret)
        try:
            for index, link in enumerate(links, 1):
                if self.stop.is_set():
                    break
                try:
                    record = client.fetch(link)
                    event = ("record", record)
                except (MetadataError, ValueError) as exc:
                    event = ("error", f"Link {index}: {exc}")
                except Exception:
                    event = ("error", f"Link {index}: resposta inesperada da plataforma. Tente novamente.")
                if self.stop.is_set():
                    break
                self.messages.put(event)
                self.messages.put(("progress", f"Consultadas {index} de {len(links)} músicas"))
        finally:
            client.close()
            self.messages.put(("done", None))

    def poll(self):
        while not self.messages.empty():
            kind, value = self.messages.get_nowait()
            if kind == "record":
                index = len(self.records)
                self.records.append(value)
                self.table.insert("", "end", iid=str(index), values=(value["platform"], value["title"],
                                  ", ".join(value["artists"]) or "Não informado", value["album"] or "Não informado"))
                self.export_button.configure(state="normal")
                if index == 0:
                    self.table.selection_set("0")
                    self.select()
            elif kind == "error":
                self.master.write_log(value)
                # Errors remain in the table as well as the main log.
                self.table.insert("", "end", iid="error" + str(len(self.table.get_children())),
                                  values=("Erro", value, "", ""))
            elif kind == "progress":
                self.status.set(value)
            elif kind == "done":
                self.busy = False
                self.fetch_button.configure(state="normal")
                self.cancel_button.configure(state="disabled")
                errors = sum(item.startswith("error") for item in self.table.get_children())
                state = "Cancelado" if self.stop.is_set() else "Consulta encerrada"
                self.status.set(f"{state} • {len(self.records)} resultados • {errors} erros. Selecione uma linha para ver os detalhes.")
        self.after_id = self.after(100, self.poll)

    def selected_record(self):
        selected = self.table.selection()
        if selected and selected[0].isdigit():
            return self.records[int(selected[0])]

    def select(self, _=None):
        record = self.selected_record()
        self.source_button.configure(state="normal" if record else "disabled")
        self.cover_button.configure(state="normal" if record and record.get("cover_url") else "disabled")
        if not record:
            selected = self.table.selection()
            self.set_details(self.table.item(selected[0], "values")[1] if selected else "")
            return
        labels = {"title": "Título", "artists": "Artistas", "album": "Álbum", "album_artists": "Artistas do álbum",
                  "release_date": "Lançamento", "duration_ms": "Duração (ms)", "track_number": "Faixa",
                  "disc_number": "Disco", "genre": "Gênero", "isrc": "ISRC", "explicit": "Explícita",
                  "cover_url": "Capa", "source_url": "Link na plataforma", "method": "Origem dos dados", "notes": "Observações"}
        lines = []
        for key, label in labels.items():
            value = record.get(key)
            if isinstance(value, list):
                value = "; ".join(value)
            if isinstance(value, bool):
                value = "Sim" if value else "Não"
            lines.append(f"{label}: {value if value is not None and value != '' else 'Não informado'}")
        self.set_details("\n".join(lines))

    def set_details(self, value):
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", value)
        self.details.configure(state="disabled")

    def open_url(self, field):
        record = self.selected_record()
        if record and str(record.get(field, "")).startswith("https://"):
            webbrowser.open(record[field])

    def export(self):
        if not self.records:
            return
        filename = filedialog.asksaveasfilename(parent=self, title="Exportar metadados", defaultextension=".json",
                                              initialfile="metadados.json", filetypes=[("JSON", "*.json")])
        if filename:
            try:
                Path(filename).write_text(json.dumps(self.records, ensure_ascii=False, indent=2), encoding="utf-8")
                self.status.set("Metadados exportados em JSON.")
            except OSError as exc:
                messagebox.showerror("Exportação", str(exc), parent=self)

    def cancel(self):
        self.stop.set()
        self.cancel_button.configure(state="disabled")
        self.status.set("Cancelando; aguardando a requisição atual encerrar…")

    def close(self):
        self.stop.set()
        self.after_cancel(self.after_id)
        self.destroy()
