"""A card view of the existing queue; Treeview remains the selection/order model."""
import tkinter as tk
from tkinter import ttk
from i18n import tr

class QueueCards(ttk.Frame):
    def __init__(self,parent,app,scroll):
        super().__init__(parent)
        self.app,self.scroll=app,scroll
        from queue_artwork import QueueArtwork
        self.artwork=QueueArtwork()
        self.covers={}
        self.metadata_requested=set()
        self.rows={};self.signature=None;self.limit=30
        for event in ('<Delete>','<BackSpace>'):self.bind(event,lambda _:self.remove_selected())
        self.columnconfigure(0,weight=1)
        self.bind('<Configure>',self.wrap_labels)
        self.traces=[(var,var.trace_add('write',self.changed)) for var in (app.queue_view,app.queue_card_size)]

    def changed(self,*_):
        if self.app.queue_view.get()=='Compacto':
            from metadata_badges import apply_tree_badge
            self.app.tree.configure(show='tree headings')
            self.app.tree.column('#0',width=52,minwidth=52,stretch=False)
            for key in self.app.tree.get_children():
                job=self.app.jobs.get(key,{})
                apply_tree_badge(self.app.tree,key,job.get('catalog_record') or job.get('queue_info') or {})
        self.signature=None
        self.refresh()

    def refresh(self):
        complete=self.app.queue_view.get()=='Completa'
        if not complete:
            self.pack_forget()
            self.app.queue_size_controls.pack_forget()
            self.app.queue_filter.compact(self.scroll)
            return
        self.app.tree.pack_forget();self.scroll.pack_forget()
        if self.app.queue_filter.view:self.app.queue_filter.view.pack_forget()
        if not self.app.queue_size_controls.winfo_manager():self.app.queue_size_controls.pack(side='left',padx=4)
        if not self.winfo_manager():self.pack(fill='both',expand=True)
        self.artwork.poll()
        keys=self.app.queue_filter.visible_keys()
        self.metadata_requested.intersection_update(keys)
        if not keys:self.app.empty_queue.lift()
        signature=(keys[:self.limit],self.app.queue_card_size.get(),len(keys)>self.limit)
        if signature!=self.signature:
            for child in self.winfo_children():child.destroy()
            self.rows={};self.covers={};self.signature=signature
            size=self.app.queue_card_size.get()
            pad,font,icon=(6,10,16) if size=='Pequeno' else (10,12,23) if size=='Médio' else (14,14,32)
            for index,key in enumerate(keys[:self.limit]):
                card=ttk.Frame(self,padding=pad,style='Card.TFrame');card.grid(row=index,column=0,sticky='ew',pady=(0,6));card.columnconfigure(1,weight=1)
                selected=tk.BooleanVar(self,value=key in self.app.tree.selection())
                ttk.Checkbutton(card,variable=selected,command=lambda k=key,v=selected:self.select(k,v.get())).grid(row=0,column=0,rowspan=3,padx=(0,8))
                title=ttk.Label(card,font=('Segoe UI',font,'bold'),style='Card.TLabel',wraplength=800);title.grid(row=0,column=1,sticky='w')
                details=ttk.Label(card,style='CardMuted.TLabel',wraplength=800);details.grid(row=1,column=1,sticky='w',pady=(3,0))
                source=ttk.Label(card,style='CardMuted.TLabel',wraplength=800);source.grid(row=2,column=1,sticky='w',pady=(3,0))
                cover=ttk.Label(card,text='♫',font=('Segoe UI',icon),style='Card.TLabel')
                cover.grid(row=0,column=2,rowspan=3,padx=8)
                cover.bind('<Button-1>',lambda _,k=key:self.select(k,k not in self.app.tree.selection()))
                self.covers[key]=cover
                for widget in (card,title,details,source):
                    widget.bind('<Button-1>',lambda _,k=key:self.select(k,k not in self.app.tree.selection()))
                for widget in card.winfo_children():
                    for event in ('<Delete>','<BackSpace>'):widget.bind(event,lambda _:self.remove_selected())
                if hasattr(self.app,'queue_control'):
                    handle=ttk.Label(card,text='↕',style='CardMuted.TLabel',cursor='fleur');handle.grid(row=0,column=3,padx=6)
                    self.app.queue_control.bind_drag(handle,key=key)
                self.app.tree._list_context.card(card,key)
                self.rows[key]=(card,selected,title,details,source,None)
            if len(keys)>self.limit:ttk.Button(self,text=tr('Mostrar mais'),command=self.more).grid(row=len(self.rows),column=0,pady=6)
            if hasattr(self.app,'theme_manager'):self.app.theme_manager.walk(self)
        selected=set(self.app.tree.selection())
        for key,(card,var,title,details,source,previous) in list(self.rows.items()):
            job=self.app.jobs.get(key,{})
            values=self.app.tree.item(key,'values')
            info=job.get('queue_info') or job.get('catalog_record') or {}
            from history_details import detail_lines
            metadata=dict(info,duration=int(info.get('duration_ms') or 0)//1000)
            subtitle=' · '.join(v for v in (', '.join(info.get('artists') or []),detail_lines(metadata,translate=tr),*map(str,values[1:])) if v)
            cover=self.covers[key]
            if not info.get('cover_url') and not job.get('_queue_lookup_requested') and key not in self.metadata_requested:
                from queue_titles import supports_lookup
                self.metadata_requested.add(key)
                if supports_lookup(job.get('url','')):
                    self.app.title_lookup.submit(key,job['url'],(self.app.spotify_client_id.get(),self.app.spotify_client_secret.get()),self.app.social_cookies.get().strip())
            artwork=self.artwork.get(info.get('cover_url'))
            if artwork and getattr(cover,'_artwork_source',None)!=artwork:
                import io
                from PIL import Image,ImageTk
                with Image.open(io.BytesIO(artwork)) as image:
                    side={'Pequeno':64,'Médio':96,'Grande':124}[self.app.queue_card_size.get()]
                    image.thumbnail((side,side))
                    cover._queue_image=ImageTk.PhotoImage(image.copy(),master=cover)
                cover.configure(image=cover._queue_image,text='')
                cover._artwork_source=artwork
            from metadata_badges import apply_badge,provider,NAMES
            origin=job.get('catalog_record') or info
            platform=NAMES.get(provider(origin),'')
            source_text=' · '.join(v for v in (platform,job.get('url','')) if v)
            apply_badge(source,origin)
            snapshot=(values[0] if values else job.get('url',''),subtitle,source_text,key in selected)
            if snapshot!=previous:
                title.configure(text=snapshot[0]);details.configure(text=subtitle);source.configure(text=snapshot[2])
                var.set(snapshot[3]);card.configure(style='HistorySelected.TFrame' if snapshot[3] else 'Card.TFrame')
                for widget in (title,details,source,cover):widget.configure(style=('HistorySelected.TLabel' if widget is title else 'HistorySelectedMuted.TLabel') if snapshot[3] else ('Card.TLabel' if widget is title else 'CardMuted.TLabel'))
                self.rows[key]=(card,var,title,details,source,snapshot)

    def wrap_labels(self,event):
        width=max(180,event.width-230)
        for row in self.rows.values():
            for label in row[2:5]:label.configure(wraplength=width)

    def select(self,key,selected):
        (self.app.tree.selection_add if selected else self.app.tree.selection_remove)(key)
        self.focus_set();self.app.refresh_queue()

    def remove_selected(self):
        self.app.remove();return 'break'

    def more(self):self.limit+=30;self.refresh()

    def resize_cards(self,event):
        if self.app.queue_view.get()!='Completa':
            from settings_scroll import scroll_page
            return scroll_page(event)
        sizes=('Pequeno','Médio','Grande');index=sizes.index(self.app.queue_card_size.get())
        target=max(0,min(2,index+(1 if event.delta>0 else -1))) if event.delta else index
        if target!=index:self.app.queue_card_size.set(sizes[target])
        return 'break'

    def shutdown(self):
        self.artwork.shutdown()
        for variable,trace in self.traces:variable.trace_remove('write',trace)
