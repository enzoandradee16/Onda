"""Stable tab identities and drag ordering without changing active content."""
from i18n import tr
import tkinter as tk
from tkinter import ttk

DEFAULT_ORDER = ('catalog', 'downloads', 'queue', 'images', 'converter', 'playlists', 'history', 'effects', 'metadata')


REQUIRED_TABS = frozenset(('catalog', 'downloads', 'queue'))

def normalize_hidden(value):
    if not isinstance(value, (list, tuple)):
        return []
    return [key for key in DEFAULT_ORDER if key not in REQUIRED_TABS and key in value]

class NavigationNotebook(ttk.Notebook):
    def select(self, tab_id=None):
        if tab_id is not None and self.tab(tab_id, 'state') == 'hidden':
            return super().select()
        return super().select(tab_id) if tab_id is not None else super().select()

    def visible_tabs(self):
        return tuple(tab for tab in self.tabs() if self.tab(tab, 'state') != 'hidden')


def normalize_order(value):
    if not isinstance(value, (list, tuple)):
        return list(DEFAULT_ORDER)
    result=[]
    for key in value:
        if isinstance(key, str) and key in DEFAULT_ORDER and key not in result:
            result.append(key)
    missing_converter='converter' not in result
    missing_queue='queue' not in result
    result += [key for key in DEFAULT_ORDER if key not in result and key not in ('queue','converter')]
    if missing_converter:result.insert(result.index('images')+1,'converter')
    if missing_queue:result.insert(result.index('downloads')+1,'queue')
    return result


class TabReorder:
    def __init__(self, notebook, pages, order, changed):
        self.notebook, self.pages, self.changed = notebook, pages, changed
        self.hidden = []
        self.drag = None
        self.apply(order)
        notebook.bind('<ButtonPress-1>', self.press, add='+')
        notebook.bind('<B1-Motion>', self.motion, add='+')
        notebook.bind('<ButtonRelease-1>', self.release, add='+')
        notebook.bind('<Escape>', self.cancel, add='+')
        notebook.bind('<Button-3>', self.context, add='+')
        self.menu=tk.Menu(notebook, tearoff=False)
        self.menu.add_command(label=tr('Mover para a esquerda'), command=lambda:self.move(-1))
        self.menu.add_command(label=tr('Mover para a direita'), command=lambda:self.move(1))
        self.menu.add_separator()
        self.menu.add_command(label=tr('Restaurar ordem das abas'), command=self.reset)

    def order(self):
        keys={str(page):key for key,page in self.pages.items()}
        return [keys[tab] for tab in self.notebook.tabs()]

    def apply(self, order):
        selected=self.notebook.select()
        for index,key in enumerate(normalize_order(order)):
            self.notebook.insert(index,self.pages[key])
        self.set_hidden(self.hidden)
        if selected and self.notebook.tab(selected,'state') != 'hidden':
            self.notebook.select(selected)

    def set_hidden(self, value):
        self.hidden = normalize_hidden(value)
        for key, page in self.pages.items():
            self.notebook.tab(page, state='hidden' if key in self.hidden else 'normal')
        selected = self.notebook.select()
        if not selected or self.notebook.tab(selected, 'state') == 'hidden':
            self.notebook.select(self.pages['catalog'])

    def hit(self, event):
        try:
            return self.notebook.tabs()[self.notebook.index(f'@{event.x},{event.y}')]
        except tk.TclError:
            return None

    def press(self, event):
        tab=self.hit(event)
        if tab:
            self.drag={'tab':tab,'x':event.x,'y':event.y,'moved':False,'before':self.order()}
            self.notebook.focus_set()
            # Select only on release, so dragging an inactive tab keeps audio playing.
            return 'break'

    def motion(self, event):
        if not self.drag:
            return
        if not self.drag['moved'] and max(abs(event.x-self.drag['x']),abs(event.y-self.drag['y']))<6:
            return 'break'
        target=self.hit(event)
        if target:
            self.drag['moved']=True
            self.notebook.configure(cursor='fleur')
            if target != self.drag['tab']:
                self.notebook.insert(self.notebook.index(target),self.drag['tab'])
        return 'break'

    def release(self, event):
        if not self.drag:
            return
        drag,self.drag=self.drag,None
        self.notebook.configure(cursor='')
        if not drag['moved']:
            if self.hit(event)==drag['tab']:
                self.notebook.select(drag['tab'])
        elif self.order()!=drag['before']:
            self.changed(self.order())
        return 'break'

    def cancel(self, event=None):
        if self.drag:
            self.apply(self.drag['before'])
            self.drag=None
            self.notebook.configure(cursor='')
            return 'break'

    def context(self, event):
        self.context_tab=self.hit(event)
        if self.context_tab:
            self.cancel()
            visible=self.notebook.visible_tabs()
            index=visible.index(self.context_tab)
            self.menu.entryconfigure(0,state='normal' if index>0 else 'disabled')
            self.menu.entryconfigure(1,state='normal' if index<len(visible)-1 else 'disabled')
            try:
                self.menu.tk_popup(event.x_root,event.y_root)
            finally:
                self.menu.grab_release()
            return 'break'

    def move(self, direction):
        target=getattr(self,'context_tab',None)
        if target:
            visible=self.notebook.visible_tabs()
            index=visible.index(target)+direction
            if 0<=index<len(visible):
                self.notebook.insert(self.notebook.index(visible[index]),target)
                self.changed(self.order())

    def reset(self):
        self.cancel()
        if self.order()!=list(DEFAULT_ORDER):
            self.apply(DEFAULT_ORDER)
            self.changed(self.order())
