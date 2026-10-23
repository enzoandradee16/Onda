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
        model={'version':1,'phrase_version':jukebox.PHRASE_VERSION,'duration':8,'bpm':120,'beats':[i*.25 for i in range(33)],'neighbors':[[] for _ in range(32)],'links':1}
        model['neighbors'][4]=[20];(self.base/'analysis.json').write_text(json.dumps(model));self.model=model
    def tearDown(self):self.env.stop();self.temp.cleanup()
    def test_twenty_minute_analysis_is_accepted_but_longer_is_rejected(self):
        model=dict(self.model,duration=1200,beats=[i*.5 for i in range(2401)],neighbors=[[] for _ in range(2400)])
        jukebox.validate_model(model)
        model['beats'][-1]=1201
        with self.assertRaises(ValueError):jukebox.validate_model(model)

    def test_low_rhythm_confidence_uses_verified_phrase_links(self):
        mono=Path(self.temp.name)/'unaccented.wav'
        with wave.open(str(mono),'wb') as output:
            output.setparams((1,2,8000,0,'NONE',''));output.writeframes(array('h',[1000]*80000).tobytes())
        vector=[1.0]+[0.0]*11+[1.0]+[0.0]*7
        with patch('jukebox._features',return_value=(vector,.1)):
            model=jukebox.analyse_wave(mono)
        self.assertEqual(model['beat_confidence'],0)
        self.assertEqual(model['matching_mode'],'conservative_phrase')
        self.assertGreater(model['links'],0)
        self.assertIsNotNone(jukebox.loop_boundary(model['neighbors']))
        with patch('jukebox._features',return_value=(vector,0)):
            silent=jukebox.analyse_wave(mono)
        self.assertEqual(silent['links'],0)

    def test_normal_mode_preserves_all_samples(self):
        for variation,normal in [(0,True),(100,True)]:
            player=jukebox.Session(self.base,seed=1)
            try:
                parts=[player.chunk(variation,0,100,normal) for _ in range(32)]
                with wave.open(str(self.base/'audio.wav'),'rb') as original:self.assertEqual(b''.join(p['pcm'] for p in parts),original.readframes(original.getnframes()))
                self.assertEqual(player.index,0);self.assertEqual(player.jumps,0);self.assertAlmostEqual(sum(p['seconds'] for p in parts),8)
            finally:player.close()
    def test_phrase_comparison_checks_the_continuation_not_just_first_beat(self):
        a=[1.0]+[0.0]*11+[.1,.1,.1,.3,.3,.3,.05,.05]
        b=[0.0,1.0]+[0.0]*10+[.1,.1,.1,.3,.3,.3,.05,.05]
        rows=[a]*8+[a,b,b,b]
        self.assertIsNone(jukebox.phrase_similarity(rows,0,8))
        self.assertAlmostEqual(jukebox.phrase_similarity([a]*12,0,8),1.0)

    def test_energy_filter_rejects_calm_phrase_after_a_loud_first_beat(self):
        levels=[.3]*32
        levels[21:28]=[.04]*7
        neighbors=[[] for _ in levels];neighbors[12]=[4,20]
        filtered=jukebox.energy_matched_links(neighbors,levels)
        self.assertEqual(filtered[12],[4])
    def test_energy_filter_preserves_similar_energy_phrases(self):
        levels=[.3]*32;levels[20:28]=[.26]*8
        neighbors=[[] for _ in levels];neighbors[12]=[20]
        self.assertEqual(jukebox.energy_matched_links(neighbors,levels),neighbors)
    def test_session_does_not_force_energy_mismatched_jump(self):
        model=dict(self.model,energy_levels=[.3]*32)
        model['energy_levels'][20:28]=[.03]*8
        (self.base/'analysis.json').write_text(json.dumps(model))
        player=jukebox.Session(self.base)
        player.random=SimpleNamespace(random=lambda:0,choice=lambda rows:rows[0])
        try:
            player.seek(4);player.since_jump=32
            part=player.chunk(100,0,100)
            self.assertFalse(part['jumped']);self.assertEqual(part['next'],5)
        finally:player.close()
    def test_cached_analysis_gets_energy_refinement_without_decoding_again(self):
        import hashlib,shutil
        source=self.base/'audio.wav'
        digest=hashlib.sha256(str(jukebox.VERSION).encode()+source.read_bytes()).hexdigest()
        base=jukebox.cache_root()/digest;base.mkdir()
        shutil.copy2(source,base/'audio.wav')
        (base/'analysis.json').write_text(json.dumps(self.model))
        result=jukebox.prepare(source)
        self.assertTrue(result['cached'])
        self.assertEqual(len(result['energy_levels']),32)
        saved=json.loads((base/'analysis.json').read_text())
        self.assertEqual(saved['energy_levels'],result['energy_levels'])
        self.assertEqual(saved['links'],sum(map(len,saved['neighbors'])))
        self.assertEqual(len(saved['join_features']),32)
        with patch.object(jukebox,'_features',side_effect=AssertionError('cached features were recomputed')):
            self.assertTrue(jukebox.prepare(source)['cached'])

    def test_old_phrase_cache_is_reanalysed_from_pcm_once(self):
        import hashlib,shutil
        source=self.base/'audio.wav'
        digest=hashlib.sha256(str(jukebox.VERSION).encode()+source.read_bytes()).hexdigest()
        base=jukebox.cache_root()/digest;base.mkdir()
        shutil.copy2(source,base/'audio.wav')
        old=dict(self.model);old.pop('phrase_version')
        (base/'analysis.json').write_text(json.dumps(old))
        with patch('audio_tools.executable',return_value='ffmpeg'),patch.object(jukebox,'_run') as decode,patch.object(jukebox,'analyse_wave',return_value=self.model) as analyse:
            self.assertTrue(jukebox.prepare(source)['cached'])
            self.assertTrue(jukebox.prepare(source)['cached'])
            self.assertEqual(analyse.call_count,1)
            self.assertEqual(decode.call_count,1)
            self.assertEqual(decode.call_args.args[0][5],str(base/'audio.wav'))

    def test_loop_boundary_prefers_broad_cycle_over_late_short_repeat(self):
        rows=[[] for _ in range(40)];rows[28]=[2];rows[37]=[31]
        self.assertEqual(jukebox.loop_boundary(rows),28)
        rows=[[] for _ in range(40)];rows[20]=[8];rows[12]=[2];rows[37]=[31]
        self.assertEqual(jukebox.loop_boundary(rows),20)
        self.assertIsNone(jukebox.loop_boundary([[],[4],[],[],[]]))

    def test_branch_chance_grows_between_jumps_and_resets_after_jump(self):
        for variation in (0,45,100):
            values=[jukebox.branch_probability(variation,wait) for wait in (4,8,16,32,100)]
            self.assertEqual(values,sorted(values));self.assertLess(values[0],values[-1])
            self.assertLessEqual(values[-1],.5)
            self.assertEqual(jukebox.branch_probability(variation,0),values[0])

    def test_repeated_return_eventually_continues_through_later_sections(self):
        model=dict(self.model,neighbors=[[] for _ in range(32)])
        model['neighbors'][22]=[2];model['neighbors'][30]=[24]
        (self.base/'analysis.json').write_text(json.dumps(model))
        player=jukebox.Session(self.base);player.random=SimpleNamespace(random=lambda:1,choice=lambda rows:rows[0])
        try:
            parts=[player.chunk(100,0,100) for _ in range(150)]
            self.assertEqual(player.loop_end,22)
            self.assertTrue(any(part['index']==31 for part in parts))
            self.assertGreaterEqual(sum(part['jumped'] for part in parts),4)
            self.assertTrue(all(part['next'] in model['neighbors'][part['index']] for part in parts if part['jumped']))
        finally:player.close()

    def test_jump_prefers_matching_pcm_edge_volume_among_unvisited_matches(self):
        model=dict(self.model,neighbors=[[] for _ in range(32)])
        model['neighbors'][4]=[20,24];(self.base/'analysis.json').write_text(json.dumps(model))
        player=jukebox.Session(self.base);player.random=SimpleNamespace(random=lambda:0,choice=lambda rows:rows[0])
        try:
            player.boundary_levels=[[.1,.1] for _ in range(32)];player.boundary_levels[20]=[.5,.5]
            player.index=4;player.since_jump=4
            self.assertEqual(player.chunk(100,0,100)['next'],24)
        finally:player.close()

    def test_loud_optional_jump_waits_but_mandatory_return_is_not_blocked(self):
        model=dict(self.model,neighbors=[[] for _ in range(32)])
        model['neighbors'][4]=[20];model['neighbors'][27]=[8]
        (self.base/'analysis.json').write_text(json.dumps(model))
        player=jukebox.Session(self.base);player.random=SimpleNamespace(random=lambda:0,choice=lambda rows:rows[0])
        try:
            player.boundary_levels=[[.1,.1] for _ in range(32)]
            player.boundary_levels[20]=[.5,.5];player.index=4;player.since_jump=4
            self.assertFalse(player.chunk(100,0,100)['jumped'])
            player.boundary_levels[8]=[.5,.5];player.index=27;player.since_jump=0
            part=player.chunk(100,0,100);self.assertTrue(part['jumped']);self.assertEqual(part['next'],8)
        finally:player.close()

    def test_join_context_prefers_matching_phrase_and_reuses_cached_features(self):
        with wave.open(str(self.base/'audio.wav'),'rb') as sound:
            model=jukebox.with_join_features(dict(self.model,energy_levels=[.1]*32),sound)
            with patch.object(jukebox,'_features',side_effect=AssertionError('must reuse features')):
                self.assertIs(jukebox.with_join_features(model,sound),model)
        self.assertEqual(len(model['join_features']),32)
        features=[[1.]+[0.]*11+[1.]+[0.]*7 for _ in range(32)]
        model=dict(model,join_features=features)
        matched=jukebox.join_context(model,7,16)
        for k in range(14,20):features[k]=[0.,1.]+[0.]*10+[0.,1.]+[0.]*6
        self.assertGreater(jukebox.join_context(model,7,16),matched)

    def test_adaptive_join_respects_smoothing_and_does_not_lengthen_vocal_risk_mix(self):
        model=dict(self.model,energy_levels=[.1]*32)
        boundary=[[.1,.1] for _ in range(32)]
        self.assertEqual(jukebox.join_fade_seconds(model,4,20,boundary,0),0)
        plain=jukebox.join_fade_seconds(model,4,20,boundary,100)
        voice=[1.]+[0.]*11+[0.,0.,0.,1.,1.,1.,0.,0.]
        model['join_features']=[voice for _ in range(32)]
        risk=jukebox.join_fade_seconds(model,4,20,boundary,100)
        self.assertGreater(risk,0);self.assertLess(risk,plain)
        self.assertLessEqual(plain,.2)

    def test_jump_uses_only_graph_neighbors_and_honors_spacing(self):
        player=jukebox.Session(self.base);player.random=SimpleNamespace(random=lambda:0,choice=lambda rows:rows[0])
        try:
            for _ in range(4):self.assertFalse(player.chunk(100,100,100)['jumped'])
            part=player.chunk(100,100,100);self.assertTrue(part['jumped']);self.assertEqual(part['next'],20);self.assertEqual(part['jumps'],1)
            self.assertEqual(len(part['pcm']),(round(1.25*jukebox.RATE)-round(jukebox.RATE))*4)
            self.assertLessEqual(max(map(abs,array('h',part['pcm']))),32767)
        finally:player.close()
    def test_infinite_mode_returns_before_ending_even_without_random_jump(self):
        model=dict(self.model,neighbors=[[] for _ in range(32)])
        model['neighbors'][27]=[8,12]
        (self.base/'analysis.json').write_text(json.dumps(model))
        player=jukebox.Session(self.base);player.random=SimpleNamespace(random=lambda:1,choice=lambda rows:rows[0])
        try:
            parts=[player.chunk(45,35,100) for _ in range(120)]
            self.assertTrue(all(part['pcm'] for part in parts))
            self.assertGreater(sum(part['seconds'] for part in parts),self.model['duration']*3)
            self.assertTrue(any(part['index']==31 for part in parts))
            self.assertTrue(any(part['next']==8 and part['jumped'] for part in parts))
            self.assertTrue(any(part['next']==12 and part['jumped'] for part in parts))
            for part in parts:
                if part['jumped']:self.assertIn(part['next'],model['neighbors'][part['index']])
        finally:player.close()
    def test_most_faithful_keeps_safe_return_and_normal_mode_disables_it(self):
        model=dict(self.model,neighbors=[[] for _ in range(32)])
        model['neighbors'][4]=[20];model['neighbors'][27]=[8]
        (self.base/'analysis.json').write_text(json.dumps(model))
        player=jukebox.Session(self.base,seed=1);player.random=SimpleNamespace(random=lambda:1,choice=lambda rows:rows[0])
        try:
            parts=[player.chunk(0,0,100) for _ in range(80)]
            jumps=[part for part in parts if part['jumped']]
            self.assertGreaterEqual(len(jumps),2)
            self.assertTrue(all(part['index']==27 and part['next']==8 for part in jumps))
            self.assertTrue(any(part['index']==31 for part in parts))
        finally:player.close()
        for variation in (0,100):
            player=jukebox.Session(self.base,seed=1)
            try:
                parts=[player.chunk(variation,0,100,True) for _ in range(32)]
                self.assertEqual([part['index'] for part in parts],list(range(32)))
                self.assertFalse(any(part['jumped'] for part in parts))
                self.assertEqual(player.index,0)
            finally:player.close()

    def test_most_faithful_has_occasional_compatible_jumps(self):
        player=jukebox.Session(self.base)
        player.random=SimpleNamespace(random=lambda:0,choice=lambda rows:rows[0])
        try:
            parts=[player.chunk(0,0,100) for _ in range(5)]
            self.assertTrue(parts[-1]['jumped'])
            self.assertEqual(parts[-1]['next'],20)
            self.assertIn(parts[-1]['next'],self.model['neighbors'][4])
        finally:player.close()
    def test_most_faithful_bounds_wait_when_compatible_edge_is_available(self):
        player=jukebox.Session(self.base)
        player.random=SimpleNamespace(random=lambda:1,choice=lambda rows:rows[0])
        try:
            player.index=4;player.since_jump=32
            part=player.chunk(0,0,100)
            self.assertTrue(part['jumped']);self.assertEqual(part['next'],20)
        finally:player.close()

    def test_missing_backward_matches_repeat_safely_and_normal_mode_reaches_end(self):
        model=dict(self.model,neighbors=[[] for _ in range(32)])
        (self.base/'analysis.json').write_text(json.dumps(model))
        player=jukebox.Session(self.base)
        try:
            self.assertIsNone(player.loop_end)
            parts=[player.chunk(100,35,100) for _ in range(96)]
            self.assertEqual(sum(part['next']==0 for part in parts),3)
            self.assertFalse(any(part['jumped'] for part in parts))
        finally:player.close()

    def test_short_cycle_escapes_even_with_minimum_variation(self):
        model=dict(self.model,neighbors=[[] for _ in range(32)])
        model['neighbors'][9]=[2]
        (self.base/'analysis.json').write_text(json.dumps(model))
        for variation in (0,45,100):
            player=jukebox.Session(self.base,seed=1)
            player.random=SimpleNamespace(random=lambda:0,choice=lambda rows:rows[0])
            try:
                parts=[player.chunk(variation,0,100) for _ in range(55)]
                self.assertTrue(any(part['index']==31 for part in parts))
                self.assertLessEqual(sum(part['jumped'] for part in parts),2)
            finally:player.close()

    def test_reprise_finishes_phrase_before_another_optional_jump(self):
        model=dict(self.model,neighbors=[[] for _ in range(32)])
        model['neighbors'][12]=[4];model['neighbors'][8]=[2];model['neighbors'][29]=[2]
        (self.base/'analysis.json').write_text(json.dumps(model))
        player=jukebox.Session(self.base,seed=1)
        player.random=SimpleNamespace(random=lambda:0,choice=lambda rows:rows[0])
        try:
            player.index=12;player.since_jump=4
            self.assertEqual(player.chunk(100,0,100)['next'],4)
            parts=[player.chunk(100,0,100) for _ in range(17)]
            self.assertEqual([part['index'] for part in parts],list(range(4,21)))
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
        with patch('matching.resolve_youtube',side_effect=resolve),patch('engine.download_with_recovery',side_effect=download),patch('jukebox.prepare',side_effect=AssertionError('Effects must not analyze rhythm')),patch('shutil.copystat',side_effect=PermissionError(13,'SELinux denies security attributes')):
            result=jukebox.fetch_audio({},record,analyze=False)
            self.assertTrue(Path(result['source']).is_file());self.assertEqual(result['record'],record)
        self.assertFalse(list(jukebox.cache_root().glob('jukebox-download-*')))
    def test_android_backend_session_roundtrip(self):
        import importlib.util
        path=Path(__file__).resolve().parent.parent/'Android/app/src/main/python/mobile_backend.py'
        spec=importlib.util.spec_from_file_location('jukebox_test_backend',path)
        backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
        callback=SimpleNamespace(onEvent=lambda _:None)
        def call(action,**config):return json.loads(backend.run('test',action,json.dumps(config),callback))
        self.assertNotIn('error',call('jukebox_open',session='player',cache=str(self.base)))
        try:
            part=call('jukebox_chunk',session='player',variation=0,volume=100)
            self.assertTrue(base64.b64decode(part['pcm']));self.assertEqual(part['index'],0)
            filtered=call('jukebox_chunk',session='player',variation=0,volume=100,seek=0,equalizer={'enabled':True,'preamp':-12})
            before=array('h',base64.b64decode(part['pcm']))[-10000:]
            after=array('h',base64.b64decode(filtered['pcm']))[-10000:]
            ratio=math.sqrt(sum(x*x for x in after)/sum(x*x for x in before))
            self.assertAlmostEqual(ratio,10**(-12/20),delta=.002)
        finally:call('jukebox_close',session='player')
        self.assertFalse(backend._jukebox_sessions)
        self.assertIn('error',call('jukebox_chunk',session='player'))

    def test_windows_progress_uses_device_clock_and_handles_byte_units(self):
        from jukebox_audio import PcmOutput,WaveTime
        import ctypes
        class Function:
            def __init__(self,callback):self.callback=callback
            def __call__(self,*args):return self.callback(*args)
        position={'unit':2,'value':4410,'error':0}
        def opened(*args):args[0]._obj.value=1;return 0
        def clock(handle,ptr,size):
            self.assertEqual(size,ctypes.sizeof(WaveTime))
            ptr._obj.type=position['unit'];ptr._obj.data[0]=position['value'];return position['error']
        api=SimpleNamespace(waveOutOpen=Function(opened),waveOutGetPosition=Function(clock),**{
            name:Function(lambda *args:0) for name in ('waveOutPrepareHeader','waveOutWrite','waveOutUnprepareHeader','waveOutPause','waveOutRestart','waveOutReset','waveOutClose')})
        updates=[]
        with patch('jukebox_audio.c.WinDLL',return_value=api):
            output=PcmOutput(progress=updates.append)
            try:
                output.notify();self.assertEqual(updates,[4410])
                output.last_notify=0;output.notify();self.assertEqual(updates,[4410])
                position.update(unit=4,value=35280);output.last_notify=0;output.notify()
                self.assertEqual(updates,[4410,8820])
                position['error']=1;output.last_notify=0;output.notify()
                self.assertEqual(updates,[4410,8820])
            finally:output.close()

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
    def test_playback_reuses_graph_items_but_controls_refresh_connections(self):
        import tkinter as tk
        from jukebox_ui import JukeboxPane
        root=tk.Tk();root.withdraw()
        try:
            pane=JukeboxPane(root,SimpleNamespace(theme_manager=SimpleNamespace(colors={}),jukebox_equalizer=tk.StringVar(value="{}")),lambda *a:None)
            pane.model={'neighbors':[[(i+12)%64] for i in range(64)]}
            pane.draw();items=pane.canvas.find_all()
            for index in range(64):pane.current=index;pane.draw()
            self.assertEqual(items,pane.canvas.find_all())
            pane.variation.set(0);pane.update_params()
            self.assertTrue(pane.canvas.find_withtag('jump-link'))
            pane.toggle_normal();self.assertFalse(pane.canvas.find_withtag('jump-link'))
            pane.toggle_normal()
            pane.variation.set(100);pane.update_params()
            self.assertTrue(pane.canvas.find_withtag('jump-link'))
            pane.flow=[(0,1),(1,13)];pane.current=13;pane.draw()
            flow=pane.canvas.find_withtag('flow');self.assertEqual(len(flow),2)
            self.assertEqual(pane.canvas.itemcget(flow[-1],'arrow'),'last')
            self.assertFalse(any(pane.canvas.type(item)=='text' for item in pane.canvas.find_all()))
            pane.variation.set(0);pane.update_params()
            self.assertEqual(pane.flow,[(0,1),(1,13)])
            self.assertEqual(len(pane.canvas.find_withtag('flow')),2)
            pane.marker_position=13.5;pane.beat_phase=.5;pane.playing=True;pane.draw()
            x1,y1,x2,y2=pane.canvas.coords(pane._graph_marker)
            w,h=pane._graph_key[1:3];radius=min(w,h)*.39;angle=13.5/64*2*math.pi-math.pi/2
            self.assertAlmostEqual((x1+x2)/2,w/2+math.cos(angle)*radius)
            self.assertAlmostEqual((y1+y2)/2,h/2+math.sin(angle)*radius)
            self.assertAlmostEqual((x2-x1)/2,6.25)
            pane.shutdown()
        finally:root.destroy()

    def test_windows_media_commands_control_existing_jukebox(self):
        import tkinter as tk,queue
        from jukebox_ui import JukeboxPane
        root=tk.Tk();root.withdraw()
        try:
            pane=JukeboxPane(root,SimpleNamespace(theme_manager=SimpleNamespace(colors={}),jukebox_equalizer=tk.StringVar(value="{}")),lambda *a:None)
            media=SimpleNamespace(events=queue.SimpleQueue(),update=lambda *a:None,close=lambda:None)
            pane.media_controls=media;pane.playing=True
            media.events.put(1);pane.sync_media();self.assertTrue(pane.paused.is_set())
            media.events.put(0);pane.sync_media();self.assertFalse(pane.paused.is_set())
            media.events.put(2);pane.sync_media();self.assertFalse(pane.playing)
            pane.shutdown()
        finally:root.destroy()

    def test_one_close_stops_jukebox_and_exits_but_export_waits(self):
        from app import App
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            from preferences import PreferenceStore
            PreferenceStore().save({'check_updates':False,'clipboard_links':False})
            app=App(show_welcome=False);app.withdraw()
            try:
                pane=app.effects_page.ensure_ready();app.close_behavior.set('Encerrar')
                pane.effects.busy=True
                with patch.object(app,'destroy') as destroy:
                    app.close();destroy.assert_not_called()
                pane.effects.busy=False;pane.jukebox.playing=True
                with patch.object(app,'destroy') as destroy:
                    app.close();destroy.assert_called_once()
                self.assertFalse(pane.jukebox.playing)
            finally:app.destroy()

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
