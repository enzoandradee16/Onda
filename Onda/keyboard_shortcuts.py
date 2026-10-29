"""Desktop shortcuts scoped to the main window and the relevant page."""

import tkinter as tk
from tkinter import ttk
from i18n import tr

SHORTCUTS = (
    ("Ctrl+1 … Ctrl+9", "Abrir aba pela posição atual"),
    ("Ctrl+Tab / Ctrl+Shift+Tab", "Ir para a próxima aba / aba anterior"),
    ("Ctrl+↑ / Ctrl+↓", "Rolar a página atual para cima / baixo"),
    ("Ctrl+A", "Selecionar todos os itens da lista atual"),
    ("Ctrl+L", "Abrir Links e focar o campo de links"),
    ("Ctrl+J", "Abrir a Fila"),
    ("Ctrl+H", "Abrir o Histórico"),
    ("Ctrl+F", "Focar a pesquisa da aba atual ou abrir Pesquisar músicas"),
    ("Ctrl+Enter", "Baixar agora na aba Links"),
    ("Ctrl+Shift+Enter", "Adicionar links à fila sem iniciar"),
    ("F5", "Iniciar downloads na aba Fila"),
    ("Shift+F5", "Parar downloads em andamento"),
    ("Ctrl+R", "Tentar novamente os itens selecionados da fila"),
    ("Alt+↑ / Alt+↓", "Mover itens selecionados da fila para cima / baixo"),
    ("Alt+Home", "Priorizar itens selecionados da fila"),
    ("Alt+V", "Alternar Compacto / Completa na Fila ou Histórico"),
    ("Ctrl+Shift+Delete", "Limpar a fila"),
    ("Ctrl+O", "Abrir a pasta de downloads"),
    ("Ctrl+,", "Abrir configurações"),
    ("Ctrl+M", "Abrir janela de metadados"),
    ("Ctrl+Shift+L", "Ver detalhes dos downloads"),
    ("Ctrl+Shift+E", "Ver falhas da fila"),
    ("F1", "Mostrar atalhos de teclado"),
    ("Alt+A", "Selecionar todos os itens da Fila ou Álbuns e playlists"),
    ("Delete / Backspace", "Remover itens quando a lista da fila está focada"),
    ("Ctrl+roda do mouse", "Alterar tamanho dos cards da Fila ou Histórico"),
    ("Shift+F10", "Abrir opções da lista focada"),
)


class KeyboardShortcuts:
    def __init__(self, app):
        self.app = app
        self.window = None
        self.tag = "OndaShortcuts" + str(id(self))
        self.bound = []
        self.commands = []
        self.rebind()
        app.shortcut_keys.trace_add('write', lambda *_: self.rebind())
        self.attach(app)
        app.bind(
            '<Map>', lambda event: self.attach(event.widget, descend=False), add='+'
        )

    def rebind(self):
        from shortcut_options import effective_bindings

        for sequence in self.bound:
            self.app.unbind_class(self.tag, sequence)
        for command in self.commands:
            self.app.deletecommand(command)
        self.bound = []
        self.commands = []
        for sequence, action in effective_bindings(
            self.app.shortcut_keys.get()
        ).items():
            callback = lambda event, key=action: self.dispatch(key, event)
            variants = [sequence]
            letter = sequence.rsplit('-', 1)[-1][:-1]
            if len(letter) == 1 and letter.isalpha():
                variants.append(sequence[:-2] + letter.upper() + '>')
            for variant in variants:
                self.commands.append(self.app.bind_class(self.tag, variant, callback))
                self.bound.append(variant)
        if self.window is not None and self.window.winfo_exists():
            self.fill_reference()

    def set_shortcut(self, action, sequence):
        import json
        from shortcut_options import load_overrides, validate_overrides

        values = load_overrides(self.app.shortcut_keys.get())
        values[action] = sequence
        self.app.shortcut_keys.set(json.dumps(validate_overrides(values)))

    def fill_reference(self):
        from shortcut_options import PRIMARY, load_overrides, display_shortcut

        table = self.reference_tree
        selected = table.selection()
        table.delete(*table.get_children())
        values = load_overrides(self.app.shortcut_keys.get())
        for action, default in PRIMARY.items():
            table.insert(
                '',
                'end',
                iid=action,
                values=(
                    display_shortcut(values.get(action, default)),
                    self.action_label(action),
                ),
            )
        for i, (key, label) in enumerate(SHORTCUTS[-4:]):
            table.insert('', 'end', iid='fixed:' + str(i), values=(tr(key), tr(label)))
        if selected and table.exists(selected[0]):
            table.selection_set(selected[0])

    @staticmethod
    def action_label(action):
        indexes = {
            'next': 1,
            'previous': 1,
            'scroll-up': 2,
            'scroll-down': 2,
            'select-all': 3,
            'links': 4,
            'queue': 5,
            'history': 6,
            'search': 7,
            'download': 8,
            'add': 9,
            'start': 10,
            'stop': 11,
            'retry': 12,
            'up': 13,
            'down': 13,
            'prioritize': 14,
            'view': 15,
            'clear': 16,
            'folder': 17,
            'settings': 18,
            'metadata': 19,
            'log': 20,
            'failures': 21,
            'help': 22,
        }
        if action.startswith('tab:'):
            return tr('Abrir aba pela posição atual') + ' ' + str(int(action[4:]) + 1)
        label = tr(SHORTCUTS[indexes[action]][1])
        return label + (
            {
                'previous': ' (←)',
                'next': ' (→)',
                'scroll-up': ' (↑)',
                'scroll-down': ' (↓)',
                'up': ' (↑)',
                'down': ' (↓)',
            }.get(action, '')
        )

    def edit_selected(self):
        from shortcut_options import PRIMARY, canonical, display_shortcut
        from tkinter import messagebox

        selected = self.reference_tree.selection()
        if not selected or selected[0] not in PRIMARY:
            return
        action = selected[0]
        dialog = tk.Toplevel(self.window)
        dialog.title(tr('Alterar atalho'))
        dialog.transient(self.window)
        body = ttk.Frame(dialog, padding=18)
        body.pack(fill='both', expand=True)
        ttk.Label(
            body, text=tr('Pressione a nova combinação de teclas.'), wraplength=420
        ).pack(anchor='w')
        text = tk.StringVar()
        candidate = ['']
        field = ttk.Entry(body, textvariable=text, state='readonly', width=40)
        field.pack(fill='x', pady=12)

        def capture(event):
            if event.keysym in (
                'Control_L',
                'Control_R',
                'Shift_L',
                'Shift_R',
                'Alt_L',
                'Alt_R',
            ):
                return 'break'
            modifiers = []
            if event.state & 4:
                modifiers.append('Control')
            if event.state & (8 | 0x20000):
                modifiers.append('Alt')
            if event.state & 1:
                modifiers.append('Shift')
            try:
                candidate[0] = canonical(
                    '<' + '-'.join(modifiers + [event.keysym]) + '>'
                )
                text.set(display_shortcut(candidate[0]))
            except ValueError as error:
                candidate[0] = ''
                text.set(tr(str(error)))
            return 'break'

        field.bind('<KeyPress>', capture)

        def save(sequence=None):
            if sequence is None and not candidate[0]:
                return
            try:
                self.set_shortcut(
                    action, candidate[0] if sequence is None else sequence
                )
            except ValueError as error:
                messagebox.showerror(tr('Atalhos'), tr(str(error)), parent=dialog)
                return
            dialog.destroy()

        row = ttk.Frame(body)
        row.pack(fill='x')
        ttk.Button(row, text=tr('Salvar'), command=save).pack(side='left')
        ttk.Button(row, text=tr('Desativar'), command=lambda: save('')).pack(
            side='left', padx=6
        )
        ttk.Button(
            row, text=tr('Restaurar padrão'), command=lambda: save(PRIMARY[action])
        ).pack(side='left')
        ttk.Button(row, text=tr('Cancelar'), command=dialog.destroy).pack(
            side='left', padx=6
        )
        dialog.grab_set()
        field.focus_set()

    def attach(self, widget, *, descend=True):
        # Consume explicit shortcut chords before generic widget keys (e.g. Delete).
        # Never attach application shortcuts to another top-level window.
        if not isinstance(widget, tk.Misc):
            return
        try:
            if widget.winfo_toplevel() != self.app:
                return
        except tk.TclError:
            return
        tags = widget.bindtags()
        if self.tag not in tags:
            widget.bindtags((self.tag, *tags))
        if descend:
            for child in widget.winfo_children():
                self.attach(child)

    def allowed(self, event):
        widget = event.widget if event is not None else self.app.focus_get() or self.app
        try:
            return (
                widget.winfo_toplevel() == self.app and self.app.grab_current() is None
            )
        except (tk.TclError, KeyError):
            return False

    def editing(self, event):
        widget = event.widget if event is not None else self.app.focus_get()
        return widget is not None and widget.winfo_class() in (
            'Text',
            'Entry',
            'TEntry',
            'TCombobox',
            'Spinbox',
            'TSpinbox',
        )

    def select(self, page, field=None):
        self.app.pages.select(page)
        if field is not None:
            field.focus_set()
            if isinstance(field, tk.Text):
                field.tag_add('sel', '1.0', 'end-1c')
            else:
                field.selection_range(0, 'end')

    def dispatch(self, action, event=None):
        if not self.allowed(event):
            return
        app = self.app
        current = app.pages.select()
        if action.startswith('tab:'):
            tabs = app.pages.visible_tabs()
            index = int(action.split(':')[1])
            if index >= len(tabs):
                return
            app.pages.select(tabs[index])
        elif action in ('next', 'previous'):
            tabs = app.pages.visible_tabs()
            index = tabs.index(current)
            app.pages.select(
                tabs[(index + (1 if action == 'next' else -1)) % len(tabs)]
            )
        elif action in ('scroll-up', 'scroll-down'):
            page = app.nametowidget(current)
            canvas = getattr(page, 'canvas', None)
            if canvas is None:
                return
            canvas.yview_scroll(-1 if action == 'scroll-up' else 1, 'pages')
        elif action == 'select-all':
            if self.editing(event):
                return
            widget = event.widget if event is not None else app.focus_get()
            if (
                isinstance(widget, ttk.Treeview)
                and str(widget.cget('selectmode')) == 'extended'
            ):
                table = widget
            elif current == str(app.queue_page):
                table = app.tree
            elif current == str(app.playlist_page):
                table = app.playlist_page.table
            elif current == str(app.history_page):
                table = app.history_page.table
            else:
                return
            table.selection_set(
                app.queue_filter.visible_keys()
                if table is app.tree
                else table.get_children()
            )
        elif action == 'links':
            self.select(app.download_page, app.urls)
        elif action == 'queue':
            app.show_queue()
        elif action == 'history':
            self.select(app.history_page)
        elif action == 'search':
            if current == str(app.playlist_page):
                field = app.playlist_page.search_entry
            elif current == str(app.history_page):
                field = app.history_page.search_entry
            elif current == str(app.queue_page):
                field = app.queue_filter.entry
            else:
                self.select(app.catalog_page)
                field = app.catalog_page.entry
            field.focus_set()
            field.selection_range(0, 'end')
        elif action in ('download', 'add'):
            if current != str(app.download_page):
                return
            if not app.updating:
                app.download_now() if action == 'download' else app.add()
        elif action == 'stop':
            if app.running or app.parallel.workers:
                app.cancel()
        elif action == 'view':
            if self.editing(event):
                return
            if current == str(app.queue_page):
                value = app.queue_view
            elif current == str(app.history_page):
                value = app.history_view
            else:
                return
            value.set('Completa' if value.get() == 'Compacto' else 'Compacto')
        elif action in ('start', 'retry', 'up', 'down', 'prioritize', 'clear'):
            if current != str(app.queue_page) or self.editing(event):
                return
            if action == 'start':
                app.start()
            elif action == 'retry':
                app.retry()
            elif action == 'clear':
                app.clear_queue()
            elif app.tree.selection():
                from advanced_ui import move_queue

                move_queue(app, {'up': -1, 'down': 1, 'prioritize': 0}[action])
                app.refresh_queue()
        elif action == 'folder':
            app.open_folder()
        elif action == 'settings':
            app.show_settings()
        elif action == 'metadata':
            app.open_metadata()
        elif action == 'log':
            app.show_log()
        elif action == 'failures':
            app.show_failures()
        elif action == 'help':
            self.show_help()
        else:
            return
        return 'break'

    def show_help(self):
        if self.window is not None and self.window.winfo_exists():
            self.window.deiconify()
            self.window.lift()
            self.window.focus_set()
            return
        window = self.window = tk.Toplevel(self.app)
        window.title(tr('Atalhos de teclado'))
        window.geometry('780x590')
        window.minsize(620, 420)
        body = ttk.Frame(window, padding=18)
        body.pack(fill='both', expand=True)
        ttk.Label(
            body, text=tr('Atalhos de teclado'), font=('Segoe UI', 16, 'bold')
        ).pack(anchor='w')
        ttk.Label(
            body,
            text=tr('Os controles da fila respeitam a aba ativa e os campos de texto.')
            + '\n'
            + tr(
                'Selecione uma ação e clique em Alterar atalho. Atalhos de edição de texto permanecem fixos.'
            ),
            wraplength=720,
            style='Muted.TLabel',
        ).pack(anchor='w', pady=(6, 12))
        panel = ttk.Frame(body)
        panel.pack(fill='both', expand=True)
        ttk.Style(window).configure('Shortcuts.Treeview', rowheight=30)
        table = ttk.Treeview(
            panel,
            columns=('key', 'action'),
            show='headings',
            style='Shortcuts.Treeview',
            selectmode='browse',
        )
        table.heading('key', text=tr('Atalho'))
        table.heading('action', text=tr('Ação'))
        table.column('key', width=225, minwidth=190, stretch=False)
        table.column('action', width=475, minwidth=260)
        self.reference_tree = table
        self.fill_reference()
        table.bind('<Double-1>', lambda event: self.edit_selected())
        table.pack(side='left', fill='both', expand=True)
        scroll = ttk.Scrollbar(panel, command=table.yview)
        scroll.pack(side='right', fill='y')
        table.configure(yscrollcommand=scroll.set)
        controls = ttk.Frame(body)
        controls.pack(fill='x', pady=(12, 0))
        ttk.Button(
            controls, text=tr('Alterar atalho'), command=self.edit_selected
        ).pack(side='left')
        ttk.Button(
            controls,
            text=tr('Restaurar atalhos padrão'),
            command=lambda: self.app.shortcut_keys.set('{}'),
        ).pack(side='left', padx=8)
        ttk.Button(body, text=tr('Fechar'), command=window.destroy).pack(
            anchor='e', pady=(12, 0)
        )
        window.bind('<Escape>', lambda event: window.destroy())
        window.bind('<F1>', lambda event: 'break')
        table.focus_set()
