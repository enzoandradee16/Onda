"""Stable tab identities and drag ordering without changing active content."""
from i18n import tr
import tkinter as tk

DEFAULT_ORDER = ('catalog', 'downloads', 'images', 'playlists', 'history', 'effects', 'metadata')


def normalize_order(value):
    if not isinstance(value, (list, tuple)):
        return list(DEFAULT_ORDER)
    result=[]
    for key in value:
        if isinstance(key, str) and key in DEFAULT_ORDER and key not in result:
            result.append(key)
    return result + [key for key in DEFAULT_ORDER if key not in result]


class TabReorder:
    def __init__(self, notebook, pages, order, changed):
        self.notebook, self.pages, self.changed = notebook, pages, changed
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
        if selected:
            self.notebook.select(selected)

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
            index=self.notebook.index(self.context_tab)
            self.menu.entryconfigure(0,state='normal' if index>0 else 'disabled')
            self.menu.entryconfigure(1,state='normal' if index<len(self.pages)-1 else 'disabled')
            try:
                self.menu.tk_popup(event.x_root,event.y_root)
            finally:
                self.menu.grab_release()
            return 'break'

    def move(self, direction):
        target=getattr(self,'context_tab',None)
        if target:
            index=self.notebook.index(target)+direction
            if 0<=index<len(self.pages):
                self.notebook.insert(index,target)
                self.changed(self.order())

    def reset(self):
        self.cancel()
        if self.order()!=list(DEFAULT_ORDER):
            self.apply(DEFAULT_ORDER)
            self.changed(self.order())
