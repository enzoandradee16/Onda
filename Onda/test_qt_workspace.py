"""Functional regression tests for the all-Qt desktop. No public network."""
import functools,http.server,json,os,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
TOOLS=Path(os.environ.get('LOCALAPPDATA',''))/'Onda/tools/ffmpeg/9.0.2'
sys.path.insert(0,str(ROOT.parent/'.venv/qt-packages'))

@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Optional Qt desktop tests')
class NativeDesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([]);cls.app.setQuitOnLastWindowClosed(False)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.env=patch.dict(os.environ,{'LOCALAPPDATA':self.temp.name,'ONDA_ALIAS_CACHE_ROOT':str(self.root/'cache'),'NO_PROXY':'127.0.0.1,localhost'});self.env.start()
        from preferences import PreferenceStore
        self.store=PreferenceStore();self.store.save({'check_updates':False,'clipboard_links':False,'folder':str(self.root/'out'),'ffmpeg':str(TOOLS),'mode':'Áudio · MP3 (320 kbps)','finish_action':'Nenhuma'})
        from qt_jukebox_ui import JukeboxBridge
        from qt_workspace_ui import DesktopWorkspace
        self.bridge=JukeboxBridge(self.store);self.ws=DesktopWorkspace(self.bridge);self.ws.settings['ffmpeg']=str(TOOLS)
    def tearDown(self):
        self.ws.shutdown();self.bridge.shutdown();self.env.stop();self.temp.cleanup()
    def wait_for(self,predicate,timeout=10000):
        from PySide6.QtCore import QTimer,QEventLoop
        deadline=time.monotonic()+timeout/1000
        while not predicate():
            self.assertLess(time.monotonic(),deadline,self.ws.status+' '+str(self.ws.logs[-3:]))
            loop=QEventLoop();QTimer.singleShot(15,loop.quit);loop.exec()
    def settle(self):
        from PySide6.QtCore import QTimer,QEventLoop
        loop=QEventLoop();QTimer.singleShot(50,loop.quit);loop.exec()
    def task_done(self,name):self.wait_for(lambda:name not in self.ws.tasks,30000)
    def tone(self,name='source.wav'):
        from test_jukebox import song
        path=self.root/name;song(path);return path
    def test_restore_unminimizes_existing_window(self):
        from unittest.mock import Mock
        from PySide6.QtCore import Qt
        self.ws.window=Mock();self.ws.window.windowState.return_value=Qt.WindowMinimized;self.ws.restore()
        self.ws.window.showNormal.assert_called_once()
        self.ws.window.requestActivate.assert_called_once()

    def test_tools_progress_ignores_stale_events_and_preserves_byte_counts(self):
        self.ws.generations['prepare_tools']=2
        self.ws.on_event('task_progress',{'action':'prepare_tools','revision':1,'event':{'done':99,'total':100}})
        self.assertEqual(self.ws.activity['tools'],{})
        self.ws.on_event('task_progress',{'action':'prepare_tools','revision':2,'event':{'done':25,'total':100,'message':'Download'}})
        self.assertEqual(self.ws.activity['tools']['done'],25)
        self.assertEqual(self.ws.activity['tools']['total'],100)

    def test_spotify_developers_opens_official_dashboard(self):
        with patch('qt_workspace_ui.QDesktopServices.openUrl') as opened:
            self.ws.invoke('spotify_developers',{})
        self.assertEqual(opened.call_args.args[0].toString(),'https://developer.spotify.com/dashboard')

    def test_account_buttons_and_tools_progress_in_qml(self):
        from unittest.mock import Mock
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QMetaObject
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;window=engine.rootObjects()[0]
        try:
            popup=window.findChild(QObject,'settingsPopup')
            QMetaObject.invokeMethod(popup,'open');popup.setProperty('category','Contas');self.settle()
            ws.account=Mock(connected=False);ws.statusChanged.emit();self.settle()
            def find(name):
                def walk(item):
                    if item.objectName()==name:return item
                    return next((result for child in item.childItems() if (result:=walk(child)) is not None),None)
                return walk(popup.property('contentItem'))
            self.assertIsNotNone(find('spotify_connect'))
            self.assertIsNone(find('spotify_disconnect'))
            self.assertIsNone(find('forget_credentials'))
            self.assertIsNotNone(find('spotify_developers'))
            ws.saved_credentials=('id','secret');ws.statusChanged.emit();self.settle()
            self.assertIsNone(find('forget_credentials'))
            ws.saved_credentials=('','')
            ws.account.connected=True;ws.statusChanged.emit();self.settle()
            self.assertIsNone(find('spotify_connect'))
            self.assertIsNotNone(find('spotify_disconnect'))
            self.assertIsNotNone(find('forget_credentials'))
            popup.setProperty('category','Ferramentas')
            for action in ('prepare_tools','update_tools'):
                ws.tasks={action:threading.Event()};ws.tool_progress={'action':action,'done':25,'total':100,'message':'Test'};ws.statusChanged.emit();self.settle()
                button=find(action)
                self.assertFalse(button.property('enabled'))
                self.assertNotIn('Cancelar',button.property('text'))
                self.assertTrue(window.findChild(QObject,'toolsProgressCard').property('visible'))
            ws.tasks.clear();ws.statusChanged.emit();self.settle()
            self.assertFalse(window.findChild(QObject,'toolsProgressCard').property('visible'))
        finally:close_application(engine,bridge)

    def test_spotify_search_warns_before_starting_without_api(self):
        from unittest.mock import Mock
        self.ws.account=Mock(connected=False);self.ws.settings.update(spotify_client_id='',spotify_client_secret='')
        self.ws.options.update(provider='Spotify',query='Song')
        messages=[];self.ws.message.connect(lambda *values:messages.append(values))
        with patch.object(self.ws,'run_task') as run:
            self.ws.invoke('search',{});run.assert_not_called()
        self.assertEqual(messages[0][0],'Configure a API do Spotify')
        for connected,identity,secret in ((True,'',''),(False,'id','secret')):
            self.ws.account.connected=connected;self.ws.settings.update(spotify_client_id=identity,spotify_client_secret=secret)
            with patch.object(self.ws,'run_task') as run:
                self.ws.invoke('search',{});run.assert_called_once()
        self.ws.account.connected=False;self.ws.settings.update(spotify_client_id='',spotify_client_secret='')
        for provider,query in (('Deezer','Song'),('Todos','Song'),('Spotify','https://open.spotify.com/track/'+'A'*22)):
            self.ws.options.update(provider=provider,query=query)
            with patch.object(self.ws,'run_task') as run:
                self.ws.invoke('search',{});run.assert_called_once()

    def test_spotify_id_autosaves_with_preferences_and_can_be_removed(self):
        self.ws.setSetting('remember_settings',True)
        self.ws.setSetting('spotify_client_id','public-client-id')
        self.ws.persist()
        self.assertEqual(self.store.load()['spotify_client_id'],'public-client-id')
        from qt_jukebox_ui import JukeboxBridge
        from qt_workspace_ui import DesktopWorkspace
        restored_bridge=JukeboxBridge(self.store);restored=DesktopWorkspace(restored_bridge)
        try:self.assertEqual(restored.settings['spotify_client_id'],'public-client-id')
        finally:restored.shutdown();restored_bridge.shutdown()
        self.assertNotIn('spotify_client_secret',self.store.load())
        self.ws.invoke('forget_credentials',{})
        self.assertEqual(self.store.load()['spotify_client_id'],'')
        self.ws.setSetting('spotify_client_id','session-only')
        self.ws.setSetting('remember_settings',False);self.ws.persist()
        self.assertIsNone(self.store.load())

    def test_shortcut_recorder_captures_keys_without_editing_text(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QMetaObject,QPointF,Qt
        from PySide6.QtTest import QTest
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;window=engine.rootObjects()[0]
        try:
            ws.bind_shortcuts();popup=window.findChild(QObject,'shortcutsPopup')
            QMetaObject.invokeMethod(popup,'open');self.settle()
            self.assertTrue(all(not shortcut.isEnabled() for shortcut in ws.shortcuts))
            def find(item,name='shortcutRecorder_links'):
                if item.objectName()==name:return item
                return next((result for child in item.childItems() if (result:=find(child,name)) is not None),None)
            recorder=find(popup.property('contentItem'));self.assertTrue(recorder.property('readOnly'))
            QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,recorder.mapToScene(QPointF(15,15)).toPoint());self.settle()
            self.assertTrue(recorder.property('recording'))
            QTest.keyClick(window,Qt.Key_B,Qt.ControlModifier|Qt.AltModifier);self.settle()
            self.assertEqual(json.loads(ws.settings['shortcut_keys'])['links'],'<Control-Alt-b>')
            self.assertTrue(all(not shortcut.isEnabled() for shortcut in ws.shortcuts))
            recorder=find(popup.property('contentItem'))
            QTest.mouseClick(window,Qt.LeftButton,Qt.NoModifier,recorder.mapToScene(QPointF(15,15)).toPoint())
            QTest.keyClick(window,Qt.Key_Escape);self.settle()
            self.assertFalse(recorder.property('recording'));self.assertTrue(popup.property('opened'))
            self.assertEqual(json.loads(ws.settings['shortcut_keys'])['links'],'<Control-Alt-b>')
            recorder.forceActiveFocus();QTest.keyClick(window,Qt.Key_Return);self.settle()
            self.assertTrue(recorder.property('recording'));QTest.keyClick(window,Qt.Key_Escape)
            disable=find(popup.property('contentItem'),'disableShortcut_links')
            QMetaObject.invokeMethod(disable,'clicked');self.settle()
            self.assertEqual(json.loads(ws.settings['shortcut_keys'])['links'],'')
            reset=find(popup.property('contentItem'),'resetShortcut_links')
            QMetaObject.invokeMethod(reset,'clicked');self.settle()
            self.assertNotIn('links',json.loads(ws.settings['shortcut_keys']))
            QMetaObject.invokeMethod(popup,'close');self.settle()
            self.assertTrue(all(shortcut.isEnabled() for shortcut in ws.shortcuts))
        finally:close_application(engine,bridge)

    def test_shortcut_capture_rejects_reserved_and_duplicate_combinations(self):
        from PySide6.QtCore import Qt
        previous=self.ws.settings['shortcut_keys']
        self.assertFalse(self.ws.captureShortcut('links',Qt.Key_C,Qt.ControlModifier.value))
        self.assertFalse(self.ws.captureShortcut('links',Qt.Key_J,Qt.ControlModifier.value))
        self.assertEqual(self.ws.settings['shortcut_keys'],previous)
        self.assertTrue(self.ws.captureShortcut('links',Qt.Key_F12,0))
        self.assertEqual(json.loads(self.ws.settings['shortcut_keys'])['links'],'<F12>')

    def test_tray_context_menu_does_not_restore_window(self):
        from PySide6.QtWidgets import QSystemTrayIcon
        reasons=QSystemTrayIcon.ActivationReason
        with patch.object(self.ws,'restore') as restore:
            for reason in (reasons.Context,reasons.MiddleClick,reasons.Unknown):
                self.ws.tray_activated(reason)
            restore.assert_not_called()
            self.ws.tray_activated(reasons.Trigger)
            self.ws.tray_activated(reasons.DoubleClick)
            self.assertEqual(restore.call_count,2)

    def test_selected_lrc_enables_display_and_invalid_file_preserves_lyrics(self):
        path=self.root/'song.lrc';path.write_text('[00:01.20]Canção',encoding='utf-16')
        self.ws.options['position']=2
        self.ws.accept_files('effectLyrics',[str(path)])
        self.assertTrue(self.ws.settings['synced_lyrics'])
        self.assertEqual(self.ws.options['lyricText'],'Canção')
        self.assertEqual(self.ws.options['effectLyricsName'],'song.lrc')
        notices=[];self.ws.message.connect(lambda title,body:notices.append(body))
        path.write_text('No timestamps',encoding='utf-8')
        self.ws.accept_files('effectLyrics',[str(path)])
        self.assertEqual(self.ws.lyrics,[(1.2,'Canção')]);self.assertTrue(notices)

    def test_retired_confirmation_setting_does_not_override_automatic_choice(self):
        from preferences import PreferenceStore
        self.assertFalse(PreferenceStore.clean({'confirm_version':True})['confirm_version'])
        for automatic in (False,True):
            self.ws.setSetting('auto_match',automatic)
            self.assertEqual(self.ws.config()['auto_match'],automatic)
            self.assertFalse(self.ws.config().get('confirm_version',False))
        self.assertNotIn('Confirmar a versão do YouTube de cada música antes de baixar',(Path(__file__).parent/'settings_schema/desktop.json').read_text('utf-8'))

    def test_audio_background_controls_are_independent(self):
        self.ws.selectPage('jukebox');self.bridge.update_state(playing=True,paused=False)
        self.ws.setSetting('background_preview',False)
        with patch.object(self.bridge,'playPause') as pause:
            self.ws.selectPage('catalog');pause.assert_not_called()
            self.ws.selectPage('jukebox');self.ws.setSetting('jukebox_background',False)
            self.ws.selectPage('catalog');pause.assert_not_called()
        self.ws.setSetting('background_preview',True);self.ws.persist()
        saved=self.store.load()
        self.assertNotIn('Continuar Jukebox em outras abas',(Path(__file__).parent/'settings_schema/desktop.json').read_text('utf-8'))
        self.ws.setSetting('jukebox_transition_seconds',8)
        self.assertEqual(self.ws.settings['jukebox_transition_seconds'],8)

    def test_effects_timers_pause_and_control_only_effects(self):
        from unittest.mock import Mock
        player=Mock(active=True);player.messages.return_value=[];player.position_snapshot.return_value=0
        player.stop.side_effect=lambda:setattr(player,'active',False)
        self.ws.preview_kind='effects';self.ws.effects_timer_clock=99
        with patch.object(self.ws,'player',player),patch.object(self.bridge,'setSleep') as jukebox_sleep:
            self.ws.invoke('effects_timer',{'minutes':1})
            with patch('qt_workspace_ui.time.monotonic',return_value=100):self.ws.tick()
            self.assertEqual(self.ws.options['effectsStopRemaining'],59)
            player.active=False
            with patch('qt_workspace_ui.time.monotonic',return_value=120):self.ws.tick()
            self.assertEqual(self.ws.options['effectsStopRemaining'],59)
            player.active=True
            with patch('qt_workspace_ui.time.monotonic',return_value=180):self.ws.tick()
            self.assertFalse(player.active);jukebox_sleep.assert_not_called()
            player.active=True;self.ws.preview_kind='effects'
            self.ws.invoke('effects_timer',{'next':True,'minutes':1})
            with patch.object(self.ws,'play_effects_entry') as next_track,patch('qt_workspace_ui.time.monotonic',return_value=241):
                self.ws.tick();next_track.assert_called_once_with(0)

    def test_playback_navigation_opens_first_configured_tab(self):
        self.ws.setSetting('playback_tab_order','Jukebox infinito primeiro')
        self.ws.selectNavigationPage('effects');self.assertEqual(self.ws.currentPage,'jukebox')
        self.ws.selectPage('effects');self.assertEqual(self.ws.currentPage,'effects')
        self.ws.setSetting('playback_tab_order','Efeitos primeiro')
        self.ws.selectNavigationPage('effects');self.assertEqual(self.ws.currentPage,'effects')

    def test_settings_persist_preserve_and_disable_remembering(self):
        self.ws.setSetting('theme_accent','Turquesa');self.ws.setSetting('concurrent_downloads','3');self.ws.persist()
        data=self.store.load();self.assertEqual(data['theme_accent'],'Turquesa');self.assertEqual(data['concurrent_downloads'],'3')
        self.ws.setSetting('remember_settings',False);self.ws.setSetting('theme_mode','Escuro');self.ws.persist();self.assertFalse(self.store.path.exists())
        self.assertFalse(self.store.remember_enabled())
    def test_hidden_tabs_and_order_keep_required_navigation(self):
        self.ws.setSetting('hidden_tabs',['catalog','downloads','queue','images','metadata']);self.assertEqual(self.ws.hiddenTabs,['images','metadata'])
        self.ws.selectPage('images');self.assertEqual(self.ws.currentPage,'catalog')
        self.ws.invoke('tab_move',{'key':'history','direction':-1});self.assertLess(self.ws.settings['tab_order'].index('history'),self.ws.defaults['tab_order'].index('history'))
    def test_tab_order_moves_only_inside_its_category(self):
        self.ws.setSetting('tab_order',['images','catalog','converter','downloads','queue','playlists','history','effects','metadata'])
        self.ws.invoke('tab_move',{'key':'downloads','direction':-1})
        groups={};current=None
        for row in self.ws.navigation:
            if row.get('group'):current=row['group'];groups[current]=[]
            else:groups[current].append(row['key'])
        self.assertEqual(groups['BIBLIOTECA'],['downloads','catalog','queue','playlists','history'])
        self.assertEqual(groups['FERRAMENTAS'],['images','converter','effects','metadata'])
        before=list(self.ws.settings['tab_order'])
        self.ws.invoke('tab_move',{'key':'images','direction':-1})
        self.assertEqual(self.ws.settings['tab_order'],before)
        self.ws.invoke('tab_move',{'key':'images','direction':1})
        tools=[row for row in self.ws.navigation if row.get('key') in groups['FERRAMENTAS']]
        self.assertEqual([row['key'] for row in tools],['converter','images','effects','metadata'])
        self.assertFalse(tools[0]['canMoveUp']);self.assertFalse(tools[-1]['canMoveDown'])

    def test_queue_duplicate_filters_order_and_persistence(self):
        urls=['https://example.com/b.mp3','https://example.com/a.mp3']
        self.ws.enqueue(urls);self.ws.enqueue(urls);self.assertEqual(len(self.ws.jobs),2)
        self.ws.jobs[0]['display_name']='B';self.ws.jobs[1]['display_name']='A';self.ws.queue_action('sort:Título');self.assertEqual(self.ws.jobs[0]['display_name'],'A')
        self.ws.setOption('queueQuery','b.mp3');self.assertEqual(self.ws.queueModel.count,1)
        self.ws.toggle_row('queue',0,True);self.ws.queue_action('remove');self.assertEqual(len(self.ws.jobs),1);self.assertEqual(len(self.ws.library.load_queue()),1)
    def test_search_uses_existing_service_and_filters(self):
        rows=[{'title':'One','artists':['A'],'album':'First','source_url':'https://www.deezer.com/track/1'},{'title':'Two','artists':['B'],'album':'Second','source_url':'https://www.deezer.com/track/2'}]
        with patch('qt_operations_ui.perform',return_value={'tracks':rows}):
            self.ws.setOption('query','test');self.ws.invoke('search',{});self.task_done('search')
        self.assertEqual(self.ws.catalogModel.count,2);self.ws.setOption('filterArtist','B');self.assertEqual(self.ws.catalogModel.count,1)
        self.assertEqual(self.ws.catalogModel.rows[0]['title'],'Two')
    def test_cancelled_task_cannot_apply_result(self):
        release=threading.Event();applied=[]
        def work(*args):release.wait(2);return 'stale'
        with patch('qt_operations_ui.perform',side_effect=work):
            self.ws.run_task('probe',{},applied.append);self.ws.cancel_task('probe');release.set();self.task_done('probe')
        self.assertEqual(applied,[])
    def test_new_task_ignores_old_generation(self):
        release=threading.Event();applied=[]
        def work(action,config,*args):
            if config['source']=='old':release.wait(2)
            return config['source']
        with patch('qt_operations_ui.perform',side_effect=work):
            self.ws.run_task('probe',{'source':'old'},applied.append);self.ws.run_task('probe',{'source':'new'},applied.append);self.task_done('probe');release.set();self.settle()
        self.assertEqual(applied,['new'])
    def test_background_update_does_not_hide_manual_task(self):
        pending=[]
        with patch.object(self.ws,'launch_thread',side_effect=pending.append):
            self.ws.run_task('app_update',background=True)
            self.assertIn('app_update',self.ws.activity['busy'])
            self.assertIn('app_update',self.ws.activity['background'])
            old_revision=self.ws.generations['app_update']
            self.ws.run_task('app_update')
            self.assertNotIn('app_update',self.ws.activity['background'])
            self.ws.on_event('task_finished',{'action':'app_update','revision':old_revision})
            self.assertIn('app_update',self.ws.activity['busy'])
            self.ws.on_event('task_finished',{'action':'app_update','revision':self.ws.generations['app_update']})
            self.assertNotIn('app_update',self.ws.activity['busy'])
            self.assertEqual(self.ws.activity['background'],[])

    def test_card_sizes_change_geometry_and_persist_for_each_list(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QMetaObject,Q_ARG
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;window=engine.rootObjects()[0]
        def visible_item(name):
            def visit(item):
                if item.objectName()==name and item.isVisible():return item
                for child in item.childItems():
                    result=visit(child)
                    if result is not None:return result
            return visit(window.contentItem())
        try:
            ws.searched({'tracks':[{'title':'Track','artists':['Artist'],'album':'Album','source_url':'https://example.com/track'}]})
            ws.enqueue(['https://example.com/download.mp3'])
            ws.models['playlists'].replace([{'title':'Track','artist':'Artist','album':'Album'}])
            ws.models['history'].replace([{'title':'Track','date':'2026-10-20','mode':'MP3'}])
            for page,key,card_name in [('catalog','catalog_card_size','libraryTrackCard'),('playlists','playlist_card_size','libraryTrackCard'),('history','history_card_size','libraryTrackCard'),('queue','queue_card_size','downloadQueueCard')]:
                ws.selectPage(page)
                if page=='history':ws.models['history'].replace([{'title':'Track','date':'2026-10-20','mode':'MP3'}])
                self.settle();sizes=[]
                for index,size in enumerate(('Pequeno','Médio','Grande')):
                    choice=visible_item('cardSizeChoice');self.assertIsNotNone(choice)
                    choice.setProperty('currentIndex',index);QMetaObject.invokeMethod(choice,'activated',Q_ARG(int,index));self.settle()
                    self.assertEqual(ws.preferences[key],size)
                    card=visible_item(card_name);self.assertIsNotNone(card,page);sizes.append(card.height())
                self.assertLess(sizes[0],sizes[2],(page,sizes));self.assertLessEqual(sizes[0],sizes[1]);self.assertLessEqual(sizes[1],sizes[2])
                ws.setSetting(key,'Médio')
            ws.persist()
            for key in ('catalog_card_size','playlist_card_size','history_card_size','queue_card_size'):self.assertEqual(ws.store.load()[key],'Médio')
        finally:close_application(engine,bridge)

    def test_links_and_queue_have_separate_controls_and_navigation(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QMetaObject
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;window=engine.rootObjects()[0]
        try:
            ws.selectPage('downloads');self.settle()
            def control(name):return window.findChild(QObject,name)
            for name in ('downloadQueueList','downloadQueueTools','downloadQueueFilters'):
                self.assertFalse(control(name).property('visible'))
            self.assertFalse(control('addLinksButton').property('enabled'))
            ws.setOption('links','https://example.com/test.mp3')
            QMetaObject.invokeMethod(control('addLinksButton'),'clicked');self.settle()
            self.assertEqual(ws.currentPage,'downloads');self.assertFalse(ws.running)
            self.assertTrue(control('linksQueueNotice').property('visible'))
            QMetaObject.invokeMethod(control('viewDownloadQueueButton'),'clicked');self.settle()
            self.assertEqual(ws.currentPage,'queue')
            for name in ('downloadQueueList','downloadQueueTools','downloadQueueFilters'):
                self.assertTrue(control(name).property('visible'))
            self.assertFalse(control('addLinksButton').property('visible'))
            ws.selectPage('downloads');self.settle();ws.setOption('links','https://example.com/other.mp3')
            with patch.object(ws,'start_queue') as start:
                QMetaObject.invokeMethod(control('downloadLinksNowButton'),'clicked')
                start.assert_called_once()
            self.assertEqual(ws.currentPage,'queue');self.assertEqual(len(ws.jobs),2)
        finally:close_application(engine,bridge)

    def test_queue_context_opens_with_right_click(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,Qt,QPointF
        from PySide6.QtTest import QTest
        from PySide6.QtQml import QQmlExpression
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;window=engine.rootObjects()[0]
        try:
            ws.enqueue(['https://example.com/a.mp3']);ws.selectPage('queue');self.settle()
            def find(item):
                if item.objectName()=='downloadQueueCard' and item.isVisible():return item
                for child in item.childItems():
                    result=find(child)
                    if result is not None:return result
            card=find(window.contentItem());self.assertIsNotNone(card)
            for _ in range(10):self.settle()
            window.requestActivate();self.settle()
            position=card.mapToScene(QPointF(card.width()/2,card.height()/2)).toPoint()
            QTest.mouseClick(window,Qt.RightButton,Qt.NoModifier,position);self.settle()
            menu=next(menu for menu in window.findChildren(QObject,'queueContextMenu') if QQmlExpression(engine.rootContext(),menu,'visible').evaluate()[0])
            self.wait_for(lambda:QQmlExpression(engine.rootContext(),menu,'opened').evaluate()[0])
            self.assertEqual(ws.activity['selected'],0)
            self.assertEqual(menu.property('targetId'),ws.jobs[0]['id'])
            ws.invoke('queue_action',{'name':'remove','id':menu.property('actionId')})
            self.assertEqual(len(ws.jobs),0)
        finally:close_application(engine,bridge)

    def test_queue_context_preserves_selected_rows_and_copies_links(self):
        self.ws.enqueue(['https://example.com/a.mp3','https://example.com/b.mp3','https://example.com/c.mp3'])
        self.ws.jobs[0]['checked']=True;self.ws.jobs[1]['checked']=True
        self.assertEqual(self.ws.activity['selected'],2)
        self.ws.invoke('queue_copy_links',{})
        self.assertEqual(self.app.clipboard().text(),'https://example.com/a.mp3\nhttps://example.com/b.mp3')
        identity=self.ws.jobs[2]['id']
        self.ws.invoke('queue_copy_links',{'id':identity})
        self.assertEqual(self.app.clipboard().text(),'https://example.com/c.mp3')
        self.assertEqual([job['checked'] for job in self.ws.jobs],[True,True,False])
        self.ws.invoke('queue_action',{'name':'remove','id':identity})
        self.assertEqual(len(self.ws.jobs),2)
        self.ws.invoke('undo_queue',{})
        self.assertEqual(len(self.ws.jobs),3)

    def test_clipboard_requires_confirmation_and_deduplicates(self):
        from types import SimpleNamespace
        self.ws.settings['clipboard_links']=True
        with patch('qt_workspace_ui.QGuiApplication.clipboard',return_value=SimpleNamespace(text=lambda:'https://www.youtube.com/watch?v=abcdefghijk')),patch.object(self.ws,'enqueue') as add:
            self.ws.clipboard_changed();add.assert_not_called();self.assertEqual(self.ws.choice['type'],'confirm')
            self.ws.replyChoice(self.ws.choice['identity'],{'yes':True});add.assert_called_once()
            self.ws.clipboard_changed();self.assertFalse(self.ws.choice)
    def test_media_selection_and_duplicate_choices_forward_replies(self):
        self.ws.present_choice('media',{'type':'choose_media','candidates':[{'id':'a','kind':'Vídeo','title':'A'}]})
        self.assertTrue(self.ws.choice['candidates'][0]['outputCodes'])
        self.ws.replyChoice('media',{'cancel':True});self.assertFalse(self.ws.choice)
        picked=[];self.ws.confirm('Dup','file',lambda:picked.append(True));self.ws.replyChoice(self.ws.choice['identity'],{'yes':False});self.assertEqual(picked,[])
    def test_converter_real_audio_and_original_preserved(self):
        if not TOOLS.is_dir():self.skipTest('FFmpeg required')
        source=self.tone();original=source.read_bytes();target=self.root/'result.mp3'
        self.ws.accept_files('converter',[str(source)]);self.assertEqual(self.ws.options['converterFormat'],'MP3')
        self.ws.convert_to([str(source)],str(target));self.task_done('convert')
        self.assertTrue(target.is_file(),self.ws.status);self.assertEqual(source.read_bytes(),original);self.assertEqual(len(self.ws.library.history()),1)
    def test_metadata_single_and_batch_use_existing_editor(self):
        if not TOOLS.is_dir():self.skipTest('FFmpeg required')
        source=self.tone();target=self.root/'taggable.mp3';self.ws.options['converterFormat']='MP3';self.ws.convert_to([str(source)],str(target));self.task_done('convert')
        self.ws.accept_files('metadata',[str(target)]);self.task_done('audio_read');self.ws.options['metadata']['title']='Edited';self.ws.edit_audio();self.task_done('audio_edit')
        from audio_library import read_audio
        results=[row for row in self.ws.library.history() if row['path']!=str(target)]
        self.assertTrue(results,self.ws.status);self.assertEqual(read_audio(results[0]['path'])['title'],'Edited');self.assertNotEqual(read_audio(target)['title'],'Edited')
        other=self.root/'second.mp3';other.write_bytes(target.read_bytes());self.ws.accept_files('metadata',[str(target),str(other)]);self.task_done('audio_read')
        self.ws.options['metadata']['album']='Batch album';self.ws.options['metadataFields']={'album':True};self.ws.edit_audio();self.task_done('audio_edit')
        self.assertIn('2 arquivos salvos',self.ws.status)
    def test_images_export_preserves_source(self):
        from PIL import Image
        source=self.root/'source.png';Image.new('RGB',(160,90),'blue').save(source);original=source.read_bytes()
        self.ws.accept_files('image',[str(source)]);self.ws.setSetting('image_format','JPG');self.ws.invoke('image_export',{});self.task_done('image_export')
        self.assertEqual(source.read_bytes(),original);self.assertEqual(len(list((self.root/'out').glob('*.jpg'))),1)
    def test_remote_image_preview_direct_and_page(self):
        from PIL import Image
        source=self.root/'remote.png';Image.new('RGB',(160,90),'blue').save(source)
        (self.root/'page.html').write_text('<meta property="og:image" content="/remote.png">')
        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(self.root)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            self.ws.accept_files('image',[str(source)])
            for name in ('remote.png','page.html'):
                self.ws.setOption('imageUrl',f'http://127.0.0.1:{server.server_port}/{name}')
                self.assertEqual(self.ws.options['imageSource'],'')
                self.ws.invoke('image_preview',{});self.task_done('image_preview')
                self.assertTrue(self.ws.options['imagePreview'],self.ws.status)
                self.assertEqual(self.ws.options['imageInfo']['source'],{'width':160,'height':90,'format':'PNG'})
                from PySide6.QtCore import QUrl
                with Image.open(QUrl(self.ws.options['imagePreview']).toLocalFile()) as preview:self.assertEqual(preview.size,(160,90))
        finally:server.shutdown();server.server_close();thread.join()
    def test_embedded_artwork_is_a_qt_image_url(self):
        import base64,io
        from PIL import Image
        data=io.BytesIO();Image.new('RGB',(80,80),'red').save(data,format='PNG')
        self.ws.audio_loaded({'record':{'title':'Artwork'},'cover':base64.b64encode(data.getvalue()).decode('ascii')})
        from PySide6.QtGui import QImage
        cover=self.ws.options['metadataCover'];self.assertTrue(cover.startswith('data:image/png;base64,'))
        self.assertFalse(QImage.fromData(base64.b64decode(cover.split(',',1)[1])).isNull())
        self.ws.invoke('undo_cover',{});self.assertEqual(self.ws.options['metadataCover'],cover)
    def test_sidebar_groups_do_not_mix_tools_and_library(self):
        rows=self.ws.navigation
        self.assertEqual([row['group'] for row in rows if 'group' in row],['BIBLIOTECA','FERRAMENTAS'])
        split=next(i for i,row in enumerate(rows) if row.get('group')=='FERRAMENTAS')
        self.assertEqual({row['key'] for row in rows[1:split]},{'catalog','downloads','queue','playlists','history'})
        self.assertEqual({row['key'] for row in rows[split+1:]},{'images','converter','effects','metadata'})
    def test_comparison_summary_is_readable_and_notifications_can_be_disabled(self):
        messages=[];self.ws.message.connect(lambda title,text:messages.append((title,text)))
        result={'counts':{'present':2,'missing':11,'review':1,'queued':3},'has_previous':True,'new_count':4,'removed_count':1}
        self.ws.collection_compared(result)
        self.assertIn('Ausentes: 11',messages[-1][1]);self.assertIn('Já disponíveis: 2',messages[-1][1]);self.assertIn('Adicionadas à playlist: 4',messages[-1][1]);self.assertNotIn('"counts"',messages[-1][1])
        self.assertEqual(self.ws.taskLabel('collection'),'carregamento da playlist');self.assertNotIn('unknown',self.ws.taskLabel('unknown'))
        self.ws.setSetting('notifications_enabled',False);self.ws.persist();self.assertIs(self.store.load()['notifications_enabled'],False)
        messages.clear();self.ws.collection_compared(result);self.ws.show_result({'message':'Concluído'})
        self.assertEqual(messages,[]);self.assertEqual(self.ws.status,'Concluído')
        self.ws.show_result({'message':'Consulta solicitada'},notification=False);self.assertEqual(messages[-1][1],'Consulta solicitada')
        self.ws.invoke('invalid_action',{});self.assertGreater(len(messages),1)
        self.ws.setSetting('notifications_enabled',True);self.ws.show_result({'message':'Pronto'});self.assertEqual(messages[-1][1],'Pronto')
    def test_notifications_toggle_controls_queue_sound_and_system_notice(self):
        from unittest.mock import Mock
        with patch.object(self.ws,'tray',Mock()) as tray,patch('winsound.PlaySound') as sound:
            self.ws.settings.update(finish_action='Som e notificação',notifications_enabled=False)
            self.ws.queue_finished();tray.showMessage.assert_not_called();sound.assert_not_called()
            self.ws.settings['notifications_enabled']=True;self.ws.queue_finished();tray.showMessage.assert_called_once();sound.assert_called_once()
    def test_collection_comparison_selects_only_missing(self):
        self.ws.collection_loaded({'title':'List','tracks':[{'title':'A','artists':['X'],'source_url':'https://www.deezer.com/track/1'},{'title':'B','artists':['X'],'source_url':'https://www.deezer.com/track/2'}]})
        self.ws.collection_compared({'items':[{'index':0,'state':'present'},{'index':1,'state':'missing'}],'counts':{'present':1,'missing':1}})
        self.ws.invoke('playlist_missing',{});self.assertFalse(self.ws.playlistModel.rows[0]['checked']);self.assertTrue(self.ws.playlistModel.rows[1]['checked'])
    def test_engine_real_download_from_local_server(self):
        if not TOOLS.is_dir():self.skipTest('FFmpeg required')
        source=self.tone()
        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
            def copyfile(self,*args):
                try:super().copyfile(*args)
                except ConnectionError:pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(self.root)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            self.ws.enqueue([f'http://127.0.0.1:{server.server_port}/{source.name}'],{'mode':'original','playlist':False,'synced_lyrics':False},start=True)
            self.wait_for(lambda:not self.ws.active,30000)
            self.assertEqual(self.ws.jobs[0]['state'],'Concluído',self.ws.jobs[0].get('last_error'));self.assertTrue(self.ws.library.history())
        finally:server.shutdown();server.server_close();thread.join()
    def test_worker_interactive_protocol_and_cancellation(self):
        fixture=self.root/'worker.py';fixture.write_text('import json,sys\njson.loads(sys.stdin.readline())\nprint(json.dumps({"type":"choose_media","candidates":[{"id":"a","kind":"Foto","title":"A"}]}),flush=True)\nreply=json.loads(sys.stdin.readline())\nassert reply["selected_ids"]==["a"]\nprint(json.dumps({"type":"done"}),flush=True)\n',encoding='utf-8')
        job=self.ws.enqueue(['https://example.com/a.mp3'])[0];identity=job['id'];cancel=threading.Event();self.ws.active[identity]={'cancel':cancel,'process':None};job['state']='Em andamento'
        self.ws.launch_thread(lambda:self.ws.process_worker(identity,{},cancel,str(fixture)))
        self.wait_for(lambda:bool(self.ws.choice));self.ws.replyChoice(identity,{'selected_ids':['a']});self.wait_for(lambda:not self.ws.active)
        self.assertEqual(job['state'],'Concluído')
    def test_effects_queue_auto_advance_waits_for_transition_boundary(self):
        row={'source':'next.mp3','record':{'title':'Next'},'duration':120}
        self.ws.options.update(effectsQueue=[row,row],effectsQueueIndex=0,duration=100,speed=50,previewActive=True,effectsPaused=False)
        self.ws.effects_transport=True;self.ws.preview_kind='effects';self.ws.player.active=True
        self.ws.settings.update(jukebox_gradual_transition=True,jukebox_transition_seconds=3)
        with patch.object(self.ws,'play_effects_entry') as advance,patch.object(self.ws.player,'position_snapshot',return_value=98):
            self.ws.tick();advance.assert_not_called()
        with patch.object(self.ws,'play_effects_entry') as advance,patch.object(self.ws.player,'position_snapshot',return_value=99):
            self.ws.tick();advance.assert_called_once_with(1)
        self.ws.settings['jukebox_gradual_transition']=False
        with patch.object(self.ws,'play_effects_entry') as advance,patch.object(self.ws.player,'position_snapshot',return_value=99):
            self.ws.tick();advance.assert_not_called()
            self.ws.player.active=False;self.ws.tick();advance.assert_called_once_with(1)
    def test_effects_queue_switch_respects_gradual_setting(self):
        from audio_tools import PreviewPlayer
        for gradual in (False,True):
            self.ws.stop_preview();self.ws.settings.update(jukebox_gradual_transition=gradual,jukebox_transition_seconds=3)
            row={'source':'next.mp3','record':{'title':'Next','artists':[]},'duration':120,'cover_url':''}
            self.ws.options.update(effectsQueue=[row],effectsQueueIndex=-1,effectsSource='old.mp3',effectsRecord={'title':'Old'},duration=100,position=20)
            self.ws.preview_kind='effects';old=self.ws.player;old.active=True;old.position=20
            incoming=PreviewPlayer()
            def play(*args,**kwargs):self.ws.player.active=True
            with patch('audio_tools.PreviewPlayer',return_value=incoming),patch.object(old,'play') as outgoing,patch.object(self.ws,'run_task'),patch.object(incoming if gradual else old,'play',side_effect=play) as started:
                self.ws.play_effects_entry(0)
                self.assertEqual(self.ws.options['effectsQueueIndex'],0)
                self.assertEqual(self.ws.options['effectsSource'],'next.mp3')
                self.assertEqual(started.call_args.kwargs['fade_in'],3 if gradual else 0)
                self.assertEqual(started.call_args.kwargs['fade_out'],3 if gradual else 0)
                self.assertEqual(len(self.ws.effects_tails),1 if gradual else 0)
                if gradual:self.assertEqual(outgoing.call_args.kwargs['fade_out'],3)
            self.ws.stop_preview();incoming.close()
    def test_effects_transport_resumes_and_stops_without_using_jukebox_queue(self):
        self.ws.options.update(effectsSource='song.mp3',duration=300,position=40,speed=100)
        def play(*args,**kwargs):self.ws.player.active=True
        with patch.object(self.ws.player,'play',side_effect=play) as playing,patch.object(self.bridge,'nextTrack') as next_track,patch.object(self.bridge,'previousTrack') as previous:
            self.ws.invoke('effects_play_pause',{})
            self.assertTrue(playing.call_args.kwargs['full_track'])
            self.assertEqual(playing.call_args.kwargs['duration'],260)
            with patch.object(self.ws.player,'position_snapshot',return_value=65):self.ws.invoke('effects_play_pause',{})
            self.assertFalse(self.ws.player.active);self.assertTrue(self.ws.options['effectsPaused'])
            self.ws.invoke('effects_skip',{'seconds':10});self.assertEqual(self.ws.options['position'],75)
            self.ws.invoke('effects_play_pause',{});self.assertEqual(playing.call_args.kwargs['start'],75)
            self.ws.invoke('effects_stop',{});self.assertEqual(self.ws.options['position'],0)
            self.assertFalse(self.ws.player.active)
            next_track.assert_not_called();previous.assert_not_called()
    def test_effects_search_has_inline_progress_and_cancellation(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QMetaObject
        app,engine,bridge=create_application(complete=False);ws=engine.workspace
        try:
            ws.selectPage('effects');self.settle()
            window=engine.rootObjects()[0]
            button=window.findChild(QObject,'effectsSearchButton')
            progress=window.findChild(QObject,'effectsSearchProgress')
            self.assertFalse(progress.property('visible'))
            for operation in ('effects_search','effects_load'):
                cancel=threading.Event();ws.tasks[operation]=cancel;ws.statusChanged.emit();self.settle()
                self.assertTrue(progress.property('visible'))
                self.assertTrue(button.property('enabled'))
                self.assertEqual(button.property('text'),bridge.translate('Cancelar'))
                QMetaObject.invokeMethod(button,'clicked');self.settle()
                self.assertTrue(cancel.is_set())
                ws.tasks.pop(operation);ws.statusChanged.emit();self.settle()
                self.assertFalse(progress.property('visible'))
        finally:
            ws.tasks.clear();close_application(engine,bridge)
    def test_window_layout_is_persisted_independently_of_settings(self):
        from PySide6.QtGui import QWindow
        window=QWindow();window.setGeometry(40,50,600,400)
        self.ws.attach(window);self.ws.capture_window_layout();self.ws.save_window_layout()
        data=json.loads(self.ws.store.path.with_name('window.json').read_text())
        self.assertEqual((data['x'],data['y'],data['width'],data['height']),(40,50,600,400))
        restored=QWindow();self.ws.attach(restored)
        self.assertEqual((restored.x(),restored.y(),restored.width(),restored.height()),(40,50,600,400))
        self.ws.window_save_timer.stop()
    def test_miniplayer_lyrics_and_queue_resize_without_clipping(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QMetaObject
        app,engine,bridge=create_application(complete=False)
        try:
            mini=engine.rootObjects()[0].findChild(QObject,'miniPlayer')
            QMetaObject.invokeMethod(mini,'show');self.settle()
            for mode in ('lyricsVisible','queueVisible','lyricsVisible','queueVisible'):
                mini.setProperty(mode,True);self.settle()
                self.assertGreaterEqual(mini.height(),450)
                if mode=='lyricsVisible':
                    lyrics=mini.findChild(QObject,'miniPlayerLyrics')
                    self.assertGreater(lyrics.property('height'),100)
                    self.assertLess(lyrics.property('y')+lyrics.property('height'),mini.height())
                mini.setProperty(mode,False);self.settle()
                self.assertLessEqual(mini.height(),310)
        finally:close_application(engine,bridge)
    def test_qml_all_pages_settings_and_decisions_have_no_runtime_warnings(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QMetaObject,qInstallMessageHandler
        warnings=[];old=qInstallMessageHandler(lambda kind,context,msg:warnings.append(msg))
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;window=engine.rootObjects()[0]
        try:
            for name in ('catalog','downloads','queue','playlists','history','images','converter','effects','metadata','jukebox'):
                ws.selectPage(name);self.settle();self.assertFalse(window.grabWindow().isNull())
            settings=window.findChild(QObject,'settingsPopup');QMetaObject.invokeMethod(settings,'open');self.settle()
            for category in ('Geral','Aparência','Downloads','Imagens','Áudio','Contas','Ferramentas','Desempenho'):settings.setProperty('category',category);self.settle()
            QMetaObject.invokeMethod(settings,'close')
            ws.searched({'tracks':[{'title':'A','artists':['X'],'source_url':'https://www.deezer.com/track/1'},{'title':'B','artists':['X'],'source_url':'https://www.deezer.com/track/2'}]})
            ws.invoke('compare_results',{'index':0});self.settle();QMetaObject.invokeMethod(window.findChild(QObject,'comparisonPopup'),'close')
            from PIL import Image
            cover=self.root/'gui-cover.png';Image.new('RGB',(100,80),'green').save(cover);ws.accept_files('cover_path',[str(cover)]);ws.invoke('crop_cover',{});self.settle();QMetaObject.invokeMethod(window.findChild(QObject,'coverCropPopup'),'close')
            QMetaObject.invokeMethod(window.findChild(QObject,'shortcutsPopup'),'open');self.settle();QMetaObject.invokeMethod(window.findChild(QObject,'shortcutsPopup'),'close')
            QMetaObject.invokeMethod(window.findChild(QObject,'resetPopup'),'open');self.settle();QMetaObject.invokeMethod(window.findChild(QObject,'resetPopup'),'close')
            ws.present_choice('link',{'type':'confirm','title':'Link copiado','message':'Deseja iniciar o download?\nhttps://example.com/image.jpg'});self.settle()
            popup=window.findChild(QObject,'decisionPopup');self.assertLess(popup.property('height'),300);self.assertGreater(popup.property('height'),120);ws.replyChoice('link',{'cancel':True});self.settle()
            ws.present_choice('media',{'type':'choose_media','candidates':[{'id':'a','kind':'Foto','title':'A'}]});self.settle();ws.replyChoice('media',{'cancel':True});self.settle()
            import tkinter
            self.assertIsNone(tkinter._default_root)
            self.assertNotIn('qt_workspace_server_ui',sys.modules)
        finally:close_application(engine,bridge);qInstallMessageHandler(old)
        self.assertEqual(warnings,[])
    def test_warning_sizes_follow_message_in_light_and_pure_black(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QMetaObject,qInstallMessageHandler
        warnings=[];old=qInstallMessageHandler(lambda kind,context,msg:warnings.append(msg))
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;window=engine.rootObjects()[0]
        try:
            for theme in ('Claro','Preto puro'):
                ws.setSetting('theme_mode',theme);ws.message.emit('ONDA','Concluído.');self.settle()
                popup=window.findChild(QObject,'messagePopup');short=(popup.property('width'),popup.property('height'))
                self.assertLess(short[0],400);self.assertLess(short[1],230)
                ws.message.emit('Conferência de arquivos locais','Já disponíveis: 2'+chr(10)+'Ausentes: 11'+chr(10)+'Precisam de revisão: 1'+chr(10)+'Já na fila: 0');self.settle()
                self.assertGreater(popup.property('height'),short[1]);self.assertGreater(popup.property('width'),short[0])
                ws.message.emit('Aviso longo',('Texto longo para conferir a rolagem e o limite de tamanho. '+chr(10))*100);self.settle()
                self.assertLessEqual(popup.property('height'),500);self.assertLessEqual(popup.property('width'),window.width()-48)
                self.assertFalse(window.grabWindow().isNull());QMetaObject.invokeMethod(popup,'close')
                ws.present_choice('short',{'type':'confirm','title':'Confirmar','message':'Continuar?'});self.settle()
                decision=window.findChild(QObject,'decisionPopup');small=decision.property('width');self.assertLess(small,400)
                ws.replyChoice('short',{'cancel':True})
                ws.present_choice('long',{'type':'confirm','title':'Link copiado','message':'Deseja iniciar o download? '+('https://example.com/long-image-name.jpg'*5)});self.settle()
                self.assertGreater(decision.property('width'),small);self.assertLessEqual(decision.property('height'),window.height()-70);ws.replyChoice('long',{'cancel':True})
        finally:close_application(engine,bridge);qInstallMessageHandler(old)
        self.assertEqual(warnings,[])
    def test_preview_controls_respect_durations_background_and_owner(self):
        from unittest.mock import Mock
        player=Mock(active=False);player.messages.return_value=[];player.position_snapshot.return_value=12
        player.play.side_effect=lambda *args,**kwargs:setattr(player,'active',True)
        player.stop.side_effect=lambda:setattr(player,'active',False)
        with patch.object(self.ws,'player',player):
            self.ws.searched({'tracks':[{'title':'Song','artists':['Artist'],'source_url':'https://www.deezer.com/track/1','preview_url':'https://example.com/preview.mp3'}]})
            self.ws.setSetting('search_preview_duration','15 segundos');self.ws.invoke('preview_catalog',{'index':0})
            self.assertEqual(player.play.call_args.kwargs['duration'],15);self.assertTrue(self.ws.options['previewActive'])
            self.ws.setOption('speed',90);self.assertFalse(self.ws.preview_timer.isActive())
            self.ws.invoke('preview_catalog',{'index':0});self.assertFalse(self.ws.options['previewActive'])
            self.ws.selectPage('effects');self.ws.options['effectsSource']='test.wav';self.ws.setSetting('effects_preview_duration','180 segundos');self.ws.setSetting('effects_keep_pitch',True)
            self.ws.invoke('effects_preview',{'processed':True});self.assertEqual(player.play.call_args.kwargs['duration'],25);self.assertTrue(player.play.call_args.kwargs['keep_pitch'])
            self.ws.setSetting('background_preview',True);self.ws.selectPage('downloads');self.assertTrue(player.active)
            self.ws.setSetting('background_preview',False);self.assertTrue(player.active)
            self.ws.selectPage('effects');self.ws.invoke('effects_preview',{'processed':False});self.assertFalse(self.ws.options['previewProcessed'])
            self.ws.invoke('effects_preview',{'processed':False});self.assertFalse(player.active)
            self.ws.invoke('effects_preview',{'processed':True});self.ws.selectPage('catalog');self.assertTrue(player.active)
    def test_platform_icons_are_tinted_and_load_in_both_themes(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtQml import QQmlComponent
        from PySide6.QtCore import QUrl
        from qt_platform_icons_ui import PlatformIcons
        from PySide6.QtGui import QColor
        app,engine,bridge=create_application(complete=False)
        try:
            for theme in ('Claro','Preto puro'):
                engine.workspace.setSetting('theme_mode',theme);color=bridge.palette['text'];provider=PlatformIcons()
                for key in ('deezer','spotify','apple_music','youtube'):
                    image=provider.requestImage(key+'/'+color.lstrip('#'),None,None);self.assertFalse(image.isNull())
                    pixels=[image.pixelColor(x,y) for x in range(image.width()) for y in range(image.height()) if image.pixelColor(x,y).alpha()>200]
                    self.assertTrue(pixels);self.assertLessEqual(max(abs(a-b) for a,b in zip(pixels[0].getRgb()[:3],QColor(color).getRgb()[:3])),1)
                component=QQmlComponent(engine);component.setData(('import QtQuick; Image { property bool ready: status === Image.Ready; width: 24; height: 24; source: "image://platform/deezer/'+color.lstrip('#')+'" }').encode(),QUrl())
                icon=component.create();self.assertIsNotNone(icon);self.settle();self.assertTrue(icon.property('ready'));icon.deleteLater()
        finally:close_application(engine,bridge)
    def test_primary_search_and_load_buttons_cancel_their_real_tasks(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QMetaObject,qInstallMessageHandler
        warnings=[];old=qInstallMessageHandler(lambda kind,context,msg:warnings.append(msg))
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;window=engine.rootObjects()[0]
        def operation(action,config,cancel,emit):
            cancel.wait(3)
            return {'tracks':[{'title':'Stale','source_url':'https://example.com/stale'}]}
        try:
            with patch('qt_operations_ui.perform',side_effect=operation):
                for page,label,task in [('catalog','Pesquisar','search'),('playlists','Carregar','collection')]:
                    ws.selectPage(page);self.settle();button=window.findChild(QObject,'libraryLoadButton');self.assertEqual(button.property('text'),label)
                    QMetaObject.invokeMethod(button,'clicked');self.settle();self.assertEqual(button.property('text'),'Cancelar');cancel=ws.tasks[task]
                    QMetaObject.invokeMethod(button,'clicked');self.assertTrue(cancel.is_set())
                    self.wait_for(lambda:task not in ws.tasks);self.settle();self.assertEqual(button.property('text'),label)
                    self.assertEqual(ws.catalogModel.count,0);self.assertEqual(ws.playlistModel.count,0)
        finally:close_application(engine,bridge);qInstallMessageHandler(old)
        self.assertEqual(warnings,[])
    def test_export_cancel_targets_only_its_worker(self):
        own=threading.Event();other=threading.Event()
        self.ws.active={'export':{'cancel':own,'process':None,'operation':'effects_export'},'download':{'cancel':other,'process':None}}
        self.assertIn('effects_export',self.ws.activity['busy']);self.ws.cancel_task('effects_export');self.assertTrue(own.is_set());self.assertFalse(other.is_set());self.ws.active.clear()
    def test_image_information_reports_original_and_output_not_thumbnail(self):
        from PIL import Image
        from PySide6.QtCore import QUrl
        source=self.root/'large.png';Image.new('RGB',(2000,1000),'blue').save(source)
        self.ws.accept_files('image',[str(source)]);self.task_done('image_info')
        self.assertEqual(self.ws.options['imageInfo']['source'],{'width':2000,'height':1000,'format':'PNG'})
        self.ws.invoke('image_preview',{});self.task_done('image_preview')
        self.assertEqual(self.ws.options['imageInfo']['output']['width'],2000)
        with Image.open(QUrl(self.ws.options['imagePreview']).toLocalFile()) as preview:self.assertEqual(preview.size,(1400,700))
        self.ws.setSetting('image_format','JPG');self.ws.setSetting('image_size','Até 1280 × 720');self.ws.invoke('image_preview',{});self.task_done('image_preview')
        self.assertEqual(self.ws.options['imageInfo']['source']['width'],2000)
        self.assertEqual(self.ws.options['imageInfo']['output'],{'width':1280,'height':640,'format':'JPEG'})
        self.ws.setOption('imageUrl','https://example.com/next.png');self.assertEqual(self.ws.options['imageInfo'],{})
    def test_library_empty_states_change_with_results_and_page(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;window=engine.rootObjects()[0]
        try:
            ws.selectPage('catalog');self.settle();empty=window.findChild(QObject,'libraryEmptyState')
            self.assertTrue(empty.property('visible'));self.assertEqual(empty.property('heading'),'Encontre sua próxima música')
            ws.searched({'tracks':[]});self.settle();self.assertEqual(empty.property('heading'),'Nenhuma música encontrada')
            ws.searched({'tracks':[{'title':'Song','source_url':'https://example.com/song'}]});self.settle();self.assertFalse(empty.property('visible'))
            ws.selectPage('history');self.settle();empty=window.findChild(QObject,'libraryEmptyState');self.assertTrue(empty.property('visible'));self.assertEqual(empty.property('heading'),'Seu histórico está vazio')
            ws.setOption('historyQuery','missing');self.settle();self.assertEqual(empty.property('heading'),'Nenhum arquivo encontrado')
        finally:close_application(engine,bridge)
    def test_effects_read_embedded_artwork_and_clear_it_for_next_file(self):
        import io
        from PIL import Image
        from mutagen.wave import WAVE
        from mutagen.id3 import TIT2,TPE1,TALB,APIC
        source=self.tone('tagged.wav');cover=io.BytesIO();Image.new('RGB',(80,80),'red').save(cover,format='PNG')
        audio=WAVE(source);audio.add_tags();audio.tags.add(TIT2(encoding=3,text=['Song title']));audio.tags.add(TPE1(encoding=3,text=['Artist']));audio.tags.add(TALB(encoding=3,text=['Album']));audio.tags.add(APIC(encoding=3,mime='image/png',type=3,desc='Front',data=cover.getvalue()));audio.save()
        original=source.read_bytes();self.ws.accept_files('effects',[str(source)]);self.task_done('effects_info')
        self.assertEqual(self.ws.options['effectsRecord']['title'],'Song title');self.assertEqual(self.ws.options['effectsRecord']['artists'],['Artist']);self.assertEqual(self.ws.options['effectsRecord']['album'],'Album')
        self.assertTrue(self.ws.options['effectsCover'].startswith('data:image/png;base64,'));self.assertGreater(self.ws.options['duration'],0);self.assertEqual(source.read_bytes(),original)
        plain=self.tone('plain.wav');self.ws.accept_files('effects',[str(plain)]);self.assertEqual(self.ws.options['effectsCover'],'');self.task_done('effects_info')
        self.assertEqual(self.ws.options['effectsRecord']['title'],'plain');self.assertEqual(self.ws.options['effectsCover'],'')
    def test_silence_detection_and_conversion_trim_only_edges(self):
        import math,wave
        from array import array
        from silence import detect,cached
        from video_converter import convert_video,probe_video
        if not TOOLS.is_dir():self.skipTest('FFmpeg required')
        source=self.root/'padded.wav';rate=44100;samples=array('h')
        for length,tone in [(1,False),(1,True),(.5,False),(1,True),(1,False)]:
            samples.extend(round(math.sin(i*2*math.pi*440/rate)*12000) if tone else 0 for i in range(round(rate*length)))
        with wave.open(str(source),'wb') as out:out.setparams((1,2,rate,0,'NONE',''));out.writeframes(samples.tobytes())
        original=source.read_bytes();result=detect(source,str(TOOLS));self.assertAlmostEqual(result['leading'],1,places=2);self.assertAlmostEqual(result['trailing'],1,places=2);self.assertEqual(len(result['intervals']),3)
        target=self.root/'trimmed.mp3'
        with patch('silence.detect',side_effect=AssertionError('Cached analysis should be reused')):
            convert_video({'source':str(source),'output':str(target),'video_format':'MP3','ffmpeg':str(TOOLS),'trim_silence':True,'silence_results':[result]})
        self.assertAlmostEqual(probe_video(target,str(TOOLS),audio_only=True)['duration'],2.5,delta=.15);self.assertEqual(source.read_bytes(),original)
        source.write_bytes(original+b'0');self.assertIsNone(cached(source,[result]))
    def test_queue_undo_restores_clear_and_order(self):
        self.ws.enqueue(['https://example.com/one.mp3','https://example.com/two.mp3'])
        ids=[job['id'] for job in self.ws.jobs];self.ws.jobs[0]['checked']=True;self.ws.queue_action('up');self.assertFalse(self.ws.undo_history.entries);self.ws.jobs[0]['checked']=False;self.ws.jobs[1]['checked']=True;self.ws.queue_action('up');self.assertNotEqual([job['id'] for job in self.ws.jobs],ids)
        self.ws.invoke('undo_queue',{});self.assertEqual([job['id'] for job in self.ws.jobs],ids)
        self.ws.queue_action('clear');self.assertFalse(self.ws.jobs);self.ws.invoke('undo_queue',{});self.assertEqual([job['id'] for job in self.ws.jobs],ids)
    def test_search_queues_remote_playback_and_requests_early_preparation(self):
        record={'title':'Remote song','artists':['Artist'],'album':'Album','source_url':'https://www.deezer.com/track/1','cover_url':'https://example.com/cover.png','duration_ms':180000}
        self.ws.searched({'tracks':[record]})
        with patch.object(self.bridge,'prepare_next_queued') as prepare:
            self.ws.invoke('jukebox_add',{'index':0});prepare.assert_called_once()
        entry=self.bridge.queuedTracks[0];self.assertEqual(entry['kind'],'catalog');self.assertEqual(entry['artist'],'Artist');self.assertEqual(entry['album'],'Album');self.assertEqual(entry['cover'],record['cover_url']);self.assertEqual(entry['duration'],180);self.assertEqual(self.ws.jobs,[])
        self.ws.invoke('catalog_add',{'index':0});row=self.ws.queueModel.rows[0];self.assertEqual(row['track_title'],'Remote song');self.assertEqual(row['track_artist'],'Artist');self.assertEqual(row['track_album'],'Album');self.assertEqual(row['track_cover'],record['cover_url'])
    def test_queue_destination_menu_routes_playback_and_download_separately(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QUrl,QMetaObject
        from PySide6.QtQml import QQmlComponent
        app,engine,bridge=create_application(complete=False);ws=engine.workspace
        try:
            ws.searched({'tracks':[{'title':'Song','artists':['Artist'],'source_url':'https://www.deezer.com/track/1'}]})
            component=QQmlComponent(engine,QUrl.fromLocalFile(str(ROOT/'qml/QueueDestinationMenu.qml')));menu=component.create();self.assertIsNotNone(menu,component.errors());menu.setProperty('recordIndex',0)
            playback=menu.findChild(QObject,'playbackDestination');QMetaObject.invokeMethod(playback,'triggered');self.assertEqual(len(bridge.queuedTracks),1);self.assertEqual(ws.jobs,[])
            download=menu.findChild(QObject,'downloadDestination');QMetaObject.invokeMethod(download,'triggered');self.assertEqual(len(ws.jobs),1);self.assertEqual(len(bridge.queuedTracks),1);menu.deleteLater()
        finally:close_application(engine,bridge)
    def test_metadata_artwork_is_next_to_controls_and_full_artist_is_visible(self):
        import io,base64
        from PIL import Image
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QPointF
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;window=engine.rootObjects()[0]
        try:
            cover=io.BytesIO();Image.new('RGB',(100,100),'blue').save(cover,format='PNG')
            window.resize(1360,900)
            ws.selectPage('metadata');ws.audio_loaded({'record':{'title':'Song','artists':['Stardust','Other Artist'],'album':'Album'},'cover':base64.b64encode(cover.getvalue()).decode()});self.settle()
            def find(item,name):
                if item.objectName()==name:return item
                return next((result for child in item.childItems() if (result:=find(child,name)) is not None),None)
            self.assertEqual(find(window.contentItem(),'metadataField_artists').property('text'),'Stardust, Other Artist')
            art=window.findChild(QObject,'metadataArtwork');self.assertTrue(art.property('visible'))
            self.assertGreater(art.mapToScene(QPointF(0,0)).x(),find(window.contentItem(),'metadataField_title').mapToScene(QPointF(0,0)).x()+400)
            self.assertLess(art.mapToScene(QPointF(0,0)).x(),900)
        finally:close_application(engine,bridge)
    def test_queue_metadata_update_keeps_the_model_and_selection(self):
        self.ws.enqueue(['https://example.com/one.mp3']);job=self.ws.jobs[0];self.ws.toggle_row('queue',0,True)
        with patch.object(self.ws.models['queue'],'replace',wraps=self.ws.models['queue'].replace) as reset:
            self.ws.on_event(job['id'],{'type':'queue_title','title':'Artist - Song','queue_info':{'title':'Song','artists':['Artist'],'album':'Album','cover_url':'https://example.com/cover.png','duration_ms':180000}});reset.assert_not_called()
        row=self.ws.queueModel.rows[0];self.assertTrue(row['checked']);self.assertEqual(row['track_artist'],'Artist');self.assertEqual(row['track_duration'],180)
    def test_close_exits_qt_without_second_click(self):
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QTimer
        app,engine,bridge=create_application(complete=False);ws=engine.workspace
        timer=QTimer();timer.setSingleShot(True);timer.timeout.connect(ws.requestClose);timer.start(100)
        watchdog=QTimer();watchdog.setSingleShot(True);watchdog.timeout.connect(lambda:app.exit(99));watchdog.start(4000)
        try:self.assertEqual(app.exec(),0)
        finally:timer.stop();watchdog.stop();close_application(engine,bridge)

    def test_comparison_rejects_same_record_and_displays_differences(self):
        self.ws.searched({'tracks':[{'title':'Song','artists':['Artist'],'album':'One','source_url':'https://www.deezer.com/track/1'},{'title':'Song live','artists':['Artist'],'album':'Two','source_url':'https://www.deezer.com/track/2'}]})
        self.assertIn('já foi selecionada',self.ws.compareText(0,0));text=self.ws.compareText(0,1);self.assertIn('Song live',text);self.assertIn('Two',text)
    def test_cover_crop_is_square_and_does_not_change_original(self):
        from PIL import Image
        source=self.root/'cover.png';Image.new('RGB',(700,400),'green').save(source);original=source.read_bytes()
        self.ws.accept_files('cover_path',[str(source)]);self.ws.invoke('apply_cover_crop',{'zoom':2,'x':.1,'y':-.1});self.task_done('cover_crop')
        target=Path(self.ws.options['cover_path']);self.assertNotEqual(target,source)
        with Image.open(target) as image:self.assertEqual(image.size,(1000,1000))
        self.assertEqual(source.read_bytes(),original)
    def test_worker_cancel_stops_blocked_process(self):
        fixture=self.root/'blocked.py';fixture.write_text('import sys,json,time\njson.loads(sys.stdin.readline())\nprint(json.dumps({"type":"stage","message":"ready"}),flush=True)\ntime.sleep(60)\n',encoding='utf-8')
        job=self.ws.enqueue(['https://example.com/cancel.mp3'])[0];identity=job['id'];cancel=threading.Event();self.ws.active[identity]={'cancel':cancel,'process':None};job['state']='Em andamento'
        self.ws.launch_thread(lambda:self.ws.process_worker(identity,{},cancel,str(fixture)))
        self.wait_for(lambda:self.ws.active[identity]['process'] is not None);process=self.ws.active[identity]['process'];self.ws.stop_job(identity);self.wait_for(lambda:not self.ws.active)
        self.assertIsNotNone(process.poll());self.assertEqual(job['state'],'Cancelado')
    def test_effects_export_real_worker(self):
        if not TOOLS.is_dir():self.skipTest('FFmpeg required')
        source=self.tone();target=self.root/'effects.mp3';self.ws.accept_files('effects',[str(source)]);self.task_done('effects_info');self.assertGreater(self.ws.options['duration'],0)
        with patch('PySide6.QtWidgets.QFileDialog.getSaveFileName',return_value=(str(target),'')):self.ws.export_effects()
        self.wait_for(lambda:not self.ws.active,20000);self.assertTrue(target.is_file(),self.ws.logs);self.assertTrue(self.ws.library.history())
    def test_settings_import_export_keeps_secrets_out(self):
        path=self.root/'settings.json';self.ws.settings['spotify_client_secret']='private-secret';self.ws.settings['social_cookies']='private-cookies.txt'
        with patch('PySide6.QtWidgets.QFileDialog.getSaveFileName',return_value=(str(path),'')):self.ws.settings_file_action('export_settings')
        raw=path.read_text(encoding='utf-8');self.assertNotIn('private-secret',raw);self.assertNotIn('private-cookies',raw)
        self.ws.setSetting('theme_accent','Azul')
        with patch('PySide6.QtWidgets.QFileDialog.getOpenFileName',return_value=(str(path),'')):self.ws.settings_file_action('import_settings')
        self.assertNotEqual(self.ws.settings['theme_accent'],'Azul')
    def test_schedule_does_not_override_manual_stop(self):
        self.ws.settings.update(schedule_enabled=True,schedule_start='00:00',schedule_stop='23:59');self.ws.enqueue(['https://example.com/queued.mp3']);self.ws.stop_queue()
        with patch.object(self.ws,'fill_queue') as fill:self.ws.tick();fill.assert_not_called()

    def test_power_countdown_can_be_cancelled_without_system_command(self):
        with patch('qt_workspace_ui.subprocess.run') as command:
            self.ws.shutdown_countdown();self.assertTrue(self.ws.shutdown_timer.isActive())
            self.ws.replyChoice(self.ws.choice['identity'],{'cancel':True});self.assertFalse(self.ws.shutdown_timer.isActive());command.assert_not_called()

    def test_qml_buttons_add_links_and_convert_real_file(self):
        if not TOOLS.is_dir():self.skipTest('FFmpeg required')
        from qt_desktop_ui import create_application,close_application
        from PySide6.QtCore import QObject,QMetaObject
        app,engine,bridge=create_application(complete=False);ws=engine.workspace;window=engine.rootObjects()[0]
        try:
            ws.selectPage('downloads');self.settle();ws.setOption('links','https://example.com/test.mp3')
            button=window.findChild(QObject,'addLinksButton');self.assertIsNotNone(button);self.assertTrue(button.property('enabled'));QMetaObject.invokeMethod(button,'clicked')
            self.assertEqual(len(ws.jobs),1);self.assertFalse(ws.running)
            ws.selectPage('converter');self.settle();source=self.tone();target=self.root/'qml-converted.mp3';ws.accept_files('converter',[str(source)]);self.settle()
            button=window.findChild(QObject,'convertButton');self.assertIsNotNone(button);self.assertTrue(button.property('enabled'))
            with patch('PySide6.QtWidgets.QFileDialog.getSaveFileName',return_value=(str(target),'')):QMetaObject.invokeMethod(button,'clicked')
            self.wait_for(lambda:'convert' not in ws.tasks,20000);self.assertTrue(target.is_file(),ws.status)
        finally:close_application(engine,bridge)

    def test_worker_prepares_connected_account_metadata_before_serializing(self):
        fixture=self.root/'engine.py';fixture.write_text('import sys,json\nconfig=json.loads(sys.stdin.readline())\nassert config["catalog_record"]["title"]=="Prepared"\nprint(json.dumps({"type":"done"}),flush=True)\n',encoding='utf-8')
        job=self.ws.enqueue(['https://example.com/account.mp3'])[0];identity=job['id'];cancel=threading.Event();self.ws.active[identity]={'cancel':cancel,'process':None};job['state']='Em andamento'
        with patch('spotify_metadata.prepare_spotify_config',return_value={'catalog_record':{'title':'Prepared'}}) as prepare:
            self.ws.launch_thread(lambda:self.ws.process_worker(identity,{},cancel,str(fixture)));self.wait_for(lambda:not self.ws.active)
            prepare.assert_called_once_with({},self.ws.account)
        self.assertEqual(job['state'],'Concluído')

if __name__=='__main__':unittest.main()
