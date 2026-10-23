import errno
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from file_output import publish
from library import LibraryStore
from preferences import PreferenceStore


class AuditRegressions(unittest.TestCase):
    def test_replace_across_volumes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'song.mp3'
            source.write_bytes(b'new')
            folder = root / 'output'
            folder.mkdir()
            target = folder / source.name
            target.write_bytes(b'old')
            replace = os.replace

            def cross_volume(origin, destination):
                if Path(origin) == source:
                    raise OSError(errno.EXDEV, 'Different volumes')
                return replace(origin, destination)

            with patch('file_output.os.replace', side_effect=cross_volume):
                self.assertEqual(publish(source, folder, 'replace'), (str(target), False))
            self.assertEqual(target.read_bytes(), b'new')
            self.assertFalse(source.exists())
            self.assertEqual(list(folder.iterdir()), [target])

    def test_failed_cross_volume_copy_preserves_both_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'song.mp3'
            source.write_bytes(b'new')
            folder = root / 'output'
            folder.mkdir()
            target = folder / source.name
            target.write_bytes(b'old')
            with patch('file_output.os.replace', side_effect=OSError(errno.EXDEV, 'Different volumes')):
                with patch('file_output.shutil.copyfileobj', side_effect=OSError('Disk full')):
                    with self.assertRaises(OSError):
                        publish(source, folder, 'replace')
            self.assertEqual(source.read_bytes(), b'new')
            self.assertEqual(target.read_bytes(), b'old')
            self.assertEqual(list(folder.iterdir()), [target])

    def test_history_search_handles_unicode_before_limiting(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LibraryStore(Path(directory) / 'library.db')
            store.add_history(Path(directory) / 'ÁGUA - CANÇÃO.mp3', 'mp3')
            with store.connect() as db:
                db.executemany('INSERT INTO history(name) VALUES (?)', [('Other',)] * 1001)
            self.assertEqual(len(store.history('água - canção')), 1)

    def test_nonfinite_preferences_do_not_discard_valid_settings(self):
        for value in (float('inf'), float('-inf'), float('nan')):
            with self.subTest(value=value):
                result = PreferenceStore.clean(dict(sidebar_width=value, jukebox_transition_seconds=value, language='en'))
                self.assertEqual(result['language'], 'en')
                self.assertNotIn('sidebar_width', result)
                self.assertNotIn('jukebox_transition_seconds', result)
