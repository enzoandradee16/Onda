"""Selective multi-file metadata editor; originals are preserved by default."""

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox
from i18n import tr
from i18n_tk import display_var


class BatchMetadataEditor(tk.Toplevel):
    def __init__(self, parent, app, sources=()):
        super().__init__(parent)
        self.app = app
        self.sources = list(dict.fromkeys(str(Path(p).resolve()) for p in sources))
        self.busy = False
        self.events = queue.Queue()
        self.cover = ''
        self.title(tr('Editar metadados em lote'))
        self.geometry('700x740')
        self.minsize(620, 640)
        self.transient(app)
        self.protocol('WM_DELETE_WINDOW', self.close)
        from settings_scroll import SettingsCategory

        scroller = SettingsCategory(self, self.cget('background'), padding=20)
        scroller.pack(fill='both', expand=True)
        body = scroller.content
        self.bind('<MouseWheel>', scroller.wheel, add='+')
        self.count = tk.StringVar()
        ttk.Label(
            body, text=tr('Editar metadados em lote'), font=('Segoe UI', 18, 'bold')
        ).pack(anchor='w')
        ttk.Label(body, textvariable=display_var(self.count)).pack(
            anchor='w', pady=(8, 0)
        )
        self.files = tk.Text(body, height=4, wrap='word', state='disabled')
        self.files.pack(fill='x', pady=8)
        self.widgets = []

        def button(label, command):
            widget = ttk.Button(body, text=tr(label), command=command)
            widget.pack(anchor='w', pady=4)
            self.widgets.append(widget)
            return widget

        button('Escolher vários arquivos de áudio', self.choose)
        ttk.Label(
            body,
            text=tr(
                'Marque somente os campos que deseja alterar. Campos desmarcados serão preservados.'
            ),
            wraplength=620,
        ).pack(anchor='w', pady=10)
        self.fields = {}
        self.selected = {}
        for key, label in [
            ('artists', 'Artistas (separados por ;)'),
            ('album', 'Álbum'),
            ('genre', 'Gênero'),
            ('release_date', 'Data'),
            ('track_number', 'Faixa'),
            ('disc_number', 'Disco'),
        ]:
            row = ttk.Frame(body)
            row.pack(fill='x', pady=3)
            selected, value = tk.BooleanVar(value=False), tk.StringVar()
            entry = ttk.Entry(row, textvariable=value, state='disabled')
            check = ttk.Checkbutton(
                row,
                text=tr(label),
                variable=selected,
                command=lambda selected=selected, entry=entry: entry.configure(
                    state='normal' if selected.get() else 'disabled'
                ),
            )
            check.pack(side='left')
            entry.pack(side='right', fill='x', expand=True, padx=(12, 0))
            self.fields[key], self.selected[key] = value, selected
            self.widgets.append(check)
        self.cover_label = tk.StringVar(value='Nenhuma capa selecionada')
        button('Aplicar uma capa aos arquivos', self.choose_cover)
        ttk.Label(body, textvariable=display_var(self.cover_label)).pack(anchor='w')
        button('Remover capa selecionada', self.remove_cover)
        self.overwrite = tk.BooleanVar(value=False)
        check = ttk.Checkbutton(
            body, text=tr('Sobrescrever arquivo original'), variable=self.overwrite
        )
        check.pack(anchor='w', pady=10)
        self.widgets.append(check)
        ttk.Label(
            body,
            text=tr(
                'Por padrão, cópias editadas são salvas ao lado dos arquivos originais.'
            ),
            wraplength=620,
        ).pack(anchor='w')
        self.status = tk.StringVar()
        ttk.Label(body, textvariable=display_var(self.status), wraplength=620).pack(
            anchor='w', pady=10
        )
        self.apply = button('Aplicar aos arquivos selecionados', self.run)
        self.refresh_files()
        if hasattr(app, 'theme_manager'):
            app.theme_manager.walk(self)
        self._poll = self.after(100, self.poll)

    def refresh_files(self):
        self.count.set(f'{len(self.sources)} arquivos selecionados')
        self.files.configure(state='normal')
        self.files.delete('1.0', 'end')
        self.files.insert('1.0', '\n'.join(self.sources))
        self.files.configure(state='disabled')

    def choose(self):
        paths = filedialog.askopenfilenames(
            parent=self,
            title=tr('Escolher vários arquivos de áudio'),
            filetypes=[(tr('Áudio'), '*.mp3 *.m4a *.flac *.wav *.ogg *.opus')],
        )
        if paths:
            self.sources = list(dict.fromkeys(paths))
            self.refresh_files()

    def choose_cover(self):
        value = filedialog.askopenfilename(
            parent=self,
            title=tr('Aplicar uma capa aos arquivos'),
            filetypes=[(tr('Imagens'), '*.jpg *.jpeg *.png *.webp')],
        )
        if value:
            self.cover = value
            self.cover_label.set(Path(value).name)

    def remove_cover(self):
        self.cover = ''
        self.cover_label.set('Nenhuma capa selecionada')

    def run(self):
        if self.busy:
            return
        changes = {
            key: value.get()
            for key, value in self.fields.items()
            if self.selected[key].get()
        }
        if 'artists' in changes:
            changes['artists'] = [
                part.strip() for part in changes['artists'].split(';') if part.strip()
            ]
        if (
            not self.sources
            or len(self.sources) > 500
            or not changes
            and not self.cover
        ):
            messagebox.showwarning(
                tr('Editar metadados em lote'),
                tr(
                    'Escolha de 1 a 500 arquivos e selecione pelo menos um campo ou uma capa.'
                ),
                parent=self,
            )
            return
        if self.overwrite.get() and not messagebox.askyesno(
            tr('Editar metadados em lote'),
            tr('Os arquivos originais selecionados serão substituídos. Continuar?'),
            parent=self,
        ):
            return
        config = {
            'sources': [{'source': p} for p in self.sources],
            'changes': changes,
            'cover_path': self.cover,
            'overwrite_original': self.overwrite.get(),
        }
        self.busy = True
        for widget in self.widgets:
            widget.configure(state='disabled')

        def worker():
            try:
                from batch_metadata import edit_batch

                result = edit_batch(
                    config,
                    lambda kind, **event: self.events.put(
                        ('progress', event.get('message', ''))
                    ),
                )
                self.events.put(('result', result))
            except Exception as error:
                self.events.put(('error', str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def poll(self):
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == 'progress':
                self.status.set(value)
                continue
            self.busy = False
            for widget in self.widgets:
                widget.configure(state='normal')
            if kind == 'error':
                self.status.set(value)
            else:
                self.status.set(value['message'])
                for result in value['results']:
                    if not result['overwritten']:
                        self.app.record_history(result['path'], result['mode'].upper())
                self.app.history_page.refresh()
                if value['errors']:
                    messagebox.showwarning(
                        tr('Editar metadados em lote'),
                        '\n'.join(
                            item['name'] + ': ' + tr(item['error'])
                            for item in value['errors'][:10]
                        ),
                        parent=self,
                    )
        self._poll = self.after(100, self.poll)

    def close(self):
        if self.busy:
            self.status.set('Aguarde o processamento terminar antes de fechar.')
            return
        self.after_cancel(self._poll)
        self.destroy()
