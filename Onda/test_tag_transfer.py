import tempfile
import unittest
import wave
import os
import subprocess
from pathlib import Path

from audio_library import read_audio, write_audio, edit_copy
from tag_transfer import snapshot, encode, decode
from mutagen import File
from mutagen.id3 import APIC, TXXX, USLT


class FullTagTransferTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('ONDA_METADATA_FFMPEG'), 'FFmpeg required')
    def test_native_and_cross_format_custom_tags_and_cover(self):
        from mutagen.mp4 import MP4FreeForm
        from tag_transfer import apply
        with tempfile.TemporaryDirectory() as folder:
            paths=[]
            for suffix in ('mp3','m4a','flac','ogg','opus'):
                path=Path(folder)/('audio.'+suffix)
                subprocess.run([os.environ['ONDA_METADATA_FFMPEG'],'-v','error','-f','lavfi','-i','sine=duration=0.2',str(path)],check=True)
                write_audio(path,{'title':'Original','artists':['A','B']})
                native=File(path)
                if suffix=='mp3':native.tags.add(TXXX(encoding=3,desc='CUSTOM',text=['abc']))
                elif suffix=='m4a':native.tags['----:com.apple.iTunes:CUSTOM']=[MP4FreeForm(b'abc')]
                else:native.tags['CUSTOM']=['abc']
                native.save()
                payload=snapshot(path)
                remaining=apply(path,payload,payload['tags'])
                write_audio(path,remaining)
                self.assertEqual(snapshot(path)['portable']['CUSTOM' if suffix in ('mp3','m4a') else 'custom'],['abc'])
                paths.append(path)
            payload=snapshot(paths[0])
            for target in paths[1:]:
                remaining=apply(target,payload,payload['tags'])
                write_audio(target,remaining)
                self.assertEqual(read_audio(target)['title'],'Original')

    def test_custom_tags_multiple_covers_lyrics_and_draft_without_audio_change(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = [Path(folder) / name for name in ('source.wav', 'target.wav')]
            for path in (source, target):
                with wave.open(str(path), 'wb') as stream:
                    stream.setparams((1, 2, 8000, 0, 'NONE', ''))
                    stream.writeframes(b'\x01\x00' * 800)
            write_audio(source, {'title': 'Original', 'artists': ['A', 'B'], 'comment': 'Preservado'})
            write_audio(target, {'title': 'Destino'})
            native = File(source)
            native.tags.add(TXXX(encoding=3, desc='CUSTOM', text=['um', 'dois']))
            native.tags.add(USLT(encoding=3, lang='por', text='Letra completa'))
            for kind in (3, 4):
                native.tags.add(APIC(encoding=3, mime='image/jpeg', type=kind, desc=str(kind), data=b'cover' + bytes([kind])))
            native.save()
            payload = decode(encode(snapshot(source, {'title': 'Editado'})))
            before = source.read_bytes()
            edit_copy(dict(source=str(target), edit_metadata=True, overwrite_original=True, changes=payload['tags'], tag_transfer=payload))
            self.assertEqual(read_audio(target)['title'], 'Editado')
            tags = File(target).tags
            self.assertEqual(tags['TXXX:CUSTOM'].text, ['um', 'dois'])
            self.assertEqual(tags.getall('USLT')[0].text, 'Letra completa')
            self.assertEqual(len(tags.getall('APIC')), 2)
            self.assertEqual(read_audio(target)['comment'], 'Preservado')
            self.assertEqual(source.read_bytes(), before)
            with wave.open(str(target)) as stream:
                self.assertEqual(stream.readframes(stream.getnframes()), b'\x01\x00' * 800)
            # Unselected title must stay unchanged when only album is pasted.
            edit_copy(dict(source=str(target), edit_metadata=True, overwrite_original=True, changes={'album': 'Novo'}, tag_transfer=payload, tag_transfer_cover=False))
            self.assertEqual(read_audio(target)['title'], 'Editado')
            self.assertEqual(read_audio(target)['album'], 'Novo')


if __name__ == '__main__':
    unittest.main()
