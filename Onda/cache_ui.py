"""Settings cache controls: disk work stays off Tk's event thread."""

import queue, threading
import tkinter as tk
from tkinter import ttk
from i18n import tr
from cache_cleanup import cache_info, clear_cache


class CacheControls(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.events = queue.Queue()
        self.working = False
        self.timer = None
        self.closed = False
        ttk.Label(self, text=tr('Cache'), font=('Segoe UI', 13, 'bold')).pack(
            anchor='w', pady=(12, 6)
        )
        ttk.Label(
            self,
            text=tr(
                'Limpa capas, buscas e caches temporários. Downloads, fila, histórico, contas e escolhas salvas são preservados.'
            ),
            wraplength=480,
        ).pack(anchor='w')
        self.status = tk.StringVar(value=tr('Calculando cache…'))
        ttk.Label(self, textvariable=self.status).pack(anchor='w', pady=6)
        self.clear_button = ttk.Button(
            self, text=tr('Limpar cache'), command=lambda: self.run(True)
        )
        self.clear_button.pack(anchor='w')
        ttk.Button(
            self, text=tr('Atualizar tamanho'), command=lambda: self.run(False)
        ).pack(anchor='w', pady=6)
        self.bind("<Destroy>", self.on_destroy, add="+")
        self.run(False)
        self.timer = self.after(100, self.poll)

    def run(self, clear):
        if self.working:
            return
        app = self.app
        catalog = app.catalog_page._content
        searching = catalog is not None and catalog.search_button.cget("text") == tr(
            "Cancelar"
        )
        if clear and (
            searching
            or app.running
            or app.active
            or app.updating
            or any(
                page.busy
                for page in (
                    app.playlist_page,
                    app.effects_page,
                    app.metadata_page,
                    app.converter_page,
                )
            )
        ):
            self.status.set(
                tr('Aguarde as operações em andamento antes de limpar o cache.')
            )
            return
        self.working = True
        self.clear_button.configure(state='disabled')
        if clear:
            app.catalog_page.stop_preview()
            app.effects_page.stop_preview()
            app.metadata_page.stop_preview()
            cards = getattr(app, 'queue_cards', None)
            if cards:
                cards.artwork.cache.clear()
        events = self.events

        def worker():
            try:
                events.put((clear, (clear_cache if clear else cache_info)()))
            except Exception:
                events.put((clear, None))

        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        try:
            clear, result = self.events.get_nowait()
            self.working = False
            self.clear_button.configure(state='normal')
            if result is None:
                self.status.set(tr('Não foi possível limpar ou calcular o cache.'))
            else:
                template = (
                    'Cache limpo. Restante em disco: {size} MB.'
                    if clear
                    else 'Cache em disco: {size} MB.'
                )
                self.status.set(
                    tr(template).replace('{size}', f"{result['bytes']/1048576:.2f}")
                )
                if result.get('failed'):
                    self.status.set(tr('Alguns arquivos em uso foram preservados.'))
        except queue.Empty:
            pass
        if not self.closed:
            self.timer = self.after(100, self.poll)

    def on_destroy(self, event):
        if event.widget is self:
            self.closed = True
            if self.timer:
                self.after_cancel(self.timer)
                self.timer = None
