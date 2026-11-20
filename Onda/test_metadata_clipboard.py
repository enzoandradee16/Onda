import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave

from audio_library import read_audio, write_audio
from metadata_clipboard import encode, decode


def audio(path):
    with wave.open(str(path), 'wb') as output:
        output.setparams((1, 2, 8000, 0, 'NONE', ''))
        output.writeframes(b'\x01\x00' * 800)


class MetadataTransferTests(unittest.TestCase):
    def test_roundtrip_preserves_unicode_lists_empty_and_excludes_paths(self):
        record = dict(
            title='Canção',
            artists=['A', 'B'],
            album='',
            composer='C',
            comment='linha 1\nlinha 2',
            source='private.wav',
            duration=10,
        )
        tags = decode(encode(record))
        self.assertEqual(
            tags, {k: v for k, v in record.items() if k not in ('source', 'duration')}
        )

    def test_untrusted_clipboard_is_rejected_before_use(self):
        for value in (
            'text',
            '[]',
            '{}',
            'x' * (256 * 1024 + 1),
            json.dumps(dict(format='onda.tags', version=2, tags={'title': 'A'})),
            json.dumps(dict(format='onda.tags', version=1, tags={'source': 'private'})),
            json.dumps(dict(format='onda.tags', version=1, tags={'artists': 'A'})),
            json.dumps(dict(format='onda.tags', version=1, tags={'title': 3})),
        ):
            with self.subTest(value=value[:80]), self.assertRaises(ValueError):
                decode(value)

    def test_extended_tags_copy_clear_and_preserve_audio_and_other_tags(self):
        from mutagen import File
        from mutagen.id3 import USLT, TXXX

        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder) / 'source.wav', Path(folder) / 'target.wav'
            audio(source)
            audio(target)
            original = dict(
                title='Música',
                artists=['A', 'B'],
                album_artist='Vários',
                composer='Compositor',
                comment='Comentário',
            )
            write_audio(source, original)
            native = File(target)
            native.add_tags()
            native.tags.add(USLT(encoding=3, lang='por', text='letra preservada'))
            native.tags.add(TXXX(encoding=3, desc='custom', text=['preservado']))
            native.save()
            with wave.open(str(target)) as stream:
                before = stream.readframes(stream.getnframes())
            write_audio(target, decode(encode(read_audio(source))))
            result = read_audio(target)
            for key, value in original.items():
                self.assertEqual(result[key], value)
            with wave.open(str(target)) as stream:
                self.assertEqual(before, stream.readframes(stream.getnframes()))
            self.assertEqual(
                File(target).tags.getall('USLT')[0].text, 'letra preservada'
            )
            self.assertEqual(File(target).tags['TXXX:custom'].text, ['preservado'])
            write_audio(target, {'composer': '', 'comment': ''})
            self.assertEqual(read_audio(target)['composer'], '')
            self.assertEqual(read_audio(target)['comment'], '')

    def test_partial_paste_applies_to_batch_without_changing_titles(self):
        from batch_metadata import edit_batch

        with tempfile.TemporaryDirectory() as folder:
            files = [Path(folder) / f'{i}.wav' for i in range(2)]
            for i, path in enumerate(files):
                audio(path)
                write_audio(path, {'title': str(i)})
            tags = decode(encode({'album': 'Álbum', 'comment': 'Coleção'}))
            result = edit_batch(
                dict(
                    sources=[{'source': str(p)} for p in files],
                    changes=tags,
                    overwrite_original=True,
                )
            )
            self.assertFalse(result['errors'])
            for i, path in enumerate(files):
                self.assertEqual(read_audio(path)['title'], str(i))
                self.assertEqual(read_audio(path)['comment'], 'Coleção')

    @unittest.skipUnless(
        os.environ.get('ONDA_METADATA_FFMPEG'), 'Optional real-format check'
    )
    def test_real_formats_roundtrip_without_changing_decoded_audio(self):
        ffmpeg = os.environ['ONDA_METADATA_FFMPEG']
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'source.wav'
            audio(source)
            for suffix in ('mp3', 'm4a', 'flac', 'ogg', 'opus'):
                with self.subTest(format=suffix):
                    path = Path(folder) / ('target.' + suffix)
                    subprocess.run(
                        [ffmpeg, '-v', 'error', '-i', str(source), str(path)],
                        check=True,
                    )

                    def digest():
                        return subprocess.check_output(
                            [
                                ffmpeg,
                                '-v',
                                'error',
                                '-i',
                                str(path),
                                '-map',
                                '0:a:0',
                                '-f',
                                'hash',
                                '-hash',
                                'sha256',
                                '-',
                            ]
                        )

                    before = digest()
                    tags = dict(
                        title='Título',
                        artists=['A', 'B'],
                        album_artist='AA',
                        composer='C',
                        comment='Comentários',
                    )
                    write_audio(path, tags)
                    result = read_audio(path)
                    for key, value in tags.items():
                        self.assertEqual(result[key], value)
                    self.assertEqual(digest(), before)


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional desktop check')
class MetadataDesktopTests(unittest.TestCase):
    def test_editing_title_preserves_untouched_extended_tags(self):
        from qt_workspace_ui import DesktopWorkspace
        from types import SimpleNamespace
        from unittest.mock import Mock

        workspace = SimpleNamespace(
            options={
                'metadataSources': ['audio.wav'],
                'metadata': {
                    'title': 'Novo',
                    'composer': 'Original',
                    'comment': 'Original',
                },
                'metadataOriginal': {
                    'title': 'Antigo',
                    'composer': 'Original',
                    'comment': 'Original',
                },
                'metadataFields': {},
                'overwrite_original': False,
                'normalize_volume': False,
                'cover_path': '',
                'lyrics_path': '',
            },
            run_task=Mock(),
            show_result=Mock(),
        )
        DesktopWorkspace.edit_audio(workspace)
        self.assertEqual(
            workspace.run_task.call_args.args[1]['changes'], {'title': 'Novo'}
        )

    def test_copy_paste_marks_batch_fields_without_saving(self):
        from PySide6.QtWidgets import QApplication
        from qt_workspace_ui import DesktopWorkspace
        from types import SimpleNamespace
        from unittest.mock import Mock

        app = QApplication.instance() or QApplication([])
        workspace = SimpleNamespace(
            options={
                'metadataSources': ['target.wav', 'other.wav'],
                'metadata': {'title': 'Preservar'},
                'metadataFields': {},
            },
            optionsChanged=Mock(),
            _metadata_transfer_cover='',
        )
        workspace.metadata_clipboard_text = lambda: app.clipboard().text()
        app.clipboard().setText(encode({'album': 'Novo'}))
        DesktopWorkspace.paste_metadata_tags(workspace)
        self.assertEqual(workspace.options['metadata']['title'], 'Preservar')
        self.assertEqual(workspace.options['metadataFields'], {'album': True})
        self.assertEqual(workspace._metadata_transfer['tags'], {'album': 'Novo'})

    def test_metadata_menu_and_paste_shortcut_in_real_window(self):
        from unittest.mock import patch
        from PySide6.QtCore import QObject, Qt, qInstallMessageHandler
        from PySide6.QtTest import QTest
        from qt_desktop_ui import create_application, close_application
        from preferences import PreferenceStore

        with (
            tempfile.TemporaryDirectory() as folder,
            patch.dict(
                os.environ,
                {
                    'LOCALAPPDATA': folder,
                    'ONDA_ALIAS_CACHE_ROOT': folder,
                },
            ),
        ):
            PreferenceStore().save({'check_updates': False, 'clipboard_links': False})
            warnings = []
            old_handler = qInstallMessageHandler(
                lambda kind, context, text: warnings.append(text)
            )
            app, engine, bridge = create_application(complete=False)
            try:
                workspace = engine.workspace
                workspace.selectPage('metadata')
                source = Path(folder) / 'audio.wav'
                audio(source)
                write_audio(source, {'title': 'Original'})
                workspace.options.update(
                    metadataSources=[str(source)], metadata={'title': 'Original'}
                )
                workspace.optionsChanged.emit()
                window = engine.rootObjects()[0]
                window.requestActivate()
                QTest.qWait(100)
                texts = [obj.property('text') for obj in window.findChildren(QObject)]
                self.assertIn('Copiar tags', texts)
                self.assertIn('Colar tags', texts)
                menu = window.findChild(QObject, 'toolContextMenu')
                self.assertTrue(
                    any(
                        obj.property('text') == 'Identificar pelo áudio'
                        for obj in menu.findChildren(QObject)
                    )
                )
                app.clipboard().setText('')
                workspace.copy_metadata_tags()
                for _ in range(100):
                    if workspace.metadataClipboardAvailable:
                        break
                    QTest.qWait(50)
                from tag_transfer import decode as decode_full

                self.assertEqual(
                    decode_full(workspace.metadata_clipboard_text())['tags']['title'],
                    'Original',
                )
                app.clipboard().setText(encode({'album': 'Colado pelo atalho'}))
                QTest.keyClick(window, Qt.Key_V, Qt.ControlModifier | Qt.ShiftModifier)
                QTest.qWait(30)
                self.assertEqual(
                    workspace.options['metadata']['album'], 'Colado pelo atalho'
                )
                workspace.present_choice(
                    'metadata-card-test',
                    {
                        'type': 'choose_catalog',
                        'candidates': [
                            {
                                'source_url': 'test:recording',
                                'title': 'Título',
                                'artists': ['Artista'],
                                'album': 'Álbum',
                                'release_date': '2026',
                                'duration_ms': 123000,
                                'isrc': 'TEST123',
                                'platform': 'MusicBrainz',
                            }
                        ],
                    },
                )
                QTest.qWait(60)

                def visual_items(item):
                    yield item
                    for child in item.childItems():
                        yield from visual_items(child)

                rows = [
                    obj
                    for obj in visual_items(window.contentItem())
                    if obj.objectName() == 'decisionCandidateRow'
                ]
                self.assertEqual(len(rows), 1)
                self.assertLess(rows[0].property('height'), 200)
                app.clipboard().setText('texto comum')
                QTest.qWait(20)
                self.assertFalse(workspace.metadataClipboardAvailable)
                self.assertEqual(
                    [text for text in warnings if 'ToolView.qml' in text], []
                )
            finally:
                close_application(engine, bridge)
                qInstallMessageHandler(old_handler)
