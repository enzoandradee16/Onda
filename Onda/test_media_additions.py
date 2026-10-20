import ctypes as c
import json
import os
from pathlib import Path
import subprocess
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from synced_lyrics import parse_lrc,line_at,read_lrc
from video_converter import convert_batch,ConversionCancelled
from drop_input import dropped_files,dropped_links

class LyricsTests(unittest.TestCase):
    def test_timestamps_offsets_seeks_and_empty_lines(self):
        rows=parse_lrc('[ar:Artist]\n[offset:-500]\n[00:02.00][00:04.500]Chorus\n[00:03.1]\ninvalid')
        self.assertEqual(rows,[(1.5,'Chorus'),(2.6,''),(4.0,'Chorus')])
        for time,expected in [(0,''),(1.5,'Chorus'),(2.7,''),(5,'Chorus'),(2,'Chorus')]:
            self.assertEqual(line_at(rows,time),expected)
        self.assertEqual(parse_lrc('plain lyrics'),[])
        with self.assertRaises(ValueError):parse_lrc('x'*(1024*1024+1))

    def test_lrc_utf16_and_utf8_bom(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'letra.lrc'
            for encoding in ('utf-16','utf-8-sig','cp1252'):
                path.write_bytes('[00:01.20]Canção de teste'.encode(encoding))
                self.assertEqual(read_lrc(path),[(1.2,'Canção de teste')])

    def test_lrc_file_encoding_and_default_off(self):
        from advanced_options import DEFAULTS,clean_advanced,export_settings,import_settings
        from preferences import PreferenceStore
        payload=export_settings({'synced_lyrics':True},'windows')
        self.assertTrue(import_settings(payload,'windows')['synced_lyrics'])
        self.assertTrue(PreferenceStore.clean({'synced_lyrics':True})['synced_lyrics'])
        self.assertFalse(DEFAULTS['synced_lyrics'])
        self.assertEqual(clean_advanced({'synced_lyrics':True}),{'synced_lyrics':True})
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'song.lrc';path.write_bytes('[00:01]Canção'.encode('cp1252'))
            self.assertEqual(read_lrc(path),[(1,'Canção')])

class DropTests(unittest.TestCase):
    def test_only_supported_existing_files_and_urls(self):
        with tempfile.TemporaryDirectory() as root:
            audio=Path(root)/'song.mp3';audio.touch()
            unsafe=Path(root)/'program.exe';unsafe.touch()
            self.assertEqual(dropped_files([str(audio),str(audio),str(unsafe),root]),[str(audio.resolve())])
        links=dropped_links('https://www.youtube.com/watch?v=abcdefghijk\nhttps://www.youtube.com/watch?v=abcdefghijk\nhttps://example.com\nplain text')
        self.assertEqual(len(links),1)
        self.assertFalse(dropped_links('just text'))

class AudioBatchTests(unittest.TestCase):
    def test_rejects_bad_batch_and_honors_cancellation(self):
        for config in ({'sources':[],'output_folder':'.'},{'sources':['a']*1001,'video_format':'INVALID'}):
            with self.assertRaises(ValueError):convert_batch(config)
        with self.assertRaises(ConversionCancelled):convert_batch({'sources':['a'],'output_folder':'.'},cancelled=lambda:True)

    def test_real_conversion_tags_collision_failure_and_originals(self):
        from ffmpeg_runtime import existing_folder
        folder=existing_folder()
        if not folder:self.skipTest('FFmpeg not prepared')
        with tempfile.TemporaryDirectory() as root:
            base=Path(root);source=base/'tone.wav';bad=base/'bad.mp3';bad.write_text('not audio')
            subprocess.run([str(folder/'ffmpeg.exe'),'-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.5','-metadata','title=Original title',str(source)],check=True,creationflags=0x08000000)
            original=source.read_bytes();output=base/'out';output.mkdir();existing=output/'tone - convertido.mp3';existing.write_bytes(b'preserve')
            events=[]
            result=convert_batch({'sources':[str(source),str(bad)],'output_folder':str(output),'ffmpeg':str(folder),'video_format':'MP3','audio_bitrate':'128k'},lambda kind,**data:events.append((kind,data)))
            self.assertEqual(len(result['results']),1);self.assertEqual(len(result['failures']),1)
            self.assertEqual(source.read_bytes(),original);self.assertEqual(existing.read_bytes(),b'preserve')
            from mutagen import File
            audio=File(result['results'][0]['path'],easy=True)
            self.assertEqual(audio['title'],['Original title'])
            self.assertIn('(2)',result['results'][0]['path'])
            self.assertTrue(any(kind=='file' for kind,data in events))
            self.assertFalse(list(output.glob('.onda-convert-*')))

@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'),'Tk integration')
class DesktopMediaTests(unittest.TestCase):
    def test_native_drop_registration_delivery_and_converter_selection(self):
        from app import App
        from ctypes import wintypes as w
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,{'LOCALAPPDATA':root}):
            app=App(show_welcome=False);app.clipboard_watch.shutdown();app.update()
            try:
                self.assertTrue(app.drop_target.registered)
                target=app.drop_target;received=[];target.receive=received.append
                # IDataObject providing real HGLOBAL Unicode text to the OLE target.
                kernel=c.WinDLL('kernel32');kernel.GlobalAlloc.argtypes=[w.UINT,c.c_size_t];kernel.GlobalAlloc.restype=c.c_void_p
                text='https://www.youtube.com/watch?v=abcdefghijk'
                raw=(text+'\0').encode('utf-16-le');wanted=13
                class Medium(c.Structure):_fields_=[('type',w.DWORD),('handle',c.c_void_p),('owner',c.c_void_p)]
                def get_data(this,fmt,medium):
                    identity=c.cast(fmt,c.POINTER(w.WORD))[0]
                    if identity!=wanted:return -2147221404
                    handle=kernel.GlobalAlloc(0x42,len(raw));pointer=target.kernel.GlobalLock(handle);c.memmove(pointer,raw,len(raw));target.kernel.GlobalUnlock(handle)
                    value=c.cast(medium,c.POINTER(Medium)).contents;value.type=1;value.handle=handle;value.owner=None
                    return 0
                callback=c.WINFUNCTYPE(c.c_long,c.c_void_p,c.c_void_p,c.c_void_p)(get_data)
                table=(c.c_void_p*7)();table[3]=c.cast(callback,c.c_void_p)
                class Data(c.Structure):_fields_=[('table',c.POINTER(c.c_void_p))]
                data=Data(table)
                point=target.callbacks[6].argtypes[3]()
                effect=w.DWORD(1)
                self.assertEqual(target.callbacks[6](None,c.byref(data),0,point,c.byref(effect)),0)
                if target.timer:target.root.after_cancel(target.timer);target.timer=None
                target.poll();self.assertEqual(received,[{'text':text}]);self.assertEqual(effect.value,1)
                file=Path(root)/'dropped.wav';file.touch()
                import struct
                wanted=15;raw=struct.pack('<IiiII',20,0,0,0,1)+(str(file)+'\0\0').encode('utf-16-le')
                target.callbacks[6](None,c.byref(data),0,point,c.byref(effect))
                self.assertEqual(target.events.get_nowait(),{'files':[str(file)]})
                from drop_input import receive
                pane=app.converter_page.ensure_ready()
                self.assertEqual(pane.preview_button.winfo_manager(),'')
                receive(app,{'files':[str(file)]});app.update()
                window=next(widget for widget in app.winfo_children() if isinstance(widget,tk.Toplevel) and widget.title()=='Abrir arquivos no ONDA')
                from tkinter import ttk
                button=next(widget for widget in window.winfo_children()[0].winfo_children() if isinstance(widget,ttk.Button) and widget.cget('text')=='Abrir')
                button.invoke();app.update()
                self.assertEqual(app.converter_page.source.get(),str(file.resolve()))
                self.assertEqual(pane.preview_button.winfo_manager(),'pack')
                pane.set_sources([]);self.assertEqual(pane.preview_button.winfo_manager(),'')
                with patch('drop_input.dropped_links',return_value=[text]),patch('tkinter.messagebox.askyesno',return_value=False),patch.object(app,'add') as add:
                    receive(app,{'text':text});add.assert_not_called()
                pane=app.converter_page.ensure_ready()
                pane.set_sources(['first.wav','second.flac'])
                self.assertEqual(pane.format.get(),'MP3');self.assertEqual(len(pane.sources),2)
                self.assertFalse(pane.option_cells[1].winfo_manager())
                self.assertEqual(pane.option_cells[4].winfo_manager(),'grid')
                self.assertEqual(pane.choose_button.cget('text'),'Escolher arquivo')
                pane.set_sources(['clip.mp4']);pane.format.set('MP4')
                self.assertEqual(pane.option_cells[1].winfo_manager(),'grid')
                effects=app.effects_page.ensure_ready()
                effects.lyric_rows=parse_lrc('[00:01]Test');app.synced_lyrics.set(True);effects.set_position(2)
                self.assertEqual(effects.lyric_text.get(),'Test')
                app.synced_lyrics.set(False);effects.set_position(2);self.assertEqual(effects.lyric_text.get(),'')
            finally:app.destroy()


class VideoBatchTests(unittest.TestCase):
    def test_video_batch_and_incompatible_audio_are_isolated(self):
        from ffmpeg_runtime import existing_folder
        folder=existing_folder()
        if not folder:self.skipTest('FFmpeg not prepared')
        with tempfile.TemporaryDirectory() as root:
            base=Path(root);video=base/'clip.mp4';audio=base/'audio.wav'
            subprocess.run([str(folder/'ffmpeg.exe'),'-v','error','-f','lavfi','-i','color=size=64x64:duration=0.5','-c:v','libx264',str(video)],check=True,creationflags=0x08000000)
            subprocess.run([str(folder/'ffmpeg.exe'),'-v','error','-f','lavfi','-i','sine=duration=0.5',str(audio)],check=True,creationflags=0x08000000)
            before=video.read_bytes()
            result=convert_batch({'sources':[str(video),str(audio)],'output_folder':str(base/'out'),'ffmpeg':str(folder),'video_format':'MKV'})
            self.assertEqual(len(result['results']),1)
            self.assertEqual(len(result['failures']),1)
            self.assertEqual(Path(result['results'][0]['path']).suffix,'.mkv')
            self.assertEqual(result['results'][0]['width'],64)
            self.assertEqual(video.read_bytes(),before)
