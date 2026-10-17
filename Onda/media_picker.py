"""Select individual photos/videos before downloading a large carousel."""
from i18n import tr
from i18n_tk import TranslatedCombobox, display_var
import io
import queue
import threading
import tkinter as tk
from tkinter import ttk


class MediaPicker(tk.Toplevel):
    def __init__(self, app, event, confirm, cancel):
        super().__init__(app)
        self.title(tr("Escolher fotos e vídeos"))
        self.geometry("850x600")
        self.minsize(730, 500)
        self.transient(app)
        self.configure(bg="#101419")
        self.protocol("WM_DELETE_WINDOW", cancel)
        self.items = event["candidates"]
        self.confirm, self.cancel = confirm, cancel
        self.variables = {item["id"]: tk.BooleanVar(value=item.get("auto_select_media",True) is not False) for item in self.items}
        self.video_modes = {}
        self.results = queue.Queue()
        self.generation = 0
        self.preview_image = None
        self.cookies = app.social_cookies.get().strip()
        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=tr("O que você quer baixar?"), font=("Segoe UI", 18, "bold"), anchor="center").pack(fill="x")
        ttk.Label(body, text=tr(f"{len(self.items)} mídias encontradas · marque as desejadas e confirme."), style="Muted.TLabel", anchor="center").pack(fill="x", pady=(6, 16))
        panels = ttk.Frame(body)
        panels.pack(fill="both", expand=True)
        left = ttk.Frame(panels)
        left.pack(side="left", fill="both", expand=True)
        canvas = tk.Canvas(left, bg="#191f27", highlightthickness=0, width=350)
        scrollbar = ttk.Scrollbar(left, command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        rows = ttk.Frame(canvas, padding=8)
        embedded = canvas.create_window((0, 0), window=rows, anchor="nw")
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(embedded, width=event.width))
        rows.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<MouseWheel>", lambda event: canvas.yview_scroll(-int(event.delta/120), "units"))
        for item in self.items:
            row = ttk.Frame(rows)
            row.pack(fill="x", pady=4)
            dimensions = f" · {item['width']} × {item['height']}" if item.get("width") and item.get("height") else ""
            ttk.Checkbutton(row, text=tr(f"{item['number']:02d} · {item['kind']}{dimensions}"),
                            variable=self.variables[item["id"]], command=lambda value=item: self.changed(value)).pack(side="left")
            ttk.Button(row, text=tr("Ver"), command=lambda value=item: self.preview(value), width=5).pack(side="right")
            from media_selection import output_choices
            choices = {} if item.get("automatic_quality") else output_choices(item)
            if item.get('photo_choice') and not item.get('has_audio'):
                ttk.Label(rows, text=tr('A plataforma não disponibilizou a música desta foto.'),
                          wraplength=320, style='Muted.TLabel').pack(fill='x', padx=20)
            if choices:
                mode = item.get('default_mode', 'mp4')
                label = next((label for label, value in choices.items() if value == mode), next(iter(choices)))
                self.video_modes[item['id']] = tk.StringVar(value=label)
                TranslatedCombobox(rows, textvariable=self.video_modes[item['id']], values=tuple(choices),
                             state='readonly', width=27).pack(fill='x', padx=(20, 8), pady=(0, 8))

        right = ttk.Frame(panels, width=340)
        right.pack(side="right", fill="both", padx=(16, 0))
        right.pack_propagate(False)
        self.preview_title = tk.StringVar()
        ttk.Label(right, textvariable=display_var(self.preview_title), wraplength=320, anchor="center").pack(fill="x", pady=(4, 12))
        self.preview_label = ttk.Label(right, text=tr("Selecione Ver para visualizar."), anchor="center")
        self.preview_label.pack(fill="both", expand=True)
        ttk.Label(right, text=tr("Vídeos mostram uma miniatura."), style="Muted.TLabel", anchor="center").pack(fill="x", pady=8)
        footer = ttk.Frame(body)
        footer.pack(fill="x", pady=(16, 0))
        self.select_all_button = ttk.Button(footer, command=lambda: self.select_all(len(self.selected()) != len(self.items)))
        self.select_all_button.pack(side="left")
        self.download_button = ttk.Button(footer, style="Accent.TButton", command=self.accept)
        self.download_button.pack(side="right")
        ttk.Button(footer, text=tr("Cancelar"), command=cancel).pack(side="right", padx=8)
        self.changed()
        self.after_id = self.after(100, self.poll)
        if self.items:
            self.preview(self.items[0])
        self.grab_set()

    def selected(self):
        return [key for key, variable in self.variables.items() if variable.get()]

    def changed(self, item=None):
        count = len(self.selected())
        self.select_all_button.configure(text=tr("Desmarcar todas" if self.items and count == len(self.items) else "Selecionar todas"))
        self.download_button.configure(text=tr(f"Baixar selecionados ({count})"), state="normal" if count else "disabled")
        if item:
            self.preview(item)

    def select_all(self, value):
        for variable in self.variables.values():
            variable.set(value)
        self.changed()

    def accept(self):
        if self.selected():
            from media_selection import output_choices
            items = {item['id']: item for item in self.items}
            modes = {key: output_choices(items[key])[variable.get()] for key, variable in self.video_modes.items() if key in self.selected()}
            self.confirm({'selected_ids': self.selected(), 'media_modes': modes} if modes else self.selected())

    def preview(self, item):
        self.generation += 1
        generation = self.generation
        self.preview_title.set(f"{item['number']:02d} · {item['kind']}\n{item['title'][:100]}")
        self.preview_image = None
        self.preview_label.configure(image="", text=tr("Carregando miniatura…"))
        if not item.get("thumbnail"):
            self.preview_label.configure(text=tr("Miniatura não disponível."))
            return
        def worker():
            try:
                from PIL import Image, ImageOps
                from social_media import session_for
                with session_for(self.cookies) as session, session.get(item["thumbnail"], stream=True, timeout=(10, 15)) as response:
                    response.raise_for_status()
                    content = bytearray()
                    for chunk in response.iter_content(64 * 1024):
                        content.extend(chunk)
                        if len(content) > 8 * 1024 * 1024:
                            raise ValueError("Miniatura muito grande")
                with Image.open(io.BytesIO(content)) as original:
                    result = ImageOps.contain(original.convert("RGB"), (320, 370))
                self.results.put((generation, result))
            except Exception:
                self.results.put((generation, None))
        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            while True:
                generation, result = self.results.get_nowait()
                if generation != self.generation:
                    continue
                if result is None:
                    self.preview_label.configure(image="", text=tr("Não foi possível carregar a miniatura."))
                else:
                    from PIL import ImageTk
                    self.preview_image = ImageTk.PhotoImage(result, master=self)
                    self.preview_label.configure(text=tr(""), image=self.preview_image)
        except queue.Empty:
            pass
        self.after_id = self.after(100, self.poll)

    def destroy(self):
        self.generation += 1
        if getattr(self, "after_id", None):
            self.after_cancel(self.after_id)
            self.after_id = None
        super().destroy()
