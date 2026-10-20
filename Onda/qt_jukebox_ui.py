"""Qt adapter for the existing Jukebox engine; workers never touch QML objects."""
import base64
from collections import deque
import json
import math
import os
from pathlib import Path
import queue
import threading
import time
import uuid
from types import SimpleNamespace

from PySide6.QtCore import QObject, Property, Signal, Slot, Qt, QTimer, QUrl
from jukebox import Session, prepare, fetch_audio, Cancelled, RATE
from jukebox_equalizer import clean, presets, preset_name
from preferences import PreferenceStore
from i18n import tr, set_language

class JukeboxBridge(QObject):
    changed=Signal()
    queueChanged=Signal()
    positionChanged=Signal()
    graphChanged=Signal()
    appearanceChanged=Signal()
    equalizerChanged=Signal()
    _event=Signal(int,str,object)

    def __init__(self,store=None,parent=None):
        super().__init__(parent)
        self.store=store or PreferenceStore()
        try:self.preferences=self.store.load() or {}
        except (ValueError,OSError):self.preferences={}
        set_language(self.store.load_language())
        self.closed=False;self.revision=0;self.cancelled=threading.Event();self.paused=threading.Event()
        from playback_controls import SleepTimer
        self.sleep=SleepTimer();self.playlist=[];self.queue_index=-1;self.track_minutes=0;self.autoplay_revision=None;self.request_number=0;self.lookup_cancelled=threading.Event();self.task_is_lookup=False
        self.clock_timer=QTimer(self);self.clock_timer.setInterval(500);self.clock_timer.timeout.connect(self.tick_sleep)
        self.workers=[];self.seeks=queue.SimpleQueue();self.model=None;self.records=[]
        self._state={'title':tr('Escolha sua música.'),'artist':'','album':'','cover':'','status':tr('Abra um arquivo ou pesquise uma música para começar.'),'busy':False,'playing':False,'paused':False,'ready':False,'progress':0,'results':[]}
        self._graph_cache=None;self._position=0.;self._phase=0.;self._elapsed=0.;self._jumps=0;self.flow=[]
        self._params=(45.,35.,80.,False);self._equalizer=clean(self.preferences.get('jukebox_equalizer'))
        self.config_provider=None;self.window=None;self.media=None;self.media_failed=False
        self.media_timer=QTimer(self);self.media_timer.setInterval(100);self.media_timer.timeout.connect(self.sync_media)
        self.save_timer=QTimer(self);self.save_timer.setSingleShot(True);self.save_timer.setInterval(400);self.save_timer.timeout.connect(self.save_preferences)
        self._pending={};self._event.connect(self.handle_event,Qt.ConnectionType.QueuedConnection)

    @Property('QVariantMap',notify=changed)
    def state(self):return dict(self._state)
    @Property('QVariantList',notify=queueChanged)
    def queuedTracks(self):return [dict(row,current=index==self.queue_index) for index,row in enumerate(self.playlist)]
    @Property('QVariantMap',notify=changed)
    def playback(self):
        return {'queue':self.queuedTracks,'current':self.queue_index,'trackMinutes':self.track_minutes,'sleepActive':self.sleep.deadline is not None,'remaining':math.ceil(self.sleep.remaining())}
    @Slot(int)
    def setSleep(self,minutes):
        if minutes<=0:self.sleep.cancel();self.clock_timer.stop()
        else:self.sleep.arm(min(720,minutes)*60);self.clock_timer.start()
        self.changed.emit()
    def tick_sleep(self):
        if self.sleep.deadline is not None and self.sleep.remaining()<=0:
            self.stop();self.update_state(status=tr('Temporizador encerrado. Reprodução parada suavemente.'))
        self.changed.emit()
    @Slot(int)
    def setTrackMinutes(self,minutes):self.track_minutes=max(0,min(60,minutes));self.changed.emit()
    def queue_info(self,entry,record,cover=''):
        artists=record.get('artists') or []
        entry.update(title=record.get('title') or entry['title'],artist=', '.join(artists) if isinstance(artists,list) else str(artists),album=record.get('album') or '',cover=cover or record.get('cover_url') or '',duration=int(record.get('duration') or float(record.get('duration_ms') or 0)/1000))
    @Slot('QVariantList')
    def enqueueFiles(self,urls):
        added=[]
        for value in urls:
            url=QUrl(value)
            if url.isLocalFile() and len(self.playlist)<500:
                entry={'id':uuid.uuid4().hex,'title':Path(url.toLocalFile()).stem,'source':url.toLocalFile(),'kind':'file','artist':'','album':'','cover':'','duration':0}
                self.playlist.append(entry);added.append(dict(entry))
        self.queueChanged.emit();self.changed.emit()
        def load():
            from audio_library import read_audio,cover_preview
            from mutagen import MutagenError
            for entry in added:
                if self.closed:return
                try:
                    record=read_audio(entry['source']);cover=cover_preview(entry['source']) or ''
                    self.emit(0,'queue_info',{'id':entry['id'],'record':record,'cover':('data:image/png;base64,'+cover) if cover else ''})
                except (OSError,ValueError,MutagenError):pass
        if added:self.start_worker(load)
    def enqueueRecord(self,record):
        if len(self.playlist)>=500:return
        entry={'id':uuid.uuid4().hex,'title':record['title'],'record':dict(record),'kind':'catalog'};self.queue_info(entry,record);self.playlist.append(entry);self.queueChanged.emit();self.changed.emit()
    @Slot(int)
    def enqueueResult(self,index):
        if 0<=index<len(self.records):self.enqueueRecord(self.records[index])
    @Slot(int)
    def removeQueued(self,index):
        if not 0<=index<len(self.playlist):return
        if index==self.queue_index and self._state['busy'] and self.autoplay_revision is not None:self.cancelOperation()
        self.playlist.pop(index)
        if index<self.queue_index:self.queue_index-=1
        elif index==self.queue_index:self.queue_index=-1
        self.queueChanged.emit();self.changed.emit()
    @Slot(int,int)
    def moveQueued(self,index,direction):
        target=index+direction
        if not 0<=index<len(self.playlist) or not 0<=target<len(self.playlist):return
        current=self.playlist[self.queue_index]['id'] if self.queue_index>=0 else None
        self.playlist.insert(target,self.playlist.pop(index));self.queue_index=next((i for i,row in enumerate(self.playlist) if row['id']==current),-1);self.queueChanged.emit();self.changed.emit()
    @Slot()
    def clearPlaybackQueue(self):
        if self._state['busy'] and self.autoplay_revision is not None:self.cancelOperation()
        self.playlist=[];self.queue_index=-1;self.queueChanged.emit();self.changed.emit()
    @Slot(int)
    def playQueued(self,index):
        if not 0<=index<len(self.playlist):return
        self.queue_index=index;entry=self.playlist[index]
        if entry['kind']=='file':self.openFile(QUrl.fromLocalFile(entry['source']))
        else:self.prepare_record(dict(entry['record']))
        self.queue_index=index;self.autoplay_revision=self.revision;self.queueChanged.emit();self.changed.emit()
    @Slot()
    def nextTrack(self):
        if self.queue_index+1<len(self.playlist):self.playQueued(self.queue_index+1)
        else:self.stop();self.update_state(status=tr('Fim da fila de reprodução.'))

    @Property(float,notify=positionChanged)
    def position(self):return self._position
    @Property(float,notify=positionChanged)
    def phase(self):return self._phase
    @Property(str,notify=positionChanged)
    def elapsed(self):
        minutes,seconds=divmod(int(self._elapsed),60);return f'{minutes:02}:{seconds:02}'
    @Property(int,notify=positionChanged)
    def jumps(self):return self._jumps
    @Property('QVariantMap',notify=graphChanged)
    def graph(self):
        if self._graph_cache is not None:return self._graph_cache
        rows=self.model['neighbors'] if self.model else [[] for _ in range(64)]
        variation,_,_,normal=self._params
        limit=0 if normal else math.ceil(90*(.15+.85*variation/100))
        links=[(i,j) for i,row in enumerate(rows) for j in row] if limit else []
        self._graph_cache={'count':len(rows),'links':links[::max(1,len(links)//max(1,limit))][:limit],'flow':list(self.flow)}
        return self._graph_cache
    @Property('QVariantMap',notify=appearanceChanged)
    def palette(self):
        from appearance import palette
        return palette(self.preferences.get('theme_mode','Claro'),self.preferences.get('theme_accent','Vermelho'),self.preferences.get('pure_black_separators',False))
    @Property(bool,notify=appearanceChanged)
    def animations(self):return self.preferences.get('qt_animations',True)
    @Property(float,notify=appearanceChanged)
    def fontScale(self):
        try:return max(.75,min(2,float(str(self.preferences.get('interface_font_size','100%')).rstrip('%'))/100))
        except (ValueError,TypeError):return 1.
    @Property(float,notify=appearanceChanged)
    def spacing(self):return {'Compacto':.85,'Confortável':1.15}.get(self.preferences.get('interface_spacing'),1.)
    @Property('QStringList',constant=True)
    def themes(self):return ['Claro','Escuro','Preto puro','Seguir o sistema','Alto contraste']
    @Property('QStringList',constant=True)
    def accents(self):
        from appearance import ACCENTS
        return list(ACCENTS)
    @Property(str,notify=appearanceChanged)
    def theme(self):return self.preferences.get('theme_mode','Claro')
    @Property(str,notify=appearanceChanged)
    def accent(self):return self.preferences.get('theme_accent','Vermelho')
    @Property('QVariantMap',notify=equalizerChanged)
    def equalizer(self):return self._equalizer
    @Property('QStringList',constant=True)
    def presetNames(self):return list(presets())
    @Property(str,notify=equalizerChanged)
    def presetName(self):return preset_name(self._equalizer)

    def update_graph(self):
        self._graph_cache=None;self.graphChanged.emit()

    @Slot(str,result=str)
    def translate(self,text):return tr(text)
    def update_state(self,**values):
        if any(self._state.get(k)!=v for k,v in values.items()):self._state.update(values);self.changed.emit()
    def persist(self,values):
        self.preferences.update(values);self._pending.update(values);self.save_timer.start()
    @Slot()
    def save_preferences(self):
        self.save_timer.stop()
        if not self._pending:return
        if not self.store.remember_enabled():self._pending.clear();return
        try:
            latest=self.store.load() or {};latest.update(self._pending);self.store.save(latest);self._pending.clear()
        except (ValueError,OSError):self.update_state(status=tr('Não foi possível salvar as configurações deste computador.'))
    @Slot(str,str,bool)
    def setAppearance(self,theme,accent,animations):
        if theme not in self.themes or accent not in self.accents:return
        self.persist({'theme_mode':theme,'theme_accent':accent,'qt_animations':animations});self.appearanceChanged.emit()
    @Slot(float,float,float,bool)
    def setParams(self,variation,smooth,volume,normal):
        values=tuple(max(0.,min(100.,v)) for v in (variation,smooth,volume))+(bool(normal),)
        graph_changed=values[0]!=self._params[0] or values[3]!=self._params[3]
        self._params=values
        if graph_changed:self.update_graph()
    @Slot(str)
    def applyPreset(self,name):
        if name in presets():self.set_equalizer(presets()[name])
    def set_equalizer(self,value):
        self._equalizer=clean(value);self.persist({'jukebox_equalizer':json.dumps(self._equalizer)});self.equalizerChanged.emit()
    @Slot(bool)
    def enableEqualizer(self,value):self.set_equalizer(dict(self._equalizer,enabled=value))
    @Slot(float)
    def setPreamp(self,value):self.set_equalizer(dict(self._equalizer,preamp=value))
    @Slot(int,float,float,float)
    def setBand(self,index,frequency,gain,q):
        if not 0<=index<10:return
        value=clean(self._equalizer);value['bands'][index]={'frequency':frequency,'gain':gain,'q':q};self.set_equalizer(value)
    @Slot()
    def resetEqualizer(self):self.set_equalizer(dict(clean(),enabled=self._equalizer['enabled']))

    def config(self):
        if self.config_provider is not None:return self.config_provider()
        from ffmpeg_runtime import existing_folder
        from credentials import CredentialStore,CredentialError
        try:credentials=CredentialStore().load() or ('','')
        except CredentialError:credentials=('','')
        return {'ffmpeg':str(existing_folder() or ''),'spotify_client_id':credentials[0],'spotify_client_secret':credentials[1]}
    def emit(self,revision,kind,value):
        if not self.closed:self._event.emit(revision,kind,value)
    def task(self,function,stop_current=True):
        if stop_current:self.stop(reset_timer=False);self.cancelled=threading.Event();cancel=self.cancelled
        else:self.lookup_cancelled.set();self.lookup_cancelled=threading.Event();cancel=self.lookup_cancelled
        self.task_is_lookup=not stop_current
        self.request_number+=1;request=self.request_number;revision=self.revision
        def post(kind,value):
            if request==self.request_number and not cancel.is_set():self.emit(revision,'lookup_error' if kind=='error' and not stop_current else kind,value)
        self.update_state(busy=True,progress=0,results=[])
        def worker():
            try:post('result',function(cancel,lambda v:post('progress',v)))
            except Cancelled:pass
            except Exception as error:post('error',str(error))
            finally:post('idle',None)
        self.start_worker(worker)
    def start_worker(self,function):
        self.workers=[worker for worker in self.workers if worker.is_alive()]
        thread=threading.Thread(target=function,daemon=True);self.workers.append(thread);thread.start()
    @Slot(QUrl)
    def openFile(self,url):
        if not url.isLocalFile():return
        self.queue_index=-1;self.queueChanged.emit();source=url.toLocalFile();config=self.config()
        self.update_state(status=tr('Analisando ritmo e trechos semelhantes…'))
        def analyse(cancel,progress):
            model=prepare(source,config['ffmpeg'],cancel.is_set,progress)
            from audio_library import read_audio,cover_preview
            model['_cover']=cover_preview(source) or ''
            try:
                tags=read_audio(source);model['media_title']=tags.get('title','');model['media_artist']=', '.join(tags.get('artists',[]));model['album']=tags.get('album') or ''
            except (OSError,ValueError):pass
            return model
        self.task(analyse)
    @Slot(str)
    def search(self,query):
        query=query.strip()
        if not query or self._state['busy']:return
        config=self.config();provider=self.preferences.get('catalog_provider','Todos')
        self.update_state(status=tr('Pesquisando…'))
        def search(cancel,progress):
            from metadata import MetadataClient,is_streaming_link
            if query.startswith(('http://','https://')) and not is_streaming_link(query):return {'tracks':[{'title':query,'artists':[],'source_url':query,'_jukebox_direct':True}]}
            from music_search import search_music
            from spotify_account import SpotifyAccount
            client=MetadataClient(config['spotify_client_id'],config['spotify_client_secret'])
            try:return {'tracks':search_music(client,query,provider,account=SpotifyAccount(self.store.path.with_name('spotify-account.dpapi')),limit=12,cancelled=cancel.is_set,automatic=True)['tracks']}
            finally:client.close()
        self.task(search,stop_current=False)
    @Slot(int)
    def selectResult(self,index):
        if not 0<=index<len(self.records) or self._state['busy']:return
        self.queue_index=-1;self.prepare_record(dict(self.records[index]))
    def prepare_record(self,record):
        config=self.config()
        self.update_state(status=tr('Obtendo áudio para análise…'))
        def fetch(cancel,progress):
            direct=record.get('_jukebox_direct');model=fetch_audio(dict(config,url=record['source_url']) if direct else config,None if direct else record,cancel.is_set,progress)
            if model.get('cover_url') and not cancel.is_set():
                from catalog_ui import cover_png
                try:model['_cover']=base64.b64encode(cover_png(model['cover_url']) or b'').decode()
                except (OSError,ValueError):pass
            return model
        self.task(fetch)

    @Slot(int,str,object)
    def handle_event(self,revision,kind,value):
        if self.closed:return
        if kind=='queue_info':
            entry=next((row for row in self.playlist if row['id']==value['id']),None)
            if entry is not None:self.queue_info(entry,value['record'],value['cover']);self.queueChanged.emit()
            return
        if revision!=self.revision:return
        if kind=='progress':self.update_state(progress=value)
        elif kind=='result':
            if 'tracks' in value:
                self.records=value['tracks'];self.update_state(results=[{'title':r['title'],'artist':', '.join(r.get('artists',[]))} for r in self.records],status=tr('Escolha uma música nos resultados.') if self.records else tr('Nenhuma música encontrada.'))
            else:
                self.model=value;self.flow=[];self._position=0;self._phase=0
                cover=value.get('_cover','');cover=base64.b64encode(cover).decode() if isinstance(cover,bytes) else cover
                self.update_state(title=value.get('media_title') or value['title'],artist=value.get('media_artist') or '',album=value.get('album') or '',cover=('data:image/png;base64,'+cover) if cover else '',ready=True,results=[],status=tr('Análise concluída.' if value['links'] else 'Sem saltos compatíveis: a faixa será repetida normalmente.'))
                if self.queue_index>=0 and self.autoplay_revision==revision:
                    self.playlist[self.queue_index].update(title=self._state['title'],artist=self._state['artist'],album=self._state['album'],cover=self._state['cover'],duration=int(value.get('duration') or 0));self.queueChanged.emit()
                self.update_graph();self.positionChanged.emit()
        elif kind=='position':
            self._position=value['index']+value['phase'];self._phase=value['phase'];self._elapsed=value['elapsed'];self._jumps=value['jumps']
            if value['edges']:self.flow=(self.flow+value['edges'])[-24:];self.update_graph()
            self.positionChanged.emit()
            if self.track_minutes and self.queue_index>=0 and self._elapsed>=self.track_minutes*60:self.nextTrack()
        elif kind=='lookup_error':self.update_state(status=str(value))
        elif kind=='error':self.autoplay_revision=None;self.update_state(status=str(value),playing=False,paused=False);self.media_timer.stop();self.sync_media()
        elif kind=='idle':
            self.update_state(busy=False)
            if self.autoplay_revision==revision and self._state['ready']:
                self.autoplay_revision=None;self.playPause()
        elif kind=='stopped':self.update_state(playing=False,paused=False);self.media_timer.stop();self.sync_media()

    @Slot()
    def playPause(self):
        if self._state['playing']:
            if self.paused.is_set():self.paused.clear()
            else:self.paused.set()
            self.update_state(paused=self.paused.is_set());self.sync_media();return
        if not self.model or self._state['busy']:return
        self.cancelled=threading.Event();self.paused.clear();cancel=self.cancelled;revision=self.revision
        cache=self.model['cache'];initial=int(self._position);self.seeks=queue.SimpleQueue();seeks=self.seeks
        self._elapsed=0;self._jumps=0;self.flow=[];self.positionChanged.emit();self.update_graph()
        self.update_state(playing=True,paused=False,status=tr('Reproduzindo…'));self.sync_media();self.media_timer.start()
        def worker():
            session=output=None
            try:
                from jukebox_audio import PcmOutput
                session=Session(cache);session.seek(initial);timeline=deque();submitted=0;heard_jumps=0
                def progress(played):
                    nonlocal heard_jumps
                    edges=[];index=initial;phase=0.
                    while timeline and timeline[0][0]<=played:
                        _,part=timeline.popleft();edges.append((part['index'],part['next']));heard_jumps=part['jumps'];index=part['next']
                    if timeline:
                        end,part=timeline[0];index=part['index'];frames=part['frames'];phase=max(0.,min(1.,(played-end+frames)/max(1,frames)))
                    self.emit(revision,'position',dict(index=index,phase=phase,edges=edges,elapsed=played/RATE,jumps=heard_jumps))
                output=PcmOutput(progress=progress);output.gain=self.sleep.gain
                while not cancel.is_set():
                    target=None
                    while not seeks.empty():target=seeks.get()
                    if target is not None:session.seek(target)
                    part=session.chunk(*self._params,equalizer=self._equalizer);frames=len(part['pcm'])//4;submitted+=frames
                    timeline.append((submitted,dict(index=part['index'],next=part['next'],jumps=part['jumps'],frames=frames)))
                    output.write(part['pcm'],cancel.is_set,self.paused.is_set)
            except Cancelled:pass
            except Exception as error:self.emit(revision,'error',str(error))
            finally:
                if output:output.close()
                if session:session.close()
                self.emit(revision,'stopped',None)
        self.start_worker(worker)
    @Slot()
    def cancelOperation(self):
        if self.task_is_lookup:
            self.lookup_cancelled.set();self.request_number+=1;self.update_state(busy=False)
        else:self.stop()
    @Slot()
    def stop(self,reset_timer=True):
        if reset_timer:self.sleep.cancel();self.clock_timer.stop()
        self.autoplay_revision=None;self.lookup_cancelled.set();self.request_number+=1
        self.revision+=1;self.cancelled.set();self.paused.clear();self.media_timer.stop()
        self._position=0.;self._phase=0.;self.flow=[];self._elapsed=0.;self._jumps=0
        self.update_state(playing=False,paused=False,busy=False);self.update_graph();self.positionChanged.emit();self.sync_media()
    @Slot(int)
    def seek(self,index):
        if self.model and 0<=index<len(self.model['neighbors']):
            self.seeks.put(index);self._position=float(index);self._phase=0.;self.flow=[];self.update_graph();self.positionChanged.emit()
    def sync_media(self):
        if self.closed:return
        if self._state['playing'] and self.media is None and not self.media_failed and self.window is not None and os.name=='nt':
            try:
                from windows_media import MediaControls
                self.media=MediaControls(SimpleNamespace(winfo_id=lambda:int(self.window.winId())))
            except (OSError,AttributeError):self.media_failed=True
        if self.media:
            for _ in range(8):
                try:button=self.media.events.get_nowait()
                except queue.Empty:break
                if button==0 and (not self._state['playing'] or self.paused.is_set()):self.playPause()
                elif button==1 and self._state['playing'] and not self.paused.is_set():self.playPause()
                elif button==2:self.stop()
            self.media.update(self._state['title'],self._state['artist'],self._state['playing'],self._state['paused'])
    @Slot()
    def shutdown(self):
        if self.closed:return
        self.stop();self.clock_timer.stop();self.closed=True;self.save_preferences()
        if self.media:self.media.close();self.media=None
        deadline=time.monotonic()+2
        for worker in self.workers:worker.join(timeout=max(0,deadline-time.monotonic()))
        self._event.disconnect(self.handle_event)
        self.media_timer.timeout.disconnect(self.sync_media)
        self.save_timer.timeout.disconnect(self.save_preferences)
