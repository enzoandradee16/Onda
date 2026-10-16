from datetime import datetime
import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import Mock,patch

from advanced_options import export_settings,import_settings,release_update,schedule_allowed,version_key,clean_advanced
from audio_library import edit_copy,read_audio,normalize_audio

class AdvancedOptionsTests(unittest.TestCase):
    def test_schedule_handles_midnight_boundaries_and_invalid_input(self):
        options={'schedule_enabled':True,'schedule_start':'22:00','schedule_stop':'07:00'}
        for hour,minute,allowed in ((21,59,False),(22,0,True),(0,0,True),(6,59,True),(7,0,False)):
            self.assertEqual(schedule_allowed(options,datetime(2026,10,12,hour,minute)),allowed)
        self.assertFalse(schedule_allowed(dict(options,schedule_start='garbage')))
        self.assertFalse(schedule_allowed(dict(options,schedule_stop='22:00')))
    def test_cross_platform_transfer_excludes_all_secrets_and_paths(self):
        payload=export_settings({'mode':'Áudio · MP3 (320 kbps)','height':'1080p','fps':'Original','theme_mode':'Claro','theme_accent':'Verde-Água','concurrent_downloads':'3','spotify_client_secret':'secret','cookies_file':'private.txt','folder':'private','output_uri':'private'},'windows')
        self.assertNotIn('secret',json.dumps(payload));self.assertNotIn('private',json.dumps(payload))
        android=import_settings(payload,'android');self.assertEqual(android['mode'],'mp3');self.assertEqual(android['theme'],'Claro');self.assertEqual(android['height'],1080)
        pc=import_settings(export_settings(android,'android'),'windows')
        self.assertEqual(pc['mode'],'Áudio · MP3 (320 kbps)');self.assertEqual(pc['concurrent_downloads'],'3')
        self.assertEqual(clean_advanced({'concurrent_downloads':'400','normalize_volume':'yes','schedule_start':'28:20'}),{})
    def test_updates_select_platform_and_compare_pre_releases(self):
        releases=[{'tag_name':'v1.0.0-beta.1','assets':[{'name':'Onda-1.0.0-beta.1-Setup-Windows-x64.exe','browser_download_url':'https://github.com/enzoandradee16/Onda/releases/download/v1/setup.exe'}]},
                  {'tag_name':'android-1.0.0-alpha.2','assets':[{'name':'ONDA-Android-1.0.0-alpha.2.apk','browser_download_url':'https://github.com/enzoandradee16/Onda/releases/download/v2/app.apk'}]}]
        self.assertFalse(release_update('windows','1.0.0-beta.1',releases)['available'])
        self.assertTrue(release_update('android','1.0.0-alpha.1',releases)['available'])
        self.assertFalse(release_update('android','1.0.0',releases)['available'])
        self.assertLess(version_key('1.0.0-beta.2'),version_key('1.0.0'))
        releases[1]['assets'][0]['browser_download_url']='https://untrusted.example/file.apk'
        self.assertFalse(release_update('android','1.0.0-alpha.1',releases)['available'])

@unittest.skipUnless(os.environ.get('ONDA_FFMPEG'),'FFmpeg integration')
class AudioLibraryTests(unittest.TestCase):
    def test_edit_can_replace_original_without_changing_name_or_leaving_a_copy(self):
        from audio_tools import executable
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'Artista - Música.mp3'
            subprocess.run([executable('ffmpeg'),'-v','error','-y','-f','lavfi','-i','sine=duration=1','-c:a','libmp3lame',str(source)],check=True,capture_output=True)
            result=edit_copy({'source':str(source),'overwrite_original':True,'edit_metadata':True,'changes':{'title':'Título corrigido','artists':['Artista']}})
            self.assertEqual(Path(result['path']),source.resolve())
            self.assertTrue(result['overwritten'])
            self.assertEqual(read_audio(source)['title'],'Título corrigido')
            self.assertEqual(list(Path(folder).iterdir()),[source])

    def test_failed_edit_or_publication_preserves_original(self):
        from audio_tools import executable
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'Original.mp3'
            subprocess.run([executable('ffmpeg'),'-v','error','-y','-f','lavfi','-i','sine=duration=1','-c:a','libmp3lame',str(source)],check=True,capture_output=True)
            original=source.read_bytes()
            config={'source':str(source),'overwrite_original':True,'edit_metadata':True,'changes':{'title':'Novo'}}
            with patch('audio_library.write_audio',side_effect=ValueError('edição falhou')):
                with self.assertRaises(ValueError):edit_copy(config)
            self.assertEqual(source.read_bytes(),original)
            with patch('audio_library.os.replace',side_effect=PermissionError('arquivo em uso')):
                with self.assertRaises(PermissionError):edit_copy(config)
            self.assertEqual(source.read_bytes(),original)
            self.assertEqual(list(Path(folder).iterdir()),[source])

    def test_replace_does_not_overwrite_a_concurrent_change(self):
        from audio_tools import executable
        from audio_library import write_audio
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'Original.mp3'
            subprocess.run([executable('ffmpeg'),'-v','error','-y','-f','lavfi','-i','sine=duration=1','-c:a','libmp3lame',str(source)],check=True,capture_output=True)
            external=source.read_bytes()+b'external-change'
            def modify(target,*args,**kwargs):
                write_audio(target,*args,**kwargs)
                source.write_bytes(external)
            with patch('audio_library.write_audio',side_effect=modify):
                with self.assertRaisesRegex(ValueError,'mudou durante'):
                    edit_copy({'source':str(source),'overwrite_original':True,'edit_metadata':True,'changes':{'title':'Novo'}})
            self.assertEqual(source.read_bytes(),external)

    def test_normalization_preserves_tags_cover_and_supports_editor_and_lrc(self):
        from PIL import Image
        import io
        from audio_tools import executable
        from mutagen import File
        from tagging import apply_tags
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            art=io.BytesIO();Image.new('RGB',(40,30),'blue').save(art,format='JPEG')
            for suffix,codec in (('mp3','libmp3lame'),('m4a','aac'),('flac','flac'),('wav','pcm_s16le'),('ogg','libvorbis'),('opus','libopus')):
                source=root/('Original.'+suffix)
                subprocess.run([executable('ffmpeg'),'-v','error','-y','-f','lavfi','-i','sine=frequency=440:duration=2','-af','volume=0.1','-c:a',codec,str(source)],check=True,capture_output=True)
                if suffix in ('wav','ogg','opus'):
                    from audio_library import write_audio
                    cover_file=root/'capa.jpg';cover_file.write_bytes(art.getvalue())
                    write_audio(source,{'title':'Música','artists':['Artista'],'album':'Álbum'},str(cover_file))
                else:apply_tags(source,{'title':'Música','artists':['Artista'],'album':'Álbum','source_url':'https://example.com/music'},{'source_url':'https://example.com/audio'},(art.getvalue(),'image/jpeg'))
                from audio_library import cover_preview
                import base64
                preview=cover_preview(source)
                self.assertTrue(preview,suffix)
                with Image.open(io.BytesIO(base64.b64decode(preview))) as thumbnail:
                    self.assertLessEqual(max(thumbnail.size),240)
                original=source.read_bytes()
                preview=normalize_audio(source,{'ffmpeg':os.environ['ONDA_FFMPEG']},preview=True)
                self.assertTrue(preview.is_file());self.assertEqual(read_audio(preview)['title'],'Música')
                lyric=root/'letra.lrc';lyric.write_text('[00:01.00]Letra de teste\n',encoding='utf-8')
                result=edit_copy({'source':str(source),'folder':folder,'ffmpeg':os.environ['ONDA_FFMPEG'],'normalize_volume':True,'edit_metadata':True,'changes':{'title':'Novo título','artists':['Outro artista']},'lyrics_path':str(lyric)})
                target=Path(result['path']);record=read_audio(target)
                self.assertEqual(record['title'],'Novo título');self.assertEqual(record['album'],'Álbum');self.assertEqual(record['artists'],['Outro artista'])
                self.assertEqual(source.read_bytes(),original);self.assertTrue(target.with_suffix('.lrc').is_file())
                native=File(target)
                if suffix in ('mp3','wav'):self.assertEqual(native.tags.getall('APIC')[0].data,art.getvalue());self.assertIn('Letra de teste',native.tags.getall('USLT')[0].text)
                elif suffix=='m4a':self.assertEqual(bytes(native.tags['covr'][0]),art.getvalue());self.assertIn('Letra de teste',native.tags['\xa9lyr'][0])
                elif suffix=='flac':self.assertEqual(native.pictures[0].data,art.getvalue());self.assertIn('Letra de teste',native.tags['lyrics'][0])
                else:
                    import base64
                    from mutagen.flac import Picture
                    self.assertEqual(Picture(base64.b64decode(native.tags['metadata_block_picture'][0])).data,art.getvalue())
                    self.assertIn('Letra de teste',native.tags['lyrics'][0])
                measured=subprocess.run([executable('ffmpeg'),'-v','info','-i',str(target),'-af','loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,check=True)
                import re
                levels=json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}',measured.stderr.decode(errors='replace'),re.S)[-1])
                self.assertAlmostEqual(float(levels['input_i']),-16,delta=1)
                self.assertLessEqual(float(levels['input_tp']),-1.2)
                probe=json.loads(subprocess.check_output([executable('ffprobe'),'-v','error','-show_entries','format=duration','-of','json',str(target)]))
                self.assertAlmostEqual(float(probe['format']['duration']),2,delta=.2)

class ResumeTransferTests(unittest.TestCase):
    def test_http_range_resumes_from_saved_partial(self):
        from social_media import save_media,session_for
        import hashlib
        data=b'\x89PNG\r\n\x1a\n'+b'fixture'*1000
        requests=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                header=self.headers.get('Range');requests.append(header)
                offset=int(header.split('=')[1].split('-')[0]) if header else 0
                self.send_response(206 if offset else 200);self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(data)-offset))
                if offset:self.send_header('Content-Range',f'bytes {offset}-{len(data)-1}/{len(data)}')
                self.end_headers();self.wfile.write(data[offset:])
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with tempfile.TemporaryDirectory() as folder:
                config={'url':'https://www.instagram.com/p/test/','mode':'photos','folder':folder}
                identity=hashlib.sha256(json.dumps({key:config.get(key) for key in ('url','mode','audio_quality','height','fps','work_id','_identity')},sort_keys=True).encode()).hexdigest()[:20]
                staging=Path(folder)/'.onda-work'/identity;staging.mkdir(parents=True)
                partial=staging/'Autor - Foto - 01.png.part';partial.write_bytes(data[:1000])
                with session_for() as session:target=save_media(session,f'http://127.0.0.1:{server.server_port}/image.png',{'extension':'png','user':'Autor','title':'Foto'},config,Mock(),Mock(),1)
                self.assertEqual(Path(target).read_bytes(),data);self.assertEqual(requests,['bytes=1000-'])
        finally:server.shutdown();server.server_close();thread.join()

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class AdvancedDesktopTests(unittest.TestCase):
    def test_parallel_queue_runs_two_workers_and_serializes_choices(self):
        from app import App
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False);app.withdraw();app.folder.set(folder);app.concurrent_downloads.set('2')
            try:
                with patch.object(app,'supervise'),patch('app.binaries',return_value=True):
                    app.add(['https://example.com/one.mp3','https://example.com/two.mp3','https://example.com/three.mp3'])
                    ids=list(app.tree.get_children());app.start()
                    self.assertEqual(len(app.parallel.workers),2)
                    self.assertTrue(app.parallel.admit(ids[0],{'type':'choose_media'}))
                    self.assertFalse(app.parallel.admit(ids[1],{'type':'choose_media'}))
                    app.parallel.finish(ids[0],{'success':True,'cancelled':False})
                    self.assertEqual(len(app.parallel.workers),2);self.assertIn(ids[2],app.parallel.workers)
                    app.parallel.stop();app.parallel.workers.clear();app.active=None;app.set_state(ids[2],"Na fila")
                from advanced_ui import move_queue
                app.tree.selection_set(ids[2]);move_queue(app,0)
                self.assertEqual(app.library.load_queue()[0]['url'],'https://example.com/three.mp3')
            finally:app.destroy()


    @unittest.skipUnless(os.environ.get('ONDA_FFMPEG'),'FFmpeg integration')
    def test_two_real_desktop_workers_complete_three_downloads(self):
        import time
        from app import App
        from audio_tools import executable
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            root=Path(folder)
            subprocess.run([executable('ffmpeg'),'-v','error','-y','-f','lavfi','-i','sine=frequency=440:duration=2',str(root/'one.wav')],check=True,capture_output=True)
            import shutil
            for name in ('two','three'):shutil.copy2(root/'one.wav',root/(name+'.wav'))
            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=folder))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            app=App(show_welcome=False);app.withdraw();app.folder.set(str(root/'out'));app.ffmpeg.set(os.environ['ONDA_FFMPEG']);app.concurrent_downloads.set('2');app.mode.set('Áudio · MP3 (320 kbps)');app.normalize_volume.set(True)
            try:
                app.add([f'http://127.0.0.1:{server.server_port}/{name}.wav' for name in ('one','two','three')]);app.start()
                simultaneous=False;deadline=time.monotonic()+60
                while time.monotonic()<deadline and (app.parallel.workers or app.running):
                    app.update();simultaneous |= len(app.parallel.processes)>=2;time.sleep(.03)
                self.assertTrue(simultaneous)
                self.assertEqual([j['state'] for j in app.jobs.values()],['Concluído']*3)
                self.assertEqual(len(app.library.history()),3)
            finally:
                app.cancel();app.destroy();server.shutdown();server.server_close();thread.join()

    def test_two_worker_dialogs_are_displayed_one_at_a_time(self):
        import io
        from app import App
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder}):
            app=App(show_welcome=False);app.withdraw();app.folder.set(folder)
            try:
                app.add(['https://example.com/one.mp3','https://example.com/two.mp3']);ids=list(app.jobs)
                app.parallel.workers=set(ids)
                for key in ids:app.parallel.processes[key]=Mock(poll=Mock(return_value=None),stdin=io.StringIO())
                app.after_cancel(app._poll_after)
                for key in ids:app.events.put((key,{'type':'choose_duplicate','path':'fixture.mp3'}))
                app.poll_events()
                first=app.choice_window;self.assertEqual(app.parallel.choice_item,ids[0]);self.assertEqual(len(app.parallel.waiting),1)
                app.send_reply(ids[0],{'choice':'keep'})
                app.after_cancel(app._poll_after);app.poll_events()
                self.assertIsNot(app.choice_window,first);self.assertEqual(app.parallel.choice_item,ids[1])
                app.send_reply(ids[1],{'choice':'keep'})
            finally:app.parallel.workers.clear();app.active=None;app.destroy()

if __name__=='__main__':unittest.main()
