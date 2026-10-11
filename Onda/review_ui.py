"""Metadata/collision dialogs used by the worker's request/reply protocol."""
import base64
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from review import apply_review, local_cover


class MetadataReview(tk.Toplevel):
    def __init__(self, parent, event, on_select, on_cancel):
        super().__init__(parent)
        self.title("Onda • Revisar antes de baixar")
        self.geometry("730x670")
        self.minsize(650, 630)
        self.configure(bg="#10151e")
        self.transient(parent)
        self.record = event["record"]
        from audio_tools import PreviewPlayer
        self.player = PreviewPlayer()
        self.audio_source = event.get("audio_source")
        self.callback = on_select
        self.messages = queue.Queue()
        self.generation = 0
        self.photo = None
        self.ffmpeg = parent.ffmpeg.get()
        self.cover_path = ""
        self.variables = {}
        self.poll_id = None
        body = ttk.Frame(self, padding=22)
        body.pack(fill="both", expand=True)
        body.columnconfigure(1, weight=1)
        ttk.Label(body, text="Sua música, do seu jeito.", font=("Segoe UI", 19, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))
        self.art = ttk.Label(body, text="Capa", anchor="center", width=18)
        self.art.grid(row=1, column=0, rowspan=3, padx=(0, 20))
        for row, (field, label) in enumerate((("title", "Música"), ("artists", "Artistas (separados por ;)") , ("album", "Álbum")), 1):
            panel = ttk.Frame(body)
            panel.grid(row=row, column=1, sticky="ew", pady=4)
            ttk.Label(panel, text=label, style="Muted.TLabel").pack(anchor="w")
            value = "; ".join(self.record.get("artists", [])) if field == "artists" else self.record.get(field) or ""
            self.variables[field] = tk.StringVar(value=value)
            ttk.Entry(panel, textvariable=self.variables[field]).pack(fill="x", pady=(3, 0))
        details = ttk.Frame(body)
        details.grid(row=4, column=0, columnspan=2, sticky="ew", pady=16)
        for column, (field, label) in enumerate((("release_date", "Data"), ("genre", "Gênero"), ("track_number", "Faixa"), ("disc_number", "Disco"))):
            details.columnconfigure(column, weight=1)
            ttk.Label(details, text=label, style="Muted.TLabel").grid(row=0, column=column, sticky="w")
            self.variables[field] = tk.StringVar(value=self.record.get(field) or "")
            ttk.Entry(details, textvariable=self.variables[field], width=14).grid(row=1, column=column, sticky="ew", padx=(0, 8), pady=5)
        ttk.Label(body, text="Capa · imagem inteira, sem cortes", font=("Segoe UI", 11, "bold")).grid(row=5, column=0, columnspan=2, sticky="w")
        self.cover_url = tk.StringVar(value=self.record.get("cover_url") or "")
        ttk.Entry(body, textvariable=self.cover_url).grid(row=6, column=0, columnspan=2, sticky="ew", pady=8)
        buttons = ttk.Frame(body)
        buttons.grid(row=7, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Escolher JPEG/PNG", command=self.choose_cover).pack(side="left")
        ttk.Button(buttons, text="Usar URL da capa", command=self.use_url).pack(side="left", padx=8)
        if self.audio_source:
            ttk.Button(buttons, text="Ouvir áudio / parar", command=self.preview).pack(side="left")
        self.cover_status = tk.StringVar()
        ttk.Label(body, textvariable=self.cover_status, style="Muted.TLabel", wraplength=650).grid(row=8, column=0, columnspan=2, sticky="w", pady=10)
        ttk.Label(body, text="A edição altera as tags e o nome do arquivo. A versão de áudio escolhida é mantida.", style="Muted.TLabel", wraplength=650).grid(row=9, column=0, columnspan=2, sticky="w", pady=8)
        footer = ttk.Frame(body)
        footer.grid(row=10, column=0, columnspan=2, sticky="ew", pady=12)
        ttk.Button(footer, text="Cancelar download", command=on_cancel).pack(side="left")
        ttk.Button(footer, text="Confirmar e baixar", style="Accent.TButton", command=self.confirm).pack(side="right")
        self.protocol("WM_DELETE_WINDOW", on_cancel)
        self.load_cover()
        self.poll_id = self.after(100, self.poll)

    def choose_cover(self):
        path = filedialog.askopenfilename(parent=self, title="Capa do álbum", filetypes=[("Capas", "*.jpg *.jpeg *.png")])
        if path:
            self.cover_path = path
            self.load_cover()

    def use_url(self):
        self.cover_path = ""
        self.load_cover()

    def load_cover(self):
        self.generation += 1
        generation, path, url, folder = self.generation, self.cover_path, self.cover_url.get(), self.ffmpeg
        self.cover_status.set("Carregando capa…")
        def worker():
            try:
                from audio_tools import executable, process_options
                from tagging import fetch_cover
                cover = local_cover(path) if path else fetch_cover(url)
                if not cover:
                    self.messages.put((generation, None, "Sem capa."))
                    return
                result = subprocess.run([executable("ffmpeg", folder), "-v", "error", "-i", "pipe:0", "-vf",
                    "scale=150:150:force_original_aspect_ratio=decrease", "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
                    input=cover[0], capture_output=True, timeout=20, **process_options())
                if result.returncode:
                    raise ValueError("Não foi possível ler a capa.")
                self.messages.put((generation, result.stdout, "Capa local selecionada." if path else "Capa da URL selecionada."))
            except Exception as exc:
                self.messages.put((generation, None, str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        for message in self.player.messages():
            self.cover_status.set(message)
        for _ in range(10):
            try:
                generation, image, status = self.messages.get_nowait()
            except queue.Empty:
                break
            if generation != self.generation:
                continue
            self.cover_status.set(status)
            if image:
                self.photo = tk.PhotoImage(data=base64.b64encode(image))
                self.art.configure(image=self.photo, text="", width=0)
            else:
                self.photo = None
                self.art.configure(image="", text="Sem prévia", width=18)
        self.poll_id = self.after(100, self.poll)

    def preview(self):
        if self.player.active:
            self.player.stop()
            return
        from urllib.parse import urlsplit
        host = (urlsplit(self.audio_source).hostname or "").lower()
        youtube = host in ("youtu.be", "youtube.com", "www.youtube.com", "music.youtube.com")
        self.cover_status.set("Preparando a prévia do áudio escolhido…")
        self.player.play(self.audio_source, self.ffmpeg, youtube=youtube)

    def confirm(self):
        try:
            changes = {key: variable.get().strip() for key, variable in self.variables.items()}
            changes["artists"] = [a.strip() for a in changes["artists"].split(";") if a.strip()]
            for field in ("track_number", "disc_number"):
                changes[field] = int(changes[field]) if changes[field] else None
            changes.update(cover_url=self.cover_url.get().strip(), cover_path=self.cover_path)
            apply_review(self.record, changes)
        except (ValueError, OSError) as exc:
            messagebox.showerror("Revisar metadados", str(exc), parent=self)
            return
        self.callback(changes)

    def destroy(self):
        self.generation += 1
        self.player.close()
        if self.poll_id:
            self.after_cancel(self.poll_id)
            self.poll_id = None
        super().destroy()


class DuplicateDialog(tk.Toplevel):
    def __init__(self, parent, event, on_select, on_cancel):
        super().__init__(parent)
        self.title("Onda • Arquivo já existe")
        self.geometry("660x290")
        self.minsize(600, 270)
        self.configure(bg="#10151e")
        self.transient(parent)
        body = ttk.Frame(self, padding=24)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Esta música já está na pasta.", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(body, text=event["path"], wraplength=600, style="Muted.TLabel").pack(anchor="w", pady=16)
        ttk.Label(body, text="Manter ambos acrescenta (2), (3)… ao nome da nova cópia.", style="Muted.TLabel").pack(anchor="w", pady=8)
        row = ttk.Frame(body)
        row.pack(fill="x", pady=16)
        for label, choice in (("Ignorar novo", "skip"), ("Substituir existente", "replace"), ("Manter ambos", "keep")):
            ttk.Button(row, text=label, command=lambda value=choice: on_select(value)).pack(side="left", padx=(0, 8))
        self.protocol("WM_DELETE_WINDOW", on_cancel)
