"""Desktop Jukebox workspace, reusing catalog search and the shared PCM engine."""
import io,math,queue,threading
from collections import deque
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
        self.params=(45,35,80,False);self.current=0;self.marker_position=None;self.beat_phase=0.;self.flow=[];self.photo=None;self.seeks=queue.SimpleQueue()
        self.query=tk.StringVar();self.status=tk.StringVar(value='Abra um arquivo ou pesquise uma música para começar.')
        self.artist=tk.StringVar();self.album=tk.StringVar();self.title=tk.StringVar(value='Escolha sua música.');self.stats=tk.StringVar(value='Tempo ouvido: 0:00 · Saltos: 0')
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
        from jukebox_equalizer import clean as clean_equalizer
        self.equalizer=clean_equalizer(app.jukebox_equalizer.get())
        app.jukebox_equalizer.trace_add("write",lambda *_:setattr(self,"equalizer",clean_equalizer(app.jukebox_equalizer.get())))
        strip=ttk.Frame(self,style='Card.TFrame',padding=10);strip.grid(row=4,column=0,sticky='ew',pady=(10,8));strip.columnconfigure(1,weight=1)
        self.cover=ttk.Label(strip,text='♪',font=('Segoe UI',28),style='Card.TLabel');self.cover.grid(row=0,column=0,rowspan=4,padx=(0,12))
        ttk.Label(strip,textvariable=self.title,style='Card.TLabel',font=('Segoe UI',12,'bold'),wraplength=650).grid(row=0,column=1,sticky='w')
        self.artist_label=ttk.Label(strip,textvariable=self.artist,style='CardMuted.TLabel',wraplength=650)
        self.artist_label.grid(row=1,column=1,sticky='w',pady=(3,0));self.artist_label.grid_remove()
        self.album_label=ttk.Label(strip,textvariable=self.album,style='CardMuted.TLabel',wraplength=650)
        self.album_label.grid(row=2,column=1,sticky='w',pady=(3,0));self.album_label.grid_remove()
        ttk.Label(strip,textvariable=display_var(self.status),style='CardMuted.TLabel',wraplength=650).grid(row=3,column=1,sticky='w',pady=(3,0))
        ttk.Button(strip,text=tr('Equalizador'),style='Accent.TButton',command=self.open_equalizer).grid(row=3,column=2,sticky='e',padx=(12,0))
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
        ttk.Label(actions,text=tr('Volume')).pack(side='left',padx=(12,4));ttk.Scale(actions,from_=0,to=100,variable=self.volume,command=lambda _:self.update_params()).pack(side='left',fill='x',expand=True,padx=(0,14))
        ttk.Label(self,textvariable=display_var(self.stats),style='Muted.TLabel').grid(row=7,column=0,sticky='w')
        self.bar=ttk.Progressbar(self,maximum=100);self.bar.grid(row=8,column=0,sticky='ew',pady=6);self.bar.grid_remove()
        self.body.bind('<Configure>',self.layout);self.timer=self.after(80,self.poll);self.last_colors=None;self.media_controls=None;self.media_failed=False
    def open_equalizer(self):
        from jukebox_equalizer_ui import EqualizerWindow
        window=getattr(self,"equalizer_window",None)
        if window is not None and window.winfo_exists():window.lift();return
        self.equalizer_window=EqualizerWindow(self.app)
    @property
    def busy(self):return self.computing or self.playing
    def layout(self,event):
        width=min(event.width,max(1,self.winfo_toplevel().winfo_width()-64))
        stacked=width<max(660,self.controls.winfo_reqwidth()+330)
        if getattr(self,'_stacked',None)==stacked:return
        self._stacked=stacked
        if stacked:self.controls.grid(row=1,column=0,columnspan=2,sticky='ew');self.canvas.grid(row=0,column=0,columnspan=2,sticky='ew')
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
        self.artist.set('');self.album.set('');self.artist_label.grid_remove();self.album_label.grid_remove()
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
            from audio_library import read_audio
            try:
                tags=read_audio(source);result['media_title']=tags.get('title','');result['media_artist']=', '.join(tags.get('artists',[]));result['album']=tags.get('album') or ''
            except (ValueError,OSError):pass
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
        self.flow=[];self.marker_position=float(self.current);self.beat_phase=0.;self.seeks.put(self.current);self.draw()

    def set_track_info(self,record):
        self.title.set(record.get('media_title') or record['title'])
        for variable,label,key in ((self.artist,self.artist_label,'media_artist'),(self.album,self.album_label,'album')):
            text=record.get(key) or '';variable.set(text)
            label.grid() if text else label.grid_remove()

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
        initial=self.current;self.flow=[];self.seeks=queue.SimpleQueue()
        def worker():
            session=output=None
            try:
                from jukebox_audio import PcmOutput
                session=Session(cache);session.seek(initial);timeline=deque();submitted=0;heard_jumps=0
                def progress(played):
                    nonlocal heard_jumps
                    edges=[];index=initial
                    while timeline and timeline[0][0]<=played:
                        _,heard=timeline.popleft();edges.append((heard['index'],heard['next']));heard_jumps=heard['jumps'];index=heard['next']
                    phase=0.
                    if timeline:
                        end,part=timeline[0];frames=len(part['pcm'])//4;index=part['index']
                        phase=max(0.,min(1.,(played-(end-frames))/max(1,frames)))
                    self.events.put((generation,'position',dict(index=index,phase=phase,edges=edges,elapsed=played/RATE,jumps=heard_jumps)))
                output=PcmOutput(progress=progress)
                while not cancel.is_set():
                    target=None
                    while not self.seeks.empty():target=self.seeks.get()
                    if target is not None:session.seek(target)
                    part=session.chunk(*self.params,equalizer=self.equalizer)
                    submitted+=len(part['pcm'])//4;timeline.append((submitted,part))
                    output.write(part['pcm'],cancel.is_set,self.paused.is_set)
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
        self.play_button.configure(text=tr('Reproduzir'),state='normal' if self.model else 'disabled');self.bar.grid_remove();self.current=0;self.marker_position=None;self.beat_phase=0.;self.flow=[]
    cancel=stop_preview
    def draw(self):
        if self.closed:return
        colors=getattr(self.app.theme_manager,'colors',None) or {};bg=colors.get('surface',colors.get('bg','#ffffff'));accent=colors.get('accent','#bd2738');muted=colors.get('muted','#8b9bae');text=colors.get('text','#17202e')
        canvas=self.canvas;w,h=max(200,canvas.winfo_width()),max(200,canvas.winfo_height());cx,cy=w/2,h/2;radius=min(w,h)*.39
        key=(id(self.model),w,h,bg,accent,muted,text,self.params[0],self.params[1],self.params[3])
        if getattr(self,'_graph_key',None)==key:
            self.move_marker();return
        self._graph_key=key;self._graph_nodes={};self._graph_hot=set();self._flow_key=None
        canvas.configure(bg=bg);canvas.delete('all')
        n=len(self.model['neighbors']) if self.model else 64
        def point(index):
            angle=index/n*2*math.pi-math.pi/2;return cx+math.cos(angle)*radius,cy+math.sin(angle)*radius
        from appearance import blend
        variation,smooth,_,normal=self.params
        strength=0 if normal else .15+.85*max(0,min(1,variation/100))
        ink=blend(bg,accent,.18+.22*strength) if colors.get('mode')!='Alto contraste' else accent
        if self.model:
            links=[(i,j) for i,row in enumerate(self.model['neighbors']) for j in row]
            # Visual density represents jump frequency, without inventing new connections.
            limit=math.ceil(90*strength)
            visible=links[::max(1,len(links)//max(1,limit))][:limit]
            for i,j in visible:
                a,b=point(i),point(j);canvas.create_line(*a,cx,cy,*b,smooth=True,fill=ink,width=1+smooth/100,tags='jump-link')
        step=max(1,n//150)
        for i in range(0,n,step):
            x,y=point(i);self._graph_nodes[i]=canvas.create_oval(x-3,y-3,x+3,y+3,fill=muted,outline='')
        self._graph_marker=canvas.create_oval(0,0,12,12,fill=accent,outline=bg)
        self.move_marker()
    def move_marker(self):
        # Playback moves only the marker and changed node colors, not the entire graph.
        canvas=self.canvas;key=self._graph_key;w,h=key[1:3];accent,muted=key[4:6]
        n=len(self.model['neighbors']) if self.model else 64
        position=self.current if self.marker_position is None else self.marker_position
        angle=position/n*2*math.pi-math.pi/2;radius=min(w,h)*.39
        x,y=w/2+math.cos(angle)*radius,h/2+math.sin(angle)*radius
        pulse=6+2*(1-self.beat_phase)**3 if self.playing else 6
        canvas.coords(self._graph_marker,x-pulse,y-pulse,x+pulse,y+pulse)
        hot={self.current}
        for index in self._graph_hot-hot:
            if index in self._graph_nodes:canvas.itemconfigure(self._graph_nodes[index],fill=muted)
        for index in hot-self._graph_hot:
            if index in self._graph_nodes:canvas.itemconfigure(self._graph_nodes[index],fill=accent)
        self._graph_hot=hot
        flow_key=tuple(self.flow)
        if self._flow_key==flow_key:return
        self._flow_key=flow_key;canvas.delete('flow')
        from appearance import blend
        for k,(start,end) in enumerate(self.flow):
            ink=blend(key[3],accent,.75+.25*(k+1)/len(self.flow))
            if end==(start+1)%n:
                canvas.create_arc(w/2-radius,h/2-radius,w/2+radius,h/2+radius,start=90-start/n*360,extent=-360/n,style='arc',outline=ink,width=4,tags='flow')
            else:
                def point(i):
                    angle=i/n*2*math.pi-math.pi/2;return w/2+math.cos(angle)*radius,h/2+math.sin(angle)*radius
                canvas.create_line(*point(start),w/2,h/2,*point(end),smooth=True,fill=ink,width=3.5,arrow='last',arrowshape=(12,15,5),tags='flow')
        canvas.tag_raise(self._graph_marker)

    def poll(self):
        if self.closed:return
        redraw=False
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
                    self.model=result;self.source=result['source'];self.set_track_info(result)
                    self.photo=None;self.cover.configure(image='',text='♪')
                    if result.get('_cover'):
                        from PIL import Image,ImageTk
                        with Image.open(io.BytesIO(result['_cover'])) as picture:
                            picture.thumbnail((88,88));self.photo=ImageTk.PhotoImage(picture,master=self)
                        self.cover.configure(image=self.photo,text='')
                    self.status.set('Análise concluída.' if result['links'] else 'Sem saltos compatíveis: a faixa será repetida normalmente.');self.bar.configure(value=100);self.play_button.configure(state='normal');redraw=True
            elif kind=='idle':self.computing=False
            elif kind=='position':
                self.current=value['index'];self.beat_phase=value.get('phase',0.);self.marker_position=self.current+self.beat_phase
                edges=value.get('edges',[])
                if 'edge' in value:edges=edges+[value['edge']]
                self.flow=(self.flow+edges)[-24:]
                minutes,seconds=divmod(int(value['elapsed']),60);self.stats.set(tr('Tempo ouvido: {time} · Saltos: {count}').replace('{time}',f'{minutes}:{seconds:02}').replace('{count}',str(value['jumps'])));redraw=True
            elif kind=='error':self.bar.grid_remove();self.status.set(value['message']);self.playing=False;self.play_button.configure(text=tr('Reproduzir'))
            elif kind=='stopped':self.playing=False;self.play_button.configure(text=tr('Reproduzir'))
        colors=self.app.theme_manager.colors
        if colors!=self.last_colors:
            self.last_colors=colors
            redraw=True
        if redraw and self.winfo_ismapped():self.draw()
        self.sync_media()
        self.timer=self.after(40 if self.playing and self.winfo_ismapped() else 80 if self.winfo_ismapped() or self.busy else 500,self.poll)
    def sync_media(self):
        if self.playing and self.media_controls is None and not self.media_failed:
            try:
                from windows_media import MediaControls
                self.media_controls=MediaControls(self.app)
            except (OSError,AttributeError) as error:
                self.media_failed=True
                if hasattr(self.app,'write_log'):self.app.write_log(str(error))
        if self.media_controls is None:return
        for _ in range(8):
            try:button=self.media_controls.events.get_nowait()
            except queue.Empty:break
            if button==0 and self.playing and self.paused.is_set():self.play_pause()
            elif button==1 and self.playing and not self.paused.is_set():self.play_pause()
            elif button==2 and self.playing:self.stop()
        model=self.model or {}
        try:self.media_controls.update(model.get('media_title') or self.title.get(),model.get('media_artist') or tr('Jukebox infinito'),self.playing,self.paused.is_set())
        except OSError as error:
            self.media_controls.close();self.media_controls=None;self.media_failed=True
            if hasattr(self.app,'write_log'):self.app.write_log(str(error))

    def shutdown(self):
        self.closed=True;self.stop_preview()
        if self.media_controls:self.media_controls.close();self.media_controls=None
        if self.timer:self.after_cancel(self.timer);self.timer=None
