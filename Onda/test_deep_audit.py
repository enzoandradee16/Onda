import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

from audio_library import edit_copy, normalize_audio
from batch_metadata import edit_batch
from playlist_sync import scan_folder


class DeepAuditTests(unittest.TestCase):
    def test_android_batch_propagates_cancel_to_editor(self):
        from test_android_session import backend
        def edit(*args,**kwargs):
            backend.cancel('audit-batch')
            return {'path':'first.wav'}
        payload={'sources':[{'source':'first.wav'},{'source':'second.wav'}],'changes':{'album':'New'}}
        with patch('batch_metadata.edit_copy',side_effect=edit) as worker:
            result=json.loads(backend.run('audit-batch','audio_batch_edit',json.dumps(payload),Mock()))
        self.assertTrue(result['cancelled'])
        self.assertEqual(worker.call_count,1)
        self.assertNotIn('audit-batch',backend._jobs)

    def test_corrupt_audio_does_not_abort_collection_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            bad=Path(directory)/'broken.wav';bad.write_bytes(b'RIFF\x04\x00\x00\x00WAVE')
            other=Path(directory)/'video.mp4';other.write_bytes(b'media')
            inventory=scan_folder(directory)
            self.assertEqual(len(inventory),2)
            self.assertTrue(next(row for row in inventory if Path(row['path']).resolve()==bad.resolve())['uncertain'])

    def test_tagging_preserves_files_with_old_temporary_names(self):
        from tagging import apply_tags
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'song.mp3';source.write_bytes(b'audio')
            neighbors=[source.with_name('song.tagging.mp3'),source.with_name('song.mp3.metadata.tmp')]
            for path in neighbors:path.write_bytes(b'unrelated user file')
            apply_tags(source,{'title':'Song','artists':['Artist'],'source_url':'https://example.com/catalog'},{'source_url':'https://example.com/audio'})
            for path in neighbors:self.assertEqual(path.read_bytes(),b'unrelated user file')
            self.assertTrue(source.with_suffix('.mp3.metadata.json').is_file())

    def test_normalization_never_overwrites_neighboring_files(self):
        for preview in (False, True):
            with self.subTest(preview=preview), tempfile.TemporaryDirectory() as directory:
                source=Path(directory)/'song.wav';source.write_bytes(b'original')
                neighbor=source.with_name('song.volume-preview.wav' if preview else 'song.normalizing.wav')
                neighbor.write_bytes(b'unrelated user file')
                measured=dict(input_i='-20',input_tp='-3',input_lra='2',input_thresh='-30',target_offset='0')
                def run(command, **kwargs):
                    if command[-1]!='-':Path(command[-1]).write_bytes(b'normalized')
                    return Mock(returncode=0,stderr=json.dumps(measured).encode())
                with patch('audio_tools.executable',return_value='ffmpeg'),patch('audio_library.subprocess.run',side_effect=run),patch('effects_worker.preserve_tags'):
                    output=normalize_audio(source,{},preview=preview)
                self.assertEqual(neighbor.read_bytes(),b'unrelated user file')
                self.assertEqual(output.read_bytes(),b'normalized')
                self.assertEqual(source.read_bytes(),b'original' if preview else b'normalized')

    def test_cancelled_batch_stops_before_editing_next_file(self):
        cancelled=threading.Event()
        def edit(*args,**kwargs):
            cancelled.set()
            return {'path':'first.wav'}
        with patch('batch_metadata.edit_copy',side_effect=edit) as worker:
            with self.assertRaises(InterruptedError):
                edit_batch({'sources':[{'source':'first.wav'},{'source':'second.wav'}],'changes':{'album':'New'}},cancelled=cancelled.is_set)
            self.assertEqual(worker.call_count,1)

    def test_cancellation_before_publish_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'song.wav';source.write_bytes(b'original')
            cancelled=threading.Event()
            with patch('audio_library.read_audio'),patch('audio_library.write_audio',side_effect=lambda *args:cancelled.set()):
                with self.assertRaises(InterruptedError):
                    edit_copy({'source':str(source),'edit_metadata':True,'overwrite_original':True},cancelled=cancelled.is_set)
            self.assertEqual(source.read_bytes(),b'original')
            self.assertEqual(list(Path(directory).iterdir()),[source])

    def test_malformed_sidecar_does_not_abort_collection_scan(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'song.mp4';source.write_bytes(b'media')
            source.with_suffix('.mp4.metadata.json').write_text('[]',encoding='utf-8')
            inventory=scan_folder(directory)
            self.assertEqual(len(inventory),1)
            self.assertTrue(inventory[0]['uncertain'])
