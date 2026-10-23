import unittest,threading,importlib.util
from pathlib import Path
from unittest.mock import patch
from qt_operations_ui import perform

class EffectsMetadataTests(unittest.TestCase):
    def test_pc_queue_preserves_catalog_data_for_untagged_audio(self):
        record={'title':'One More Time','artists':['Daft Punk'],'album':'Discovery','cover_url':'https://example.com/cover.jpg'}
        with patch('audio_library.read_audio',return_value={'title':'audio','artists':[],'duration':403}),patch('audio_library.cover_preview',return_value=''):
            rows=perform('effects_queue_info',{'sources':['audio.webm'],'records':{'audio.webm':record}},threading.Event(),lambda *a,**k:None)
        self.assertEqual(rows[0]['record']['title'],'One More Time')
        self.assertEqual(rows[0]['record']['artists'],['Daft Punk'])
        self.assertEqual(rows[0]['record']['album'],'Discovery')
        self.assertEqual(rows[0]['record']['cover_url'],record['cover_url'])
        self.assertEqual(rows[0]['duration'],403)
    def test_android_keeps_catalog_cover_and_title(self):
        path=Path(__file__).resolve().parent.parent/'Android/app/src/main/python/mobile_backend.py'
        spec=importlib.util.spec_from_file_location('effects_metadata_backend',path)
        backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
        original=backend.perform
        record={'title':'One More Time','artists':['Daft Punk'],'album':'Discovery','cover_url':'https://example.com/cover.jpg'}
        with patch('audio_library.read_audio',return_value={'title':'audio','artists':[],'duration':403}),patch('audio_library.cover_preview',return_value=''),patch.object(backend,'perform',side_effect=lambda action,config: {'format':{'duration':'403'}} if action=='probe' else original(action,config)):
            result=backend.perform('effects_info',{'source':'audio.webm','record':record})
        self.assertEqual(result['record']['title'],record['title'])
        self.assertEqual(result['record']['artists'],record['artists'])
        self.assertEqual(result['record']['cover_url'],record['cover_url'])
