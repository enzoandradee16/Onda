"""Deterministic audio/graph tests: no network or audible playback."""
import base64,json,math,os,tempfile,unittest,wave
from array import array
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import jukebox

TOOLS=Path(os.environ.get('LOCALAPPDATA',''))/'Onda/tools/ffmpeg/9.0.2'

def song(path,seconds=8,silent=False):
    samples=array('h')
    for i in range(int(seconds*jukebox.RATE)):
        t=i/jukebox.RATE;phase=t%.5
        value=0 if silent else round((math.sin(t*2*math.pi*261.63)+math.sin(t*2*math.pi*329.63)+math.sin(t*2*math.pi*392))*2400*(.4+.6*math.exp(-phase*24)))
        samples.extend((value,value))
    with wave.open(str(path),'wb') as out:out.setparams((2,2,jukebox.RATE,0,'NONE',''));out.writeframes(samples.tobytes())

class JukeboxTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,{'ONDA_ALIAS_CACHE_ROOT':self.temp.name});self.env.start()
        self.base=jukebox.cache_root()/('a'*64);self.base.mkdir(parents=True)
        song(self.base/'audio.wav')
        model={'version':1,'duration':8,'bpm':120,'beats':[i*.25 for i in range(33)],'neighbors':[[] for _ in range(32)],'links':1}
        model['neighbors'][4]=[20];(self.base/'analysis.json').write_text(json.dumps(model));self.model=model
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def test_normal_and_zero_variation_preserve_all_samples(self):
        for variation,normal in [(0,False),(100,True)]:
            player=jukebox.Session(self.base,seed=1)
            try:
                parts=[player.chunk(variation,0,100,normal) for _ in range(32)]
                with wave.open(str(self.base/'audio.wav'),'rb') as original:self.assertEqual(b''.join(p['pcm'] for p in parts),original.readframes(original.getnframes()))
                self.assertEqual(player.index,0);self.assertEqual(player.jumps,0);self.assertAlmostEqual(sum(p['seconds'] for p in parts),8)
            finally:player.close()
    def test_jump_uses_only_graph_neighbors_and_honors_spacing(self):
        player=jukebox.Session(self.base);player.random=SimpleNamespace(random=lambda:0,choice=lambda rows:rows[0])
        try:
            for _ in range(4):self.assertFalse(player.chunk(100,100,100)['jumped'])
            part=player.chunk(100,100,100);self.assertTrue(part['jumped']);self.assertEqual(part['next'],20);self.assertEqual(part['jumps'],1)
            self.assertEqual(len(part['pcm']),(round(1.25*jukebox.RATE)-round(jukebox.RATE))*4)
            self.assertLessEqual(max(map(abs,array('h',part['pcm']))),32767)
        finally:player.close()
    def test_manual_seek_plays_selected_beat_without_counting_jump(self):
        player=jukebox.Session(self.base)
        try:
            player.seek(20);part=player.chunk(0,0,100)
            self.assertEqual(part['index'],20);self.assertEqual(part['next'],21)
            self.assertEqual(part['jumps'],0)
            for invalid in (-1,32,1.5):
                with self.assertRaises(ValueError):player.seek(invalid)
        finally:player.close()

    def test_active_cache_is_protected_until_all_sessions_close(self):
        from cache_cleanup import clear_cache
        a,b=jukebox.Session(self.base),jukebox.Session(self.base)
        a.close();clear_cache();self.assertTrue((self.base/'audio.wav').exists())
        b.close();clear_cache();self.assertFalse((self.base/'audio.wav').exists())
    def test_invalid_graph_and_external_cache_are_rejected(self):
        bad=dict(self.model,neighbors=[[999]]+self.model['neighbors'][1:])
        with self.assertRaises(ValueError):jukebox.validate_model(bad)
        with self.assertRaises(ValueError):jukebox.Session(Path(self.temp.name))
        bad=dict(self.model,beats=[0,float('nan')]+self.model['beats'][2:])
        with self.assertRaises(ValueError):jukebox.validate_model(bad)
    def test_stop_rejects_further_rendering(self):
        player=jukebox.Session(self.base);player.close();player.close()
        with self.assertRaises(ValueError):player.chunk()
    @unittest.skipUnless((TOOLS/'ffmpeg.exe').is_file(),'Local FFmpeg required')
    def test_real_analysis_cache_and_cancel(self):
        source=Path(self.temp.name)/'chords.wav';song(source)
        first=jukebox.prepare(source,str(TOOLS));self.assertFalse(first['cached']);jukebox.validate_model(first)
        self.assertTrue(70<=first['bpm']<=190);self.assertGreater(len(first['beats']),8);self.assertGreater(first['links'],0)
        with patch('jukebox._run',side_effect=AssertionError('Cache must not decode again')):self.assertTrue(jukebox.prepare(source,str(TOOLS))['cached'])
        with self.assertRaises(jukebox.Cancelled):jukebox.prepare(source,str(TOOLS),lambda:True)
    @unittest.skipUnless((TOOLS/'ffmpeg.exe').is_file(),'Local FFmpeg required')
    def test_silence_has_no_fake_compatible_jumps(self):
        source=Path(self.temp.name)/'silence.wav';song(source,4,True)
        model=jukebox.prepare(source,str(TOOLS));self.assertEqual(model['links'],0)
    @unittest.skipUnless((TOOLS/'ffmpeg.exe').is_file(),'Local FFmpeg required')
    def test_cancelled_analysis_never_commits_a_cache(self):
        source=Path(self.temp.name)/'cancel.wav';song(source,10)
        import threading
        cancelled=threading.Event()
        def progress(value):
            if value>0:cancelled.set()
        with self.assertRaises(jukebox.Cancelled):jukebox.prepare(source,str(TOOLS),cancelled.is_set,progress)
        completed=list(jukebox.cache_root().glob('*/analysis.json'))
        self.assertEqual(completed,[self.base/'analysis.json'])

    def test_online_fetch_uses_recovery_and_single_audio_cache(self):
        record={'source_url':'https://www.deezer.com/track/1','title':'Song','artists':['Artist']}
        jar=object()
        def resolve(record,logger,*args,**kwargs):
            logger.youtube_cookiejar=jar
            return {'source_url':'https://www.youtube.com/watch?v=abcdefghijk'}
        def download(url,options,configure,saved):
            downloader=SimpleNamespace(add_post_processor=lambda *a,**k:None)
            configure(downloader)
            self.assertIs(downloader.cookiejar,jar)
            self.assertEqual(url,'https://www.youtube.com/watch?v=abcdefghijk');self.assertEqual(options['format'],'bestaudio');self.assertTrue(options['noplaylist']);self.assertEqual(options['playlistend'],1)
            path=Path(options['outtmpl'].replace('%(ext)s','wav'));song(path);saved.append(str(path));return 0
        with patch('matching.resolve_youtube',side_effect=resolve),patch('engine.download_with_recovery',side_effect=download),patch('jukebox.prepare',return_value={'cache':str(self.base)}):
            result=jukebox.fetch_audio({},record);self.assertEqual(result['title'],'Artist — Song');self.assertEqual(result['source'],str(self.base/'audio.wav'))
        self.assertFalse(list(jukebox.cache_root().glob('jukebox-download-*')))
    def test_android_backend_session_roundtrip(self):
        import importlib.util
        path=Path(__file__).resolve().parent.parent/'Celular/app/src/main/python/mobile_backend.py'
        spec=importlib.util.spec_from_file_location('jukebox_test_backend',path)
        backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
        callback=SimpleNamespace(onEvent=lambda _:None)
        def call(action,**config):return json.loads(backend.run('test',action,json.dumps(config),callback))
        self.assertNotIn('error',call('jukebox_open',session='player',cache=str(self.base)))
        try:
            part=call('jukebox_chunk',session='player',variation=0,volume=100)
            self.assertTrue(base64.b64decode(part['pcm']));self.assertEqual(part['index'],0)
        finally:call('jukebox_close',session='player')
        self.assertFalse(backend._jukebox_sessions)
        self.assertIn('error',call('jukebox_chunk',session='player'))

    def test_windows_output_bounds_and_releases_buffers(self):
        from jukebox_audio import PcmOutput
        class Function:
            def __init__(self,callback):self.callback=callback
            def __call__(self,*args):return self.callback(*args)
        counts={}
        def event(name,*args):
            counts[name]=counts.get(name,0)+1
            if name=='waveOutOpen':args[0]._obj.value=1
            if name=='waveOutWrite':args[1]._obj.flags|=1
            return 0
        api=SimpleNamespace(**{name:Function(lambda *args,n=name:event(n,*args)) for name in ('waveOutOpen','waveOutPrepareHeader','waveOutWrite','waveOutUnprepareHeader','waveOutPause','waveOutRestart','waveOutReset','waveOutClose')})
        with patch('jukebox_audio.c.WinDLL',return_value=api):
            output=PcmOutput();output.write(bytes(jukebox.RATE*4),lambda:False,lambda:False);self.assertLessEqual(len(output.buffers),2);output.close()
        self.assertEqual(counts['waveOutPrepareHeader'],counts['waveOutUnprepareHeader']);self.assertEqual(counts['waveOutClose'],1)

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class JukeboxUiTests(unittest.TestCase):
    def test_shared_tab_preserves_identity_and_effects_controls(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            from preferences import PreferenceStore
            PreferenceStore().save({'check_updates':False})
            from app import App
            app=App(show_welcome=False);app.withdraw()
            try:
                pane=app.effects_page.ensure_ready()
                self.assertEqual(app.pages.tab(app.effects_page,'text'),'Reprodução e efeitos')
                self.assertEqual(len(app.pages.tabs()),9);self.assertEqual(len(pane.modes.tabs()),2)
                pane.duration=42;self.assertEqual(pane.effects.duration,42)
                pane.jukebox.playing=True;self.assertTrue(pane.busy)
                pane.modes.select(pane.effects);pane.switched();self.assertFalse(pane.jukebox.playing)
                pane.effects.preview_active=True
                pane.modes.select(pane.jukebox);pane.switched();self.assertFalse(pane.effects.preview_active)
                pane.jukebox.draw()
                pane.jukebox.model={'cache':'old'};pane.jukebox.source='old.wav'
                pane.use_file(str(Path(folder)/'new.wav'));app.update()
                self.assertEqual(pane.effects.source.get(),str(Path(folder)/'new.wav'))
                self.assertIsNone(pane.jukebox.model)
            finally:app.destroy()
