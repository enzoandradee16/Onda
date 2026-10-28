import base64,hashlib,io,json,math,os,tempfile,unittest,wave
from array import array
from pathlib import Path
from unittest.mock import patch
from effects_export import export_config


class EffectsExportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'audio.wav'
        data=array('h')
        for i in range(44100*2):
            value=round(math.sin(i*2*math.pi*440/44100)*6000);data.extend((value,value))
        with wave.open(str(self.source),'wb') as out:out.setparams((2,2,44100,0,'NONE',''));out.writeframes(data.tobytes())
        self.record=dict(title='Midnight Pretenders',artists=['Tomoko Aran'],album='Fuyü-Kükan',release_date='1983-05-21',genre='City pop',track_number=3)
    def tearDown(self):self.temp.cleanup()
    def test_names_and_disabled_effects_use_the_actual_parameters(self):
        for speed,reverb,suffix in ((85,0,'Slowed'),(100,25,'Reverb'),(85,25,'Slowed + Reverb'),(115,0,'Sped Up'),(115,25,'Sped Up + Reverb'),(100,0,'')):
            config=export_config(self.source,self.record,speed=speed,reverb=reverb)
            self.assertEqual(config['export_name'],'Tomoko Aran - Midnight Pretenders'+(' - '+suffix if suffix else ''))
        disabled=export_config(self.source,self.record,speed=85,reverb=25,enabled=False)
        self.assertEqual(disabled['speed'],100);self.assertEqual(disabled['reverb'],0)
        self.assertEqual(disabled['export_name'],'Tomoko Aran - Midnight Pretenders')
    def test_real_exports_restore_metadata_artwork_and_effects_in_all_formats(self):
        from effects_worker import render
        from audio_library import read_audio,cover_preview
        from PIL import Image
        tools=Path(os.environ.get('ONDA_FFMPEG',''))
        if not (tools/'ffmpeg.exe').is_file():self.skipTest('FFmpeg required')
        image=Image.new('RGB',(32,32),'navy');buffer=io.BytesIO();image.save(buffer,'PNG')
        cover='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()
        original=hashlib.sha256(self.source.read_bytes()).hexdigest()
        for extension in ('mp3','m4a','flac','wav'):
            for speed,reverb,suffix in ((85,0,'Slowed'),(100,25,'Reverb'),(85,25,'Slowed + Reverb')):
                with self.subTest(format=extension,effect=suffix):
                    config=export_config(self.source,self.record,speed=speed,reverb=reverb,cover_data=cover)
                    output=self.root/(config['export_name']+'.'+extension)
                    config.update(output=str(output),ffmpeg=str(tools));events=[]
                    with patch('effects_worker.emit',side_effect=lambda kind,**values:events.append((kind,values))):code=render(config)
                    self.assertEqual(code,0,events)
                    tags=read_audio(output)
                    json.dumps(tags)
                    self.assertEqual(tags['title'],'Midnight Pretenders - '+suffix)
                    self.assertEqual(tags['artists'],['Tomoko Aran']);self.assertEqual(tags['album'],'Fuyü-Kükan')
                    self.assertEqual(str(tags['release_date']),'1983-05-21');self.assertEqual(tags['genre'],'City pop')
                    self.assertTrue(cover_preview(output))
                    self.assertGreater(tags['duration'],2/(speed/100)-.1)
                    if reverb:self.assertGreater(tags['duration'],2/(speed/100)+.5)
                    if extension=='wav' and not reverb:
                        with wave.open(str(output),'rb') as audio:
                            rate=audio.getframerate();samples=array('h',audio.readframes(audio.getnframes()))[::2]
                        segment=samples[rate//10:rate//2]
                        crossings=sum(a<=0<b for a,b in zip(segment,segment[1:]))
                        frequency=crossings/(len(segment)/rate)
                        self.assertAlmostEqual(frequency,440*.85,delta=4)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(),original)


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Qt interface')
class ExportControllerTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture
    setUpClass=classmethod(Fixture.setUpClass.__func__)
    setUp=Fixture.setUp;tearDown=Fixture.tearDown
    def test_shared_export_uses_metadata_and_snapshots_effects_before_dialog(self):
        self.ws.selectPage('jukebox')
        self.bridge.model=dict(source=str(self.root/'audio.wav'),media_title='Midnight Pretenders',media_artist='Tomoko Aran',album='Fuyü-Kükan')
        self.ws.setOption('effectsEnabled',True);self.ws.setOption('speed',85);self.ws.setOption('reverb',25)
        self.ws.settings['folder']=str(self.root/'downloads')
        self.ws.options['effectsSource']='legacy.wav'
        def choose(*args):
            self.assertEqual(Path(args[2]).name,'Tomoko Aran - Midnight Pretenders - Slowed + Reverb.mp3')
            self.assertEqual(Path(args[2]).parent,self.root/'downloads')
            self.ws.setOption('speed',120)
            return str(self.root/'export.mp3'),''
        with patch('PySide6.QtWidgets.QFileDialog.getSaveFileName',side_effect=choose),patch.object(self.ws,'launch_thread',side_effect=lambda callback:callback()),patch.object(self.ws,'process_worker') as worker:
            self.ws.dispatch('unified_effects_export',{})
        config=worker.call_args.args[1]
        self.assertEqual(config['speed'],85);self.assertEqual(config['reverb'],25)
        self.assertEqual(config['record']['title'],'Midnight Pretenders');self.assertEqual(config['record']['artists'],['Tomoko Aran'])
        self.assertEqual(self.ws.options['effectsSource'],'legacy.wav')
