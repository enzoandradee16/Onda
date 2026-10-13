"""Dedicated image controls; transfers still use the shared supervised queue."""
import io
import queue
import tempfile
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageOps, ImageTk
from image_output import FORMATS, validate_options, transform_image, open_preview

from image_output import IMAGE_SIZES as SIZES


class ImagesPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(0, 14, 0, 0))
        self.app = app
        self.url = tk.StringVar()
        self.format = app.image_format
        self.size = app.image_size
        self.width, self.height = app.image_width, app.image_height
        self.keep_ratio = app.image_keep_ratio
        self.status = tk.StringVar(value='A imagem inteira é preservada. Arquivos vão para a pasta das configurações.')
        self.events = queue.Queue()
        self.busy, self.closed, self.preview_bytes, self.preview_url = False, False, None, None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        ttk.Label(self, text='Imagens do seu jeito.', font=('Segoe UI', 21, 'bold'), anchor='center').grid(row=0, column=0, sticky='ew')
        ttk.Label(self, text='Baixe, converta e ajuste o tamanho sem cortar a imagem.', style='Muted.TLabel', anchor='center').grid(row=1, column=0, sticky='ew', pady=(5, 16))
        card = ttk.Frame(self, style='Card.TFrame', padding=14)
        card.grid(row=2, column=0, sticky='ew')
        card.columnconfigure(0, weight=1)
        ttk.Entry(card, textvariable=self.url).grid(row=0, column=0, sticky='ew', columnspan=3)
        self.preview_button = ttk.Button(card, text='Ver prévia', command=self.preview)
        self.preview_button.grid(row=0, column=3, padx=(8, 0))
        options = ttk.Frame(card, style='Card.TFrame')
        options.grid(row=1, column=0, columnspan=4, sticky='ew', pady=(12, 0))
        for col, text, var, values, width in ((0, 'Formato', self.format, tuple(FORMATS), 12), (1, 'Tamanho máximo', self.size, tuple(SIZES), 22)):
            ttk.Label(options, text=text, style='CardMuted.TLabel').grid(row=0, column=col, sticky='w')
            ttk.Combobox(options, textvariable=var, values=values, state='readonly', width=width).grid(row=1, column=col, sticky='w', padx=(0, 12), pady=(4, 0))
        self.custom = ttk.Frame(card, style='Card.TFrame')
        self.custom.grid(row=2, column=0, columnspan=4, sticky='ew', pady=(10, 0))
        ttk.Label(self.custom, text='Largura × altura (px)', style='CardMuted.TLabel').pack(side='left', padx=(0, 10))
        ttk.Entry(self.custom, textvariable=self.width, width=7).pack(side='left')
        ttk.Label(self.custom, text=' × ', style='CardMuted.TLabel').pack(side='left')
        ttk.Entry(self.custom, textvariable=self.height, width=7).pack(side='left')
        ttk.Checkbutton(card, text='Manter proporção (sem ampliar ou distorcer)', variable=self.keep_ratio).grid(row=3, column=0, columnspan=4, sticky='w', pady=(10, 0))
        self.format_note = ttk.Label(card, text='SVG incorpora a imagem original; não vetoriza. Animações usam o primeiro quadro.', style='CardMuted.TLabel', wraplength=680)
        self.format_note.grid(row=4, column=0, columnspan=4, sticky='w', pady=(8, 0))
        self.preview_label = ttk.Label(self, text='A prévia aparecerá aqui.', anchor='center', style='Muted.TLabel')
        self.preview_label.grid(row=3, column=0, sticky='nsew', pady=12)
        ttk.Label(self, textvariable=self.status, wraplength=740, anchor='center', style='Muted.TLabel').grid(row=4, column=0, sticky='ew')
        actions = ttk.Frame(self)
        actions.grid(row=5, column=0, sticky='ew', pady=12)
        ttk.Button(actions, text='Adicionar à fila', command=self.enqueue).pack(side='right')
        ttk.Button(actions, text='Baixar agora', style='Accent.TButton', command=lambda:self.enqueue(True)).pack(side='right', padx=8)
        ttk.Button(actions, text='Abrir pasta', command=app.open_folder).pack(side='left')
        self.size.trace_add('write', self.changed)
        for var in (self.format, self.width, self.height, self.keep_ratio):
            var.trace_add('write', self.changed)
        self.url.trace_add('write', self.link_changed)
        self.changed()
        self._poll = self.after(100, self.poll)

    def options(self):
        size = SIZES[self.size.get()]
        if size is None:
            try:
                size = int(self.width.get()), int(self.height.get())
            except ValueError:
                raise ValueError('Informe largura e altura em pixels.')
            if min(size) < 1:
                raise ValueError('As dimensões personalizadas devem ser maiores que zero.')
        return validate_options({'format':self.format.get(), 'width':size[0], 'height':size[1], 'keep_ratio':self.keep_ratio.get()})

    def changed(self, *_):
        if self.format.get() == 'SVG':
            self.format_note.grid()
        else:
            self.format_note.grid_remove()
        if self.size.get() == 'Personalizado':
            self.custom.grid()
        else:
            self.custom.grid_remove()
        if self.preview_bytes:
            self.render_preview()

    def link_changed(self, *_):
        self.preview_bytes = None
        self.preview_label.configure(image='', text='Clique em Ver prévia para conferir a imagem.')
        self.status.set('Links de imagem ou publicações com fotos. Respeite o acesso permitido pelo site.')

    def enqueue(self, start=False):
        if start and self.app.updating:
            messagebox.showinfo('Download em andamento', 'Aguarde a operação atual terminar ou adicione à fila.', parent=self)
            return
        try:
            options = self.options()
            from engine import validate_url
            url = validate_url(self.url.get())
        except (ValueError, KeyError) as exc:
            messagebox.showwarning('Imagens', str(exc), parent=self)
            return
        added = self.app.add(lines=[url], overrides={'mode':'photos', 'playlist':False, 'image_options':options}, reuse_existing=start)
        if added:
            self.app.pages.select(self.app.download_page)
            if start:
                self.app.start(only_item=added[0])

    def preview(self):
        if self.busy:
            return
        try:
            from engine import validate_url
            url = validate_url(self.url.get())
            self.options()
        except (ValueError, KeyError) as exc:
            messagebox.showwarning('Prévia', str(exc), parent=self)
            return
        cookies = self.app.social_cookies.get().strip()
        requested = self.url.get().strip()
        self.busy = True
        self.preview_button.configure(state='disabled')
        self.status.set('Carregando prévia…')
        def work():
            try:
                from media_links import prepare_link
                with tempfile.TemporaryDirectory(prefix='onda-image-preview-') as folder:
                    files=[]
                    def emit(event, **data):
                        if event == 'file': files.append(data['path'])
                    done, _ = prepare_link({'url':url,'mode':'photos','folder':folder,'cookies_file':cookies,'duplicate_policy':'keep'}, emit, None)
                    if not done or not files:
                        raise ValueError('Prévia disponível para links diretos de imagem e páginas com imagem principal. Publicações continuam disponíveis pelo download.')
                    data=Path(files[0]).read_bytes()
                    with Image.open(io.BytesIO(data)) as image:
                        image.verify()
                    self.events.put((requested, data, None))
            except Exception as exc:
                self.events.put((requested, None, str(exc)))
        threading.Thread(target=work, daemon=True).start()

    def render_preview(self):
        try:
            options=self.options()
            with tempfile.TemporaryDirectory(prefix='onda-image-render-') as folder:
                path=Path(folder)/'preview.img'
                path.write_bytes(self.preview_bytes)
                output=transform_image(path, options)
                with open_preview(output) as image:
                    image=ImageOps.exif_transpose(image)
                    dimensions=image.size
                    image.thumbnail((600, 270), Image.Resampling.LANCZOS)
                    self.photo=ImageTk.PhotoImage(image, master=self)
                self.preview_label.configure(image=self.photo, text='')
                self.status.set(f'{dimensions[0]} × {dimensions[1]} px · tamanho estimado: {output.stat().st_size / 1024:.1f} KB · prévia do primeiro quadro')
        except (ValueError, OSError, KeyError) as exc:
            self.status.set(str(exc))

    def poll(self):
        try:
            while True:
                url, data, error=self.events.get_nowait()
                self.busy=False
                self.preview_button.configure(state='normal')
                if url != self.url.get().strip():
                    continue
                if error:
                    self.status.set(error)
                else:
                    self.preview_bytes, self.preview_url=data,url
                    self.render_preview()
        except queue.Empty:
            pass
        if not self.closed:
            self._poll=self.after(100,self.poll)

    def shutdown(self):
        self.closed=True
        self.after_cancel(self._poll)
