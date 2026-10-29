"""Audio and sidecar names must be reserved together without overwriting data."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave

from audio_library import edit_copy
from file_output import publish


class CompanionOutputTests(unittest.TestCase):
    def test_edit_copy_preserves_an_orphan_lyric_and_embeds_new_lyrics(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'song.wav'
            lyrics = root / 'input.lrc'
            with wave.open(str(source), 'wb') as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8000)
                audio.writeframes(b'\0\0' * 8000)
            original = source.read_bytes()
            lyrics.write_text('[00:00.00]New lyrics', encoding='utf-8')
            old = root / 'song - Editada.lrc'
            old.write_text('User lyrics', encoding='utf-8')
            result = edit_copy({'source': str(source), 'lyrics_path': str(lyrics)})
            final = Path(result['path'])
            self.assertEqual(old.read_text(encoding='utf-8'), 'User lyrics')
            self.assertEqual(final.name, 'song - Editada (2).wav')
            self.assertEqual(
                final.with_suffix('.lrc').read_text(encoding='utf-8'),
                lyrics.read_text(encoding='utf-8'),
            )
            from mutagen import File

            self.assertIn('New lyrics', File(final).tags.getall('USLT')[0].text)
            self.assertEqual(source.read_bytes(), original)

    def test_concurrent_pairs_keep_their_own_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'out'

            def save(index):
                work = root / str(index)
                work.mkdir()
                source = work / 'song.wav'
                source.write_bytes(str(index).encode())
                lyric = work / 'song.lrc'
                lyric.write_bytes(str(index).encode())
                final, _ = publish(source, output, companions={'.lrc': lyric})
                return Path(final)

            with ThreadPoolExecutor(max_workers=4) as workers:
                paths = list(workers.map(save, range(8)))
            self.assertEqual(len(set(paths)), 8)
            for path in paths:
                self.assertEqual(
                    path.read_bytes(), path.with_suffix('.lrc').read_bytes()
                )

    def test_failed_companion_copy_removes_only_reserved_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'song.wav'
            source.write_bytes(b'audio')
            lyric = root / 'song.lrc'
            lyric.write_bytes(b'lyrics')
            output = root / 'out'
            output.mkdir()
            existing = output / 'song.lrc'
            existing.write_bytes(b'owned')
            import shutil

            original_copy = shutil.copyfileobj

            def copy(original, target):
                if str(original.name).endswith('.lrc'):
                    raise OSError('disk full')
                return original_copy(original, target)

            with (
                patch('file_output.shutil.copyfileobj', side_effect=copy),
                self.assertRaises(OSError),
            ):
                publish(source, output, companions={'.lrc': lyric})
            self.assertEqual(list(output.iterdir()), [existing])
            self.assertEqual(existing.read_bytes(), b'owned')
            self.assertEqual(source.read_bytes(), b'audio')


if __name__ == '__main__':
    unittest.main()
