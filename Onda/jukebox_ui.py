"""Desktop Jukebox workspace, reusing catalog search and the shared PCM engine."""
import io,math,queue,threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog
from i18n import tr
from i18n_tk import display_var
from jukebox import prepare,fetch_audio,Session,Cancelled,RATE

class JukeboxPane(ttk.Frame):
    def __init__(self,parent,app,use_file):
        super().__init__(parent);self.app=app;self.use_file=use_file
        self.source='';self.model=None;self.records=[];self.events=queue.Queue();self.generation=0;self.closed=False
        self.cancelled=threading.Event();self.paused=threading.Event();self.computing=False;self.playing=False
        self.params=(45,35,80,False);self.current=0;self.photo=None;self.seeks=queue.SimpleQueue()
        self.query=tk.StringVar();self.status=tk.StringVar(value='Abra um arquivo ou pesquise uma música para começar.')
        self.title=tk.StringVar(value='Escolha sua música.');self.stats=tk.StringVar(value='Tempo ouvido: 0:00 · Saltos: 0')
        self.variation=tk.DoubleVar(value=45);self.smooth=tk.DoubleVar(value=35);self.volume=tk.DoubleVar(value=80)
        self.columnconfigure(0,weight=1)
        search=ttk.Frame(self);search.grid(row=0,column=0,sticky='ew',pady=(8,10));search.columnconfigure(1,weight=1)
        ttk.Button(search,text=tr('Abrir arquivo'),command=self.choose).grid(row=0,column=0,padx=(0,8))
        self.entry=ttk.Entry(search,textvariable=self.query);self.entry.grid(row=0,column=1,sticky='ew');self.entry.bind('<Return>',lambda _:self.search())
        ttk.Button(search,text=tr('Pesquisar'),style='Accent.TButton',command=self.search).grid(row=0,column=2,padx=(8,0))
        ttk.Label(self,text=tr('Pesquise uma música ou cole um link'),style='Muted.TLabel').grid(row=1,column=0,sticky='w')
        self.results=ttk.Treeview(self,columns=('title','artist'),show='headings',height=4,selectmode='browse')
        self.results.heading('title',text=tr('Música'));self.results.heading('artist',text=tr('Artista'));self.results.bind('<Double-1>',lambda _:self.load_selected())
        self.load=ttk.Button(self,text=tr('Usar música selecionada'),command=self.load_selected)
        strip=ttk.Frame(self,style='Card.TFrame',padding=10);strip.grid(row=4,column=0,sticky='ew',pady=(10,8));strip.columnconfigure(1,weight=1)
        self.cover=ttk.Label(strip,text='♪',font=('Segoe UI',28),style='Card.TLabel');self.cover.grid(row=0,column=0,rowspan=2,padx=(0,12))
        ttk.Label(strip,textvariable=self.title,style='Card.TLabel',font=('Segoe UI',12,'bold'),wraplength=650).grid(row=0,column=1,sticky='w')
        ttk.Label(strip,textvariable=display_var(self.status),style='CardMuted.TLabel',wraplength=650).grid(row=1,column=1,sticky='w')
        self.body=ttk.Frame(self);self.body.grid(row=5,column=0,sticky='nsew');self.body.columnconfigure(0,weight=1);self.body.columnconfigure(1,weight=1)
        self.canvas=tk.Canvas(self.body,width=320,height=320,highlightthickness=0);self.canvas.grid(row=0,column=0,sticky='nsew',padx=(0,10));self.canvas.bind('<Configure>',lambda _:self.draw());self.canvas.bind('<Button-1>',self.seek_point)
        self.controls=ttk.Frame(self.body,style='Card.TFrame',padding=14);self.controls.grid(row=0,column=1,sticky='nsew')
        ttk.Label(self.controls,text=tr('Como a música se transforma'),font=('Segoe UI',12,'bold'),style='Card.TLabel').pack(anchor='w',pady=(0,12))
        for label,var,left,right in [('Variação',self.variation,'Mais fiel','Mais saltos'),('Transição suave',self.smooth,'Curta','Longa')]:
            ttk.Label(self.controls,text=tr(label),style='Card.TLabel').pack(anchor='w')
            ttk.Scale(self.controls,from_=0,to=100,variable=var,command=lambda _:self.update_params()).pack(fill='x',pady=6)
            guide=ttk.Frame(self.controls,style='Card.TFrame');guide.pack(fill='x',pady=(0,14))
            ttk.Label(guide,text=tr(left),style='CardMuted.TLabel').pack(side='left');ttk.Label(guide,text=tr(right),style='CardMuted.TLabel').pack(side='right')
        ttk.Label(self.controls,text=tr('A análise fica salva para os próximos usos.'),style='CardMuted.TLabel',wraplength=280).pack(anchor='w',pady=8)
        ttk.Label(self.controls,text=tr('Os saltos dependem de trechos compatíveis. A detecção de batidas é uma estimativa.'),style='CardMuted.TLabel',wraplength=280).pack(anchor='w')
        actions=ttk.Frame(self);actions.grid(row=6,column=0,sticky='ew',pady=12)
        self.play_button=ttk.Button(actions,text=tr('Reproduzir'),style='Accent.TButton',command=self.play_pause,state='disabled');self.play_button.pack(side='left')
        ttk.Button(actions,text=tr('Parar'),command=self.stop).pack(side='left',padx=8)
        self.normal=ttk.Button(actions,text=tr('Reprodução normal'),command=self.toggle_normal);self.normal.pack(side='left')
        ttk.Label(actions,text=tr('Volume')).pack(side='left',padx=(12,4));ttk.Scale(actions,from_=0,to=100,variable=self.volume,command=lambda _:self.update_params()).pack(side='left',fill='x',expand=True)
        ttk.Label(self,textvariable=display_var(self.stats),style='Muted.TLabel').grid(row=7,column=0,sticky='w')
        self.bar=ttk.Progressbar(self,maximum=100);self.bar.grid(row=8,column=0,sticky='ew',pady=6);self.bar.grid_remove()
        self.body.bind('<Configure>',self.layout);self.timer=self.after(80,self.poll);self.last_colors=None
    @property
    def busy(self):return self.computing or self.playing
    def layout(self,event):
        width=min(event.width,max(1,self.winfo_toplevel().winfo_width()-64))
        if width<max(660,self.controls.winfo_reqwidth()+330):self.controls.grid(row=1,column=0,columnspan=2,sticky='ew');self.canvas.grid(row=0,column=0,columnspan=2,sticky='ew')
        else:self.controls.grid(row=0,column=1,columnspan=1,sticky='nsew');self.canvas.grid(row=0,column=0,columnspan=1,sticky='nsew')
    def config(self):
        return {'ffmpeg':self.app.ffmpeg.get(),'cookies_file':self.app.youtube_cookies.get(),'spotify_client_id':self.app.spotify_client_id.get(),'spotify_client_secret':self.app.spotify_client_secret.get(),'youtube_cookies_file':self.app.youtube_cookies.get()}
    def choose(self):
        path=filedialog.askopenfilename(parent=self.app,title=tr('Abrir arquivo'),filetypes=[(tr('Áudio'),'*.mp3 *.m4a *.flac *.wav *.ogg *.opus *.aac *.webm'),(tr('Todos os arquivos'),'*.*')])
        if path:self.use_file(path,'jukebox')
    def set_source(self,path):
        if path==self.source and self.model:return
        self.results.grid_remove();self.load.grid_remove()
        self.stop_preview();self.source=str(path);self.model=None;self.title.set(Path(path).stem);self.analyse()
    def task(self,function):
        self.stop_preview();self.generation+=1;generation=self.generation;cancel=threading.Event();self.cancelled=cancel;self.computing=True;self.model=None;self.play_button.configure(state='disabled');self.bar.grid();self.bar.configure(value=0);self.stats.set('Tempo ouvido: 0:00 · Saltos: 0')
        def emit(kind,**values):self.events.put((generation,kind,values))
        def worker():
            try:emit('result',value=function(cancel,lambda value:emit('progress',value=value)))
            except Cancelled:emit('cancelled')
            except Exception as error:
                message=str(error)
                if 'sign in to confirm' in message.lower():
                    message=tr('O YouTube pediu verificação. Importe cookies válidos em Configurações → Contas → Importar cookies do YouTube e tente novamente. Você também pode abrir um arquivo local.')
                emit('error',message=message)
            finally:emit('idle')
        threading.Thread(target=worker,daemon=True).start()
    def analyse(self):
        source,folder=self.source,self.app.ffmpeg.get();self.status.set('Analisando ritmo e trechos semelhantes…')
        def analyse(cancel,progress):
            result=prepare(source,folder,cancel.is_set,progress)
            from audio_library import cover_preview
            import base64
            cover=cover_preview(source)
            if cover:result['_cover']=base64.b64decode(cover)
            return result
        self.task(analyse)
    def search(self):
        query=self.query.get().strip()
        if not query:return
        self.status.set('Pesquisando…');config=self.config();account=self.app.spotify_account
        if query.startswith(('https://','http://')):
            from metadata import is_streaming_link
            if not is_streaming_link(query):
                self.task(lambda cancel,progress:{'tracks':[{'title':query,'artists':[],'source_url':query,'_jukebox_direct':True}]});return
        def search(cancel,progress):
            from music_search import search_music
            from metadata import MetadataClient
            client=MetadataClient(config['spotify_client_id'],config['spotify_client_secret'])
            try:return {'tracks':search_music(client,query,self.app_provider,account=account,limit=12,cancelled=cancel.is_set,automatic=True)['tracks']}
            finally:client.close()
        self.app_provider=self.app.catalog_provider.get();self.task(search)
    def load_selected(self):
        selected=self.results.selection()
        if not selected:return
        record=dict(self.records[int(selected[0])]);self.title.set(' — '.join([', '.join(record.get('artists',[])),record.get('title','')]));self.status.set('Obtendo áudio para análise…');config=self.config()
        self.results.grid_remove();self.load.grid_remove()
        def load(cancel,progress):
            direct=record.get('_jukebox_direct')
            result=fetch_audio(dict(config,url=record['source_url']) if direct else config,None if direct else record,cancel.is_set,progress)
            if result.get('cover_url') and not cancel.is_set():
                try:
                    from catalog_ui import cover_png
                    result['_cover']=cover_png(result['cover_url'])
                except Exception:pass
            return result
        self.task(load)
    def seek_point(self,event):
        if not self.model or self.computing:return
        w,h=max(200,self.canvas.winfo_width()),max(200,self.canvas.winfo_height())
        dx,dy=event.x-w/2,event.y-h/2;radius=min(w,h)*.39
        if abs(math.hypot(dx,dy)-radius)>18:return
        n=len(self.model['neighbors'])
        self.current=round(((math.atan2(dy,dx)+math.pi/2)%(2*math.pi))/(2*math.pi)*n)%n
        self.seeks.put(self.current);self.draw()

    def update_params(self):
        self.params=(self.variation.get(),self.smooth.get(),self.volume.get(),self.params[3])
        self.draw()
    def toggle_normal(self):
        a,b,c,normal=self.params;self.params=(a,b,c,not normal);self.normal.configure(text=tr('Jukebox infinito' if not normal else 'Reprodução normal'));self.draw()
    def play_pause(self):
        if self.playing:
            if self.paused.is_set():self.paused.clear();self.play_button.configure(text=tr('Pausar'));self.status.set('Reproduzindo…')
            else:self.paused.set();self.play_button.configure(text=tr('Retomar'));self.status.set('Pausado.')
            return
        if not self.model or self.computing:return
        if not (Path(self.model['cache'])/'analysis.json').is_file():
            self.model=None;self.play_button.configure(state='disabled');self.status.set('O cache foi limpo. Abra ou pesquise a música novamente.');return
        self.app.catalog_page.stop_preview();self.app.metadata_page.stop_preview()
        self.cancelled=threading.Event();cancel=self.cancelled;self.paused.clear();self.playing=True;self.stats.set('Tempo ouvido: 0:00 · Saltos: 0');self.play_button.configure(text=tr('Pausar'));self.status.set('Reproduzindo…');generation=self.generation;cache=self.model['cache']
        initial=self.current;self.seeks=queue.SimpleQueue()
        def worker():
            session=output=None
            try:
                from jukebox_audio import PcmOutput
                session=Session(cache);session.seek(initial);output=PcmOutput()
                while not cancel.is_set():
                    target=None
                    while not self.seeks.empty():target=self.seeks.get()
                    if target is not None:session.seek(target)
                    part=session.chunk(*self.params)
                    output.write(part['pcm'],cancel.is_set,self.paused.is_set)
                    self.events.put((generation,'position',dict(index=part['index'],elapsed=output.played/RATE,jumps=part['jumps'])))
            except Cancelled:pass
            except Exception as error:self.events.put((generation,'error',{'message':str(error)}))
            finally:
                if output:output.close()
                if session:session.close()
                self.events.put((generation,'stopped',{}))
        threading.Thread(target=worker,daemon=True).start()
    def stop(self):
        self.stop_preview();self.status.set('Reprodução encerrada.')
    def stop_preview(self):
        self.generation+=1;self.cancelled.set();self.paused.clear();self.playing=False;self.computing=False
        self.play_button.configure(text=tr('Reproduzir'),state='normal' if self.model else 'disabled');self.bar.grid_remove();self.current=0
    cancel=stop_preview
    def draw(self):
        if self.closed:return
        colors=getattr(self.app.theme_manager,'colors',None) or {};bg=colors.get('surface',colors.get('bg','#ffffff'));accent=colors.get('accent','#bd2738');muted=colors.get('muted','#8b9bae');text=colors.get('text','#17202e')
        canvas=self.canvas;canvas.configure(bg=bg);canvas.delete('all');w,h=max(200,canvas.winfo_width()),max(200,canvas.winfo_height());cx,cy=w/2,h/2;radius=min(w,h)*.39
        n=len(self.model['neighbors']) if self.model else 64
        def point(index):
            angle=index/n*2*math.pi-math.pi/2;return cx+math.cos(angle)*radius,cy+math.sin(angle)*radius
        from appearance import blend
        variation,smooth,_,normal=self.params
        strength=0 if normal else max(0,min(1,variation/100))
        ink=blend(bg,accent,.15+.55*strength) if colors.get('mode')!='Alto contraste' else accent
        if self.model:
            links=[(i,j) for i,row in enumerate(self.model['neighbors']) for j in row]
            # Visual density represents jump frequency, without inventing new connections.
            limit=math.ceil(90*strength)
            visible=links[::max(1,len(links)//max(1,limit))][:limit]
            for i,j in visible:
                a,b=point(i),point(j);canvas.create_line(*a,cx,cy,*b,smooth=True,fill=ink,width=1+smooth/100,tags='jump-link')
        step=max(1,n//150)
        hot={j for i,j in visible if i==self.current} if self.model else set()
        for i in range(0,n,step):
            x,y=point(i);size=3 if i!=self.current else 7;canvas.create_oval(x-size,y-size,x+size,y+size,fill=accent if i==self.current or i in hot else muted,outline='')
        x,y=point(self.current);canvas.create_oval(x-6,y-6,x+6,y+6,fill=accent,outline=bg)
        mask=radius*.38
        canvas.create_oval(cx-mask,cy-mask,cx+mask,cy+mask,fill=bg,outline='')
        canvas.create_text(cx,cy-12,text=tr('Jukebox infinito'),fill=text,font=('Segoe UI',13,'bold'));canvas.create_text(cx,cy+24,text='∞',fill=accent,font=('Segoe UI',30))
    def poll(self):
        if self.closed:return
        for _ in range(50):
            try:generation,kind,value=self.events.get_nowait()
            except queue.Empty:break
            if generation!=self.generation:continue
            if kind=='progress':self.bar.configure(value=value['value'])
            elif kind=='result':
                result=value['value'];self.bar.grid_remove()
                if 'tracks' in result:
                    self.records=result['tracks'];self.results.delete(*self.results.get_children())
                    for i,record in enumerate(self.records):self.results.insert('','end',iid=str(i),values=(record['title'],', '.join(record.get('artists',[]))))
                    if self.records:self.results.grid(row=2,column=0,sticky='ew',pady=6);self.load.grid(row=3,column=0,sticky='w');self.status.set('Escolha uma música nos resultados.')
                    else:self.status.set('Nenhuma música encontrada.')
                else:
                    self.model=result;self.source=result['source'];self.title.set(result['title']);
                    self.photo=None;self.cover.configure(image='',text='♪')
                    if result.get('_cover'):
                        from PIL import Image,ImageTk
                        with Image.open(io.BytesIO(result['_cover'])) as picture:
                            picture.thumbnail((64,64));self.photo=ImageTk.PhotoImage(picture,master=self)
                        self.cover.configure(image=self.photo,text='')
                    self.status.set('Análise concluída.' if result['links'] else 'Sem saltos compatíveis: a faixa será repetida normalmente.');self.bar.configure(value=100);self.play_button.configure(state='normal');self.draw()
            elif kind=='idle':self.computing=False
            elif kind=='position':self.current=value['index'];minutes,seconds=divmod(int(value['elapsed']),60);self.stats.set(tr('Tempo ouvido: {time} · Saltos: {count}').replace('{time}',f'{minutes}:{seconds:02}').replace('{count}',str(value['jumps'])));self.draw()
            elif kind=='error':self.bar.grid_remove();self.status.set(value['message']);self.playing=False;self.play_button.configure(text=tr('Reproduzir'))
            elif kind=='stopped':self.playing=False;self.play_button.configure(text=tr('Reproduzir'))
        colors=self.app.theme_manager.colors
        if colors!=self.last_colors:
            self.last_colors=colors
            self.draw()
        self.timer=self.after(80,self.poll)
    def shutdown(self):
        self.closed=True;self.stop_preview()
        if self.timer:self.after_cancel(self.timer);self.timer=None
