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
        self.app=app
        self.window=None
        self.tag="OndaShortcuts"+str(id(self))
        bindings={
            '<Control-l>':'links','<Control-j>':'queue','<Control-h>':'history',
            '<Control-a>':'select-all','<Control-f>':'search','<Control-Return>':'download',
            '<Control-KP_Enter>':'download','<Control-Shift-Return>':'add',
            '<Control-Shift-KP_Enter>':'add','<F5>':'start','<Shift-F5>':'stop',
            '<Control-r>':'retry','<Alt-Up>':'up','<Alt-Down>':'down',
            '<Alt-Home>':'prioritize','<Alt-v>':'view','<Control-Shift-Delete>':'clear',
            '<Control-o>':'folder','<Control-comma>':'settings','<Control-m>':'metadata',
            '<Control-Shift-l>':'log','<Control-Shift-e>':'failures','<F1>':'help',
            '<Control-Tab>':'next','<Control-Shift-Tab>':'previous',
            '<Control-ISO_Left_Tab>':'previous',
            '<Control-Up>':'scroll-up','<Control-Down>':'scroll-down',
        }
        bindings.update({f'<Control-Key-{number}>':f'tab:{number-1}' for number in range(1,10)})
        for sequence,action in bindings.items():
            callback=lambda event,key=action:self.dispatch(key,event)
            app.bind_class(self.tag,sequence,callback)
            # Windows Caps Lock and Shift can change a letter's keysym.
            letter=sequence.rsplit('-',1)[-1][:-1]
            if len(letter)==1 and letter.isalpha():
                app.bind_class(self.tag,sequence[:-2]+letter.upper()+'>',callback)
        self.attach(app)
        app.bind('<Map>',lambda event:self.attach(event.widget,descend=False),add='+')

    def attach(self,widget,*,descend=True):
        # Consume explicit shortcut chords before generic widget keys (e.g. Delete).
        # Never attach application shortcuts to another top-level window.
        if not isinstance(widget,tk.Misc):return
        try:
            if widget.winfo_toplevel()!=self.app:return
        except tk.TclError:return
        tags=widget.bindtags()
        if self.tag not in tags:widget.bindtags((self.tag,*tags))
        if descend:
            for child in widget.winfo_children():self.attach(child)

    def allowed(self,event):
        widget=event.widget if event is not None else self.app.focus_get() or self.app
        try:
            return widget.winfo_toplevel()==self.app and self.app.grab_current() is None
        except (tk.TclError,KeyError):return False

    def editing(self,event):
        widget=event.widget if event is not None else self.app.focus_get()
        return widget is not None and widget.winfo_class() in ('Text','Entry','TEntry','TCombobox','Spinbox','TSpinbox')

    def select(self,page,field=None):
        self.app.pages.select(page)
        if field is not None:
            field.focus_set()
            if isinstance(field,tk.Text):field.tag_add('sel','1.0','end-1c')
            else:field.selection_range(0,'end')

    def dispatch(self,action,event=None):
        if not self.allowed(event):return
        app=self.app
        current=app.pages.select()
        if action.startswith('tab:'):
            tabs=app.pages.visible_tabs();index=int(action.split(':')[1])
            if index>=len(tabs):return
            app.pages.select(tabs[index])
        elif action in ('next','previous'):
            tabs=app.pages.visible_tabs();index=tabs.index(current)
            app.pages.select(tabs[(index+(1 if action=='next' else -1))%len(tabs)])
        elif action in ('scroll-up','scroll-down'):
            page=app.nametowidget(current)
            canvas=getattr(page,'canvas',None)
            if canvas is None:return
            canvas.yview_scroll(-1 if action=='scroll-up' else 1,'pages')
        elif action=='select-all':
            if self.editing(event):return
            widget=event.widget if event is not None else app.focus_get()
            if isinstance(widget,ttk.Treeview) and str(widget.cget('selectmode'))=='extended':
                table=widget
            elif current==str(app.queue_page):table=app.tree
            elif current==str(app.playlist_page):table=app.playlist_page.table
            elif current==str(app.history_page):table=app.history_page.table
            else:return
            table.selection_set(app.queue_filter.visible_keys() if table is app.tree else table.get_children())
        elif action=='links':self.select(app.download_page,app.urls)
        elif action=='queue':app.show_queue()
        elif action=='history':self.select(app.history_page)
        elif action=='search':
            if current==str(app.playlist_page):field=app.playlist_page.search_entry
            elif current==str(app.history_page):field=app.history_page.search_entry
            elif current==str(app.queue_page):field=app.queue_filter.entry
            else:
                self.select(app.catalog_page)
                field=app.catalog_page.entry
            field.focus_set();field.selection_range(0,'end')
        elif action in ('download','add'):
            if current!=str(app.download_page):return
            if not app.updating:
                app.download_now() if action=='download' else app.add()
        elif action=='stop':
            if app.running or app.parallel.workers:app.cancel()
        elif action=='view':
            if self.editing(event):return
            if current==str(app.queue_page):value=app.queue_view
            elif current==str(app.history_page):value=app.history_view
            else:return
            value.set('Completa' if value.get()=='Compacto' else 'Compacto')
        elif action in ('start','retry','up','down','prioritize','clear'):
            if current!=str(app.queue_page) or self.editing(event):return
            if action=='start':app.start()
            elif action=='retry':app.retry()
            elif action=='clear':app.clear_queue()
            elif app.tree.selection():
                from advanced_ui import move_queue
                move_queue(app,{'up':-1,'down':1,'prioritize':0}[action])
                app.refresh_queue()
        elif action=='folder':app.open_folder()
        elif action=='settings':app.show_settings()
        elif action=='metadata':app.open_metadata()
        elif action=='log':app.show_log()
        elif action=='failures':app.show_failures()
        elif action=='help':self.show_help()
        else:return
        return 'break'

    def show_help(self):
        if self.window is not None and self.window.winfo_exists():
            self.window.deiconify();self.window.lift();self.window.focus_set();return
        window=self.window=tk.Toplevel(self.app)
        window.title(tr('Atalhos de teclado'))
        window.geometry('780x590');window.minsize(620,420)
        body=ttk.Frame(window,padding=18);body.pack(fill='both',expand=True)
        ttk.Label(body,text=tr('Atalhos de teclado'),font=('Segoe UI',16,'bold')).pack(anchor='w')
        ttk.Label(body,text=tr('Os controles da fila respeitam a aba ativa e os campos de texto.'),wraplength=720,style='Muted.TLabel').pack(anchor='w',pady=(6,12))
        panel=ttk.Frame(body);panel.pack(fill='both',expand=True)
        ttk.Style(window).configure('Shortcuts.Treeview',rowheight=30)
        table=ttk.Treeview(panel,columns=('key','action'),show='headings',style='Shortcuts.Treeview',selectmode='browse')
        table.heading('key',text=tr('Atalho'));table.heading('action',text=tr('Ação'))
        table.column('key',width=225,minwidth=190,stretch=False);table.column('action',width=475,minwidth=260)
        for key,label in SHORTCUTS:table.insert('', 'end',values=(tr(key),tr(label)))
        table.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(panel,command=table.yview);scroll.pack(side='right',fill='y');table.configure(yscrollcommand=scroll.set)
        ttk.Button(body,text=tr('Fechar'),command=window.destroy).pack(anchor='e',pady=(12,0))
        window.bind('<Escape>',lambda event:window.destroy())
        window.bind('<F1>',lambda event:'break')
        table.focus_set()
