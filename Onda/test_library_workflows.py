import hashlib
from pathlib import Path
import tempfile
import unittest
import wave
from unittest.mock import patch

from duplicate_links import source_key, duplicate_job
from file_output import destination, publish, ORGANIZATIONS
from output_rules import FILENAME_TEMPLATES, output_filename, preview_path
from batch_metadata import edit_batch
from audio_library import read_audio, write_audio
from library import LibraryStore


class DuplicateTests(unittest.TestCase):
    def test_spotify_sharing_and_locale(self):
        self.assertEqual(
            source_key('https://open.spotify.com/intl-pt/track/ABC?si=123'),
            source_key('spotify:track:ABC'),
        )

    def test_youtube_variants(self):
        urls = [
            'https://youtu.be/abc?si=xyz',
            'https://www.youtube.com/watch?v=abc&utm_source=share',
            'https://youtube.com/shorts/abc',
            'https://music.youtube.com/watch?v=abc',
        ]
        self.assertEqual(len({source_key(url) for url in urls}), 1)

    def test_deezer_locale(self):
        self.assertEqual(
            source_key('https://www.deezer.com/br/track/123'),
            source_key('https://deezer.com/track/123?utm_source=test'),
        )

    def test_format_and_versions_are_independent(self):
        one = {'url': 'https://youtu.be/abc', 'mode': 'mp3'}
        self.assertTrue(
            duplicate_job(one, dict(one, url='https://youtube.com/watch?v=abc'))
        )
        self.assertFalse(duplicate_job(one, dict(one, mode='flac')))
        self.assertFalse(
            duplicate_job(one, dict(one, selected_catalog_url='spotify:track:OTHER'))
        )
        self.assertFalse(duplicate_job(one, dict(one, _operation='effects_export')))

    def test_generic_parameters_are_preserved(self):
        self.assertNotEqual(
            source_key('https://example.com/audio?id=1'),
            source_key('https://example.com/audio?id=2'),
        )

    def test_unknown_provider_resources_are_not_collapsed(self):
        base = 'https://example.com/audio'
        for other in (
            'http://example.com/audio',
            'https://www.example.com/audio',
            'https://example.com/audio/',
            'https://example.com:8443/audio',
            'https://user@example.com/audio',
        ):
            self.assertNotEqual(source_key(base), source_key(other), other)

    def test_playlist_identity_requires_youtube_host(self):
        first = {
            'url': 'https://example.com/one?list=abc',
            'playlist': True,
            'mode': 'mp3',
        }
        self.assertFalse(
            duplicate_job(first, dict(first, url='https://example.com/two?list=abc'))
        )
        self.assertTrue(
            duplicate_job(
                dict(first, url='https://youtube.com/watch?v=one&list=abc'),
                dict(first, url='https://youtube.com/watch?v=two&list=abc'),
            )
        )

    def test_quality_and_image_sizes_are_independent(self):
        for field, value in (
            ('audio_quality', '192'),
            ('height', 720),
            ('fps', 60),
            ('image_options', {'width': 300}),
        ):
            first = {'url': 'https://example.com/audio', 'mode': 'mp3'}
            self.assertFalse(duplicate_job(first, dict(first, **{field: value})))

    def test_history_requires_existing_file_and_supports_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / 'track.mp3'
            file.write_bytes(b'test')
            store = LibraryStore(root / 'history.db')
            store.add_history(file, 'MP3', 'https://youtu.be/abc?si=test')
            self.assertEqual(
                LibraryStore(root / 'history.db').find_duplicate(
                    'https://youtube.com/watch?v=abc', 'mp3'
                ),
                str(file.resolve()),
            )
            self.assertIsNone(store.find_duplicate('https://youtu.be/abc', 'flac'))
            file.unlink()
            self.assertIsNone(store.find_duplicate('https://youtu.be/abc', 'mp3'))

    def test_queue_preserves_new_options_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LibraryStore(Path(directory) / 'history.db')
            store.save_queue(
                [
                    {
                        'url': 'https://example.com',
                        'mode': 'mp3',
                        'folder': directory,
                        'filename_template': 'Faixa - Música',
                        'detect_duplicates': True,
                        'spotify_client_secret': 'secret',
                    }
                ]
            )
            row = store.load_queue()[0]
            self.assertEqual(row['filename_template'], 'Faixa - Música')
            self.assertTrue(row['detect_duplicates'])
            self.assertNotIn('spotify_client_secret', row)


class OrganizationTests(unittest.TestCase):
    def test_all_presets_stay_under_root(self):
        record = {
            'platform': 'Deezer',
            'id': '1',
            'title': '../../Song',
            'artists': ['../Artist'],
            'album': '../Album',
            'genre': '../Genre',
            'release_date': '2026-01-01',
            'track_number': '2/10',
            'disc_number': 1,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for folder in ORGANIZATIONS:
                config = {'folder': directory, 'organization': folder, 'mode': 'flac'}
                result = destination(config, record)
                self.assertTrue(result.is_relative_to(root), folder)
                for template in FILENAME_TEMPLATES:
                    name = output_filename(
                        'old.flac', dict(config, filename_template=template), record
                    )
                    self.assertEqual(Path(name).name, name)
                    self.assertTrue(name.endswith('.flac'))

    def test_track_and_disc_names(self):
        record = {
            'artists': ['Artist'],
            'title': 'Song',
            'track_number': '2/10',
            'disc_number': 3,
        }
        self.assertEqual(
            output_filename('x.mp3', {'filename_template': 'Faixa - Música'}, record),
            '02 - Song.mp3',
        )
        self.assertEqual(
            output_filename(
                'x.flac', {'filename_template': 'Disco-Faixa - Música'}, record
            ),
            '3-02 - Song.flac',
        )
        self.assertEqual(
            output_filename(
                'x.mp3', {'filename_template': 'Faixa - Música'}, {'title': 'Song'}
            ),
            'Song.mp3',
        )

    def test_playlist_folder_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            for folder in ORGANIZATIONS:
                self.assertEqual(
                    destination(
                        {
                            'folder': directory,
                            'organization': folder,
                            'playlist_title': 'Collection',
                        },
                        {'artists': ['A']},
                    ),
                    Path(directory).resolve() / 'Collection',
                )

    def test_new_name_uses_existing_collision_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.mp3'
            source.write_bytes(b'new')
            target = root / 'out'
            target.mkdir()
            (target / '01 - Song.mp3').write_bytes(b'old')
            path, skipped = publish(
                source,
                target,
                'keep',
                config={'filename_template': 'Faixa - Música'},
                record={'title': 'Song', 'track_number': 1},
            )
            self.assertFalse(skipped)
            self.assertEqual(Path(path).name, '01 - Song (2).mp3')
            self.assertEqual((target / '01 - Song.mp3').read_bytes(), b'old')

    def test_preview_and_preference_transfer(self):
        from advanced_options import export_settings, import_settings

        options = {
            'organization': 'Artista / Ano - Álbum',
            'filename_template': 'Faixa - Música',
            'detect_duplicates': False,
        }
        self.assertIn('2026', preview_path(options))
        self.assertIn('01 - Música.mp3', preview_path(options))
        loaded = import_settings(export_settings(options, 'android'), 'android')
        for key in options:
            self.assertEqual(loaded[key], options[key])


class BatchTests(unittest.TestCase):
    def make_audio(self, root, name):
        path = root / name
        with wave.open(str(path), 'wb') as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(8000)
            stream.writeframes(b'\0\0' * 800)
        write_audio(
            path,
            {
                'title': 'Title ' + name,
                'artists': ['Artist'],
                'album': 'Original album',
                'genre': 'Old',
            },
        )
        return path

    def test_copies_keep_original_and_unselected_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = [self.make_audio(root, name) for name in ('one.wav', 'two.wav')]
            hashes = [hashlib.sha256(p.read_bytes()).digest() for p in files]
            result = edit_batch(
                {
                    'sources': [{'source': str(p)} for p in files],
                    'changes': {'genre': 'New'},
                }
            )
            self.assertEqual(len(result['results']), 2)
            self.assertEqual(result['errors'], [])
            for original, edited, before in zip(files, result['results'], hashes):
                self.assertEqual(hashlib.sha256(original.read_bytes()).digest(), before)
                data = read_audio(edited['path'])
                self.assertEqual(data['genre'], 'New')
                self.assertEqual(data['album'], 'Original album')
                self.assertEqual(data['artists'], ['Artist'])

    def test_overwrite_only_selected_field(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_audio(Path(directory), 'one.wav')
            result = edit_batch(
                {
                    'sources': [{'source': str(path)}],
                    'changes': {'album': 'New album'},
                    'overwrite_original': True,
                }
            )
            self.assertTrue(result['results'][0]['overwritten'])
            self.assertEqual(read_audio(path)['album'], 'New album')
            self.assertEqual(read_audio(path)['genre'], 'Old')

    def test_failed_file_does_not_stop_remaining_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.make_audio(root, 'one.wav')
            result = edit_batch(
                {
                    'sources': [
                        {'source': str(root / 'missing.wav')},
                        {'source': str(path)},
                    ],
                    'changes': {'album': 'New'},
                }
            )
            self.assertEqual(len(result['results']), 1)
            self.assertEqual(len(result['errors']), 1)

    def test_duplicate_source_processed_once_and_fields_can_clear(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.make_audio(Path(directory), 'one.wav')
            result = edit_batch(
                {
                    'sources': [
                        {'source': str(path)},
                        {'source': str(path.parent / '.' / path.name)},
                    ],
                    'changes': {'album': '', 'artists': []},
                }
            )
            self.assertEqual(len(result['results']), 1)
            data = read_audio(result['results'][0]['path'])
            self.assertEqual(data['album'], '')
            self.assertEqual(data['artists'], [])
            self.assertEqual(data['genre'], 'Old')

    def test_invalid_cover_leaves_original_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = self.make_audio(root, 'one.wav')
            before = path.read_bytes()
            cover = root / 'invalid.jpg'
            cover.write_bytes(b'not an image')
            result = edit_batch(
                {
                    'sources': [{'source': str(path)}],
                    'changes': {},
                    'cover_path': str(cover),
                    'overwrite_original': True,
                }
            )
            self.assertEqual(len(result['errors']), 1)
            self.assertEqual(result['results'], [])
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(list(root.glob('.onda-edit-*')))

    def test_selection_limits_and_large_values(self):
        for options in (
            {'sources': [], 'changes': {'album': 'A'}},
            {'sources': [{'source': 'a'}] * 501, 'changes': {'album': 'A'}},
            {'sources': [{'source': 'a'}], 'changes': {'album': 'A' * 4097}},
        ):
            with (
                self.subTest(options=len(options['sources'])),
                self.assertRaises(ValueError),
            ):
                edit_batch(options)

    def test_empty_selection_and_invalid_fields_rejected(self):
        for changes in (
            {},
            {'source_url': 'bad'},
            {'track_number': '-2'},
            {'artists': 'bad'},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                edit_batch(
                    {'sources': [{'source': 'anything.wav'}], 'changes': changes}
                )

    def test_android_publication_failure_is_per_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = [self.make_audio(root, name) for name in ('one.wav', 'two.wav')]

            def emit(kind, **event):
                if kind == 'file' and 'one' in event['path']:
                    raise OSError('Publication denied')

            result = edit_batch(
                {
                    'sources': [{'source': str(p)} for p in files],
                    'changes': {'album': 'New'},
                    '_android_batch': True,
                },
                emit,
            )
            self.assertEqual(len(result['errors']), 1)
            self.assertEqual(len(result['results']), 1)


import os


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'), 'Tk integration')
class WorkflowUiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name})
        self.env.start()
        from app import App

        self.app = App(show_welcome=False)
        self.app.withdraw()
        self.app.folder.set(self.temp.name)

    def tearDown(self):
        pane = self.app.metadata_page
        if pane.batch_editor is not None and pane.batch_editor.winfo_exists():
            pane.batch_editor.close()
        self.app.destroy()
        self.env.stop()
        self.temp.cleanup()
        from i18n import set_language

        set_language('pt-BR')

    def test_duplicate_prompt_can_skip_or_add_canonical_link(self):
        first = 'https://youtu.be/abcdefghijk'
        second = 'https://www.youtube.com/watch?v=abcdefghijk&si=shared'
        self.app.add([first])
        with patch('app.messagebox.askyesno', return_value=False) as choice:
            self.assertEqual(self.app.add([second]), [])
            choice.assert_called_once()
        with patch('app.messagebox.askyesno', return_value=True):
            self.assertEqual(len(self.app.add([second])), 1)

    def test_detection_can_be_disabled_for_exact_duplicate(self):
        self.app.detect_duplicates.set(False)
        self.app.add(['https://example.com/same'])
        with patch('app.messagebox.askyesno') as choice:
            self.assertEqual(len(self.app.add(['https://example.com/same'])), 1)
            choice.assert_not_called()
        self.assertEqual(len(self.app.jobs), 2)

    def test_failed_queue_item_does_not_block_adding_again(self):
        key = self.app.add(['https://example.com/retry'])[0]
        self.app.jobs[key]['state'] = 'Erro'
        with patch('app.messagebox.askyesno') as choice:
            self.assertEqual(len(self.app.add(['https://example.com/retry'])), 1)
            choice.assert_not_called()

    def test_history_multiselect_opens_selective_batch_editor(self):
        root = Path(self.temp.name)
        files = [
            BatchTests.make_audio(self, root, name) for name in ('one.wav', 'two.wav')
        ]
        for file in files:
            self.app.library.add_history(file, 'WAV')
        history = self.app.history_page
        history.refresh()
        keys = history.table.get_children()
        history.table.selection_set(keys)
        history.edit_batch()
        editor = self.app.metadata_page.batch_editor
        editor.withdraw()
        self.assertEqual(len(editor.sources), 2)
        self.assertFalse(editor.overwrite.get())
        self.assertFalse(any(value.get() for value in editor.selected.values()))
        self.app.history_view.set('Completa')
        history.refresh()
        history.toggle_card(keys[0])
        self.assertEqual(len(history.table.selection()), 1)

    def test_duplicate_history_prompt_uses_source_and_format(self):
        file = Path(self.temp.name) / 'old.mp3'
        file.write_bytes(b'old')
        self.app.mode.set('Áudio · MP3 (320 kbps)')
        self.app.library.add_history(file, 'MP3', 'https://youtu.be/abcdefghijk')
        with patch('app.messagebox.askyesno', return_value=False) as choice:
            self.assertEqual(
                self.app.add(['https://youtube.com/watch?v=abcdefghijk']), []
            )
            choice.assert_called_once()


if __name__ == '__main__':
    unittest.main()
