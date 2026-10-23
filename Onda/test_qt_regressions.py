"""Review regressions: real Qt controller, isolated storage, no media/network workers."""
import os,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch

class MemoryCredentials:
    def __init__(self):self.record=None
    def load(self):return self.record
    def save(self,identity,secret):self.record=(identity,secret)
    def forget(self):self.record=None

@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Optional Qt desktop tests')
class ReviewRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([]);cls.app.setQuitOnLastWindowClosed(False)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        env=patch.dict(os.environ,{'LOCALAPPDATA':self.temp.name,'ONDA_ALIAS_CACHE_ROOT':self.temp.name});env.start();self.addCleanup(env.stop)
        os.environ.pop('SPOTIFY_CLIENT_ID',None);os.environ.pop('SPOTIFY_CLIENT_SECRET',None)
        self.vault=MemoryCredentials();credentials=patch('credentials.CredentialStore',return_value=self.vault);credentials.start();self.addCleanup(credentials.stop)
        from preferences import PreferenceStore
        from qt_jukebox_ui import JukeboxBridge
        from qt_workspace_ui import DesktopWorkspace
        self.store=PreferenceStore();self.store.save({'check_updates':False,'clipboard_links':False,'detect_duplicates':False,'folder':self.temp.name,'finish_action':'Nenhuma','concurrent_downloads':'2','memory_reserve':'Sem reserva'})
        self.bridge=JukeboxBridge(self.store);self.ws=DesktopWorkspace(self.bridge)
        self.addCleanup(self.bridge.shutdown);self.addCleanup(self.ws.shutdown)
        workers=patch.object(self.ws,'launch_thread');self.launch=workers.start();self.addCleanup(workers.stop)
        self.ws.title_lookup.submit=Mock();self.ws.queue_finished=Mock()
    def add(self,name,now=False):return self.ws.enqueue(['https://example.com/'+name+'.mp4'],start=now)[0]
    def finish(self,job,cancelled=False,success=True):self.ws.on_event('finished',{'id':job['id'],'cancelled':cancelled,'success':success})
    def test_immediate_excludes_pending_and_completes_once(self):
        old=self.add('old');new=self.add('new',True)
        self.assertEqual(old['state'],'Na fila');self.assertEqual(new['state'],'Em andamento')
        self.finish(new);self.assertEqual(old['state'],'Na fila');self.ws.queue_finished.assert_called_once()
        self.ws.fill_queue();self.ws.queue_finished.assert_called_once()
    def test_immediate_requests_extend_when_slots_are_full(self):
        self.ws.settings['concurrent_downloads']='1'
        old=self.add('old');a=self.add('a',True);b=self.add('b',True)
        self.finish(a);self.assertEqual(b['state'],'Em andamento');self.assertEqual(old['state'],'Na fila')
        self.finish(b);self.ws.queue_finished.assert_called_once()
    def test_global_queue_extends_scoped_run(self):
        old=self.add('old');self.add('new',True);self.ws.start_queue()
        self.assertEqual(old['state'],'Em andamento')
        extra=self.add('extra');self.ws.fill_queue();self.assertEqual(extra['state'],'Na fila')
        self.finish(old);self.assertEqual(extra['state'],'Em andamento')
    def test_empty_immediate_request_does_not_start_queue(self):
        old=self.add('old');self.ws.enqueue([],start=True)
        self.assertEqual(old['state'],'Na fila');self.ws.queue_finished.assert_not_called()
    def test_duplicate_confirmation_keeps_scope(self):
        old=self.add('old');self.ws.settings['detect_duplicates']=True
        with patch.object(self.ws.library,'find_duplicate',return_value='existing.mp4'):self.ws.enqueue(['https://example.com/new.mp4'],start=True)
        self.ws.replyChoice(self.ws.choice['identity'],{'yes':True})
        self.assertEqual(old['state'],'Na fila');self.assertEqual(self.ws.jobs[-1]['state'],'Em andamento')
    def test_storage_confirmation_keeps_scope(self):
        old=self.add('old')
        with patch('queue_control.storage_report',return_value=(0,0,0,True)):new=self.add('new',True)
        self.assertEqual(new['state'],'Na fila');self.ws.replyChoice(self.ws.choice['identity'],{'yes':True})
        self.assertEqual(old['state'],'Na fila');self.assertEqual(new['state'],'Em andamento')
    def test_add_links_button_keeps_scope(self):
        old=self.add('old');self.ws.options['links']='https://example.com/new.mp4';self.ws.dispatch('add_links',{'start':True})
        self.assertEqual(old['state'],'Na fila');self.assertEqual(self.ws.jobs[-1]['state'],'Em andamento')
    def test_playlist_batch_checks_storage_once_and_keeps_scope(self):
        old=self.add('old')
        records=[{'source_url':'https://example.com/'+name+'.mp4','title':name} for name in ('a','b')]
        with patch('queue_control.storage_report',return_value=(0,0,0,False)) as storage:
            added=self.ws.enqueue_tracks(records,start=True)
        self.assertEqual(sum(call.kwargs.get('check_space',True) for call in storage.call_args_list),1)
        self.assertEqual(old['state'],'Na fila')
        self.assertTrue(all(job['state']=='Em andamento' for job in added))
    def test_pause_reasons_survive_queue_persistence(self):
        a=self.add('manual');self.ws.queue_action('pause',a['id'])
        b=self.add('scheduled');b.update(state='Pausado',_pause_reason='schedule');self.ws.save_queue()
        restored=self.ws.library.load_queue()
        self.assertEqual([job['_pause_reason'] for job in restored],['manual','schedule'])
        self.assertTrue(all(job['state']=='Pausado' for job in restored))
    def test_pending_pause_and_scoped_resume(self):
        a=self.add('a');old=self.add('old');self.ws.queue_action('pause',a['id']);self.assertEqual(a['state'],'Pausado')
        self.ws.queue_action('resume',a['id']);self.assertEqual(a['state'],'Em andamento');self.assertEqual(old['state'],'Na fila')
        self.finish(a);self.assertEqual(a['state'],'Concluído')
    def test_global_start_preserves_manual_pause(self):
        a=self.add('a');b=self.add('b');self.ws.queue_action('pause',a['id']);self.ws.start_queue()
        self.assertEqual(a['state'],'Pausado');self.assertEqual(b['state'],'Em andamento');self.finish(b);self.ws.queue_finished.assert_not_called()
    def test_last_pause_is_not_completion(self):
        a=self.add('a',True);self.ws.queue_action('pause',a['id']);self.finish(a,True,False)
        self.assertEqual(a['state'],'Pausado');self.ws.queue_finished.assert_not_called()
        self.ws.queue_action('resume',a['id']);self.finish(a);self.ws.queue_finished.assert_called_once()
    def test_resume_waits_for_old_worker(self):
        a=self.add('a',True);self.ws.queue_action('pause',a['id']);self.ws.queue_action('resume',a['id']);self.assertEqual(self.launch.call_count,1)
        self.finish(a,True,False);self.assertEqual(self.launch.call_count,2);self.assertEqual(a['state'],'Em andamento')
        self.finish(a);self.assertEqual(a['state'],'Concluído')
    def test_schedule_only_resumes_its_pauses(self):
        self.ws.settings['schedule_enabled']=True
        a=self.add('manual');b=self.add('scheduled');self.ws.queue_action('pause',a['id']);b.update(state='Pausado',_pause_reason='schedule')
        with patch('advanced_options.schedule_allowed',return_value=True):self.ws.tick()
        self.assertEqual(a['state'],'Pausado');self.assertEqual(b['state'],'Em andamento')
    def test_schedule_preserves_scope_across_closed_window(self):
        old=self.add('old');a=self.add('a');self.ws.begin_queue({a['id']})
        with patch('advanced_options.schedule_allowed',return_value=False):self.ws.tick();self.finish(a,True,False)
        self.assertEqual(a.get('_pause_reason'),'schedule')
        with patch('advanced_options.schedule_allowed',return_value=True):self.ws.tick()
        self.assertEqual(a['state'],'Em andamento');self.assertEqual(old['state'],'Na fila')
    def test_schedule_does_not_replace_manual_reason(self):
        a=self.add('a',True);self.ws.queue_action('pause',a['id'])
        with patch('advanced_options.schedule_allowed',return_value=False):self.ws.tick();self.finish(a,True,False)
        with patch('advanced_options.schedule_allowed',return_value=True):self.ws.tick()
        self.assertEqual(a['state'],'Pausado');self.assertEqual(a['_pause_reason'],'manual')
    def test_stop_and_empty_queue_do_not_report_completion(self):
        self.ws.start_queue();self.ws.queue_finished.assert_not_called()
        a=self.add('a',True);self.ws.stop_queue();self.finish(a,True,False);self.ws.queue_finished.assert_not_called()
    def test_social_worker_gets_social_cookies(self):
        self.ws.settings.update(social_cookies='/social.txt',youtube_cookies='/youtube.txt')
        with patch.object(self.ws,'process_worker') as worker:
            self.ws.enqueue(['https://www.instagram.com/p/example/'],start=True);self.launch.call_args.args[0]()
        self.assertEqual(worker.call_args.args[1]['cookies_file'],'/social.txt')
    def test_stable_selection_order_at_boundaries_and_gaps(self):
        for action,selection,expected in [('down','AB','CABD'),('up','CD','ACDB'),('priority','BD','BDAC'),('down','AC','BADC'),('up','AB','ABCD'),('down','CD','ABCD')]:
            with self.subTest(action=action,selection=selection):
                self.ws.jobs=[]
                for name in 'ABCD':self.add(name)['checked']=name in selection
                self.ws.queue_action(action);self.assertEqual(''.join(Path(job['url']).stem for job in self.ws.jobs),expected)
    def test_cleared_secret_stays_removed_after_reopen(self):
        self.ws.settings.update(spotify_client_id='id',spotify_client_secret='secret',remember_settings=True);self.ws.persist();self.assertEqual(self.vault.load(),('id','secret'))
        self.ws.setSetting('spotify_client_secret','');self.ws.persist();self.assertIsNone(self.vault.load())
        from qt_jukebox_ui import JukeboxBridge
        from qt_workspace_ui import DesktopWorkspace
        bridge=JukeboxBridge(self.store);other=DesktopWorkspace(bridge)
        try:self.assertEqual(other.settings['spotify_client_secret'],'');self.assertEqual(other.settings['spotify_client_id'],'id')
        finally:other.shutdown();bridge.shutdown()
    def test_credentials_removable_without_oauth(self):
        self.ws.account=Mock(connected=False);self.ws.settings.update(spotify_client_id='id',spotify_client_secret='secret');self.ws.persist()
        self.assertTrue(self.ws.activity['hasCredentials']);self.ws.dispatch('forget_credentials',{})
        self.assertFalse(self.ws.activity['hasCredentials']);self.assertIsNone(self.vault.load())
    def test_individual_shortcut_disable_persists_and_reset_restores(self):
        from shortcut_options import effective_bindings
        self.ws.dispatch('shortcut_set',{'key':'links','sequence':''});self.ws.persist()
        self.assertNotIn('links',effective_bindings(self.store.load()['shortcut_keys']).values())
        self.ws.dispatch('shortcut_reset',{'key':'links'});self.assertIn('links',effective_bindings(self.ws.settings['shortcut_keys']).values())
    def test_restore_preserves_window_state(self):
        from PySide6.QtGui import QWindow
        from PySide6.QtCore import Qt
        window=QWindow();self.ws.attach(window)
        try:
            for show,expected in [(window.showNormal,Qt.WindowNoState),(window.showMaximized,Qt.WindowMaximized),(window.showFullScreen,Qt.WindowFullScreen)]:
                show();self.app.processEvents();window.hide();self.ws.restore();self.app.processEvents();self.assertEqual(window.windowState(),expected)
                window.showMinimized();self.app.processEvents();self.ws.restore();self.app.processEvents();self.assertEqual(window.windowState(),expected)
        finally:window.close();self.ws.window=None

    def test_zero_available_memory_blocks_new_download(self):
        self.ws.settings['memory_reserve']='512 MB'
        with patch('performance.available_memory_mb',return_value=0):
            job=self.add('low-memory',True)
        self.assertEqual(job['state'],'Na fila')
        self.launch.assert_not_called()

    def test_low_memory_does_not_block_finished_queue(self):
        job=self.add('finished',True)
        self.ws.settings['memory_reserve']='512 MB'
        with patch('performance.available_memory_mb',return_value=1):self.finish(job)
        self.assertFalse(self.ws.running)
        self.ws.queue_finished.assert_called_once()

    def test_resume_mixed_selection_does_not_redownload_completed(self):
        done=self.add('done',True);self.finish(done)
        paused=self.add('paused');self.ws.queue_action('pause',paused['id'])
        done['checked']=paused['checked']=True
        self.ws.queue_action('resume')
        self.assertEqual(done['state'],'Concluído')
        self.assertEqual(paused['state'],'Em andamento')

    def test_repeated_low_memory_poll_does_not_repeat_notice(self):
        self.ws.settings['memory_reserve']='512 MB'
        with patch.object(self.ws,'notify') as notice,patch('performance.available_memory_mb',return_value=1):
            self.add('waiting',True)
            for _ in range(5):self.ws.fill_queue()
        warnings=[call for call in notice.call_args_list if 'memória livre' in str(call)]
        self.assertEqual(len(warnings),1)

    def test_cancel_all_preserves_completed_and_failed_results(self):
        done=self.add('done',True);self.finish(done)
        failed=self.add('failed',True);self.finish(failed,success=False)
        pending=self.add('pending')
        self.ws.queue_action('cancel_all')
        self.assertEqual(done['state'],'Concluído')
        self.assertEqual(failed['state'],'Falhou')
        self.assertEqual(pending['state'],'Cancelado')

    def test_memory_wait_recovers_and_warns_again_for_new_shortage(self):
        self.ws.settings['memory_reserve']='512 MB'
        with patch('performance.available_memory_mb',return_value=1):job=self.add('waiting',True)
        with patch('performance.available_memory_mb',return_value=1024):self.ws.fill_queue()
        self.assertEqual(job['state'],'Em andamento')
        self.assertFalse(self.ws.memory_waiting)
        with patch('performance.available_memory_mb',return_value=1),patch.object(self.ws,'notify') as notice:
            self.add('second',True)
        self.assertTrue(any('memória livre' in str(call) for call in notice.call_args_list))

    def test_queue_metadata_selection_deduplicates_and_skips_active(self):
        paths=[Path(self.temp.name)/name for name in ('a.mp3','b.flac','active.mp3')]
        for path in paths:path.touch()
        for i,path in enumerate(paths):
            job=self.add(str(i));job.update(checked=True,output_files=[str(path),str(path)])
        self.ws.active[self.ws.jobs[-1]['id']]={'cancel':__import__('threading').Event(),'process':None}
        with patch.object(self.ws,'accept_files') as accept:
            self.ws.dispatch('queue_edit',{})
        accept.assert_called_once_with('metadata',[str(path.resolve()) for path in paths[:2]])
        self.assertEqual(self.ws.currentPage,'metadata')
        self.ws.active.clear()

    def test_history_metadata_uses_selected_existing_audio_only(self):
        audio=Path(self.temp.name)/'song.mp3';audio.touch()
        self.ws.models['history'].replace([{'path':str(audio),'checked':True}])
        with patch.object(self.ws,'accept_files') as accept:self.ws.dispatch('history_edit',{})
        accept.assert_called_once_with('metadata',[str(audio.resolve())])

    def test_seek_target_survives_timer_tick_before_preview_restart(self):
        self.ws.player.active=True;self.ws.preview_kind='effects'
        with patch.object(self.ws.player,'position_snapshot',return_value=12):
            self.ws.setOption('position',90)
            self.ws.tick()
            self.assertEqual(self.ws.options['position'],90)
        self.ws.preview_timer.stop();self.ws.player.active=False

    def test_lyrics_enhanced_tracks_words_and_jukebox_jumps(self):
        from synced_lyrics import parse_lrc,karaoke_at,line_at
        rows=parse_lrc('[00:10.00]<00:10.00>Hello <00:11.00>world')
        self.assertEqual(line_at(rows,10.5),'Hello world')
        self.assertIn('<b>Hello </b>world',karaoke_at(rows,10.5))
        self.assertIn('<b>world</b>',karaoke_at(rows,11.5))
        self.assertEqual(karaoke_at(rows,5),'')
        self.ws.bridge.model={'source':'example.wav','beats':[0,10,20],'duration':20}
        self.ws.bridge._position=1.5;self.ws.bridge._phase=.5
        self.ws.selectPage('jukebox')
        self.assertEqual(self.ws.lyricsFrame()['position'],15)
        self.ws.bridge._position=0;self.ws.bridge._phase=.2
        self.assertEqual(self.ws.lyricsFrame()['position'],2)

    def test_manual_download_ignores_schedule_and_keeps_filling_slots(self):
        self.ws.settings.update(schedule_enabled=True,concurrent_downloads='1')
        old=self.add('old')
        with patch('advanced_options.schedule_allowed',return_value=False):
            a=self.add('a',True);b=self.add('b',True)
            self.ws.tick()
            self.assertFalse(self.ws.active[a['id']]['cancel'].is_set())
            self.finish(a)
            self.assertEqual(b['state'],'Em andamento')
            self.assertEqual(old['state'],'Na fila')

    def test_manual_global_download_works_outside_schedule(self):
        self.ws.settings['schedule_enabled']=True
        a=self.add('a')
        with patch('advanced_options.schedule_allowed',return_value=False):
            self.ws.start_queue();self.ws.tick()
        self.assertEqual(a['state'],'Em andamento')

    def test_automatic_queue_still_waits_for_schedule(self):
        self.ws.settings['schedule_enabled']=True
        a=self.add('a')
        with patch('advanced_options.schedule_allowed',return_value=False):self.ws.begin_queue()
        self.assertEqual(a['state'],'Na fila')

    def test_history_card_edit_uses_multiple_checked_files(self):
        files=[Path(self.temp.name)/name for name in ('first.mp3','second.flac')]
        for path in files:path.touch()
        self.ws.models['history'].replace([dict(id=i,path=str(path),checked=True) for i,path in enumerate(files)])
        with patch.object(self.ws,'accept_files') as accept:self.ws.dispatch('history_edit',{'index':0})
        accept.assert_called_once_with('metadata',[str(path.resolve()) for path in files])

    def test_online_lyrics_without_song_warns_and_does_not_start_task(self):
        for page in ('effects','jukebox'):
            self.ws.selectPage(page)
            with patch.object(self.ws,'run_task') as task,patch.object(self.ws,'notify') as notice:
                self.ws.dispatch('lyrics_online',{})
                task.assert_not_called()
                notice.assert_called_once_with('Selecione uma música antes de buscar a letra online.')
