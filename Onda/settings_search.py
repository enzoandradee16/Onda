"""Search actual settings labels in the current language and reveal their location."""

import tkinter as tk
from tkinter import ttk
import unicodedata
from i18n import tr


def normalize(text):
    return ''.join(
        c
        for c in unicodedata.normalize('NFD', text.casefold())
        if not unicodedata.combining(c)
    )


class SettingsSearch(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.query = tk.StringVar()
        self.records = []
        self.results = []
        self.timer = None
        ttk.Label(self, text=tr('Pesquisar configurações')).pack(anchor='w')
        entry = self.entry = ttk.Entry(self, textvariable=self.query)
        entry.pack(fill='x', pady=(4, 6))
        self.list = tk.Listbox(
            self, height=4, exportselection=False, activestyle='dotbox'
        )
        self.list.bind('<ButtonRelease-1>', self.open)
        self.list.bind('<Return>', self.open)
        entry.bind('<Return>', self.open)
        self.status = ttk.Label(self, style='Muted.TLabel')
        self.query.trace_add('write', self.changed)
        app.settings_window.bind(
            "<Control-f>",
            lambda _: (entry.focus_set(), entry.selection_range(0, "end"), "break")[-1],
        )
        self.bind('<Destroy>', self.destroyed, add='+')

    def changed(self, *_):
        if self.timer:
            self.after_cancel(self.timer)
        self.timer = self.after(160, self.search)

    def widgets(self, parent):
        for widget in parent.winfo_children():
            yield widget
            yield from self.widgets(widget)

    def search(self):
        if self.timer:
            self.after_cancel(self.timer)
        self.timer = None
        terms = normalize(self.query.get()).split()
        self.results = []
        self.list.delete(0, 'end')
        if not terms:
            self.list.pack_forget()
            self.status.pack_forget()
            return
        app = self.app
        seen = set()
        for tab in app.settings_pages.tabs():
            page = app.settings_categories[tab]
            category = app.settings_pages.tab(tab, 'text')
            for widget in self.widgets(page.content):
                if not isinstance(widget, (ttk.Label, ttk.Checkbutton, ttk.Button)):
                    continue
                text = str(widget.cget('text') or '').strip()
                if not text or (category, text) in seen:
                    continue
                if all(term in normalize(category + ' ' + text) for term in terms):
                    seen.add((category, text))
                    self.results.append((tab, widget, text, category))
        self.results.sort(
            key=lambda row: (
                normalize(row[2]) != normalize(self.query.get().strip()),
                len(row[2]),
            )
        )
        for _, _, text, category in self.results:
            self.list.insert(
                'end',
                category + ' · ' + (text[:110] + '…' if len(text) > 110 else text),
            )
        self.list.pack(fill='x')
        if not self.results:
            self.status.configure(text=tr('Nenhuma configuração encontrada.'))
            self.status.pack(anchor='w')
        else:
            self.status.pack_forget()
            self.list.selection_set(0)

    def open(self, event=None):
        if self.timer:
            self.search()
        if not self.results:
            return 'break'
        selected = self.list.curselection()
        tab, widget, text, category = self.results[selected[0] if selected else 0]
        app = self.app
        app.settings_pages.select(tab)
        page = app.settings_categories[tab]
        self.query.set('')
        self.search()
        self.status.configure(text=category + ' · ' + text[:110])
        self.status.pack(anchor='w')
        app.settings_window.update_idletasks()
        y = widget.winfo_rooty() - page.content.winfo_rooty()
        page.canvas.yview_moveto(max(0, (y - 24) / max(1, page.content.winfo_height())))
        widget.focus_set()
        return 'break'

    def destroyed(self, event):
        if event.widget is self and self.timer:
            self.after_cancel(self.timer)
            self.timer = None
