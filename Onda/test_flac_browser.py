import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from flac_browser import search_url, validate_flac, import_flac


class BrowserProtocolTests(unittest.TestCase):
    def test_query_keeps_special_characters(self):
        from urllib.parse import parse_qs, urlsplit
        url=search_url({'artists':['Björk & X'], 'title':'A/B + C'})
        self.assertEqual(urlsplit(url).netloc,'flacdownloader.com')
        self.assertEqual(parse_qs(urlsplit(url).query)['q'],['Björk & X A/B + C'])

    def test_cancel_does_not_start_download(self):
        from engine import ask_flac_browser
        with patch('engine.emit') as emit:
            with self.assertRaisesRegex(ValueError,'cancelada'):
                ask_flac_browser({'title':'Test'},'https://flacdownloader.com/pt/',io.StringIO('{"cancel":true}'))
        self.assertEqual(emit.call_args.args[0],'choose_flac')

    def test_streaming_flac_never_resolves_youtube(self):
        from engine import run_worker
        record={'title':'Song', 'artists':['Artist'], 'platform':'Deezer', 'source_url':'https://www.deezer.com/track/1'}
        with patch('engine.binaries',return_value=True), patch('metadata.MetadataClient') as client, \
             patch('matching.resolve_youtube') as youtube, patch('lossless_source.download_flac',return_value=0) as importer:
            client.return_value.resolve.return_value=record
            with tempfile.TemporaryDirectory() as folder:
                result=run_worker({'url':record['source_url'],'mode':'flac','folder':folder})
            self.assertEqual(result,0)
            youtube.assert_not_called()
            self.assertEqual(importer.call_args.args[1],record)

    def test_reject_disguised_mp3(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'fake.flac'
            path.write_bytes(b'ID3'+b'0'*100)
            with self.assertRaisesRegex(ValueError,'não contém'):
                validate_flac(path)


@unittest.skipUnless(os.environ.get('ONDA_FFMPEG'), 'requires local FFmpeg')
class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.source=self.root/'original.flac'
        self.ffmpeg=str(Path(os.environ['ONDA_FFMPEG'])/'ffmpeg.exe')
        subprocess.run([self.ffmpeg,'-v','error','-f','lavfi','-i','sine=frequency=440:duration=1',str(self.source)],check=True)
        self.record={'title':'Song','artists':['Artist'],'album':'Album','platform':'Deezer','id':'1',
                     'source_url':'https://www.deezer.com/track/1','duration_ms':1000}
        self.config={'folder':str(self.root/'out'),'organization':'Pasta de destino','ffmpeg':os.environ['ONDA_FFMPEG']}
        self.events=[]

    def tearDown(self):
        self.temp.cleanup()

    def emit(self,kind,**values):
        self.events.append({'type':kind,**values})

    def run_import(self):
        return import_flac(self.config,self.record,lambda *_:str(self.source),self.emit,None)

    def test_import_preserves_original_tags_and_external_provenance(self):
        from mutagen.flac import FLAC,Picture
        import base64
        original=FLAC(self.source)
        picture=Picture();picture.mime='image/png';picture.type=3
        picture.data=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        original.add_picture(picture);original.save()
        before=self.source.read_bytes()
        self.assertEqual(self.run_import(),0)
        result=self.root/'out/Artist - Song.flac'
        audio=FLAC(result)
        self.assertEqual(audio['title'],['Song'])
        self.assertEqual(audio['album'],['Album'])
        self.assertEqual(audio.pictures[0].data,picture.data)
        metadata=json.loads(audio['onda_metadata'][0])
        self.assertEqual(metadata['provider'],'FLAC Downloader')
        self.assertNotIn('youtube_title',metadata)
        self.assertEqual(self.source.read_bytes(),before)
        self.assertTrue(Path(str(result)+'.metadata.json').exists())
        self.assertEqual(self.events[-1]['type'],'done')
        self.assertFalse((result.parent/'.onda-work').exists())

    def test_duplicate_skip_preserves_existing_file(self):
        self.run_import()
        target=self.root/'out/Artist - Song.flac'
        before=target.read_bytes()
        self.config['duplicate_policy']='skip'
        self.run_import()
        self.assertEqual(target.read_bytes(),before)
        self.assertTrue(self.events[-2]['skipped'])

    def test_duration_mismatch_does_not_publish(self):
        self.record['duration_ms']=180000
        with self.assertRaisesRegex(ValueError,'duração'):
            self.run_import()
        self.assertFalse((self.root/'out/Artist - Song.flac').exists())
        self.assertFalse(any(e['type']=='done' for e in self.events))

    def test_decode_failure_does_not_publish(self):
        with patch('flac_browser.subprocess.run',return_value=subprocess.CompletedProcess([],1)):
            with self.assertRaisesRegex(ValueError,'decodificar'):
                self.run_import()
        self.assertTrue(self.source.exists())
        self.assertFalse((self.root/'out/Artist - Song.flac').exists())


if __name__=='__main__':
    unittest.main()
