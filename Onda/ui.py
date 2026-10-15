"""Desktop presentation, kept separate from download and queue behavior."""
from i18n import tr
from i18n_tk import TranslatedCombobox, display_var
import tkinter as tk
from tkinter import ttk

from engine import MODES, HEIGHTS, FPS_OPTIONS, MP3_QUALITIES, M4A_QUALITIES

BG = "#101419"
SURFACE = "#191f27"
INPUT = "#222a35"
TEXT = "#eef3f8"
MUTED = "#91a0b3"
ACCENT = "#79e2c4"
LINE = "#2a3441"
FORMAT_LABELS = {"Vídeo (MKV)": "video", "Vídeo (MP4)": "mp4", "MP3": "mp3", "M4A": "m4a", "FLAC": "flac", "Áudio original": "original", "Fotos / carrossel": "photos", "Post completo": "social"}


class UiMixin:
    def _style(self):
        from appearance import palette
        from interface_fonts import font_family, font_scale
        scale = font_scale(self.interface_font_size.get())
        family = font_family(self, self.interface_font.get())
        colors = palette(self.theme_mode.get(), self.theme_accent.get(), self.pure_black_separators.get())
        BG, SURFACE, INPUT, TEXT, MUTED, ACCENT, LINE = (colors[key] for key in ('bg','surface','input','text','muted','accent','line'))
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, font=(family, round(10 * scale)),
                        bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=SURFACE)
        style.configure("HistorySelected.TFrame", background=colors["selected"])
        style.configure("HistorySelected.TLabel", background=colors["selected"], foreground=TEXT)
        style.configure("HistorySelectedMuted.TLabel", background=colors["selected"], foreground=MUTED)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=SURFACE, foreground=MUTED, padding=(8, 9))
        style.map("TNotebook.Tab", background=[("selected", INPUT)], foreground=[("selected", ACCENT)])
        style.configure("TLabel", background=BG)
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("Card.TLabel", background=SURFACE)
        style.configure("CardMuted.TLabel", background=SURFACE, foreground=MUTED)
        style.configure("TButton", background=INPUT, foreground=TEXT, padding=(14, 9), borderwidth=0,
                        focusthickness=0, relief="flat")
        style.map("TButton", background=[("active", colors["hover"]), ("disabled", SURFACE)],
                  foreground=[("disabled", colors["disabled"])])
        style.configure("Quiet.TButton", background=BG, foreground=MUTED, padding=(10, 7))
        style.map("Quiet.TButton", background=[("active", SURFACE), ("disabled", BG)],
                  foreground=[("active", TEXT), ("disabled", colors["disabled"])])
        style.configure("Accent.TButton", background=ACCENT, foreground=colors["accent_text"], font=(family, round(10 * scale), "bold"))
        style.map("Accent.TButton", background=[("active", colors["accent_hover"]), ("disabled", colors["line"])],
                  foreground=[("disabled", colors["muted"]), ("!disabled", colors["accent_text"])])
        style.configure("TEntry", fieldbackground=INPUT, foreground=TEXT, insertcolor=TEXT,
                        padding=8, borderwidth=0)
        style.configure("TCombobox", fieldbackground=INPUT, background=INPUT, arrowcolor=MUTED,
                        foreground=TEXT, padding=(10, 7), borderwidth=0)
        style.map("TCombobox", fieldbackground=[("readonly", INPUT)],
                  foreground=[("readonly", TEXT), ("disabled", MUTED)],
                  background=[("active", LINE), ("readonly", INPUT)])
        style.configure("TCheckbutton", background=BG, foreground=MUTED)
        style.map("TCheckbutton", background=[("active", BG)])
        style.configure("Treeview", background=SURFACE, fieldbackground=SURFACE, foreground=TEXT,
                        rowheight=round(44 * scale), borderwidth=0, relief="flat")
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.configure("Treeview.Heading", background=SURFACE, foreground=MUTED,
                        font=(family, round(9 * scale)), padding=(12, 12), borderwidth=0, relief="flat")
        style.map("Treeview.Heading", background=[("active", SURFACE)])
        style.map("Treeview", background=[("selected", colors["selected"])], foreground=[("selected", TEXT)])
        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=LINE,
                        borderwidth=0, thickness=4, lightcolor=ACCENT, darkcolor=ACCENT)
        style.configure("Vertical.TScrollbar", background=LINE, troughcolor=SURFACE,
                        arrowcolor=MUTED, borderwidth=0, arrowsize=12)
        self.option_add("*TCombobox*Listbox.font", (family, round(10 * scale)))
        self.option_add("*TCombobox*Listbox.background", INPUT)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", colors["selected"])

        style.configure('Horizontal.TScale', background=BG, troughcolor=LINE, sliderrelief='flat')
        style.configure('TRadiobutton', background=BG, foreground=TEXT)
        style.map('TRadiobutton', background=[('active', BG)])
        style.configure('TLabelframe', background=BG, bordercolor=LINE)
        style.configure('TLabelframe.Label', background=BG, foreground=TEXT)
        self.option_add('*TCombobox*Listbox.selectForeground', TEXT)

    def _layout(self):
        self.configure(bg=BG)
        main = ttk.Frame(self, padding=(24, 12, 24, 12))
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        top = ttk.Frame(main)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        mark = tk.Canvas(top, width=28, height=34, bg=BG, highlightthickness=0)
        mark.pack(side="left", padx=(0, 9))
        for x, y in ((4, 13), (10, 7), (16, 2), (22, 10)):
            mark.create_line(x, y + 4, x, 32 - y, width=3, fill=ACCENT, capstyle="round")
        ttk.Label(top, text=tr("ONDA"), font=("Segoe UI", 22, "bold"), foreground=ACCENT).pack(side="left")
        ttk.Button(top, text=tr("Configurações"), style="Quiet.TButton", command=self.show_settings).pack(side="right")
        ttk.Button(top, text=tr("Metadados"), style="Quiet.TButton", command=self.open_metadata).pack(side="right", padx=6)

        self.pages = ttk.Notebook(main)
        self.pages.grid(row=1, column=0, sticky="nsew")
        from settings_scroll import SettingsCategory, scroll_page, refresh_page_layout
        self.download_page = SettingsCategory(self.pages,BG,fill_viewport=True,padding=(0,14,0,0))
        self.bind("<MouseWheel>",scroll_page,add="+")
        self.bind("<Configure>", refresh_page_layout, add="+")
        from lazy_ui import LazyPane
        self.catalog_page = LazyPane(self.pages, self, "catalog_ui", "CatalogPane")
        self.pages.add(self.catalog_page, text=tr("Pesquisar músicas"))
        self.pages.add(self.download_page, text=tr("Links e fila"))
        self.effects_page = LazyPane(self.pages, self, "effects_ui", "EffectsPane")
        self.playlist_page = LazyPane(self.pages, self, "playlist_ui", "PlaylistPane")
        self.history_page = LazyPane(self.pages, self, "history_ui", "HistoryPane")
        self.images_page = LazyPane(self.pages, self, "images_ui", "ImagesPane")
        self.pages.add(self.images_page, text=tr("Imagens"))
        self.pages.add(self.playlist_page, text=tr("Álbuns e playlists"))
        self.pages.add(self.history_page, text=tr("Histórico"))
        self.pages.add(self.effects_page, text=tr("Slowed / Sped Up"))
        self.metadata_page = LazyPane(self.pages, self, "audio_editor_ui", "MetadataPane")
        self.pages.add(self.metadata_page, text=tr("Editar metadados"))
        self.bind("<Control-MouseWheel>",lambda event:self.history_page.resize_cards(event)
                  if self.pages.select()==str(self.history_page) else self.queue_cards.resize_cards(event)
                  if self.pages.select()==str(self.download_page) else scroll_page(event))
        from tab_order import TabReorder
        self.tab_reorder = TabReorder(self.pages, {
            'catalog': self.catalog_page, 'downloads': self.download_page,
            'images': self.images_page, 'playlists': self.playlist_page,
            'history': self.history_page, 'effects': self.effects_page, 'metadata': self.metadata_page,
        }, self.tab_order.get(), lambda order: self.tab_order.set(tuple(order)))
        self.pages.bind("<<NotebookTabChanged>>", self.tab_changed)
        main = self.download_page.content
        main.columnconfigure(0, weight=1)
        main.rowconfigure(4, weight=1, minsize=90)

        heading = ttk.Frame(main)
        heading.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(heading, text=tr("Do link para sua biblioteca."), font=("Segoe UI", 21, "bold"), anchor="center").pack(fill="x")
        ttk.Label(heading, text=tr("Músicas, vídeos e fotos, organizados do seu jeito."), style="Muted.TLabel", anchor="center").pack(fill="x", pady=(5, 0))

        card = ttk.Frame(main, style="Card.TFrame", padding=14)
        card.grid(row=2, column=0, sticky="ew")
        card.columnconfigure(0, weight=1)
        ttk.Label(card, text=tr("LINKS"), style="CardMuted.TLabel", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
        entry = tk.Frame(card, bg=INPUT)
        entry.grid(row=1, column=0, sticky="ew")
        self.urls = tk.Text(entry, height=2, bg=INPUT, fg=TEXT, insertbackground=ACCENT,
                            selectbackground="#345048", relief="flat", borderwidth=0, highlightthickness=0,
                            font=("Segoe UI", 11), padx=12, pady=8, wrap="word", undo=True)
        self.urls.pack(fill="x")
        self.url_hint = tk.Label(entry, text=tr("YouTube, Instagram, TikTok, Kwai… um link por linha"), bg=INPUT, fg=MUTED,
                                 font=("Segoe UI", 11), cursor="xterm")
        self.url_hint.place(x=12, y=12)
        self.url_hint.bind("<Button-1>", lambda _: self.urls.focus_set())
        self.urls.bind("<FocusIn>", lambda _: self.url_hint.place_forget())
        self.urls.bind("<FocusOut>", lambda _: self.refresh_placeholder())
        self.urls.bind("<<Modified>>", self.on_link_edit)
        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        actions.columnconfigure(3, weight=1)
        ttk.Label(actions, text=tr("Formato"), style="CardMuted.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 5))
        self.format_label = tk.StringVar()
        self.format_box = TranslatedCombobox(actions, textvariable=self.format_label, values=list(FORMAT_LABELS), state="readonly", width=14)
        self.format_box.grid(row=1, column=0, sticky="w", padx=(0, 14))
        self.format_box.bind("<<ComboboxSelected>>", self.change_format)
        self.quality_caption = ttk.Label(actions, text=tr("Resolução"), style="CardMuted.TLabel")
        self.quality_caption.grid(row=0, column=1, sticky="w", pady=(0, 5))
        self.quality_selector = TranslatedCombobox(actions, state="readonly", width=18)
        self.quality_selector.grid(row=1, column=1, sticky="w", padx=(0, 14))
        self.fps_label = ttk.Label(actions, text=tr("FPS máximo"), style="CardMuted.TLabel")
        self.fps_label.grid(row=0, column=2, sticky="w", pady=(0, 5))
        self.fps_selector = TranslatedCombobox(actions, textvariable=self.fps, values=list(FPS_OPTIONS), state="readonly", width=10)
        self.fps_selector.grid(row=1, column=2, sticky="w", padx=(0, 14))
        self.fixed_quality = tk.StringVar()
        self.add_button = ttk.Button(actions, text=tr("Adicionar à fila  +"), command=self.add)
        self.add_button.grid(row=1, column=3, sticky="e")
        self.download_now_button = ttk.Button(actions, text=tr("Baixar agora"), style="Accent.TButton", command=self.download_now)
        self.download_now_button.grid(row=1, column=4, sticky="e", padx=(8, 0))
        ttk.Checkbutton(card, text=tr("Revisar metadados antes de baixar"), variable=self.review_metadata).grid(row=3, column=0, sticky="w", pady=(8, 0))

        ttk.Checkbutton(card,text=tr("Normalizar volume"),variable=self.normalize_volume).grid(row=4,column=0,sticky="w",pady=(4,0))

        queue_head = ttk.Frame(main)
        queue_head.grid(row=3, column=0, sticky="ew", pady=(14, 10))
        ttk.Label(queue_head, text=tr("Seus downloads"), font=("Segoe UI", 12, "bold")).pack(side="left")
        self.queue_count = tk.StringVar(value="0 itens")
        ttk.Label(queue_head, textvariable=display_var(self.queue_count), style="Muted.TLabel").pack(side="left", padx=12)
        self.retry_button = ttk.Button(queue_head, text=tr("Tentar novamente"), style="Quiet.TButton", command=self.retry, state="disabled")
        self.retry_button.pack(side="right")
        self.remove_button = ttk.Button(queue_head, text=tr("Remover selecionados"), style="Quiet.TButton", command=self.remove, state="disabled")
        self.remove_button.pack(side="right", padx=4)
        self.clear_queue_button = ttk.Button(queue_head, text=tr("Limpar fila"), style="Quiet.TButton", command=self.clear_queue, state="disabled")
        self.clear_queue_button.pack(side="right", padx=4)
        TranslatedCombobox(queue_head,textvariable=self.queue_view,values=("Compacto","Completa"),state="readonly",width=10).pack(side="left",padx=4)
        self.queue_size_controls=ttk.Frame(queue_head)
        TranslatedCombobox(self.queue_size_controls,textvariable=self.queue_card_size,values=("Pequeno","Médio","Grande"),state="readonly",width=8).pack(side="left")
        table = ttk.Frame(main, style="Card.TFrame")
        table.grid(row=4, column=0, sticky="nsew")
        self.tree = ttk.Treeview(table, columns=("name", "format", "size", "status"), show="headings", height=5, selectmode="extended")
        from list_context import bind_queue
        bind_queue(self)
        for column, label, width in (("name", "NOME", 350), ("format", "FORMATO", 100), ("size", "TAMANHO", 125), ("status", "STATUS", 140)):
            self.tree.heading(column, text=tr(label), anchor="w")
            self.tree.column(column, width=width, minwidth=80, stretch=column == "name", anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.tag_configure("Concluído", foreground=ACCENT)
        self.tree.tag_configure("Falhou", foreground="#f2a198")
        self.tree.tag_configure("Cancelado", foreground=MUTED)
        self.tree.bind("<<TreeviewSelect>>", lambda _: self.refresh_queue())
        def remove_selected(_):
            self.remove()
            return "break"
        for key in ("<Delete>", "<BackSpace>"):
            self.tree.bind(key, remove_selected)
        self.empty_queue = ttk.Frame(table, style="Card.TFrame")
        ttk.Label(self.empty_queue, text=tr("Sua fila começa aqui"), style="Card.TLabel", font=("Segoe UI", 12, "bold")).pack()
        ttk.Label(self.empty_queue, text=tr("Adicione um link para começar."), style="CardMuted.TLabel").pack(pady=(5, 0))
        self.empty_queue.place(relx=.5, rely=.58, anchor="center")

        from queue_cards import QueueCards
        self.queue_cards=QueueCards(table,self,scroll)
        self.queue_cards.refresh()

        progress = ttk.Frame(main)
        progress.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        progress.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(progress, textvariable=display_var(self.notice_display), font=("Segoe UI", 10, "bold"), wraplength=760)
        self.status_label.grid(row=0, column=0, sticky="w")
        ttk.Button(progress,text=tr("×"),style="Quiet.TButton",command=lambda:self.status_notice.dismiss()).grid(row=0,column=2,sticky="e")
        self.progress_text = tk.StringVar(value="")
        ttk.Label(progress, textvariable=display_var(self.progress_text), foreground=ACCENT).grid(row=0, column=1, sticky="e", padx=(12, 0))
        self.bar = ttk.Progressbar(progress, mode="determinate", maximum=100)
        self.bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 8))
        self.detail_label = ttk.Label(progress, textvariable=display_var(self.detail), style="Muted.TLabel", wraplength=760)
        self.detail_label.grid(row=2, column=0, columnspan=2, sticky="w")

        footer = ttk.Frame(main)
        footer.grid(row=6, column=0, sticky="ew", pady=(12, 0))
        self.start_button = ttk.Button(footer, text=tr("Baixar fila"), style="Accent.TButton", command=self.start)
        self.start_button.pack(side="right")
        self.cancel_button = ttk.Button(footer, text=tr("Parar"), command=self.cancel, state="disabled")
        self.cancel_button.pack(side="right", padx=10)
        ttk.Button(footer, text=tr("Abrir pasta"), style="Quiet.TButton", command=self.open_folder).pack(side="left")
        ttk.Button(footer, text=tr("Ver detalhes"), style="Quiet.TButton", command=self.show_log).pack(side="left", padx=4)
        from advanced_ui import move_queue
        for label,direction in (('↑',-1),('↓',1),('Próximo',0)):
            ttk.Button(footer,text=tr(label),width=7,command=lambda step=direction:move_queue(self,step)).pack(side='left',padx=2)

        self._build_settings()
        self._build_log()
        self.mode.trace_add("write", lambda *_: self.sync_format())
        self.sync_format()
        main.bind("<Configure>", lambda e: (self.status_label.configure(wraplength=max(400, e.width-110)),
                                           self.detail_label.configure(wraplength=max(400, e.width-60))))

    def sync_format(self):
        mode = MODES[self.mode.get()]
        self.format_label.set(next(label for label, value in FORMAT_LABELS.items() if value == mode))
        self.mode_changed()

    def change_format(self, _=None):
        value = FORMAT_LABELS[self.format_label.get()]
        self.mode.set(next(label for label, mode in MODES.items() if mode == value))

    def update_quality_selector(self):
        mode = MODES[self.mode.get()]
        self.quality_caption.configure(text=tr("Resolução" if mode in ("video", "mp4") else "Qualidade"))
        for widget in (self.fps_label, self.fps_selector):
            widget.grid() if mode in ("video", "mp4") else widget.grid_remove()
        if mode in ("video", "mp4"):
            self.quality_selector.configure(textvariable=self.height, values=list(HEIGHTS), state="readonly")
        elif mode in ("mp3", "m4a"):
            variable, choices = (self.mp3_quality, MP3_QUALITIES) if mode == "mp3" else (self.m4a_quality, M4A_QUALITIES)
            self.quality_selector.configure(textvariable=variable, values=choices, state="readonly")
        else:
            self.fixed_quality.set("Todas as fotos" if mode == "photos" else "Arquivos originais" if mode == "social" else "Sem perdas (fonte)" if mode == "flac" else "Qualidade da fonte")
            self.quality_selector.configure(textvariable=self.fixed_quality, values=(), state="disabled")

    def refresh_placeholder(self):
        if not self.urls.get("1.0", "end").strip() and self.focus_get() != self.urls:
            self.url_hint.place(x=12, y=12)
        else:
            self.url_hint.place_forget()

    def on_link_edit(self, _=None):
        if self.urls.edit_modified():
            self.refresh_placeholder()
            self.urls.edit_modified(False)

    def refresh_queue(self):
        if hasattr(self,"queue_cards"):self.queue_cards.refresh()
        count = len(self.jobs)
        self.clear_queue_button.configure(state="normal" if count else "disabled")
        self.queue_count.set(f"{count} {'item' if count == 1 else 'itens'}")
        if count:
            self.empty_queue.place_forget()
        else:
            self.empty_queue.place(relx=.5, rely=.58, anchor="center")
        selected = self.tree.selection()
        self.remove_button.configure(state="normal" if selected else "disabled")
        self.retry_button.configure(state="normal" if any(self.jobs.get(i, {}).get("state") in ("Falhou", "Cancelado") for i in selected) else "disabled")

    def _build_settings(self):
        self.settings_window = tk.Toplevel(self)
        self.settings_window.withdraw()
        self.settings_window.title(tr("Onda • Configurações"))
        self.settings_window.configure(bg=BG)
        self.settings_window.geometry("650x640")
        self.settings_window.minsize(600, 620)
        self.settings_window.protocol("WM_DELETE_WINDOW", self.settings_window.withdraw)
        body = ttk.Frame(self.settings_window, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=tr("Do seu jeito."), font=("Segoe UI", 20, "bold")).pack(anchor="w")
        ttk.Label(body, text=tr("Escolha uma categoria para ajustar o Onda."), style="Muted.TLabel").pack(anchor="w", pady=(4, 18))
        bottom = ttk.Frame(body)
        bottom.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(bottom, text=tr("Ajuda"), style="Quiet.TButton", command=self.help).pack(side="left")
        ttk.Button(bottom, text=tr("Pronto"), style="Accent.TButton", command=self.settings_window.withdraw).pack(side="right")
        ttk.Style(self).configure("Settings.TNotebook.Tab", padding=(10, 8))
        self.settings_pages = ttk.Notebook(body, style="Settings.TNotebook")
        self.settings_pages.pack(fill="both", expand=True)
        from settings_scroll import SettingsCategory
        categories = {}
        self.settings_categories = {}
        for title in ("Geral", "Aparência", "Downloads", "Áudio", "Contas", "Ferramentas"):
            page = SettingsCategory(self.settings_pages, BG)
            self.settings_pages.add(page, text=tr(title))
            self.settings_categories[str(page)] = page
            categories[title] = page.content
        self.settings_window.bind("<MouseWheel>",
                                  lambda event: self.settings_categories[self.settings_pages.select()].wheel(event))

        appearance = categories['Aparência']
        from appearance import THEME_MODES, ACCENTS
        ttk.Label(appearance, text=tr('Tema e cores'), font=('Segoe UI', 13, 'bold')).pack(anchor='w', pady=(0, 12))
        ttk.Label(appearance, text=tr('Modo de aparência'), style='Muted.TLabel').pack(anchor='w')
        self.theme_mode_combo = TranslatedCombobox(appearance, textvariable=self.theme_mode, values=THEME_MODES, state='readonly', width=28)
        self.theme_mode_combo.pack(anchor='w', fill='x', pady=(6, 16))
        ttk.Checkbutton(appearance,text=tr("Mostrar bordas e separações no Preto puro"),variable=self.pure_black_separators).pack(anchor="w",pady=(0,12))
        ttk.Label(appearance, text=tr('Cor de destaque'), style='Muted.TLabel').pack(anchor='w')
        self.theme_accent_combo = TranslatedCombobox(appearance, textvariable=self.theme_accent, values=tuple(ACCENTS), state='readonly', width=28)
        self.theme_accent_combo.pack(anchor='w', fill='x', pady=(6, 16))
        from interface_fonts import font_choices, FONT_PREVIEW, FONT_SIZES
        ttk.Label(appearance, text=tr("Alterar tamanho da fonte")).pack(anchor="w", pady=(12, 4))
        TranslatedCombobox(appearance, textvariable=self.interface_font_size, values=FONT_SIZES, state="readonly", width=12).pack(anchor="w")
        ttk.Label(appearance, text=tr('Fonte da interface'), style='Muted.TLabel').pack(anchor='w')
        self.interface_font_combo = TranslatedCombobox(appearance, textvariable=self.interface_font, values=font_choices(self), state='readonly', width=28)
        self.interface_font_combo.pack(anchor='w', fill='x', pady=(6, 12))
        self.interface_font_preview = ttk.Label(appearance, text=tr(FONT_PREVIEW), font=('Segoe UI', 12))
        self.interface_font_preview.pack(anchor='w', fill='x', pady=(0, 10))
        ttk.Label(appearance, text=tr('A fonte muda na hora. Ative Lembrar configurações para manter sua escolha ao reabrir.'), style='Muted.TLabel', wraplength=480).pack(anchor='w', pady=(0, 12))
        ttk.Label(appearance, text=tr('As mudanças aparecem na hora. Seguir o sistema acompanha o modo dos aplicativos do Windows, inclusive com o Onda aberto.'), style='Muted.TLabel', wraplength=480).pack(anchor='w')
        ttk.Label(appearance, text=tr('Para manter sua escolha ao reabrir, ative Lembrar configurações na categoria Geral.'), style='Muted.TLabel', wraplength=480).pack(anchor='w', pady=(12, 0))

        ttk.Label(appearance, text=tr("Mostrar músicas no histórico"), style="Muted.TLabel").pack(anchor="w", pady=(12,4))
        TranslatedCombobox(appearance, textvariable=self.history_view, values=("Compacto", "Completa"), state="readonly", width=28).pack(anchor="w")
        ttk.Label(appearance, text=tr("Compacto: lista atual. Completa: cards com capa, artista, álbum e dados do arquivo disponíveis."), style="Muted.TLabel", wraplength=480).pack(anchor="w", pady=(6,12))
        ttk.Label(appearance,text=tr("Mostrar itens em Links e fila"),style="Muted.TLabel").pack(anchor="w",pady=(12,4))
        TranslatedCombobox(appearance,textvariable=self.queue_view,values=("Compacto","Completa"),state="readonly",width=28).pack(anchor="w")
        general = categories["Geral"]
        ttk.Label(general, text=tr("Preferências"), font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 12))
        ttk.Label(general, text=tr("Idioma")).pack(anchor="w")
        TranslatedCombobox(general, textvariable=self.language, values=("pt-BR", "es", "en"), state="readonly", width=24).pack(anchor="w", pady=(4, 6))
        ttk.Label(general, text=tr("Reinicie o ONDA para aplicar o idioma."), style="Muted.TLabel").pack(anchor="w", pady=(0, 12))
        self.restart_slot=ttk.Frame(general)
        self.restart_slot.pack(anchor="w")
        self.restart_button=ttk.Button(self.restart_slot,text=tr("Reiniciar"),command=self.restart_app)
        self.remember_checkbox = ttk.Checkbutton(general, text=tr("Lembrar configurações"), variable=self.remember_settings,
                                                command=self.toggle_remember_settings)
        self.remember_checkbox.pack(anchor="w")
        ttk.Label(general, textvariable=display_var(self.preference_status), style="Muted.TLabel", wraplength=480).pack(anchor="w", pady=(6, 12))
        ttk.Label(general, text=tr("Ative para recuperar suas opções ao abrir o aplicativo novamente."),
                  style="Muted.TLabel", wraplength=480).pack(anchor="w")

        from status_notice import NOTICE_DURATIONS
        ttk.Label(general,text=tr("Duração dos avisos")).pack(anchor="w",pady=(12,4))
        TranslatedCombobox(general,textvariable=self.notice_duration,values=tuple(NOTICE_DURATIONS),state="readonly").pack(anchor="w",fill="x")
        ttk.Label(general,text=tr("Avisos de operações em andamento permanecem até terminar. O botão × permite fechar manualmente."),style="Muted.TLabel",wraplength=480).pack(anchor="w",pady=(6,0))
        ttk.Separator(general).pack(fill='x', pady=18)
        ttk.Label(general, text=tr('Restaurar configurações'), font=('Segoe UI', 13, 'bold')).pack(anchor='w', pady=(0, 8))
        from reset_settings import show_reset
        ttk.Button(general, text=tr('Restaurar TODAS as configurações ao padrão'), command=lambda: show_reset(self, True)).pack(anchor='w', pady=(0, 8))
        ttk.Button(general, text=tr('Escolher quais configurações restaurar…'), command=lambda: show_reset(self, False)).pack(anchor='w')
        ttk.Label(general, text=tr('Você poderá conferir as opções antes de confirmar. Contas, fila, histórico e arquivos baixados são mantidos.'), style='Muted.TLabel', wraplength=480).pack(anchor='w', pady=(8, 0))

        from advanced_ui import settings_tools
        settings_tools(self,general)

        downloads = categories["Downloads"]
        ttk.Label(downloads, text=tr("Downloads e arquivos"), font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(downloads, text=tr("As opções são aplicadas aos próximos links adicionados."), style="Muted.TLabel").pack(anchor="w", pady=(0, 8))
        ttk.Checkbutton(downloads, text=tr("Escolher automaticamente a versão mais semelhante no YouTube"), variable=self.auto_match).pack(anchor="w", pady=(0, 6))
        ttk.Label(downloads, text=tr("Vale para os próximos downloads iniciados, inclusive itens já na fila. Ignora a confirmação de versão; escolhe a maior similaridade entre as versões compatíveis. Se nenhuma for compatível, informa o erro sem abrir uma escolha."), style="Muted.TLabel", wraplength=480).pack(anchor="w", fill="x", pady=(0, 12))
        ttk.Checkbutton(downloads, text=tr("Revisar metadados antes de baixar"), variable=self.review_metadata).pack(anchor="w", pady=(0, 8))
        ttk.Checkbutton(downloads, text=tr("Baixar playlist de vídeo"), variable=self.playlist).pack(anchor="w", pady=(0, 8))
        from playlist_options import PLAYLIST_LIMITS
        limit_row = ttk.Frame(downloads)
        limit_row.pack(fill="x", pady=(0, 10))
        ttk.Label(limit_row, text=tr("Máximo de itens por playlist"), style="Muted.TLabel").pack(anchor="w")
        TranslatedCombobox(limit_row, textvariable=self.playlist_limit, values=PLAYLIST_LIMITS, state="readonly", width=10).pack(fill="x", pady=(6, 0))
        ttk.Label(downloads, text=tr("Pasta de destino"), style="Muted.TLabel").pack(anchor="w")
        row = ttk.Frame(downloads)
        row.pack(fill="x", pady=(6, 8))
        ttk.Entry(row, textvariable=self.folder).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text=tr("Alterar"), command=self.choose_folder).pack(side="right", padx=(8, 0))
        from file_output import ORGANIZATIONS, DUPLICATES
        ttk.Label(downloads, text=tr("Organizar músicas em"), style="Muted.TLabel").pack(anchor="w")
        TranslatedCombobox(downloads, textvariable=self.organization, values=ORGANIZATIONS, state="readonly").pack(fill="x", pady=(6, 8))
        from output_rules import FILENAME_TEMPLATES, preview_path
        ttk.Label(downloads, text=tr("Nome dos arquivos"), style="Muted.TLabel").pack(anchor="w")
        TranslatedCombobox(downloads, textvariable=self.filename_template, values=FILENAME_TEMPLATES, state="readonly").pack(fill="x", pady=(6, 8))
        preview = tk.StringVar()
        preview_label = ttk.Label(downloads, textvariable=preview, style="Muted.TLabel", wraplength=480)
        preview_label.pack(anchor="w", pady=(0, 8))
        def update_output_preview(*_):
            preview.set(tr("Prévia de organização") + ": " + tr(preview_path({"organization": self.organization.get(), "filename_template": self.filename_template.get(), "mode": "mp3"}, translate=tr)))
        preview_traces = [(variable, variable.trace_add("write", update_output_preview)) for variable in (self.organization, self.filename_template)]
        preview_label.bind("<Destroy>", lambda event: [variable.trace_remove("write", identity) for variable, identity in preview_traces] if event.widget is preview_label else None)
        update_output_preview()
        ttk.Label(downloads, text=tr("Quando o arquivo já existir"), style="Muted.TLabel").pack(anchor="w")
        TranslatedCombobox(downloads, textvariable=self.duplicates, values=list(DUPLICATES), state="readonly").pack(fill="x", pady=(6, 8))
        ttk.Label(downloads, text=tr("Links de catálogo em FLAC baixam diretamente do Monochrome, quando disponíveis. Outros links são convertidos; isso não melhora fontes com perdas."),
                  style="Muted.TLabel", wraplength=480).pack(anchor="w", pady=(4, 0))

        audio = categories["Áudio"]
        ttk.Label(audio, text=tr("Reprodução e prévias"), font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 12))
        ttk.Checkbutton(audio, text=tr("Continuar prévia dos efeitos em outras abas"),
                        variable=self.background_preview, command=self.tab_changed).pack(anchor="w", pady=(0, 20))
        from preview_options import PREVIEW_DURATIONS
        ttk.Label(audio, text=tr("Duração das prévias"), font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 12))
        for label, variable in (("Slowed / Sped Up e Reverb", self.effects_preview_duration),
                                ("Músicas nas pesquisas", self.search_preview_duration)):
            row = ttk.Frame(audio)
            row.pack(fill="x", pady=(0, 12))
            ttk.Label(row, text=tr(label)).pack(anchor="w")
            TranslatedCombobox(row, textvariable=variable, values=PREVIEW_DURATIONS, state="readonly", width=16).pack(fill="x", pady=(6, 0))
        ttk.Label(audio, text=tr("Vale para a próxima prévia. Nas pesquisas, o catálogo pode fornecer um trecho menor."),
                  style="Muted.TLabel", wraplength=480).pack(anchor="w", pady=(4, 0))

        accounts = categories["Contas"]
        ttk.Label(accounts, text=tr("Contas e acesso"), font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 12))
        ttk.Label(accounts, text=tr("Spotify · opcional"), font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Button(accounts, text=tr("Spotify e metadados"), command=self.open_metadata).pack(anchor="w", pady=(0, 24))
        ttk.Label(accounts, text=tr("Redes sociais · login opcional"), font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(accounts, text=tr("Se a plataforma exigir login, use um arquivo cookies.txt (Netscape).\nUsado apenas nesta sessão; não vai para a fila salva."), style="Muted.TLabel", wraplength=480).pack(anchor="w")
        cookies = ttk.Frame(accounts)
        cookies.pack(fill="x", pady=(12, 0))
        ttk.Entry(cookies, textvariable=self.social_cookies).pack(side="left", fill="x", expand=True)
        ttk.Button(cookies, text=tr("Escolher"), command=self.choose_social_cookies).pack(side="left", padx=6)
        ttk.Button(cookies, text=tr("Limpar"), command=lambda: self.social_cookies.set("")).pack(side="right")

        tools_page = categories["Ferramentas"]
        ttk.Label(tools_page, text=tr("Ferramentas e atualizações"), font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 12))
        ttk.Label(tools_page, text=tr("Pasta do FFmpeg · opcional quando já configurado"), style="Muted.TLabel").pack(anchor="w")
        tools = ttk.Frame(tools_page)
        tools.pack(fill="x", pady=(8, 24))
        ttk.Entry(tools, textvariable=self.ffmpeg).pack(side="left", fill="x", expand=True)
        ttk.Button(tools, text=tr("Escolher"), command=self.choose_ffmpeg).pack(side="right", padx=(8, 0))
        ttk.Button(tools_page, text=tr("Preparar FFmpeg"), command=self.prepare_ffmpeg).pack(anchor="w", pady=(0, 8))
        ttk.Label(tools_page, text=tr("Baixado diretamente de gyan.dev uma vez por PC. Internet necessária no primeiro uso."),
                  style="Muted.TLabel", wraplength=480).pack(anchor="w", pady=(0, 12))
        self.update_button = ttk.Button(tools_page, text=tr("Atualizar ferramentas"), command=self.update_downloader)
        self.update_button.pack(anchor="w", pady=(0, 8))
        ttk.Label(tools_page, textvariable=display_var(self.update_status), style="Muted.TLabel", wraplength=480).pack(anchor="w")

    def _build_log(self):
        self.log_window = tk.Toplevel(self)
        self.log_window.withdraw()
        self.log_window.title(tr("Onda • Detalhes dos downloads"))
        self.log_window.configure(bg=BG)
        self.log_window.geometry("800x420")
        self.log_window.protocol("WM_DELETE_WINDOW", self.log_window.withdraw)
        body = ttk.Frame(self.log_window, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text=tr("Detalhes dos downloads"), font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(0, 14))
        panel = ttk.Frame(body)
        panel.pack(fill="both", expand=True)
        self.log = tk.Text(panel, bg=SURFACE, fg=MUTED, relief="flat", borderwidth=0, highlightthickness=0,
                           font=("Consolas", 10), padx=12, pady=12, state="disabled", wrap="word")
        self.log.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(panel, orient="vertical", command=self.log.yview)
        scroll.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scroll.set)

    def show_settings(self):
        self.settings_window.deiconify()
        self.settings_window.lift()

    def show_log(self):
        self.log_window.deiconify()
        self.log_window.lift()
