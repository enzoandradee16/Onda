import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from performance import clean,thread_args,priority_flags,available_memory_mb
from preferences import PreferenceStore

class PerformanceTests(unittest.TestCase):
    def test_validation_defaults_and_real_memory_query(self):
        self.assertEqual(clean({'conversion_threads':'99999','memory_reserve':True,'worker_priority':'Alta'}),{})
        self.assertEqual(thread_args({}),[])
        self.assertEqual(thread_args({},default=2),['-threads','2'])
        self.assertEqual(thread_args({'conversion_threads':'1'})[:2],['-threads','1'])
        self.assertEqual(priority_flags({'worker_priority':'Normal'}),0)
        if os.name=='nt':
            self.assertNotEqual(priority_flags({'worker_priority':'Baixa'}),0)
            self.assertGreater(available_memory_mb(),0)
        values={'conversion_threads':'4','worker_priority':'Baixa','memory_reserve':'1 GB'}
        self.assertEqual({k:PreferenceStore.clean(values)[k] for k in values},values)

    def test_above_normal_priority_and_persistence(self):
        import subprocess
        self.assertEqual(PreferenceStore.clean({'worker_priority':'Acima do normal'})['worker_priority'],'Acima do normal')
        if os.name=='nt':
            self.assertEqual(priority_flags({'worker_priority':'Acima do normal'}),subprocess.ABOVE_NORMAL_PRIORITY_CLASS)
        self.assertEqual(priority_flags({'worker_priority':'Alta'}),0)

    def test_cpu_detection_choices_and_saved_limits(self):
        from performance import cpu_threads,thread_choices
        for count in (1,6,12,None):
            with self.subTest(count=count),patch('performance.os.cpu_count',return_value=count):
                limit=count or 1
                self.assertEqual(cpu_threads(),limit)
                self.assertEqual(thread_choices(),('Automático',)+tuple(str(n) for n in range(1,limit+1)))
                self.assertEqual(clean({'conversion_threads':'32'})['conversion_threads'],str(min(32,limit)))
                self.assertEqual(thread_args({'conversion_threads':'32'})[:2],['-threads',str(min(32,limit))])
                self.assertEqual(thread_args({},default=2),['-threads',str(min(2,limit))])
                self.assertEqual(PreferenceStore.clean({'conversion_threads':'32'})['conversion_threads'],str(min(32,limit)))
        for value in ('0','-1','1.5',True):
            self.assertEqual(clean({'conversion_threads':value}),{})

    def test_download_postprocessors_receive_thread_limits(self):
        from engine import build_options
        config={'url':'https://example.com/audio','mode':'mp3','folder':'.','height':None,'audio_quality':'320 kbps','conversion_threads':'1'}
        opts=build_options(config)
        self.assertEqual(opts['postprocessor_args']['ffmpeg_o'][:2],['-threads','1'])
        config.pop('conversion_threads')
        self.assertNotIn('postprocessor_args',build_options(config))

    def test_real_conversion_uses_selected_threads_and_priority(self):
        import subprocess
        from video_converter import convert_video
        from test_video_converter import VideoConversionTests
        from ffmpeg_runtime import existing_folder
        folder=existing_folder()
        if not folder:self.skipTest('FFmpeg unavailable')
        fixture=VideoConversionTests();fixture.folder=folder
        with tempfile.TemporaryDirectory() as root:
            source=fixture.fixture(root)
            with patch('video_converter.subprocess.Popen',wraps=subprocess.Popen) as launch:
                output=Path(root)/'converted.mp4'
                convert_video({'source':str(source),'output':str(output),'ffmpeg':str(folder),'conversion_threads':'1','worker_priority':'Baixa'})
            command=next(call for call in launch.call_args_list if str(call.args[0][0]).lower().endswith('ffmpeg.exe'))
            self.assertEqual(command.args[0][command.args[0].index('-threads')+1],'1')
            if os.name=='nt':self.assertTrue(command.kwargs['creationflags']&subprocess.BELOW_NORMAL_PRIORITY_CLASS)
            self.assertTrue(output.is_file())

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class PerformanceUiTests(unittest.TestCase):
    def test_memory_wait_resume_cancel_settings_and_saved_values(self):
        from app import App
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False);app.clipboard_watch.shutdown();app.update()
            try:
                app.folder.set(folder);app.detect_duplicates.set(False)
                ids=app.add(lines=['https://example.com/one.mp3','https://example.com/two.mp3'],overrides={'display_name':'fixture'})
                app.memory_reserve.set('1 GB');app.conversion_threads.set('1');app.worker_priority.set('Baixa')
                with patch('performance.available_memory_mb',return_value=100),patch('parallel_queue.threading.Thread') as worker:
                    app.parallel.start(None)
                    worker.assert_not_called()
                    self.assertTrue(app.running);self.assertIsNotNone(app.parallel.memory_wait)
                    self.assertEqual(app.jobs[ids[0]]['state'],'Na fila')
                with patch('performance.available_memory_mb',return_value=2048),patch('parallel_queue.threading.Thread') as worker:
                    app.parallel.fill()
                    self.assertEqual(len(app.parallel.workers),1)
                    self.assertIsNone(app.parallel.memory_wait)
                    config=worker.call_args.kwargs['args'][1]
                    self.assertEqual(config['conversion_threads'],'1')
                    self.assertEqual(config['worker_priority'],'Baixa')
                    app.concurrent_downloads.set('2');app.parallel.fill()
                    self.assertEqual(len(app.parallel.workers),2)
                app.parallel.workers.clear();app.active=None
                for key in ids:app.jobs[key]['state']='Na fila'
                with patch('performance.available_memory_mb',return_value=100):
                    app.parallel.fill()
                    self.assertIsNotNone(app.parallel.memory_wait)
                    app.cancel()
                    self.assertIsNone(app.parallel.memory_wait)
                    self.assertFalse(app.running)
                app.settings_search.query.set('Threads por conversão');app.settings_search.search()
                self.assertEqual(app.settings_search.results[0][3],'Desempenho')
                app.persist_preferences()
                self.assertEqual(app.preference_store.load()['memory_reserve'],'1 GB')
            finally:
                app.parallel.workers.clear();app.active=None;app.destroy()

if __name__=='__main__':unittest.main()
