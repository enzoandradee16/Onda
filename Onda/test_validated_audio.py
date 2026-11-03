import tempfile
import unittest
from pathlib import Path
import sqlite3
from contextlib import closing

from validated_audio import ValidatedAudioStore, reference_key


class ReferencesTest(unittest.TestCase):
    def test_clearing_cache_keeps_active_stream_and_validated_reference(self):
        from cache_cleanup import clear_cache

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            audio = root / 'jukebox' / 'stream-files'
            audio.mkdir(parents=True)
            playing = audio / ('a' * 64 + '.mka')
            disposable = audio / ('b' * 64 + '.mka')
            playing.write_bytes(b'playing')
            disposable.write_bytes(b'disposable')
            store = ValidatedAudioStore(root / 'validated-audio.sqlite')
            record = dict(title='Song', artists=['Artist'])
            store.set(record, dict(id='abcdefghijk'))
            clear_cache(root, protected=[playing])
            self.assertTrue(playing.is_file())
            self.assertFalse(disposable.exists())
            self.assertEqual(store.get(record)['id'], 'abcdefghijk')

    def test_malformed_persisted_reference_is_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            store = ValidatedAudioStore(Path(folder) / 'references.sqlite')
            record = dict(title='Song', artists=['Artist'])
            store.get(record)
            for payload in ('[]', 'null', '{', '{"id":12}', '{"id":"invalid"}'):
                with closing(sqlite3.connect(store.path)) as db:
                    with db:
                        db.execute(
                            'INSERT OR REPLACE INTO audio VALUES (?,?,0)',
                            (reference_key(record), payload),
                        )
                self.assertIsNone(store.get(record))

    def test_persistent_reference_can_be_invalidated_without_audio(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'references.sqlite'
            record = dict(title='Song', artists=['Artist'], duration_ms=120000)
            selected = dict(id='abcdefghijk', source_url='https://youtu.be/abcdefghijk')
            store = ValidatedAudioStore(path)
            self.assertIsNone(store.get(record))
            store.set(record, selected)
            self.assertEqual(
                ValidatedAudioStore(path).get(record),
                dict(
                    selected, source_url='https://www.youtube.com/watch?v=abcdefghijk'
                ),
            )
            self.assertIsNone(store.get(dict(record, duration_ms=130000)))
            self.assertIsNone(store.get(dict(record, explicit=False)))
            self.assertIsNone(store.get(dict(record, version='Instrumental')))
            self.assertIsNone(store.get(dict(record, album='Other release')))
            store.forget(record)
            self.assertIsNone(store.get(record))
