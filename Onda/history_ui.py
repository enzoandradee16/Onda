from i18n import tr
from i18n_tk import TranslatedCombobox, display_var
import os
import queue
import threading
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk


class HistoryPane(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=(0, 18, 0, 0))
        self.app = app
        self.query = tk.StringVar()
        self.rows = {}
        self._selected_card = tk.StringVar()
        self._view = None
        self._generation = 0
        self._events = queue.Queue()
        self._cards = {}
        self._limit = 30
        self._closed = False
        self._view_trace = app.history_view.trace_add("write", lambda *_: self.refresh())
        self._size_trace = app.history_card_size.trace_add("write", lambda *_: self.refresh())
        self._search_after = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        ttk.Label(self, text=tr("Sua biblioteca de downloads."), font=("Segoe UI", 21, "bold"), anchor="center").grid(row=0, column=0, sticky="ew")
        search = ttk.Frame(self)
        search.grid(row=1, column=0, sticky="ew", pady=18)
        self.search_entry=ttk.Entry(search,textvariable=self.query)
        self.search_entry.pack(side="left",fill="x",expand=True)
        ttk.Button(search, text=tr("Pesquisar"), command=self.refresh).pack(side="left", padx=8)
        self.query.trace_add("write", lambda *_: self.schedule_search())
        toolbar=ttk.Frame(self)
        toolbar.grid(row=2,column=0,pady=(0,12))
        ttk.Button(toolbar,text=tr("Limpar histórico"),style="Quiet.TButton",command=self.clear).pack(side="left",padx=4)
        TranslatedCombobox(toolbar,textvariable=app.history_view,values=("Compacto","Completa"),state="readonly",width=14).pack(side="left",padx=4)
        self.size_controls=ttk.Frame(toolbar)
        ttk.Label(self.size_controls,text=tr("Cards"),style="Muted.TLabel").pack(side="left",padx=(8,4))
        TranslatedCombobox(self.size_controls,textvariable=app.history_card_size,values=("Pequeno","Médio","Grande"),state="readonly",width=14).pack(side="left",padx=(0,8))
        panel = self.panel = ttk.Frame(self)
        panel.grid(row=3, column=0, sticky="nsew")
        self.table = ttk.Treeview(panel, columns=("name", "mode", "date"), show="headings", selectmode="extended")
        from list_context import bind_history
        bind_history(self)
        for key, label, width in (("name", "ARQUIVO", 480), ("mode", "FORMATO", 100), ("date", "DATA", 200)):
            self.table.heading(key, text=tr(label))
            self.table.column(key, width=width, minwidth=80, stretch=key == "name")
        self.table.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(panel, command=self.table.yview)
        scroll.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scroll.set)
        self.table.bind("<Double-1>", lambda _: self.open())
        controls = ttk.Frame(self)
        controls.grid(row=4, column=0, sticky="ew", pady=16)
        ttk.Button(controls, text=tr("Abrir arquivo"), command=self.open).pack(side="left")
        ttk.Button(controls, text=tr("Abrir pasta"), command=lambda: self.open(True)).pack(side="left", padx=8)
        ttk.Button(controls, text=tr("Usar nos efeitos"), style="Accent.TButton", command=self.effects).pack(side="right")
        ttk.Button(controls,text=tr("Editar áudio / letra"),command=self.edit_audio).pack(side="left",padx=4)
        ttk.Button(controls,text=tr("Editar metadados em lote"),command=self.edit_batch).pack(side="left",padx=4)
        self.status = tk.StringVar()
        ttk.Label(self, textvariable=display_var(self.status), style="Muted.TLabel").grid(row=5, column=0, sticky="w")
        self.cards = ttk.Frame(self)
        self.cards.columnconfigure(0,weight=1)
        self.refresh()
        self._poll_id = self.after(100,self.poll_cards)

    def schedule_search(self):
        if self._search_after is not None:
            self.after_cancel(self._search_after)
        self._search_after = self.after(180, self.refresh)

    def shutdown(self):
        self._closed = True
        self._generation += 1
        self.app.history_view.trace_remove("write", self._view_trace)
        self.app.history_card_size.trace_remove("write",self._size_trace)
        if getattr(self,"_poll_id",None):self.after_cancel(self._poll_id)
        self.cancel_search()

    def cancel_search(self):
        if self._search_after is not None:
            self.after_cancel(self._search_after)
            self._search_after = None

    def refresh(self):
        self.cancel_search()
        if not hasattr(self, "table"):
            return
        selected = self.table.selection()
        try:
            rows = {str(row["id"]): row for row in self.app.library.history(self.query.get())}
        except Exception:
            self.status.set("Não foi possível ler o histórico.")
            return
        self.status.set(f"{len(rows)} registros · até 1000 resultados por pesquisa.")
        view = self.app.history_view.get()
        if rows == self.rows and view == self._view and view == "Compacto":
            return
        self._view = view
        self._limit = 30
        self.rows = rows
        self.table.delete(*self.table.get_children())
        for key, row in self.rows.items():
            self.table.insert("", "end", iid=key, values=(row["name"], row["mode"], row["date"][:19].replace("T", " ")))
        if selected:
            self.table.selection_set([key for key in selected if key in self.rows])
        if view == "Completa":
            self.size_controls.pack(side="right")
            self.panel.grid_remove()
            self.cards.grid(row=3,column=0,sticky="nsew")
            self.render_cards()
        else:
            self.size_controls.pack_forget()
            self._generation += 1
            self.cards.grid_remove()
            self.panel.grid()

    def render_cards(self):
        from history_details import history_details
        self._generation += 1
        generation = self._generation
        for widget in self.cards.winfo_children():widget.destroy()
        self._cards = {}
        self._card_checks = {}
        selected=self.table.selection()
        self._selected_card.set(selected[0] if selected else "")
        size=self.app.history_card_size.get()
        padding,title_size,artist_size=(8,12,10) if size=="Pequeno" else (10,13,10) if size=="Médio" else (14,14,11)
        rows=list(self.rows.items())[:self._limit]
        for index,(key,row) in enumerate(rows):
            card=ttk.Frame(self.cards,style="Card.TFrame",padding=padding)
            card.grid(row=index,column=0,sticky="ew",pady=(0,10));card.columnconfigure(1,weight=1)
            cover=ttk.Label(card,text=tr("♫"),style="Card.TLabel",width=12,anchor="center")
            cover.grid(row=0,column=0,rowspan=4,padx=(0,14))
            title=ttk.Label(card,text=row['name'],style="Card.TLabel",font=("Segoe UI",title_size,"bold"),wraplength=600)
            title.grid(row=0,column=1,sticky="w")
            artist=ttk.Label(card,text=tr("Carregando informações…"),style="Card.TLabel",font=("Segoe UI",artist_size))
            artist.grid(row=1,column=1,sticky="w",pady=4)
            details=ttk.Label(card,style="CardMuted.TLabel",wraplength=600)
            details.grid(row=2,column=1,sticky="w")
            ttk.Label(card,text=tr(f"{row['mode']} · Baixado em {row['date'][:19].replace('T',' ')}"),style="CardMuted.TLabel").grid(row=3,column=1,sticky="w",pady=(6,0))
            actions=ttk.Frame(card,style="Card.TFrame");actions.grid(row=4,column=0,columnspan=2,sticky="ew",pady=(10,0))
            for label,action in (("Abrir arquivo",self.open),("Abrir pasta",lambda:self.open(True)),("Editar metadados",self.edit_audio),("Usar nos efeitos",self.effects)):
                ttk.Button(actions,text=tr(label),command=lambda key=key,action=action:self.card_action(key,action)).pack(side="left",padx=(0,6))
            checked=tk.BooleanVar(value=key in selected)
            self._card_checks[key]=checked
            ttk.Checkbutton(actions,text=tr("Selecionar música"),variable=checked,command=lambda key=key:self.toggle_card(key)).pack(side="right")
            for widget in (card,cover,title,artist,details):
                widget.bind("<Button-1>",lambda _,key=key:self.select_card(key))
            self.table._list_context.card(card,key)
            self._cards[key]=(cover,title,artist,details)
        if len(rows)<len(self.rows):
            ttk.Button(self.cards,text=tr("Mostrar mais"),command=self.more_cards).grid(row=len(rows),column=0,pady=10)
        self.app.theme_manager.walk(self.cards)
        self.highlight_cards()
        def worker():
            for key,row in rows:
                if self._closed or generation!=self._generation:return
                try:data=history_details(row['path'])
                except Exception:data={'note':'Não foi possível ler este arquivo.'}
                self._events.put((generation,key,data))
        threading.Thread(target=worker,daemon=True).start()

    def resize_cards(self,event):
        if self.app.history_view.get() != "Completa":
            from settings_scroll import scroll_page
            return scroll_page(event)
        sizes=("Pequeno","Médio","Grande")
        if event.delta:
            index=sizes.index(self.app.history_card_size.get())
            target=max(0,min(len(sizes)-1,index+(1 if event.delta>0 else -1)))
            if target!=index:self.app.history_card_size.set(sizes[target])
        return "break"

    def more_cards(self):
        self._limit += 30
        self.render_cards()

    def select_card(self,key):
        self.table.selection_set(key)
        self._selected_card.set(key)
        self.highlight_cards()

    def toggle_card(self,key):
        if key in self.table.selection():self.table.selection_remove(key)
        else:self.table.selection_add(key)
        self.highlight_cards()

    def edit_batch(self):
        from audio_library import AUDIO_TYPES
        paths=[self.rows[key]['path'] for key in self.table.selection() if key in self.rows and Path(self.rows[key]['path']).is_file() and Path(self.rows[key]['path']).suffix.lower() in AUDIO_TYPES]
        self.app.metadata_page.open_batch(paths)

    def highlight_cards(self):
        for key,widgets in self._cards.items():
            selected=key in self.table.selection()
            if key in getattr(self,'_card_checks',{}):self._card_checks[key].set(selected)
            card=widgets[0].master
            card.configure(style="HistorySelected.TFrame" if selected else "Card.TFrame")
            for child in card.winfo_children():
                if isinstance(child,ttk.Label):
                    muted=child not in widgets[:3]
                    child.configure(style=("HistorySelectedMuted.TLabel" if muted else "HistorySelected.TLabel") if selected else ("CardMuted.TLabel" if muted else "Card.TLabel"))
                elif isinstance(child,ttk.Frame):child.configure(style="HistorySelected.TFrame" if selected else "Card.TFrame")

    def card_action(self,key,action):
        self.select_card(key)
        action()

    def poll_cards(self):
        from history_details import detail_lines
        for _ in range(30):
            try:generation,key,data=self._events.get_nowait()
            except queue.Empty:break
            if generation!=self._generation or key not in self._cards:continue
            cover,title,artist,details=self._cards[key]
            if data.get('title'):title.configure(text=data['title'])
            artist.configure(text='; '.join(data.get('artists') or []) or tr('Artista não informado'))
            details.configure(text=detail_lines(data, translate=tr))
            if data.get('cover'):
                import base64,io
                from PIL import Image,ImageTk
                side={"Pequeno":80,"Médio":140,"Grande":240}[self.app.history_card_size.get()]
                with Image.open(io.BytesIO(base64.b64decode(data['cover']))) as image:
                    image.thumbnail((side,side))
                    cover._history_image=ImageTk.PhotoImage(image.copy(),master=cover)
                cover.configure(image=cover._history_image,text=tr(""),width=0)
        if not self._closed:self._poll_id=self.after(100,self.poll_cards)

    def current(self):
        selected = self.table.selection()
        if not selected:
            return None
        path = Path(self.rows[selected[0]]["path"])
        if not path.is_file():
            self.status.set("O arquivo foi movido ou removido do computador.")
            return None
        return path

    def open(self, folder=False):
        path = self.current()
        if not path:
            return
        path = path.parent if folder else path
        try:
            if os.name == "nt":
                os.startfile(str(path))
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])
        except OSError as exc:
            self.status.set(str(exc))

    def effects(self):
        path = self.current()
        if path:
            self.app.effects_page.use_file(path)
            self.app.pages.select(self.app.effects_page)

    def edit_audio(self):
        path=self.current()
        if path:
            try:
                self.app.metadata_page.open_file(path)
                self.app.pages.select(self.app.metadata_page)
            except Exception as error:self.status.set(str(error))

    def clear(self):
        if messagebox.askyesno(tr("Histórico"), tr("Remover os registros do histórico? Os arquivos serão preservados."), parent=self.app):
            self.app.library.clear_history()
            self.refresh()
