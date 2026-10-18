"""Presentation-only filtering; the execution queue model is never detached or reordered."""
import time,unicodedata
import tkinter as tk
from tkinter import ttk
from i18n import tr
from i18n_tk import TranslatedCombobox
FILTERS=('Todos','Pendentes','Em andamento','Concluídos','Com falha','Cancelados')
STATES={'Pendentes':{'Na fila','Pendente'},'Em andamento':{'Em andamento','Baixando','Aguardando escolha'},'Concluídos':{'Concluído'},'Com falha':{'Falhou','Erro'},'Cancelados':{'Cancelado','Parado'}}
def folded(value):return ''.join(c for c in unicodedata.normalize('NFD',str(value or '').casefold()) if not unicodedata.combining(c))
def matches(job,title,query,state):
    if state in STATES and job.get('state') not in STATES[state]:return False
    if not query.strip():return True
    info=job.get('catalog_record') or job.get('queue_info') or {}
    haystack=folded(' '.join(str(v) for v in (title,job.get('url',''),info.get('artists',[]),info.get('album',''),info.get('platform',''),job.get('mode',''))))
    return all(term in haystack for term in folded(query).split())

class QueueFilter:
    def __init__(self,app,parent):
        self.app=app;self.query=tk.StringVar();self.state=tk.StringVar(value='Todos');self.summary=tk.StringVar()
        self.keys=None;self.checked=0;self.signature=None;self.view=None;self.syncing=False
        row=ttk.Frame(parent);row.pack(fill='x',pady=(8,0));row.columnconfigure(1,weight=1)
        ttk.Label(row,text=tr('Buscar na fila')).grid(row=0,column=0,padx=(0,8))
        self.entry=ttk.Entry(row,textvariable=self.query);self.entry.grid(row=0,column=1,sticky='ew')
        TranslatedCombobox(row,textvariable=self.state,values=FILTERS,state='readonly',width=18).grid(row=0,column=2,padx=8)
        ttk.Button(row,text=tr('Limpar filtros'),command=self.clear).grid(row=0,column=3)
        ttk.Label(parent,textvariable=self.summary,style='Muted.TLabel').pack(anchor='w',pady=(4,0))
        for var in (self.query,self.state):var.trace_add('write',self.changed)
    def clear(self):self.query.set('');self.state.set('Todos')
    def changed(self,*_):
        self.checked=0;self.keys=None;self.signature=None
        if hasattr(self.app,'queue_cards'):self.app.queue_cards.refresh()
    def visible_keys(self):
        now=time.monotonic()
        tree=self.app.tree;all_keys=tree.get_children()
        if self.keys is not None and getattr(self,'all_keys',None)==all_keys and now-self.checked<.25:return self.keys
        self.all_keys=all_keys
        query=self.query.get();state=self.state.get()
        keys=all_keys if not query.strip() and state=='Todos' else tuple(k for k in all_keys if matches(self.app.jobs.get(k,{}),tree.set(k,'name') if query.strip() else '',query,state))
        self.keys=keys;self.checked=now
        text=tr('Exibindo {visible} de {total} itens.').replace('{visible}',str(len(keys))).replace('{total}',str(len(all_keys)))
        self.summary.set(text)
        selected=tuple(k for k in tree.selection() if k in keys)
        if selected!=tree.selection():tree.selection_set(selected)
        return keys
    def compact(self,scroll):
        app=self.app;tree=app.tree
        filtered=bool(self.query.get().strip()) or self.state.get()!='Todos'
        if not filtered:
            if self.view:self.view.pack_forget()
            if not tree.winfo_manager():tree.pack(side='left',fill='both',expand=True)
            scroll.configure(command=tree.yview);tree.configure(yscrollcommand=scroll.set)
            if not scroll.winfo_manager():scroll.pack(side='right',fill='y')
            self.visible_keys();return
        tree.pack_forget()
        if self.view is None:
            self.view=ttk.Treeview(tree.master,columns=tree.cget('columns'),show='tree headings',selectmode='extended')
            self.view.column('#0',width=52,minwidth=52,stretch=False)
            for column in tree.cget('columns'):
                self.view.heading(column,**{k:tree.heading(column,k) for k in ('text','anchor')})
                self.view.column(column,**{k:tree.column(column,k) for k in ('width','minwidth','stretch','anchor')})
            for tag in ('Concluído','Falhou','Cancelado'):self.view.tag_configure(tag,foreground=tree.tag_configure(tag).get('foreground') or '#91a0b3')
            self.view.bind('<<TreeviewSelect>>',self.select)
            if hasattr(app,'queue_control'):app.queue_control.bind_drag(self.view,tree=self.view)
            for key in ('<Delete>','<BackSpace>'):self.view.bind(key,lambda _:app.remove())
            from list_context import ListContext,queue_actions
            ListContext(self.view,lambda:queue_actions(app),self.select)
        keys=self.visible_keys();snapshot=tuple((k,tuple(tree.item(k,'values')),tuple(tree.item(k,'image')),tuple(tree.item(k,'tags'))) for k in keys)
        if snapshot!=self.signature:
            self.signature=snapshot
            for k in self.view.get_children():
                if k not in keys:self.view.delete(k)
            for index,(key,values,image,tags) in enumerate(snapshot):
                if self.view.exists(key):self.view.item(key,values=values,image=image,tags=tags)
                else:self.view.insert('', 'end',iid=key,values=values,image=image,tags=tags)
                self.view.move(key,'',index)
        selected=tuple(k for k in tree.selection() if k in keys)
        if self.view.selection()!=selected:self.view.selection_set(selected)
        self.view.configure(yscrollcommand=scroll.set);scroll.configure(command=self.view.yview)
        if not self.view.winfo_manager():self.view.pack(side='left',fill='both',expand=True)
        if not scroll.winfo_manager():scroll.pack(side='right',fill='y')
    def select(self,*_):
        if self.view and self.view.selection()!=self.app.tree.selection():
            self.app.tree.selection_set(self.view.selection());self.app.refresh_queue()
