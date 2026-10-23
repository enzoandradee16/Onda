"""Native Qt controller; shared media engines execute off the UI thread."""
import json,os,queue,subprocess,sys,threading,time,uuid
from pathlib import Path
from PySide6.QtCore import QObject,Property,Signal,Slot,QTimer,QUrl,Qt
from PySide6.QtGui import QDesktopServices,QGuiApplication,QShortcut,QKeySequence
from qt_models_ui import RowsModel
from preferences import PreferenceStore
from library import LibraryStore
from i18n import tr
ROOT=Path(__file__).resolve().parent
PAGES={'catalog':'Pesquisar músicas','downloads':'Links','queue':'Fila','images':'Imagens','converter':'Conversor','playlists':'Álbuns e playlists','history':'Histórico','effects':'Reprodução e efeitos','metadata':'Editar metadados','jukebox':'Reprodução e efeitos'}
TAB_GROUPS=[('BIBLIOTECA',('catalog','downloads','queue','playlists','history')),('FERRAMENTAS',('images','converter','effects','metadata'))]
CHOICES={'choose_flac','choose_media','choose_version','choose_catalog','choose_duplicate','review_metadata'}
class DesktopWorkspace(QObject):
    changed=Signal();optionsChanged=Signal();settingsChanged=Signal();choiceChanged=Signal();statusChanged=Signal()
    lyricsRequested=Signal();comparisonRequested=Signal(int);cropRequested=Signal();settingsRequested=Signal();settingsCategoryRequested=Signal(str);shortcutsRequested=Signal();message=Signal(str,str);_event=Signal(str,object)
    def __init__(self,bridge,parent=None):
        super().__init__(parent);self.bridge=bridge;self.window=None;self.prepare_tools=False;self.restart_requested=False;self.closed=False
        schema=json.loads((ROOT/'settings_schema/desktop.json').read_text(encoding='utf-8'));self.defaults=schema['defaults'];self.fields=schema['fields']
        from performance import thread_choices
        for field in self.fields:
            if field['key']=='conversion_threads':field['choices']=list(thread_choices())
        self.settings=dict(self.defaults,**bridge.preferences);self.settings['remember_settings']=bridge.store.remember_enabled();self.settings['language']=bridge.store.load_language();self.settings['folder']=self.settings.get('folder') or str(Path.home()/'Downloads/Onda')
        self.store=bridge.store;self.library=LibraryStore(self.store.path.parent/'library.sqlite3')
        from spotify_account import SpotifyAccount
        self.account=SpotifyAccount(self.store.path.with_name('spotify-account.dpapi'))
        from credentials import CredentialStore,CredentialError
        self.credentials=CredentialStore()
        try:identity,secret=self.credentials.load() or ('','')
        except CredentialError:identity,secret='',''
        self.saved_credentials=(identity,secret)
        self.settings.update(spotify_client_id=os.environ.get('SPOTIFY_CLIENT_ID',bridge.preferences.get('spotify_client_id',identity) if self.settings['remember_settings'] else ''),spotify_client_secret=os.environ.get('SPOTIFY_CLIENT_SECRET',secret if self.settings['remember_settings'] else ''))
        self._page='catalog';self._status=tr('Pronto para começar');self._choice={};self.choice_callbacks={};self.pending_choices=[];self.logs=[]
        self.models={key:RowsModel(self) for key in ('queue','catalog','playlists','history')}
        from queue_undo import QueueUndo
        self.undo_history=QueueUndo()
        self.jobs=[];self.active={};self.tasks={};self.background_tasks=set();self.tool_progress={};self.generations={};self.callbacks={};self.running=False;self.closing=False;self.paused_all=False;self.schedule_blocked=False;self.manual_queue=False;self.clipboard_seen=set();self.syncing=False
        self.memory_waiting=False;self.queue_scope=None;self.queue_attempted=set();self.restore_state=Qt.WindowState.WindowNoState
        self.lyrics=[];self.last_preview_processed=True;self.preview_kind='';self.preview_source=''
        self.preview_timer=QTimer(self);self.preview_timer.setSingleShot(True);self.preview_timer.setInterval(150);self.preview_timer.timeout.connect(self.play_effects_preview)
        self.options={'effectsStopMinutes':0,'effectsStopRemaining':0,'effectsTrackMinutes':0,'effectsSwitchRemaining':0,'effectsQueue':[],'effectsQueueIndex':-1,'effectsPaused':False,'effectsVolume':80,'effectsQuery':'','effectsResults':[],'effectsOnlineRecord':{},'previewActive':False,'previewKind':'','previewSource':'','previewProcessed':False,'metadataFields':{},'lyricText':'','effectLyricsName':'','query':'','provider':self.settings.get('catalog_provider','Deezer'),'links':'','linksNotice':'','playlistUrl':'','playlistTitle':'','queueQuery':'','queueState':'Todos','historyQuery':'','silenceResults':[],'trimSilence':False,'converterSources':[],'converterFormat':'MP4','video_quality':'Equilibrada','video_resolution':'Original','video_bitrate':'Automático','audio_bitrate':'192k','video_fps':'Original','video_audio':'Manter áudio','effectsSource':'','effectsRecord':{},'effectsCover':'','speed':85,'reverb':25,'keep_pitch':self.settings.get('effects_keep_pitch',False),'effectFormat':'MP3','position':0,'duration':0,'imageInfo':{},'catalogSearched':False,'imageSource':'','imageUrl':'','imagePreview':'','metadataSources':[],'metadata':{},'cover_path':'','lyrics_path':'','normalize_volume':False,'overwrite_original':False,'comparison':{},'selectedCatalog':-1,'selectedPlaylist':-1,'filterArtist':'','filterAlbum':'','filterVersion':''}
        from audio_tools import PreviewPlayer
        self.effects_tails=[];self.player=PreviewPlayer();self.tray=None;self.shell=None;self.shortcuts=[];self.shortcuts_suspended=False;self.tasks_threads=[]
        self.shutdown_timer=QTimer(self);self.shutdown_timer.setSingleShot(True);self.shutdown_timer.setInterval(60000);self.shutdown_timer.timeout.connect(self.perform_shutdown)
        self.save_timer=QTimer(self);self.save_timer.setSingleShot(True);self.save_timer.setInterval(400);self.save_timer.timeout.connect(self.persist)
        self.timer=QTimer(self);self.timer.setInterval(300);self.timer.timeout.connect(self.tick)
        self._event.connect(self.on_event,Qt.ConnectionType.QueuedConnection)
        bridge.appearanceChanged.connect(self.from_bridge);bridge.equalizerChanged.connect(self.from_bridge);bridge.config_provider=self.config
        for index,job in enumerate(self.library.load_queue()):self.jobs.append(dict(job,id=uuid.uuid4().hex,checked=False,percent=0,queue_original=index))
        from queue_titles import TitleLookup
        from queue_timing import QueueTiming
        self.title_events=queue.SimpleQueue();self.title_lookup=TitleLookup(self.title_events);self.title_lookup.spotify_account=self.account;self.timing=QueueTiming()
        self.refresh_queue();self.refresh_history()
    @Property(str,notify=changed)
    def currentPage(self):return self._page
    @Property(str,notify=changed)
    def title(self):return tr(PAGES[self._page])
    @Property(bool,notify=changed)
    def ready(self):return True
    @Property(str,notify=statusChanged)
    def error(self):return ''
    @Property(str,notify=statusChanged)
    def status(self):return self._status
    @Property('QVariantMap',notify=optionsChanged)
    def values(self):return dict(self.options)
    @Property('QVariantMap',notify=settingsChanged)
    def preferences(self):return dict(self.settings)
    @Property('QVariantList',notify=settingsChanged)
    def settingsFields(self):return self.fields
    @Property('QStringList',notify=settingsChanged)
    def hiddenTabs(self):return list(self.settings.get('hidden_tabs',[]))
    @Property('QVariantMap',notify=choiceChanged)
    def choice(self):return dict(self._choice)
    @Property('QVariantMap',notify=statusChanged)
    def activity(self):return {'hasCredentials':any(self.saved_credentials) or bool(self.settings.get('spotify_client_id','') or self.settings.get('spotify_client_secret','')),'spotifySearchReady':self.account.connected or bool(self.settings.get('spotify_client_id','').strip() and self.settings.get('spotify_client_secret','').strip()),'credentialsSaved':any(self.saved_credentials) and self.saved_credentials==(self.settings.get('spotify_client_id',''),self.settings.get('spotify_client_secret','')),'tools':dict(self.tool_progress),'selected':sum(bool(job.get('checked')) for job in self.jobs),'visibleSelected':sum(bool(row.get('checked')) for row in self.models['queue'].rows),'total':len(self.jobs),'undoCount':len(self.undo_history.entries),'running':self.running,'active':len(self.active),'background':list(self.background_tasks),'busy':list(dict.fromkeys(list(self.tasks)+[state['operation'] for state in self.active.values() if state.get('operation')]+[job['ui_operation'] for job in self.jobs if job.get('ui_operation') and job['state']=='Na fila'])),'logs':'\n'.join(self.logs[-200:]),'spotify':self.account.connected,'elapsed':self.timing.snapshot(sum(job['state'] in ('Na fila','Em andamento') for job in self.jobs))[0] if hasattr(self,'timing') else 0}
    @Property(QObject,constant=True)
    def queueModel(self):return self.models['queue']
    @Property(QObject,constant=True)
    def catalogModel(self):return self.models['catalog']
    @Property(QObject,constant=True)
    def playlistModel(self):return self.models['playlists']
    @Property(QObject,constant=True)
    def historyModel(self):return self.models['history']
    def attach(self,window,area=None):
        self.window=window
        self.window_bounds=None
        self.window_save_timer=QTimer(self);self.window_save_timer.setSingleShot(True);self.window_save_timer.setInterval(400)
        self.window_save_timer.timeout.connect(self.save_window_layout)
        self.restore_window_layout()
        for signal in (window.xChanged,window.yChanged,window.widthChanged,window.heightChanged,window.windowStateChanged):
            signal.connect(self.capture_window_layout)
        self.remember_window_state(window.windowState())
        window.windowStateChanged.connect(self.remember_window_state)
        self.capture_window_layout()
    def restore_window_layout(self):
        try:
            data=json.loads(self.store.path.with_name('window.json').read_text(encoding='utf-8'))
            x,y,w,h=[int(data[key]) for key in ('x','y','width','height')]
            screens=QGuiApplication.screens()
            screen=next((screen for screen in screens if screen.availableGeometry().contains(x+40,y+40)),self.window.screen())
            area=screen.availableGeometry()
            w=max(self.window.minimumWidth(),min(w,area.width()));h=max(self.window.minimumHeight(),min(h,area.height()))
            x=max(area.x(),min(x,area.right()-w+1));y=max(area.y(),min(y,area.bottom()-h+1))
            self.window.setGeometry(x,y,w,h);self.window_bounds={'x':x,'y':y,'width':w,'height':h}
            if data.get('maximized') is True:self.window.showMaximized()
        except (OSError,ValueError,TypeError,KeyError):pass
    def capture_window_layout(self,*args):
        if self.window.windowState()==Qt.WindowState.WindowNoState:
            rect=self.window.geometry()
            self.window_bounds={'x':rect.x(),'y':rect.y(),'width':rect.width(),'height':rect.height()}
        self.window_save_timer.start()
    def save_window_layout(self):
        if not getattr(self,'window_bounds',None) or self.window is None:return
        state=self.window.windowState()
        if state==Qt.WindowState.WindowMinimized:state=self.restore_state
        data=dict(self.window_bounds,maximized=state==Qt.WindowState.WindowMaximized)
        target=self.store.path.with_name('window.json');temporary=target.with_suffix('.json.tmp')
        try:
            target.parent.mkdir(parents=True,exist_ok=True)
            temporary.write_text(json.dumps(data),encoding='utf-8');temporary.replace(target)
        except OSError:pass
    def remember_window_state(self,state):
        if state!=Qt.WindowState.WindowMinimized:self.restore_state=state
    def start(self):
        self.timer.start();self.setup_shell();QGuiApplication.clipboard().dataChanged.connect(self.clipboard_changed)
        from ffmpeg_runtime import existing_folder
        tools=existing_folder()
        if tools:self.settings['ffmpeg']=str(tools)
        elif self.prepare_tools:self.run_task('prepare_tools',{},lambda result:self.setSetting('ffmpeg',result))
        if self.settings.get('resume_queue') and not self.settings.get('schedule_enabled'):QTimer.singleShot(500,self.start_queue)
        if self.settings.get('check_updates'):QTimer.singleShot(3000,lambda:self.run_task('app_update',{},lambda result:self.notify(result.get('message','')),background=True))
        self.from_bridge();self.bind_shortcuts()
    def config(self):
        from engine import MODES,HEIGHTS,FPS_OPTIONS
        from file_output import DUPLICATES
        config=dict(self.settings);config.update(mode=MODES.get(config.get('mode'),'mp3'),height=HEIGHTS.get(config.get('height')),fps=FPS_OPTIONS.get(config.get('fps')),duplicate_policy=DUPLICATES.get(config.get('duplicates'),'ask'),playlist_limit=int(config.get('playlist_limit',1000)),_root=str(self.store.path.parent),_account=self.account)
        config['audio_quality']=config.get('m4a_quality') if config['mode']=='m4a' else config.get('mp3_quality');config['youtube_cookies_file']=config.get('youtube_cookies','');config['cookies_file']=config.get('social_cookies','');config['image_options']=self.image_options();return config
    def image_options(self):
        from image_output import IMAGE_SIZES
        size=IMAGE_SIZES.get(self.settings.get('image_size','Original'));width,height=size if size is not None else (int(self.settings.get('image_width',1920)),int(self.settings.get('image_height',1080)))
        return {'format':self.settings.get('image_format','Original'),'width':width,'height':height,'keep_ratio':self.settings.get('image_keep_ratio',True)}
    def notify(self,text):self._status=tr(str(text));self.statusChanged.emit()
    def log(self,text):self.logs.append(str(text));self.logs=self.logs[-400:];self.statusChanged.emit()
    @Slot(str,'QVariant')
    def setOption(self,key,value):
        self.options[key]=value
        if key=='imageUrl':
            self.cancel_task('image_info');self.cancel_task('image_preview');self.options['imageInfo']={};self.options['imageSource']='';self.options['imagePreview']=''
        self.optionsChanged.emit()
        if key in ('queueQuery','queueState'):self.refresh_queue()
        if key=='historyQuery':self.refresh_history()
        if key.startswith('filter'):self.filter_catalog()
        if key in ('speed','reverb','keep_pitch','position','effectsVolume') and self.player.active and self.preview_kind=='effects':self.preview_timer.start()
    @Slot(str,'QVariant')
    def setSetting(self,key,value):
        if key in ("background_preview","jukebox_background","effects_preview_duration"):return
        if key not in self.defaults:return
        if key=='remember_settings':
            self.settings[key]=bool(value)
            if not value:self.store.forget();self.credentials.forget();self.saved_credentials=('','')
        elif key in ('spotify_client_id','spotify_client_secret','social_cookies','youtube_cookies'):self.settings[key]=str(value);self.statusChanged.emit()
        elif key in ('tab_order','hidden_tabs'):
            from tab_order import normalize_hidden,normalize_order
            self.settings[key]=(normalize_hidden if key=='hidden_tabs' else normalize_order)(value)
        else:
            cleaned=PreferenceStore.clean({key:value})
            if key not in cleaned:return
            self.settings[key]=cleaned[key]
        if key in ('jukebox_gradual_transition','jukebox_transition_seconds') and self.player.active and self.preview_kind=='effects':
            self.options['position']=self.player.position_snapshot();self.preview_timer.start()
        if key=='synced_lyrics' and not self.settings[key]:self.options['lyricText']='';self.optionsChanged.emit()
        if key=='effects_keep_pitch':self.setOption('keep_pitch',self.settings[key])
        if key=='background_preview' and not self.settings[key] and self.preview_kind=='effects' and self._page!='effects':self.stop_preview()
        if key=='jukebox_background' and not self.settings[key] and self._page!='jukebox':self.pause_background_jukebox()
        if key=='language':self.store.save_language(value);self.notify('Reinicie o ONDA para aplicar o idioma.')
        if key=='shortcut_keys':self.bind_shortcuts()
        self.syncing=True
        try:self.bridge.preferences.update({k:v for k,v in self.settings.items() if k in self.defaults});self.bridge.appearanceChanged.emit()
        finally:self.syncing=False
        if self._page in self.hiddenTabs or self._page=='jukebox' and 'effects' in self.hiddenTabs:self.selectPage('catalog')
        self.settingsChanged.emit();self.save_timer.start()
    @Slot()
    def from_bridge(self):
        if self.syncing:return
        for key in ('theme_mode','theme_accent','qt_animations','jukebox_equalizer','jukebox_gradual_transition','jukebox_transition_seconds'):self.settings[key]=self.bridge.preferences.get(key,self.settings.get(key))
        self.settingsChanged.emit();self.save_timer.start()
        if self.tray:self.tray.setIcon(QGuiApplication.windowIcon())
    def persist(self):
        self.save_timer.stop()
        try:
            self.store.save_display(self.settings)
            if self.settings.get('remember_settings'):
                self.store.save(self.settings)
                pair=(self.settings.get('spotify_client_id','').strip(),self.settings.get('spotify_client_secret','').strip())
                if all(pair) and pair!=self.saved_credentials:
                    self.credentials.save(*pair);self.saved_credentials=pair;self.statusChanged.emit()
                elif not all(pair) and any(self.saved_credentials):
                    self.credentials.forget();self.saved_credentials=('','');self.statusChanged.emit()
        except (OSError,ValueError) as error:self.notify(error)
    @Slot()
    def pause_background_jukebox(self):
        if getattr(self,"_mini_active",False):return
        return
    @Slot(str)
    def selectNavigationPage(self,key):
        if key=='effects':key='jukebox' if self.settings.get('playback_tab_order')=='Jukebox infinito primeiro' else 'effects'
        self.selectPage(key)
    @Slot(str)
    def selectPage(self,key):
        if key not in PAGES or key in self.hiddenTabs:return
        if key!=self._page:
            if key!='jukebox':self.pause_background_jukebox()
            if self.preview_kind!='effects':self.stop_preview()
        self._page=key;self.changed.emit()
        if key=='history':self.refresh_history()
    @Slot()
    def showSettings(self):self.settingsRequested.emit()
    @Slot()
    def showShortcuts(self):self.shortcutsRequested.emit()
    @Slot()
    def showMetadata(self):self.selectPage('metadata')
    def run_task(self,action,overrides=None,callback=None,*,background=False):
        if action in ('prepare_tools','update_tools') and any(name in self.tasks for name in ('prepare_tools','update_tools')):
            self.notify('Aguarde a preparação ou atualização das ferramentas terminar.');return
        self.cancel_task(action);revision=self.generations.get(action,0)+1;self.generations[action]=revision;cancel=threading.Event();self.tasks[action]=cancel;self.callbacks[action]=callback
        if background:self.background_tasks.add(action)
        else:self.background_tasks.discard(action)
        if action in ('prepare_tools','update_tools'):self.tool_progress={'action':action,'message':self.taskLabel(action),'done':0,'total':0}
        config=dict(self.config(),**(overrides or {}));self.statusChanged.emit()
        def work():
            try:
                from qt_operations_ui import perform
                result=perform(action,config,cancel,lambda kind,**values:self._event.emit('task_progress',{'action':action,'revision':revision,'event':dict(type=kind,**values)}))
                if not cancel.is_set():self._event.emit('task_result',{'action':action,'revision':revision,'result':result})
            except Exception as error:
                if not cancel.is_set():
                    if hasattr(error,'candidates'):self._event.emit('task_result',{'action':action,'revision':revision,'result':{'tracks':error.candidates}})
                    else:self._event.emit('task_error',{'action':action,'revision':revision,'error':str(error)})
            finally:self._event.emit('task_finished',{'action':action,'revision':revision})
        self.launch_thread(work)
    def launch_thread(self,work):
        self.tasks_threads=[thread for thread in self.tasks_threads if thread.is_alive()];thread=threading.Thread(target=work,daemon=True);self.tasks_threads.append(thread);thread.start()
    def cancel_task(self,action):
        if action in self.tasks:self.tasks[action].set()
        for identity,state in list(self.active.items()):
            if state.get('operation')==action:self.stop_job(identity)
        changed=False
        for job in self.jobs:
            if job.get('ui_operation')==action and job['state']=='Na fila':job['state']='Cancelado';changed=True
        if changed:self.refresh_queue();self.save_queue()
        self.statusChanged.emit()

    @Slot(str,'QVariantMap')
    def invoke(self,action,params):
        try:self.dispatch(action,dict(params))
        except Exception as error:self.notify(error);self.message.emit(tr('ONDA'),str(error))
    def dispatch(self,action,p):
        if action=='effects_search':
            query=self.options['effectsQuery'].strip()
            if query:self.run_task('effects_search',{'query':query},lambda result:self.setOption('effectsResults',result.get('tracks',[])))
        elif action=='effects_enqueue_result':
            records=self.options['effectsResults'];index=int(p.get('index',-1))
            if not 0<=index<len(records):return
            self.run_task('effects_load',{'record':records[index]},lambda result:self.accept_files('effects_queue',[result['source']]))
        elif action=='effects_queue_play':self.play_effects_entry(int(p.get('index',0)))
        elif action=='effects_timer':
            minutes=max(0,min(180,int(p.get('minutes',0))))
            key='effectsTrackMinutes' if p.get('next') else 'effectsStopMinutes'
            remaining='effectsSwitchRemaining' if p.get('next') else 'effectsStopRemaining'
            self.options.update({key:minutes,remaining:minutes*60});self.optionsChanged.emit()
        elif action=='effects_next':self.play_effects_entry(self.options['effectsQueueIndex']+1)
        elif action=='effects_previous':
            index=self.options['effectsQueueIndex']
            if index>0:self.play_effects_entry(index-1)
            else:self.setOption('position',0)
        elif action=='effects_queue_remove':
            index=int(p.get('index',-1));rows=self.options['effectsQueue'];current=self.options['effectsQueueIndex']
            if 0<=index<len(rows):
                rows.pop(index)
                if index<=current:self.options['effectsQueueIndex']=current-1
                self.optionsChanged.emit()
        elif action=='effects_queue_move':
            index=int(p.get('index',-1));target=index+int(p.get('direction',0));rows=self.options['effectsQueue']
            if 0<=index<len(rows) and 0<=target<len(rows):
                current=self.options['effectsQueueIndex'];rows[index],rows[target]=rows[target],rows[index]
                if current==index:self.options['effectsQueueIndex']=target
                elif current==target:self.options['effectsQueueIndex']=index
                self.optionsChanged.emit()
        elif action=='effects_queue_clear':self.options.update(effectsQueue=[],effectsQueueIndex=-1);self.optionsChanged.emit()
        elif action=='effects_load':
            records=self.options['effectsResults'];index=int(p.get('index',-1))
            if not 0<=index<len(records):return
            def loaded(result):
                self.accept_files('effects',[result['source']]);self.options['effectsOnlineRecord']=result['record'];self.options['effectsResults']=[];self.optionsChanged.emit()
            self.run_task('effects_load',{'record':records[index]},loaded)
        elif action=='lyrics_online':
            jukebox=p.get('jukebox',self._page=='jukebox')
            automatic=p.get('automatic',False)
            record=dict(self.bridge.model or {}) if jukebox else dict(self.options['effectsRecord'])
            source=str(record.get('source','')) if jukebox else self.options['effectsSource']
            if not str(source).strip():
                text=tr('Selecione uma música antes de buscar a letra online.')
                self.notify(text);self.message.emit(tr('Buscar letra online'),text);return
            def loaded(result):
                if not result:return
                if 'candidates' in result:
                    candidates=result['candidates']
                    if not candidates:self.notify(tr('Letra não encontrada para esta gravação.'));return
                    def selected(reply):
                        if reply.get('cancel'):return
                        choice=next((row for row in candidates if row['id']==str(reply.get('selected_id'))),None)
                        if choice:loaded(choice)
                    self.present_choice(uuid.uuid4().hex,{'type':'choose_catalog','title':tr('Buscar letra online'),'candidates':candidates},selected);return
                if jukebox:
                    if str((self.bridge.model or {}).get('source',''))!=source:return
                    if automatic and getattr(self,'_jukebox_lyrics',[]):return
                    self._lyric_source=source;self._jukebox_lyrics=result['lines']
                else:
                    if self.options['effectsSource']!=source:return
                    if automatic and self.lyrics:return
                    self.lyrics=result['lines'];self.options['effectLyricsName']='';self.setSetting('synced_lyrics',True);self.optionsChanged.emit()
                self.notify(tr('Letra carregada.') if result['synced'] else tr('Letra sem sincronização.'))
            self.run_task('lyrics_online',{'source':source,'record':record,'automatic':automatic,'alternatives':not automatic},loaded,background=automatic)
        elif action=='configure_spotify':self.settingsCategoryRequested.emit('Contas')
        elif action=='search':
            query=self.options['query'].strip()
            if self.options['provider']=='Spotify' and not self.activity['spotifySearchReady'] and not query.startswith(('https://','http://','spotify:')):
                self.message.emit(tr('Configure a API do Spotify'),tr('Para pesquisar músicas no Spotify, configure a API em Configurações → Contas. Informe o Client ID e conecte sua conta, ou preencha Client ID e Client Secret. Você também pode pesquisar no Deezer ou Apple / iTunes.'));return
            self.run_task('search',dict(query=query,provider=self.options['provider'],refresh=p.get('refresh',False)),self.searched)
        elif action=='cancel_task':self.cancel_task(p['name'])
        elif action=='queue_copy_links':QGuiApplication.clipboard().setText('\n'.join(job['url'] for job in self.jobs if (job['id']==p['id'] if p.get('id') else job.get('checked'))))
        elif action=='queue_open_folder':QDesktopServices.openUrl(QUrl.fromLocalFile(self.settings['folder']))
        elif action=='undo_queue':self.jobs=self.undo_history.restore(self.jobs,self.active);self.refresh_queue();self.save_queue();self.statusChanged.emit();self.notify('Ação desfeita.')
        elif action=='add_links':
            if not self.options['links'].strip():return
            added=self.enqueue(self.options['links'].splitlines(),start=bool(p.get('start')))
            self.options['linksNotice']=(str(len(added))+' '+tr('itens adicionados à fila')) if added else tr('Nenhum novo item adicionado à fila.')
            self.optionsChanged.emit()
            if added and p.get('start'):
                self.selectPage('queue')
        elif action=='start_queue':self.start_queue()
        elif action=='stop_queue':self.stop_queue()
        elif action=='queue_action':self.queue_action(p['name'],p.get('id',''))
        elif action=='check':self.toggle_row(p['model'],p['index'],p['checked'])
        elif action=='check_all':
            for index in range(len(self.models[p['model']].rows)):self.toggle_row(p['model'],index,p['checked'],notify=False)
            self.statusChanged.emit()
        elif action=='catalog_select':
            self.options['selectedCatalog']=p['index'];self.optionsChanged.emit();record=self.models['catalog'].rows[p['index']]
            if (record.get('platform') or record.get('service'))=='Deezer' and not record.get('release_date'):self.run_task('release_date',{'record':record},lambda result:self.models['catalog'].update(p['index'],release_date=__import__('metadata').display_release_date(result) if result else ''))
        elif action in ('catalog_add','catalog_download'):
            record=self.models['catalog'].rows[int(p.get('index',self.options['selectedCatalog']))];self.enqueue([record['source_url']],overrides=self.music_overrides(record),start=action=='catalog_download')
        elif action=='jukebox_add':
            record=self.models['catalog'].rows[int(p.get('index',self.options['selectedCatalog']))];self.bridge.enqueueRecord(record);self.notify('Música adicionada à fila de reprodução do Jukebox.')
        elif action=='compare_results':self.comparisonRequested.emit(int(p.get('index',0)))
        elif action=='open_url':QDesktopServices.openUrl(QUrl(p['url']))
        elif action=='open_file':QDesktopServices.openUrl(QUrl.fromLocalFile(p['path']))
        elif action=='preview_catalog':
            record=self.models['catalog'].rows[int(p.get('index',self.options['selectedCatalog']))]
            if self.player.active and self.preview_kind=='catalog' and self.preview_source==record['source_url']:self.stop_preview()
            else:self.start_preview(record.get('preview_url') or record['source_url'],'catalog',identity=record['source_url'],youtube=not bool(record.get('preview_url')),duration=int(self.settings['search_preview_duration'].split()[0]))
        elif action=='stop_preview':self.stop_preview()
        elif action=='load_playlist':self.run_task('collection',{'url':self.options['playlistUrl']},self.collection_loaded)
        elif action=='playlist_add':
            self.enqueue_tracks([row for row in self.models['playlists'].rows if row.get('checked')],start=bool(p.get('start')))
        elif action=='compare_playlist':self.run_task('compare_collection',{'url':self.options['playlistUrl'],'tracks':self.models['playlists'].rows,'history':self.library.comparison_history(),'queued':self.jobs,'database':str(self.library.path)},self.collection_compared)
        elif action=='playlist_missing':
            for i,row in enumerate(self.models['playlists'].rows):self.models['playlists'].update(i,checked=row.get('comparison')=='missing')
        elif action=='pick':self.pick(p['kind'])
        elif action=='convert':self.convert()
        elif action=='detect_silence':
            if not self.options['converterSources']:raise ValueError('Escolha um arquivo para analisar.')
            self.run_task(action,{'sources':self.options['converterSources']},lambda rows:self.setOption('silenceResults',rows))
        elif action=='effects_play_pause':
            if self.player.active and self.preview_kind=='effects':
                self.options['position']=self.player.position_snapshot();self.player.stop();self.preview_timer.stop()
                for tail in self.effects_tails:tail.stop()
                self.effects_tails=[]
                self.options.update(previewActive=False,effectsPaused=True);self.optionsChanged.emit()
            else:
                if self.options['position']>=self.options['duration']:self.options['position']=0
                self.last_preview_processed=True;self.effects_transport=True
                if self.bridge.state.get('playing') and not self.bridge.state.get('paused'):self.bridge.playPause()
                self.play_effects_preview()
        elif action=='effects_stop':
            if self.preview_kind=='effects':self.stop_preview()
            self.options.update(position=0,effectsPaused=False);self.optionsChanged.emit()
        elif action=='effects_skip':
            self.setOption('position',max(0,min(self.options['duration'],self.options['position']+float(p.get('seconds',0)))))
        elif action=='effects_preview':
            processed=p.get('processed',True)
            if self.player.active and self.preview_kind=='effects' and self.last_preview_processed==processed:self.stop_preview()
            else:self.last_preview_processed=processed;self.play_effects_preview()
        elif action=='effects_export':self.export_effects()
        elif action in ('image_preview','image_export'):
            if not self.options['imageSource']:
                if action=='image_preview':
                    if not self.options['imageUrl'].strip():raise ValueError('Escolha um arquivo ou informe um link de imagem.')
                    self.run_task(action,{'source':self.options['imageUrl'].strip()},self.image_result);return
                added=self.enqueue([self.options['imageUrl']],overrides={'mode':'photos','playlist':False},start=True)
                for job in added:
                    job['ui_operation']='image_export'
                    if job['id'] in self.active:self.active[job['id']]['operation']='image_export'
                self.statusChanged.emit()
            else:self.run_task(action,{'source':self.options['imageSource']},self.image_result)
        elif action=='audio_edit':self.edit_audio()
        elif action=='metadata_preview':
            source=self.options['metadataSources'][0];normalized=p.get('normalized',False)
            if self.player.active and self.preview_kind=='metadata' and self.options['previewProcessed']==normalized:self.stop_preview()
            elif normalized:
                self.stop_preview()
                self.run_task('normalize_preview',{'source':source},lambda result:self.start_preview(result['path'],'metadata',processed=True,duration=20))
            else:self.start_preview(source,'metadata',processed=False,duration=20)
        elif action=='crop_cover':
            if self.options['cover_path']:self.cropRequested.emit()
        elif action=='apply_cover_crop':self.run_task('cover_crop',dict(p,source=self.options['cover_path']),self.cover_cropped)
        elif action=='undo_cover':self.options['cover_path']='';self.options['metadataCover']=self.options.get('originalCover','');self.optionsChanged.emit()
        elif action=='reset_selected':
            for key in p.get('keys',[]):
                if key in self.defaults:self.setSetting(key,self.defaults[key])
        elif action=='check_matches':self.run_task('check_matches',{'tracks':[row for row in self.models['playlists'].rows if row.get('checked')]},self.matches_checked)
        elif action=='update_playlist':self.update_playlist()
        elif action in ('history_edit','queue_edit'):
            sources=[]
            if action=='history_edit':
                rows=self.models['history'].rows
                selected=[row for row in rows if row.get('checked')]
                sources=[row['path'] for row in selected] if len(selected)>1 or 'index' not in p else [rows[p['index']]['path']]
            else:
                selected=[job for job in self.jobs if job['id']==p.get('id')] if p.get('id') else [job for job in self.jobs if job.get('checked')]
                for job in selected:
                    if job['id'] in self.active:continue
                    sources.extend(job.get('output_files',[]))
                    if not job.get('output_files'):
                        saved=self.library.find_duplicate(job['url'],job['mode'])
                        if saved:sources.append(saved)
            sources=list(dict.fromkeys(str(Path(path).resolve()) for path in sources if Path(path).is_file() and Path(path).suffix.lower() in ('.mp3','.flac','.m4a','.ogg','.opus','.wav','.aac','.wma','.aiff','.aif')))
            if sources:self.accept_files('metadata',sources);self.selectPage('metadata')
            else:self.notify('Escolha um arquivo de áudio.')
        elif action=='history_effects':self.accept_files('effects',[self.models['history'].rows[p['index']]['path']]);self.selectPage('effects')
        elif action=='history_retry':
            row=self.models['history'].rows[p['index']];self.enqueue([row['source']],overrides={'mode':row.get('mode','mp3')},start=True)
        elif action=='history_clear':self.confirm('Limpar histórico','Limpar o histórico? Os arquivos serão preservados.',self.clear_history)
        elif action in ('export_playlist','import_playlist','export_settings','import_settings','restore_settings','export_history'):self.settings_file_action(action)
        elif action=='save_credentials':self.credentials.save(self.settings['spotify_client_id'],self.settings['spotify_client_secret']);self.saved_credentials=(self.settings['spotify_client_id'],self.settings['spotify_client_secret']);self.statusChanged.emit();self.notify('Credenciais salvas neste computador.')
        elif action=='forget_credentials':self.credentials.forget();self.saved_credentials=('','');self.settings.update(spotify_client_id='',spotify_client_secret='');self.persist();self.settingsChanged.emit();self.statusChanged.emit()
        elif action=='spotify_developers':QDesktopServices.openUrl(QUrl('https://developer.spotify.com/dashboard'))
        elif action=='spotify_connect':
            if not self.settings.get('spotify_client_id','').strip():self.notify('Informe o Client ID do Spotify.');return
            self.run_task(action,{},self.show_result)
        elif action=='spotify_disconnect':self.account.disconnect();self.statusChanged.emit()
        elif action=='logs':self.message.emit(tr('Detalhes'),'\n'.join(self.logs[-200:]) or tr('Sem registros.'))
        elif action=='failures':self.message.emit(tr('Falhas da fila'),'\n'.join(job.get('display_name',job['url'])+': '+job.get('last_error','') for job in self.jobs if job['state']=='Falhou') or tr('Nenhuma falha.'))
        elif action=='reset_tab_order':self.setSetting('tab_order',self.defaults['tab_order'])
        elif action=='toggle_tab':
            values=list(self.hiddenTabs);key=p['key']
            if key in ('catalog','downloads','queue'):return
            if key in values:values.remove(key)
            else:values.append(key)
            self.setSetting('hidden_tabs',values)
        elif action=='tab_move':
            values=list(self.settings['tab_order']);keys=next((keys for label,keys in TAB_GROUPS if p['key'] in keys),())
            positions=[index for index,key in enumerate(values) if key in keys]
            if p['key'] in values and values.index(p['key']) in positions:
                offset=positions.index(values.index(p['key']));target=offset+int(p['direction'])
                if 0<=target<len(positions):
                    source,destination=positions[offset],positions[target];values[source],values[destination]=values[destination],values[source];self.setSetting('tab_order',values)
        elif action=='shortcuts_reset':self.setSetting('shortcut_keys','{}')
        elif action=='shortcut_reset':
            from shortcut_options import validate_overrides
            values=json.loads(self.settings.get('shortcut_keys','{}'));values.pop(p['key'],None);self.setSetting('shortcut_keys',json.dumps(validate_overrides(values)))
        elif action=='shortcut_set':
            from shortcut_options import validate_overrides
            values=json.loads(self.settings.get('shortcut_keys','{}'));sequence=p['sequence'];sequence=sequence if sequence.startswith('<') or not sequence else '<'+sequence.replace('Ctrl+','Control-').replace('Alt+','Alt-').replace('Shift+','Shift-').replace('Enter','Return').replace(',','comma')+'>';values[p['key']]=sequence;self.setSetting('shortcut_keys',json.dumps(validate_overrides(values)))
        elif action in ('cache_info','cache_clear','prepare_tools','verify_tools','app_update','update_tools'):
            if action=='cache_clear' and (self.active or self.tasks or self.bridge.state['playing']):raise ValueError('Pare as operações antes de limpar o cache.')
            self.run_task(action,{},(lambda result:self.setSetting('ffmpeg',result)) if action=='prepare_tools' else (lambda result:self.show_result(result,notification=False)))
        else:raise ValueError('Ação desconhecida: '+action)
    @Slot(str,result=str)
    def taskLabel(self,key):
        labels={'collection':'Carregamento da playlist','search':'Pesquisa','compare_collection':'Conferência de arquivos locais','check_matches':'Conferência de versões','release_date':'Data de lançamento','convert':'Conversão','probe':'Leitura do áudio','audio_read':'Leitura dos metadados','audio_edit':'Edição dos metadados','normalize_preview':'Prévia normalizada','cover_crop':'Ajuste da capa','image_preview':'Prévia da imagem','image_export':'Exportação da imagem','spotify_connect':'Conexão com Spotify','prepare_tools':'Preparação das ferramentas','verify_tools':'Verificação das ferramentas','app_update':'Verificação de atualização','update_tools':'Atualização das ferramentas','cache_info':'Consulta ao cache','cache_clear':'Limpeza do cache'}
        label=tr(labels.get(key,'Operação em andamento'))
        return label[:1].lower()+label[1:]
    @Slot(str,result=str)
    def pageLabel(self,key):return tr(PAGES.get(key,key))
    @Property('QVariantList',notify=settingsChanged)
    def shortcutFields(self):
        from shortcut_options import PRIMARY,load_overrides,display_shortcut
        names={'next':'Próxima aba','previous':'Aba anterior','links':'Links','queue':'Fila','history':'Histórico','search':'Pesquisar','download':'Baixar agora','add':'Adicionar à fila','start':'Baixar fila','stop':'Parar fila','settings':'Configurações','metadata':'Metadados','help':'Atalhos','retry':'Tentar novamente','up':'Subir','down':'Descer','prioritize':'Priorizar','folder':'Abrir pasta','clear':'Limpar fila','log':'Detalhes','failures':'Falhas','view':'Alternar visualização','select-all':'Selecionar todas','scroll-up':'Rolar para cima','scroll-down':'Rolar para baixo'}
        values=load_overrides(self.settings.get('shortcut_keys','{}'))
        return [{'key':key,'label':tr(names.get(key,'Abrir aba '+key[4:] if key.startswith('tab:') else key)),'sequence':display_shortcut(values.get(key,default))} for key,default in PRIMARY.items()]
    def searched(self,result):
        self.options['catalogSearched']=True;self.catalog_records=result.get('tracks',[]);self.filter_catalog();self.notify(str(len(self.catalog_records))+' '+tr('resultados'))
    def filter_catalog(self):
        rows=getattr(self,'catalog_records',[])
        for option,key in (('filterArtist','artists'),('filterAlbum','album'),('filterVersion','title')):
            query=str(self.options.get(option,'')).casefold().strip()
            if query:rows=[row for row in rows if query in str(row.get(key,'')).casefold()]
        self.models['catalog'].replace([self.decorate_record(row,index) for index,row in enumerate(rows)]);self.options['selectedCatalog']=-1;self.optionsChanged.emit()
    def record_name(self,record):return ' - '.join(filter(None,[', '.join(record.get('artists',[])),record.get('title','')]))
    def collection_loaded(self,result):
        self.options['playlistTitle']=result.get('title','');self.optionsChanged.emit();self.models['playlists'].replace([dict(self.decorate_record(row,index),checked=True) for index,row in enumerate(result.get('tracks',[]))]);self.notify(result.get('note') or str(self.models['playlists'].count)+' '+tr('faixas'))
    def collection_compared(self,result):
        self.options['comparison']=result;self.optionsChanged.emit()
        for index,row in enumerate(result.get('items',result.get('tracks',[]))):
            if index<len(self.models['playlists'].rows):self.models['playlists'].update(index,comparison=row.get('state','review'))
        counts=result.get('counts',{})
        labels={'present':'Já disponíveis','missing':'Ausentes','review':'Precisam de revisão','queued':'Já na fila'}
        lines=[tr(label)+': '+str(counts.get(key,0)) for key,label in labels.items()]
        if result.get('has_previous'):
            lines.extend([tr('Adicionadas à playlist')+': '+str(result.get('new_count',0)),tr('Removidas da playlist')+': '+str(result.get('removed_count',0))])
        self.notify('Conferência concluída.')
        if self.settings.get('notifications_enabled',True):self.message.emit(tr('Conferência de arquivos locais'),'\n'.join(lines))
    def refresh_history(self):
        from datetime import datetime
        rows=self.library.history(self.options.get('historyQuery',''))
        for row in rows:
            try:row['date_display']=datetime.fromisoformat(row['date']).astimezone().strftime('%d/%m/%Y %H:%M')
            except (ValueError,TypeError):row['date_display']=row['date']
        self.models['history'].replace(rows)
        if rows:self.run_task('history_details',{'rows':rows},self.history_details_loaded,background=True)
    def history_details_loaded(self,rows):
        details={row['id']:row for row in rows}
        for index,row in enumerate(self.models['history'].rows):
            if row['id'] in details:self.models['history'].update(index,**details[row['id']])

    def clear_history(self):self.library.clear_history();self.refresh_history()
    def toggle_row(self,model,index,checked,notify=True):
        row=self.models[model].rows[index];self.models[model].update(index,checked=checked)
        if model=='queue':
            job=next((job for job in self.jobs if job['id']==row['id']),None)
            if job:job['checked']=checked
            if notify:self.statusChanged.emit()
    def refresh_queue(self):
        query=self.options.get('queueQuery','').casefold();state=self.options.get('queueState','Todos')
        rows=[job for job in self.jobs if (state=='Todos' or job['state']==state) and query in (job.get('display_name','')+' '+job['url']).casefold()]
        self.models['queue'].replace([self.queue_record(job) for job in rows]);self.refresh_queue_summary()
    def refresh_queue_summary(self):
        from queue_control import storage_report
        total,unknown,required,low=storage_report(self.jobs,int(self.settings.get('concurrent_downloads',1)),check_space=False)
        self.options['queueStorage']=str(round(total/1048576,1))+' MB · '+str(unknown)+' '+tr('sem estimativa');self.optionsChanged.emit();self.statusChanged.emit()
    def queue_record(self,job):
        info=dict(job.get('catalog_record') or {});info.update({key:value for key,value in (job.get('queue_info') or {}).items() if value})
        artists=info.get('artists') or []
        return dict(job,track_title=info.get('title') or job.get('display_name') or job['url'],track_artist=', '.join(artists) if isinstance(artists,list) else str(artists),track_album=info.get('album') or '',track_cover=info.get('cover_url') or '',track_duration=int(info.get('duration') or float(info.get('duration_ms') or 0)/1000))
    def save_queue(self):self.library.save_queue(self.jobs)
    def enqueue_tracks(self,records,start=False):
        added=[]
        for record in records:
            added.extend(self.enqueue([record['source_url']],overrides=dict(self.music_overrides(record),playlist_title=self.options['playlistTitle']),start=start,defer_start=True))
        if start:self.start_queue({job['id'] for job in added})
        return added
    def enqueue(self,urls,overrides=None,start=False,*,defer_start=False):
        from engine import validate_url
        from metadata import is_streaming_link
        from download_defaults import effective_download
        from duplicate_links import source_key
        config=self.config();config.pop('_account',None);config.pop('_root',None);added=[]
        for url in urls:
            url=url.strip()
            if not url:continue
            streaming=is_streaming_link(url)
            if not streaming:url=validate_url(url)
            job=dict(config,**(overrides or {}));job.update(url=url,streaming=streaming,simple_download_mode=config['mode']);job=effective_download(job)
            if config.get('detect_duplicates') and any(source_key(previous['url'])==source_key(url) and previous['mode']==job['mode'] and previous['state'] in ('Na fila','Em andamento','Concluído') for previous in self.jobs):continue
            job.update(id=uuid.uuid4().hex,state='Na fila',percent=0,checked=False,queue_original=len(self.jobs));job.setdefault('display_name',url)
            duplicate=self.library.find_duplicate(url,job['mode']) if config.get('detect_duplicates') else None
            if duplicate:self.confirm('Duplicata encontrada',duplicate,lambda job=job:self.add_duplicate(job,start));continue
            self.jobs.append(job);added.append(job)
            from queue_titles import supports_lookup
            if not job.get('catalog_record') and supports_lookup(url):self.title_lookup.submit(job['id'],url,(self.settings.get('spotify_client_id',''),self.settings.get('spotify_client_secret','')),config.get('cookies_file',''))
        self.refresh_queue();self.save_queue()
        if added:self.notify(str(len(added))+' '+tr('itens adicionados à fila'))
        if start and added and not defer_start:self.start_queue({job['id'] for job in added})
        return added
    def add_duplicate(self,job,start):
        self.jobs.append(job);self.refresh_queue();self.save_queue()
        if start:self.start_queue({job['id']})
    @Slot()
    def start_queue(self,scope=None):
        from queue_control import storage_report
        scope=None if scope is None else set(scope)
        if scope==set():return
        total,unknown,required,low=storage_report([job for job in self.jobs if job['state']=='Na fila' and (scope is None or job['id'] in scope)],int(self.settings.get('concurrent_downloads',1)))
        if low:self.confirm('Espaço em disco','O espaço livre pode não ser suficiente. Continuar?',lambda:self.begin_queue(scope,manual=True))
        else:self.begin_queue(scope,manual=True)
    def begin_queue(self,scope=None,*,manual=False):
        self.manual_queue=manual or (self.running and self.manual_queue)
        if not self.running:
            self.queue_scope=None if scope is None else set(scope)
            self.queue_attempted=set()
        elif self.queue_scope is not None:
            if scope is None:self.queue_scope=None
            else:self.queue_scope.update(scope)
        self.schedule_blocked=False;self.running=True;self.paused_all=False;self.timing.set_running(True);self.fill_queue()
    def in_queue_scope(self,job):return self.queue_scope is None or job['id'] in self.queue_scope
    def fill_queue(self):
        from advanced_options import schedule_allowed
        from performance import available_memory_mb,RESERVES
        if not self.running or (not self.manual_queue and not schedule_allowed(self.settings)):return
        limit=int(self.settings.get('concurrent_downloads',1));started=False
        pending=any(job['state']=='Na fila' and self.in_queue_scope(job) for job in self.jobs)
        reserve=RESERVES.get(self.settings.get('memory_reserve'),0)
        available=available_memory_mb() if reserve and pending and len(self.active)<limit else None
        waiting=available is not None and available<reserve
        if waiting:
            if not self.memory_waiting:self.notify('Aguardando memória livre para iniciar o próximo download.')
            self.memory_waiting=True
            return
        self.memory_waiting=False
        for job in self.jobs:
            if len(self.active)>=limit:break
            if job['state']!='Na fila' or not self.in_queue_scope(job):continue
            started=True;identity=job['id'];cancel=threading.Event();self.active[identity]={'cancel':cancel,'process':None,'operation':job.get('ui_operation','')};job['state']='Em andamento';job.pop('last_error',None)
            self.queue_attempted.add(identity)
            for key in ('_paused','_pause_reason','_resume_requested'):job.pop(key,None)
            config=dict(job);config.update({key:value for key,value in self.config().items() if key in ('auto_metadata','auto_match','confirm_version','ffmpeg','cookies_file','youtube_cookies_file','spotify_client_id','spotify_client_secret','worker_priority','conversion_threads')});config['_cleanup_work']=True
            from download_defaults import download_cookies
            config['cookies_file']=download_cookies(config['url'],config.get('cookies_file',''),config.get('youtube_cookies_file',''))
            self.launch_thread(lambda identity=identity,config=config,cancel=cancel:self.process_worker(identity,config,cancel,'engine.py'))
        if started:self.refresh_queue();self.save_queue()
        if not self.active and not any(job['state']=='Na fila' and self.in_queue_scope(job) for job in self.jobs):
            self.running=False;self.timing.set_running(False)
            states={job['id']:job['state'] for job in self.jobs}
            paused=any(job['state']=='Pausado' and self.in_queue_scope(job) for job in self.jobs)
            if not paused and self.queue_attempted and all(states.get(identity) in ('Concluído','Falhou') for identity in self.queue_attempted):
                self.notify('Fila finalizada');self.queue_finished()
    def process_worker(self,identity,config,cancel,script):
        from audio_tools import process_options
        from performance import priority_flags
        from engine import stop_process
        process=None;success=False;last_progress=0.
        try:
            if str(script).endswith('engine.py'):
                from spotify_metadata import prepare_spotify_config
                config=prepare_spotify_config(config,self.account)
            flags=process_options();flags['creationflags']=flags.get('creationflags',0)|priority_flags(config)
            process=subprocess.Popen([str(Path(sys.executable).with_name('python.exe')),'-u',str(ROOT/script)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8'),**flags)
            self._event.emit('process',{'id':identity,'process':process})
            if cancel.is_set():stop_process(process)
            else:
                process.stdin.write(json.dumps(config)+'\n');process.stdin.flush()
                for line in process.stdout:
                    try:event=json.loads(line)
                    except ValueError:continue
                    if event.get('type')=='progress':
                        now=time.monotonic()
                        if now-last_progress<.12 and event.get('status')!='finished':continue
                        last_progress=now
                    self._event.emit(identity,event)
                    if event.get('type')=='done':success=True
            success=process.wait()==0 and success
        except Exception as error:self._event.emit(identity,{'type':'error','message':str(error)})
        finally:
            if process:
                if process.poll() is None:stop_process(process);process.wait()
                for stream in (process.stdin,process.stdout):
                    if stream:stream.close()
            self._event.emit('finished',{'id':identity,'success':success,'cancelled':cancel.is_set()})
    def stop_queue(self):
        self.schedule_blocked=True;self.running=False;self.paused_all=True;self.timing.set_running(False)
        for identity in list(self.active):self.stop_job(identity)
        self.statusChanged.emit()
    def stop_job(self,identity):
        state=self.active.get(identity)
        if not state:return
        state['cancel'].set();process=state.get('process')
        if process:
            from engine import stop_process
            threading.Thread(target=stop_process,args=(process,),daemon=True).start()
    def queue_action(self,action,identity=''):
        selected=[job for job in self.jobs if job['id']==identity] if identity else [job for job in self.jobs if job.get('checked')]
        if action=='resume':selected=[job for job in selected if job['state'] in ('Na fila','Pausado','Cancelado','Falhou') or job.get('_paused')]
        if action in ('clear','cancel_all'):selected=list(self.jobs)
        if action in ('cancel','cancel_all'):selected=[job for job in selected if job['id'] in self.active or job['state'] in ('Na fila','Pausado')]
        undo_before=None
        if self.jobs and (action.startswith('sort') or action in ('up','down','priority','remove','clear','cancel','cancel_all')) and (selected or action.startswith('sort')):
            from copy import deepcopy
            undo_before=deepcopy(self.jobs)
        if action.startswith('sort'):
            from queue_control import sorted_keys
            jobs={job['id']:job for job in self.jobs};order=action.partition(':')[2] or 'Título';keys=sorted_keys(list(jobs),jobs,order);self.jobs=[jobs[key] for key in keys]
        elif action in ('up','down','priority'):
            identities={job['id'] for job in selected}
            if action=='priority':self.jobs=selected+[job for job in self.jobs if job['id'] not in identities]
            else:
                step=-1 if action=='up' else 1
                positions=range(len(self.jobs)) if step<0 else range(len(self.jobs)-1,-1,-1)
                for index in positions:
                    target=index+step
                    if self.jobs[index]['id'] in identities and 0<=target<len(self.jobs) and self.jobs[target]['id'] not in identities:
                        self.jobs[index],self.jobs[target]=self.jobs[target],self.jobs[index]
        else:
            for job in selected:
                if action in ('cancel','cancel_all','remove','clear'):
                    for key in ('_paused','_pause_reason','_resume_requested'):job.pop(key,None)
                    if job['id'] in self.active:job['_remove']=action in ('remove','clear');self.stop_job(job['id'])
                    elif action in ('remove','clear'):self.jobs.remove(job)
                    else:job['state']='Cancelado'
                elif action=='pause' and job['state'] in ('Na fila','Em andamento','Pausado'):
                    job['_pause_reason']='manual';job.pop('_resume_requested',None)
                    if job['id'] in self.active:job['_paused']=True;self.stop_job(job['id'])
                    else:job['state']='Pausado'
                elif action in ('retry','resume'):
                    if job['id'] not in self.active:
                        for key in ('_paused','_pause_reason','_resume_requested'):job.pop(key,None)
                        job['state']='Na fila'
                    elif action=='resume' and job.get('_paused'):job['_resume_requested']=True
        if undo_before is not None and undo_before!=self.jobs:
            self.undo_history.remember(undo_before,action,[job['id'] for job in selected]);self.statusChanged.emit()
        self.refresh_queue();self.save_queue()
        if action=='resume':self.start_queue({job['id'] for job in selected})

    @Slot(str,'QVariantMap')
    def replyChoice(self,identity,reply):
        if self._choice.get('identity')!=identity:return
        callback=self.choice_callbacks.pop(identity,None)
        if callback:callback(reply)
        elif identity in self.active:
            if reply.get('cancel'):self.stop_job(identity)
            process=self.active[identity].get('process')
            if not reply.get('cancel') and process and process.poll() is None:
                try:process.stdin.write(json.dumps(reply)+'\n');process.stdin.flush()
                except (OSError,ValueError):self.stop_job(identity)
        self._choice={};self.choiceChanged.emit();self.next_choice()
    def present_choice(self,identity,event,callback=None):
        if event.get('type')=='choose_media':
            from media_selection import output_choices
            event=dict(event,candidates=[dict(row,outputLabels=list(output_choices(row)),outputCodes=list(output_choices(row).values())) for row in event.get('candidates',[])])
        if callback:self.choice_callbacks[identity]=callback
        self.pending_choices.append(dict(event,identity=identity));self.next_choice()
    def next_choice(self):
        if not self._choice and self.pending_choices:self._choice=self.pending_choices.pop(0);self.choiceChanged.emit()
    def confirm(self,title,text,callback):
        identity=uuid.uuid4().hex;self.present_choice(identity,{'type':'confirm','title':tr(title),'message':str(text)},lambda reply:callback() if reply.get('yes') else None)
    @Slot(str,object)
    def on_event(self,identity,event):
        if self.closed:return
        if identity.startswith('task_'):
            action=event['action']
            if self.generations.get(action)!=event['revision']:return
            if identity=='task_result':
                callback=self.callbacks.get(action)
                try:
                    if callback:callback(event['result'])
                    else:self.show_result(event['result'])
                except Exception as error:self.notify(error)
            elif identity=='task_error':self.notify(event['error']);self.log(event['error'])
            elif identity=='task_progress':
                progress=event['event']
                if action in ('prepare_tools','update_tools'):
                    self.tool_progress=dict(progress,action=action);self.statusChanged.emit()
                self.notify(progress.get('message',''))
            else:self.tasks.pop(action,None);self.background_tasks.discard(action);self.statusChanged.emit()
            return
        if identity=='process':
            if event['id'] in self.active:self.active[event['id']]['process']=event['process']
            return
        if identity=='finished':
            key=event['id'];state=self.active.pop(key,None);job=next((job for job in self.jobs if job['id']==key),None)
            if job:
                if event['success']:self.timing.record_completion()
                job['state']='Pausado' if job.pop('_paused',False) else 'Cancelado' if event['cancelled'] else 'Concluído' if event['success'] else 'Falhou'
                if job.pop('_resume_requested',False):job['state']='Na fila'
                if job['state']!='Pausado':job.pop('_pause_reason',None)
                if job.pop('_remove',False):self.undo_history.record_finished_removal(job,event['success']);self.jobs.remove(job)
            self.pending_choices=[row for row in self.pending_choices if row['identity']!=key]
            if self._choice.get('identity')==key:self._choice={};self.choiceChanged.emit();self.next_choice()
            self.refresh_queue();self.save_queue();self.fill_queue();self.statusChanged.emit()
            if self.closing and not self.active:self.requestClose()
            return
        job=next((job for job in self.jobs if job['id']==identity),None);kind=event.get('type')
        if kind=='queue_title' and job:
            job['display_name']=event.get('title',job['url']);job['queue_info']=event.get('queue_info',{})
            if self.options.get('queueQuery'):self.refresh_queue()
            else:
                for index,row in enumerate(self.models['queue'].rows):
                    if row['id']==identity:self.models['queue'].update(index,**self.queue_record(job));break
                self.refresh_queue_summary()
            return
        if kind in CHOICES:self.present_choice(identity,event);return
        if kind=='done' and event.get('path') and job is None:self.library.add_history(event['path'],Path(event['path']).suffix.lstrip('.'));self.refresh_history();self.notify('Arquivo exportado.')
        if kind=='file' and event.get('path'):
            if job:
                paths=job.setdefault('output_files',[])
                if event['path'] not in paths:paths.append(event['path'])
                self.save_queue()
            self.library.add_history(event['path'],event.get('mode') or (job or {}).get('mode',''),(job or {}).get('url',''));self.refresh_history()
        if job:
            if kind=='progress':
                total=event.get('total') or event.get('total_bytes') or event.get('total_bytes_estimate') or 0;job['percent']=min(100,float(event.get('downloaded',event.get('downloaded_bytes',0)))/total*100) if total else float(event.get('percent',0) or 0)
                for index,row in enumerate(self.models['queue'].rows):
                    if row['id']==identity:self.models['queue'].update(index,percent=job['percent'])
            if kind=='error':job['last_error']=event.get('message','')
        if kind in ('error','log','stage'):self.log(event.get('message',''))
    def show_result(self,result,notification=True):
        if isinstance(result,dict) and result.get('available'):
            self.confirm('Atualização do ONDA',result.get('message','')+'\n'+tr('Abrir página da atualização?'),lambda:QDesktopServices.openUrl(QUrl(result.get('page') or result.get('url',''))));return
        if isinstance(result,dict) and result.get('path'):
            self.library.add_history(result['path'],Path(result['path']).suffix.lstrip('.'));self.refresh_history()
        text=result.get('message') if isinstance(result,dict) else str(result)
        if not text and isinstance(result,dict) and result.get('path'):text=tr('Arquivo salvo:')+'\n'+str(result['path'])
        text=text or json.dumps(result,ensure_ascii=False,default=str)
        self.notify(text)
        if not notification or self.settings.get('notifications_enabled',True):self.message.emit(tr('ONDA'),text)
    def pick(self,kind):
        from PySide6.QtWidgets import QFileDialog
        if kind in ('folder','ffmpeg'):
            path=QFileDialog.getExistingDirectory(None,tr('Escolher pasta'),self.settings['folder'])
            if path:self.setSetting(kind,path)
            return
        multiple=kind in ('converter','metadata','effects_queue')
        filters={'converter':'Mídia (*.mp3 *.m4a *.aac *.flac *.wav *.ogg *.opus *.mp4 *.mkv *.mov *.avi *.webm);;Todos os arquivos (*)','effects':'Áudio (*.mp3 *.m4a *.aac *.flac *.wav *.ogg *.opus)','metadata':'Áudio (*.mp3 *.m4a *.flac *.ogg *.opus *.wav)','image':'Imagens (*.png *.jpg *.jpeg *.webp *.gif *.svg)','cover_path':'Imagens (*.png *.jpg *.jpeg *.webp)','jukeboxLyrics':'Letras sincronizadas (*.lrc *.txt);;Todos os arquivos (*)','effectLyrics':'Letras sincronizadas (*.lrc *.txt);;Todos os arquivos (*)','lyrics_path':'Letras (*.lrc *.txt)','youtube_cookies':'Cookies (*.txt)','social_cookies':'Cookies (*.txt)'}
        if multiple:paths,_=QFileDialog.getOpenFileNames(None,tr('Escolher arquivo'),'',filters.get(kind,'Todos os arquivos (*)'))
        else:
            path,_=QFileDialog.getOpenFileName(None,tr('Escolher arquivo'),'',filters.get(kind,'Todos os arquivos (*)'));paths=[path] if path else []
        if not paths:return
        self.accept_files(kind,paths)
    def accept_files(self,kind,paths):
        if kind=='effects_queue':
            if not self.options['effectsQueue'] and self.options['effectsSource'] and self.options['duration']>0:
                self.options['effectsQueue']=[dict(source=self.options['effectsSource'],record=dict(self.options['effectsRecord']),duration=self.options['duration'],cover_url=self.options['effectsCover'])];self.options['effectsQueueIndex']=0
            def loaded(rows):
                for row in rows:
                    if row.get('error'):self.notify(row['error']);continue
                    row['cover_url']='data:image/png;base64,'+row['cover'] if row.get('cover') else ''
                    self.options['effectsQueue'].append(row)
                self.optionsChanged.emit()
            self.run_task('effects_queue_info',{'sources':paths},loaded);return
        if kind=='flac_import':self.replyChoice(self._choice['identity'],{'path':paths[0]})
        elif kind in ('social_cookies','youtube_cookies'):self.setSetting(kind,paths[0])
        elif kind=='converter':
            self.cancel_task('detect_silence');self.options['converterSources']=paths;self.options['silenceResults']=[]
            from video_converter import AUDIO_INPUT_EXTENSIONS
            self.options['converterFormat']='MP3' if any(Path(path).suffix.lower() in AUDIO_INPUT_EXTENSIONS for path in paths) else 'MP4'
        elif kind=='effects':
            self.cancel_task('effects_load')
            self.stop_preview();self.options.update(effectsQueueIndex=next((i for i,row in enumerate(self.options['effectsQueue']) if row['source']==paths[0]),-1),effectsOnlineRecord={},effectsSource=paths[0],effectsRecord={'title':Path(paths[0]).stem},effectsCover='',position=0,duration=0);self.load_lyrics(str(Path(paths[0]).with_suffix('.lrc')));self.run_task('effects_info',{'source':paths[0]},self.effects_loaded)
        elif kind=='cover_path':
            self.options['cover_path']=paths[0];self.options['metadataCover']=QUrl.fromLocalFile(paths[0]).toString()
        elif kind=='jukeboxLyrics':
            from synced_lyrics import read_lrc
            self._jukebox_lyrics=read_lrc(paths[0]);self._lyric_source=str((self.bridge.model or {}).get('source',''))
        elif kind=='effectLyrics':self.load_lyrics(paths[0],selected=True)
        elif kind=='metadata':self.options['metadataFields']={};self.options['metadataSources']=paths;self.run_task('audio_read',{'source':paths[0]},self.audio_loaded)
        elif kind=='image':
            self.cancel_task('image_preview');self.options['imageInfo']={};self.options['imageUrl']='';self.options['imageSource']=paths[0];self.options['imagePreview']=QUrl.fromLocalFile(paths[0]).toString();self.run_task('image_info',{'source':paths[0]},lambda result:self.setOption('imageInfo',dict(self.options.get('imageInfo',{}),**result)))
        else:self.options[kind]=paths[0]
        self.optionsChanged.emit()
    def convert(self):
        from PySide6.QtWidgets import QFileDialog
        sources=list(self.options['converterSources'])
        if not sources:raise ValueError('Escolha um arquivo para converter.')
        fmt=self.options['converterFormat']
        if len(sources)>1:target=QFileDialog.getExistingDirectory(None,tr('Pasta de destino'),self.settings['folder'])
        else:target,_=QFileDialog.getSaveFileName(None,tr('Salvar arquivo'),str(Path(self.settings['folder'])/(Path(sources[0]).stem+' - convertido.'+fmt.lower())),fmt+' (*.'+fmt.lower()+')')
        if target:self.convert_to(sources,target)
    def convert_to(self,sources,target):
        config={key:self.options[key] for key in ('video_quality','video_resolution','video_bitrate','audio_bitrate','video_fps','video_audio')};config.update(source=sources[0],output=target,video_format=self.options['converterFormat'],trim_silence=self.options['trimSilence'],silence_results=self.options['silenceResults'])
        if len(sources)>1:config.update(sources=sources,output_folder=target)
        self.run_task('convert',config,self.show_result)
    def effects_loaded(self,result):
        if self.options.get('effectsOnlineRecord'):result['record'].update(self.options['effectsOnlineRecord'])
        self.options.update(effectsRecord=result['record'],effectsCover=('data:image/png;base64,'+result['cover']) if result.get('cover') else '',duration=result['duration'])
        if not self.options['effectsCover'] and self.options.get('effectsOnlineRecord'):self.options['effectsCover']=self.options['effectsOnlineRecord'].get('cover_url','')
        if not self.lyrics:self.dispatch('lyrics_online',{'automatic':True,'jukebox':False})
        self.optionsChanged.emit()
    def audio_loaded(self,result):
        cover=('data:image/png;base64,'+result['cover']) if result.get('cover') else ''
        self.options['metadata']=result['record'];self.options['metadataCover']=cover;self.options['originalCover']=cover;self.optionsChanged.emit()
    def image_result(self,result):
        if result.get('image_info'):self.options['imageInfo']=result['image_info'];self.optionsChanged.emit()
        if result.get('preview'):self.options['imagePreview']=QUrl.fromLocalFile(result['path']).toString()+'?v='+str(time.time());self.optionsChanged.emit()
        else:self.show_result(result)
    def edit_audio(self):
        sources=self.options['metadataSources']
        if not sources:raise ValueError('Escolha um arquivo de áudio.')
        from audio_library import FIELDS
        changes={key:value for key,value in self.options['metadata'].items() if key in FIELDS and (len(sources)==1 or self.options['metadataFields'].get(key,False))}
        if isinstance(changes.get('artists'),str):changes['artists']=[value.strip() for value in changes['artists'].split(',') if value.strip()]
        config=dict(source=sources[0],changes=changes,edit_metadata=True,overwrite_original=self.options['overwrite_original'],normalize_volume=self.options['normalize_volume'],cover_path=self.options['cover_path'],lyrics_path=self.options['lyrics_path'])
        if len(sources)>1:config['sources']=[{'source':source} for source in sources]
        self.run_task('audio_edit',config,self.show_result)
    def export_effects(self):
        from PySide6.QtWidgets import QFileDialog
        source=self.options['effectsSource']
        if not source:raise ValueError('Abra um arquivo de áudio primeiro.')
        fmt=self.options['effectFormat'].lower();target,_=QFileDialog.getSaveFileName(None,tr('Exportar música'),str(Path(source).with_name(Path(source).stem+' - efeitos.'+fmt)),'Áudio (*.'+fmt+')')
        if not target:return
        if Path(source).resolve()==Path(target).resolve():raise ValueError('Escolha outro nome para preservar o original.')
        identity=uuid.uuid4().hex;cancel=threading.Event();self.active[identity]={'cancel':cancel,'process':None,'operation':'effects_export'};self.statusChanged.emit()
        config={key:self.options[key] for key in ('speed','reverb','keep_pitch')};config.update(source=source,output=target,ffmpeg=self.settings.get('ffmpeg',''),replace=Path(target).exists(),bitrate=320,conversion_threads=self.settings.get('conversion_threads','Automático'))
        self.launch_thread(lambda:self.process_worker(identity,config,cancel,'effects_worker.py'));self.notify('Exportando a música inteira…')
    def settings_file_action(self,action):
        from PySide6.QtWidgets import QFileDialog
        from advanced_options import export_settings,import_settings
        if action=='restore_settings':
            self.confirm('Restaurar configurações','Restaurar todas as configurações?',self.reset_settings);return
        if action in ('import_settings','import_playlist'):
            path,_=QFileDialog.getOpenFileName(None,tr('Importar arquivo'),'','Arquivos (*.json *.txt *.csv *.m3u *.m3u8)')
            if not path:return
            raw=Path(path).read_text(encoding='utf-8-sig')
            if action=='import_settings':
                for key,value in import_settings(json.loads(raw),'windows').items():self.setSetting(key,value)
            else:
                from playlist_import import load_text
                from playlist_files import load_csv
                result=(load_csv if Path(path).suffix.lower()=='.csv' else load_text)(raw,int(self.settings['playlist_limit']));self.collection_loaded(result)
            return
        path,_=QFileDialog.getSaveFileName(None,tr('Exportar arquivo'),'onda.json' if action=='export_settings' else 'onda.m3u','JSON (*.json)' if action=='export_settings' else 'M3U (*.m3u);;Texto (*.txt)')
        if not path:return
        if action=='export_settings':text=json.dumps(export_settings(self.settings,'windows'),ensure_ascii=False,indent=2)
        else:
            from playlist_files import export_text
            rows=self.models['playlists'].rows if action=='export_playlist' else [dict(title=row['name'],source_url=row['path']) for row in self.models['history'].rows];text=export_text(rows,m3u=Path(path).suffix.lower()=='.m3u')
        Path(path).write_text(text,encoding='utf-8');self.notify('Arquivo exportado.')
    def reset_settings(self):
        for key,value in self.defaults.items():self.setSetting(key,value)
    def queue_finished(self):
        action=self.settings.get('finish_action','Nenhuma')
        if self.settings.get('notifications_enabled',True) and action in ('Som','Som e notificação') and os.name=='nt':
            import winsound
            winsound.PlaySound('SystemNotification',winsound.SND_ALIAS|winsound.SND_ASYNC)
        if self.settings.get('notifications_enabled',True) and self.tray and action in ('Notificação','Som e notificação'):self.tray.show();self.tray.showMessage('ONDA',tr('Fila finalizada'))
        if action=='Desligar PC':self.confirm('Desligar PC','A fila terminou. Desligar o PC após 60 segundos?',self.shutdown_countdown)
    def shutdown_countdown(self):
        self.shutdown_timer.start();self.present_choice(uuid.uuid4().hex,{'type':'power_countdown','title':tr('Desligar PC'),'message':tr('O PC será desligado após 60 segundos.')},lambda reply:self.shutdown_timer.stop())
    def perform_shutdown(self):
        if not self.active and not self.tasks:subprocess.run(['shutdown.exe','/s','/t','0'],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    def clipboard_changed(self):
        if not self.settings.get('clipboard_links'):return
        from clipboard_links import recognize_link
        candidate=recognize_link(QGuiApplication.clipboard().text())
        if candidate and candidate['key'] not in self.clipboard_seen:
            self.clipboard_seen.add(candidate['key']);self.confirm('Link copiado','Deseja iniciar o download?\n'+candidate['url'],lambda:self.enqueue([candidate['url']],start=True))
    def tick(self):
        now=time.monotonic();elapsed=max(0,now-getattr(self,'effects_timer_clock',now));self.effects_timer_clock=now
        if self.player.active and self.preview_kind=='effects':
            stop=self.options['effectsStopRemaining'];switch=self.options['effectsSwitchRemaining']
            if stop>0:
                self.options['effectsStopRemaining']=max(0,stop-elapsed)
                if self.options['effectsStopRemaining']==0:
                    self.invoke('effects_stop',{});self.options['effectsStopMinutes']=0
            if switch>0 and self.player.active:
                self.options['effectsSwitchRemaining']=max(0,switch-elapsed)
                if self.options['effectsSwitchRemaining']==0:
                    self.play_effects_entry(self.options['effectsQueueIndex']+1)
                    self.options['effectsSwitchRemaining']=self.options['effectsTrackMinutes']*60
            if stop>0 or switch>0:self.optionsChanged.emit()
        if self.running and time.monotonic()-getattr(self,'last_clock',0)>1:self.last_clock=time.monotonic();self.statusChanged.emit()
        for _ in range(30):
            try:identity,event=self.title_events.get_nowait()
            except queue.Empty:break
            self.on_event(identity,event)
        from advanced_options import schedule_allowed
        allowed=schedule_allowed(self.settings)
        if not allowed:self.schedule_blocked=False
        if self.running and not allowed and not self.manual_queue:
            for job in self.jobs:
                if job['id'] in self.active and not job.get('_paused'):
                    job['_paused']=True;job['_pause_reason']='schedule';self.stop_job(job['id'])
        elif (allowed or (self.running and self.manual_queue)) and not self.schedule_blocked:
            for job in self.jobs:
                if allowed and job['state']=='Pausado' and job.get('_pause_reason')=='schedule':
                    job['state']='Na fila';job.pop('_pause_reason',None)
            if self.running:self.fill_queue()
            elif self.settings.get('schedule_enabled') and any(job['state']=='Na fila' for job in self.jobs):self.begin_queue()
        if self.shell:
            active=[job['percent'] for job in self.jobs if job['id'] in self.active];self.shell.progress(sum(active)/len(active) if active else None,self.paused_all,self.settings.get('taskbar_progress',True))
        self.effects_tails=[tail for tail in self.effects_tails if tail.active]
        if self.preview_kind=='effects' and getattr(self,'effects_transport',False) and not self.options['effectsPaused']:
            index=self.options['effectsQueueIndex'];rows=self.options['effectsQueue']
            remaining=(self.options['duration']-self.player.position_snapshot())/max(.5,self.options['speed']/100)
            fade=self.effects_transition_seconds()
            if index+1<len(rows) and (self.player.active and remaining<=fade or self.options['previewActive'] and not self.player.active):self.play_effects_entry(index+1)
        for text in self.player.messages():self.notify(text)
        if self.options['previewActive']!=self.player.active:
            if not self.player.active and self.preview_kind=='effects' and getattr(self,'effects_transport',False) and not self.options['effectsPaused']:
                self.options['position']=self.options['duration']
            self.options['previewActive']=self.player.active;self.optionsChanged.emit()
        if self.shutdown_timer.isActive() and (self.active or self.tasks):self.shutdown_timer.stop()
        if self.player.active and self.preview_kind=='effects' and not self.preview_timer.isActive():
            self.options['position']=self.player.position_snapshot()
            from synced_lyrics import line_at
            self.options['lyricText']=line_at(self.lyrics,self.options['position']) if self.settings.get('synced_lyrics') else '';self.optionsChanged.emit()
    def setup_shell(self):
        from PySide6.QtWidgets import QSystemTrayIcon,QMenu
        from types import SimpleNamespace
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray=QSystemTrayIcon(QGuiApplication.windowIcon(),self);self.tray_menu=QMenu();self.tray_menu.addAction(tr('Abrir ONDA'),self.restore);self.tray_menu.addAction(tr('Baixar fila'),self.start_queue);self.tray_menu.addAction(tr('Parar fila'),self.stop_queue);self.tray_menu.addAction(tr('Sair'),lambda:self.requestClose(True));self.tray.setContextMenu(self.tray_menu);self.tray.activated.connect(self.tray_activated)
        try:
            from windows_shell import WindowsShell
            self.shell=WindowsShell(SimpleNamespace(winfo_id=lambda:int(self.window.winId())))
        except OSError:self.shell=None
    def tray_activated(self,reason):
        from PySide6.QtWidgets import QSystemTrayIcon
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,QSystemTrayIcon.ActivationReason.DoubleClick):
            self.restore()
    @Slot(bool)
    def suspendShortcuts(self,value):
        self.shortcuts_suspended=value
        for shortcut in self.shortcuts:shortcut.setEnabled(not value)

    @Slot(str,int,int,result=bool)
    def captureShortcut(self,action,key,modifiers):
        from shortcut_options import canonical
        keys={Qt.Key.Key_Return:'Return',Qt.Key.Key_Enter:'Return',Qt.Key.Key_Tab:'Tab',Qt.Key.Key_Backtab:'Tab',Qt.Key.Key_Up:'Up',Qt.Key.Key_Down:'Down',Qt.Key.Key_Left:'Left',Qt.Key.Key_Right:'Right',Qt.Key.Key_Home:'Home',Qt.Key.Key_End:'End',Qt.Key.Key_PageUp:'Prior',Qt.Key.Key_PageDown:'Next',Qt.Key.Key_Delete:'Delete',Qt.Key.Key_Backspace:'BackSpace',Qt.Key.Key_Comma:'comma',Qt.Key.Key_Space:'space'}
        name=keys.get(key)
        if Qt.Key.Key_F1<=key<=Qt.Key.Key_F24:name='F'+str(key-Qt.Key.Key_F1+1)
        elif Qt.Key.Key_A<=key<=Qt.Key.Key_Z or Qt.Key.Key_0<=key<=Qt.Key.Key_9:name=chr(key).lower()
        mods=[name for flag,name in ((Qt.KeyboardModifier.ControlModifier,'Control'),(Qt.KeyboardModifier.AltModifier,'Alt'),(Qt.KeyboardModifier.ShiftModifier,'Shift')) if modifiers & flag.value]
        if key==Qt.Key.Key_Backtab and 'Shift' not in mods:mods.append('Shift')
        try:
            if not name or modifiers & Qt.KeyboardModifier.MetaModifier.value:raise ValueError('Atalho inválido.')
            self.dispatch('shortcut_set',{'key':action,'sequence':canonical('<'+'-'.join(mods+[name])+'>')})
            return True
        except ValueError as error:
            self.notify(error);self.message.emit(tr('Atalhos'),tr(str(error)));return False

    def bind_shortcuts(self):
        from shortcut_options import effective_bindings,display_shortcut
        for shortcut in self.shortcuts:shortcut.setEnabled(False);shortcut.deleteLater()
        self.shortcuts=[]
        if self.window is None:return
        for sequence,action in effective_bindings(self.settings.get('shortcut_keys','{}')).items():
            shortcut=QShortcut(QKeySequence(display_shortcut(sequence).replace('Prior','PgUp').replace('Next','PgDown')),self.window);shortcut.activated.connect(lambda action=action:self.shortcut(action));shortcut.setEnabled(not self.shortcuts_suspended);self.shortcuts.append(shortcut)
    def shortcut(self,action):
        pages=self.settings.get('tab_order',list(PAGES));visible=[key for key in pages if key not in self.hiddenTabs]
        if action.startswith('tab:'):
            index=int(action[4:])
            if index<len(visible):self.selectNavigationPage(visible[index])
        elif action in ('next','previous'):
            key='effects' if self._page=='jukebox' else self._page;self.selectNavigationPage(visible[(visible.index(key)+(1 if action=='next' else -1))%len(visible)])
        elif action in ('links','queue','history','search'):self.selectPage({'links':'downloads','search':'catalog'}.get(action,action))
        elif action=='settings':self.showSettings()
        elif action=='metadata':self.showMetadata()
        elif action=='help':self.showShortcuts()
        elif action=='start':self.start_queue()
        elif action=='stop':self.stop_queue()
        elif action=='download':self.enqueue(self.options['links'].splitlines(),start=True)
        elif action=='add':self.enqueue(self.options['links'].splitlines())
        elif action in ('retry','up','down','prioritize','clear'):self.queue_action('priority' if action=='prioritize' else action)
        elif action=='folder':QDesktopServices.openUrl(QUrl.fromLocalFile(self.settings['folder']))
        elif action in ('log','failures'):self.dispatch('logs' if action=='log' else action,{})
    @Slot()
    def restore(self):
        state=self.window.windowState()
        if state!=Qt.WindowState.WindowMinimized:self.remember_window_state(state)
        if self.restore_state==Qt.WindowState.WindowMaximized:self.window.showMaximized()
        elif self.restore_state==Qt.WindowState.WindowFullScreen:self.window.showFullScreen()
        else:self.window.showNormal()
        self.window.raise_();self.window.requestActivate()
        if self.tray:self.tray.hide()
    @Slot()
    @Slot(bool)
    def requestClose(self,force=False):
        self.save_window_layout()
        if not force and self.settings.get('close_behavior')=='Minimizar para a bandeja' and self.tray:self.persist();self.save_queue();self.tray.show();self.window.hide();return
        if self.tasks:self.notify('Cancele ou aguarde as operações antes de fechar o ONDA.');return
        if self.active:self.closing=True;self.stop_queue();return
        self.shutdown_timer.stop();self.persist();self.save_queue();QGuiApplication.exit(0)
    def shutdown(self):
        if self.closed:return
        for tail in self.effects_tails:tail.close()
        self.save_window_layout()
        if hasattr(self,'window_save_timer'):self.window_save_timer.stop()
        self.closed=True;self.shutdown_timer.stop();self.title_lookup.shutdown();self.preview_timer.stop();self.timer.stop();self.save_timer.stop();self.player.close();self.persist();self.save_queue()
        for cancel in self.tasks.values():cancel.set()
        for identity in list(self.active):self.stop_job(identity)
        self.bridge.config_provider=None
        if self.shell:self.shell.close();self.shell=None
        if self.tray:self.tray.hide();self.tray.deleteLater();self.tray=None
        deadline=time.monotonic()+3
        for thread in self.tasks_threads:thread.join(timeout=max(0,deadline-time.monotonic()))

    def music_overrides(self,record):
        from engine import MODES
        mode=MODES.get(self.settings.get('playlist_mode'),'mp3')
        if mode not in ('mp3','m4a','flac','original'):mode='mp3'
        return {'catalog_record':record,'display_name':self.record_name(record),'playlist':False,'mode':mode,'audio_quality':self.settings.get('playlist_m4a_quality','256 kbps') if mode=='m4a' else self.settings.get('playlist_mp3_quality','320 kbps')}
    def update_playlist(self):
        def loaded(result):
            self.collection_loaded(result)
            def compared(value):
                self.collection_compared(value)
                self.enqueue_tracks([self.models['playlists'].rows[item['index']] for item in value['items'] if item['state']=='missing'],start=True)
            self.run_task('compare_collection',{'url':self.options['playlistUrl'],'tracks':self.models['playlists'].rows,'history':self.library.comparison_history(),'queued':self.jobs,'database':str(self.library.path)},compared)
        self.run_task('collection',{'url':self.options['playlistUrl']},loaded)
    @Slot(bool)
    def setMiniPlayerActive(self,active):self._mini_active=active
    @Slot(QObject,bool)
    def pinPlayer(self,window,pinned):
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            function=ctypes.windll.user32.SetWindowPos
            function.argtypes=[wintypes.HWND,wintypes.HWND,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_uint]
            function.restype=wintypes.BOOL
            if not function(int(window.winId()),-1 if pinned else -2,0,0,0,0,0x0001|0x0002|0x0010):
                raise ctypes.WinError()
        else:
            geometry=window.geometry();window.setFlag(Qt.WindowStaysOnTopHint,pinned);window.show();window.setGeometry(geometry)
    @Slot()
    def openLyrics(self):self.lyricsRequested.emit()
    @Slot(result='QVariantMap')
    def lyricsFrame(self):
        from synced_lyrics import karaoke_at
        jukebox=self._page=='jukebox'
        source=str((self.bridge.model or {}).get('source','')) if jukebox else self.options['effectsSource']
        position=self.options['position'];duration=self.options['duration']
        if jukebox:
            model=self.bridge.model or {};beats=model.get('beats',[]);index=min(int(self.bridge._position),max(0,len(beats)-2))
            position=beats[index]+(beats[index+1]-beats[index])*self.bridge._phase if len(beats)>1 else 0
            duration=model.get('duration',0)
        key=source if jukebox else 'effects'
        if jukebox and getattr(self,'_lyric_source',None)!=key:
            self._lyric_source=key
            from synced_lyrics import read_lrc
            try:self._jukebox_lyrics=read_lrc(str(Path(source).with_suffix('.lrc')))
            except (OSError,ValueError):self._jukebox_lyrics=[]
            if not self._jukebox_lyrics and source:QTimer.singleShot(0,lambda:self.dispatch('lyrics_online',{'automatic':True,'jukebox':True}))
        rows=(getattr(self,'_jukebox_lyrics',[]) or (self.lyrics if source==self.options['effectsSource'] else [])) if jukebox else self.lyrics
        import bisect
        active=bisect.bisect_right(rows,position,key=lambda row:row[0])-1
        import re
        lines=[dict(time=row[0],text=re.sub(r'<[^>]+>','',row[1])) for index,row in enumerate(rows)]
        return dict(text=karaoke_at(rows,position),lines=lines,active=active,position=position,duration=duration,jukebox=jukebox)
    @Slot(float,bool)
    def seekLyrics(self,seconds,jukebox):
        if jukebox:
            import bisect
            beats=(self.bridge.model or {}).get('beats',[])
            if beats:self.bridge.seek(max(0,bisect.bisect_right(beats,seconds)-1))
        else:self.setOption('position',seconds)
    def load_lyrics(self,path,selected=False):
        from synced_lyrics import read_lrc,line_at
        try:
            rows=read_lrc(path) if selected or Path(path).is_file() else []
            if selected and not rows:raise ValueError('Nenhum tempo válido na letra LRC.')
        except (ValueError,OSError) as error:
            if selected:
                self.message.emit(tr('Importar letra LRC'),str(error));return
            rows=[]
        self.lyrics=rows
        self.options['effectLyricsName']=Path(path).name if rows else ''
        if selected:self.setSetting('synced_lyrics',True)
        self.options['lyricText']=line_at(rows,self.options['position']) if self.settings.get('synced_lyrics') else ''
        self.optionsChanged.emit()
    def start_preview(self,source,kind,identity=None,processed=None,**options):
        self.preview_timer.stop();self.cancel_task('normalize_preview');self.preview_kind=kind;self.preview_source=identity or source
        self.player.play(source,self.settings.get('ffmpeg',''),**options)
        self.options.update(previewActive=self.player.active,previewKind=kind,previewSource=self.preview_source,previewProcessed=(self.last_preview_processed if kind=='effects' else bool(processed)))
        self.optionsChanged.emit()
    def stop_preview(self):
        for tail in self.effects_tails:tail.stop()
        self.effects_tails=[]
        self.preview_timer.stop();self.cancel_task('normalize_preview');self.player.stop();self.preview_kind='';self.preview_source=''
        self.options.update(previewActive=False,previewKind='',previewSource='');self.optionsChanged.emit()
    def effects_transition_seconds(self):
        return max(1,min(10,int(self.settings.get('jukebox_transition_seconds',2)))) if self.settings.get('jukebox_gradual_transition',True) else 0
    def play_effects_entry(self,index):
        rows=self.options['effectsQueue']
        if not 0<=index<len(rows):return
        if self.bridge.state.get('playing') and not self.bridge.state.get('paused'):self.bridge.playPause()
        row=rows[index];fade=min(self.effects_transition_seconds(),row['duration']/2)
        from audio_tools import PreviewPlayer
        if self.player.active and self.preview_kind=='effects' and fade:
            outgoing=self.player;position=outgoing.position_snapshot()
            remaining=(self.options['duration']-position)/max(.5,self.options['speed']/100)
            if remaining>fade+.5:
                outgoing.play(self.options['effectsSource'],self.settings.get('ffmpeg',''),speed=self.options['speed'],reverb=self.options['reverb'],start=position,duration=fade,keep_pitch=self.options['keep_pitch'],full_track=True,volume=self.options['effectsVolume'],fade_out=fade)
            self.effects_tails.append(outgoing);self.player=PreviewPlayer()
        else:self.player.stop()
        self.preview_timer.stop();self.options.update(effectsSource=row['source'],effectsRecord=row['record'],effectsCover=row.get('cover_url',''),duration=row['duration'],position=0,effectsQueueIndex=index,effectsPaused=False)
        self.load_lyrics(str(Path(row['source']).with_suffix('.lrc')))
        self.effects_transport=True;self.last_preview_processed=True;self.effects_fade_in=fade
        self.play_effects_preview();self.effects_fade_in=0
        self.dispatch('lyrics_online',{'automatic':True,'jukebox':False})
    def play_effects_preview(self):
        processed=self.last_preview_processed
        if not self.options['effectsSource']:raise ValueError('Escolha um arquivo de áudio.')
        transport=getattr(self,'effects_transport',False)
        duration=max(.1,(self.options['duration']-self.options['position'])/(self.options['speed']/100)) if transport else 25
        self.options['effectsPaused']=False
        self.start_preview(self.options['effectsSource'],'effects',speed=self.options['speed'] if processed else 100,reverb=self.options['reverb'] if processed else 0,start=self.options['position'],duration=duration,keep_pitch=self.options['keep_pitch'],full_track=transport,volume=self.options['effectsVolume'],fade_in=getattr(self,'effects_fade_in',0),fade_out=self.effects_transition_seconds() if transport else 0)
    @Slot('QVariantMap')
    def receiveDrop(self,payload):
        paths=[QUrl(url).toLocalFile() for url in payload.get('urls',[]) if QUrl(url).isLocalFile()]
        if paths:self.confirm('Abrir arquivos no ONDA',str(len(paths))+' '+tr('arquivos selecionados'),lambda:(self.accept_files('converter',paths),self.selectPage('converter')));return
        from clipboard_links import recognize_link
        links=[]
        for line in payload.get('text','').splitlines():
            candidate=recognize_link(line)
            if candidate:links.append(candidate['url'])
        if links:self.confirm('Adicionar à fila','\n'.join(links),lambda:self.enqueue(links))

    def decorate_record(self,row,index):
        from metadata import display_release_date
        url=row.get('source_url','');provider='deezer' if 'deezer' in url else 'spotify' if 'spotify' in url else 'apple_music' if 'apple' in url else 'youtube'
        label={'deezer':'Deezer','spotify':'Spotify','apple_music':'Apple Music','youtube':'YouTube'}[provider]
        return dict(row,id=str(index),artist=', '.join(row.get('artists',[])),platform=label,platform_key=provider,platform_icon=QUrl.fromLocalFile(str(ROOT/'assets/platforms'/(provider+'.png'))).toString(),release_date=display_release_date(row.get('release_date','')))

    @Property('QVariantList',notify=optionsChanged)
    def catalogChoices(self):return [{'label':self.record_name(row),'index':index} for index,row in enumerate(self.models['catalog'].rows)]
    @Slot(int,int,result=str)
    def compareText(self,left,right):
        rows=self.models['catalog'].rows
        if not (0<=left<len(rows) and 0<=right<len(rows)):return tr('Busque pelo menos dois resultados para comparar.')
        a,b=rows[left],rows[right]
        from duplicate_links import source_key
        if left==right or source_key(a.get('source_url'))==source_key(b.get('source_url')):return tr('Essa música já foi selecionada. Escolha outro resultado para comparar.')
        from edition_evidence import differences
        lines=[]
        for key,label in (('title','Título'),('artists','Artistas'),('album','Álbum'),('release_date','Data'),('duration_ms','Duração (ms)'),('isrc','ISRC'),('platform','Catálogo')):
            values=[', '.join(row.get(key) or []) if key=='artists' else str(row.get(key) or '—') for row in (a,b)];lines.append(tr(label)+': '+values[0]+'  |  '+values[1])
        return '\n\n'.join(lines+['; '.join(differences(a,b)) or tr('Sem divergências explícitas; isso não comprova a mesma gravação.')])
    def cover_cropped(self,result):self.options['cover_path']=result['path'];self.options['metadataCover']=QUrl.fromLocalFile(result['path']).toString();self.optionsChanged.emit()
    def matches_checked(self,result):
        for index,row in enumerate(self.models['playlists'].rows):
            if row['source_url'] in result:self.models['playlists'].update(index,comparison=result[row['source_url']])
        self.notify('Conferência concluída.')
    @Property('QVariantList',notify=settingsChanged)
    def navigation(self):
        icons={'catalog':'E721','downloads':'E71B','queue':'E8FD','playlists':'E93C','history':'E81C','images':'EB9F','converter':'E8AB','effects':'E768','metadata':'E8D2'}
        order=self.settings.get('tab_order',self.defaults['tab_order'])
        rows=[]
        for label,keys in TAB_GROUPS:
            rows.append({'group':label})
            members=[key for key in order if key in keys]
            rows.extend({'name':PAGES[key],'key':key,'icon':chr(int(icons[key],16)),'canMoveUp':index>0,'canMoveDown':index<len(members)-1} for index,key in enumerate(members))
        return rows

    @Slot(int,result=str)
    def clock(self,seconds):
        from queue_timing import duration_text
        return duration_text(seconds)
