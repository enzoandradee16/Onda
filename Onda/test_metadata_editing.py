import os
from pathlib import Path
import tempfile
import unittest
import uuid
import wave
import subprocess
from unittest.mock import patch

from audio_library import read_audio,write_audio,edit_copy
from metadata_editing import preview,select
from metadata_undo import undo,available


def audio(path,title):
    with wave.open(str(path),'wb') as stream:
        stream.setparams((1,2,8000,0,'NONE',''));stream.writeframes(b'\x01\x00'*800)
    write_audio(path,{'title':title,'artists':['Original'],'comment':'Preservado'})


class MetadataEditingTests(unittest.TestCase):
    def test_undo_when_android_denies_copying_extended_attributes(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'ONDA_ALIAS_CACHE_ROOT':folder}):
            source=Path(folder)/'audio.wav';audio(source,'Antes')
            edit_copy(dict(source=str(source),edit_metadata=True,overwrite_original=True,changes={'title':'Depois'},_metadata_transaction=str(uuid.uuid4())))
            with patch('shutil.copystat',side_effect=PermissionError('SELinux attribute')):
                undo()
            self.assertEqual(read_audio(source)['title'],'Antes')

    def test_copy_permission_error_does_not_accept_partial_audio(self):
        from metadata_undo import _copy_audio
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source';source.write_bytes(b'complete audio')
            target=Path(folder)/'target';target.write_bytes(b'partial')
            with patch('shutil.copy2',side_effect=PermissionError('read denied')):
                with self.assertRaises(PermissionError):_copy_audio(source,target)

    @unittest.skipUnless(os.environ.get('ONDA_METADATA_FFMPEG'),'FFmpeg required')
    def test_undo_real_formats_preserves_pcm_and_exact_artwork(self):
        from tag_transfer import snapshot
        from PIL import Image
        ffmpeg=os.environ['ONDA_METADATA_FFMPEG']
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'ONDA_ALIAS_CACHE_ROOT':folder}):
            root=Path(folder);cover=root/'cover.png';Image.new('RGB',(12,12),'blue').save(cover)
            for suffix in ('mp3','m4a','flac','ogg','opus'):
                with self.subTest(format=suffix):
                    source=root/('audio.'+suffix)
                    subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','sine=duration=0.2',str(source)],check=True)
                    write_audio(source,{'title':'Antes','artists':['Earth, Wind & Fire']},str(cover))
                    before=snapshot(source)
                    def pcm():return subprocess.check_output([ffmpeg,'-v','error','-i',str(source),'-map','0:a:0','-f','hash','-hash','sha256','-'])
                    original_pcm=pcm()
                    edit_copy(dict(source=str(source),edit_metadata=True,overwrite_original=True,changes={'title':'Depois'},_metadata_transaction=str(uuid.uuid4())))
                    undo()
                    self.assertEqual(read_audio(source)['title'],'Antes')
                    self.assertEqual(snapshot(source)['artwork'],before['artwork'])
                    self.assertEqual(pcm(),original_pcm)

    @unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'),'Desktop integration')
    def test_desktop_preview_save_and_keyboard_undo(self):
        from PySide6.QtCore import QObject,QMetaObject,Qt
        from PySide6.QtTest import QTest
        from qt_desktop_ui import create_application,close_application
        from preferences import PreferenceStore
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'LOCALAPPDATA':folder,'ONDA_ALIAS_CACHE_ROOT':folder}):
            source=Path(folder)/'song.wav';audio(source,'Antes')
            PreferenceStore().save({'check_updates':False,'clipboard_links':False})
            app,engine,bridge=create_application(complete=False)
            def wait(condition):
                import time
                deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    if condition():return
                    app.processEvents();time.sleep(.01)
                self.fail('Tempo limite no fluxo de edição.')
            try:
                workspace=engine.workspace;workspace.selectPage('metadata');workspace.accept_files('metadata',[str(source)])
                wait(lambda:bool(workspace.options['metadata']))
                workspace.options['metadata']['title']='Depois';workspace.options['overwrite_original']=True
                workspace.edit_audio();wait(lambda:workspace.choice.get('type')=='review_metadata_changes')
                self.assertEqual(read_audio(source)['title'],'Antes')
                event=workspace.choice
                workspace.replyChoice(event['identity'],{'selected':{str(i):[field['key'] for field in row['fields']] for i,row in enumerate(event['entries'])}})
                wait(lambda:'audio_edit' not in workspace.tasks)
                self.assertEqual(read_audio(source)['title'],'Depois')
                self.assertTrue(workspace.options['metadataUndoAvailable'])
                window=engine.rootObjects()[0]
                QMetaObject.invokeMethod(window.findChild(QObject,'messagePopup'),'close')
                window.requestActivate();QTest.qWait(40)
                QTest.keyClick(window,Qt.Key_Z,Qt.ControlModifier|Qt.AltModifier)
                wait(lambda:not available())
                self.assertEqual(read_audio(source)['title'],'Antes')
            finally:close_application(engine,bridge)

    def test_batch_preview_and_unchecked_fields_preserve_original_values(self):
        from batch_metadata import edit_batch
        with tempfile.TemporaryDirectory() as folder:
            paths=[Path(folder)/f'{i}.wav' for i in range(2)]
            for path in paths:audio(path,'old song')
            config=dict(sources=[{'source':str(p)} for p in paths],changes={'album':'Novo'},overwrite_original=True,
                        batch_actions={'case':'upper','find':'old','replace':'new','number_tracks':True,'start':3})
            report=preview(config)
            self.assertEqual(read_audio(paths[0])['title'],'old song')
            reply={'selected':{'0':['title','track_number'],'1':['album']}}
            chosen=select(config,report,reply)
            result=edit_batch(chosen)
            self.assertFalse(result['errors'])
            self.assertEqual(read_audio(paths[0])['title'],'NEW SONG')
            self.assertEqual(read_audio(paths[0])['track_number'],'3')
            self.assertEqual(read_audio(paths[0])['album'],'')
            self.assertEqual(read_audio(paths[1])['title'],'old song')
            self.assertEqual(read_audio(paths[1])['album'],'Novo')

    def test_undo_restores_exact_extra_tags_and_leaves_pcm_unchanged(self):
        from mutagen import File
        from mutagen.id3 import TXXX
        from tag_transfer import snapshot
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'ONDA_ALIAS_CACHE_ROOT':folder}):
            source=Path(folder)/'song.wav';audio(source,'Antes')
            other=Path(folder)/'other.wav';audio(other,'Depois')
            native=File(other);native.tags.add(TXXX(encoding=3,desc='new',text=['novo']));native.save()
            edit_copy(dict(source=str(source),edit_metadata=True,overwrite_original=True,changes={'title':'Depois'},tag_transfer=snapshot(other),_metadata_transaction=str(uuid.uuid4())))
            self.assertTrue(available());self.assertEqual(read_audio(source)['title'],'Depois')
            undo()
            self.assertFalse(available());self.assertEqual(read_audio(source)['title'],'Antes')
            self.assertNotIn('TXXX:new',File(source).tags)
            self.assertEqual(read_audio(source)['comment'],'Preservado')
            with wave.open(str(source)) as stream:self.assertEqual(stream.readframes(stream.getnframes()),b'\x01\x00'*800)

    def test_undo_rejects_later_external_changes(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'ONDA_ALIAS_CACHE_ROOT':folder}):
            source=Path(folder)/'song.wav';audio(source,'Antes')
            edit_copy(dict(source=str(source),edit_metadata=True,overwrite_original=True,changes={'title':'Depois'},_metadata_transaction=str(uuid.uuid4())))
            write_audio(source,{'title':'Alterado depois'})
            with self.assertRaisesRegex(ValueError,'mudou'):undo()
            self.assertEqual(read_audio(source)['title'],'Alterado depois')

    def test_undo_also_restores_overwritten_lrc_companion(self):
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'ONDA_ALIAS_CACHE_ROOT':folder}):
            source=Path(folder)/'song.wav';audio(source,'Antes')
            companion=source.with_suffix('.lrc');companion.write_text('[00:01.00]Antes',encoding='utf8')
            lyrics=Path(folder)/'new.lrc';lyrics.write_text('[00:01.00]Depois',encoding='utf8')
            edit_copy(dict(source=str(source),edit_metadata=True,overwrite_original=True,changes={'title':'Depois'},lyrics_path=str(lyrics),_metadata_transaction=str(uuid.uuid4())))
            self.assertIn('Depois',companion.read_text(encoding='utf8'))
            undo()
            self.assertEqual(companion.read_text(encoding='utf8'),'[00:01.00]Antes')

    def test_undo_does_not_add_a_filename_as_a_tag_to_originally_untagged_audio(self):
        from mutagen import File
        with tempfile.TemporaryDirectory() as folder,patch.dict(os.environ,{'ONDA_ALIAS_CACHE_ROOT':folder}):
            source=Path(folder)/'untagged.wav'
            with wave.open(str(source),'wb') as stream:
                stream.setparams((1,2,8000,0,'NONE',''));stream.writeframes(b'\x01\x00'*800)
            edit_copy(dict(source=str(source),edit_metadata=True,overwrite_original=True,changes={'title':'Depois'},_metadata_transaction=str(uuid.uuid4())))
            undo()
            self.assertFalse(File(source).tags)


if __name__=='__main__':unittest.main()
