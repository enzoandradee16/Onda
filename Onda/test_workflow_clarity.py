import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from collection_coverage import annotate, compare, compare_file
from tool_status import check, read, updated, display
from workflow_status import can_act, label


class CoverageTests(unittest.TestCase):
    def test_unknown_public_total_is_never_complete(self):
        report = annotate({'tracks': [{}] * 20}, uncertain=True)
        self.assertEqual(report['coverage']['state'], 'unknown')
        self.assertIsNone(report['coverage']['total'])

    def test_known_total_accounts_for_skips_and_limit(self):
        report = annotate({'tracks': [{}] * 3}, 5, skipped=1, capped=True)
        self.assertEqual(
            report['coverage'],
            dict(loaded=3, total=5, skipped=1, state='partial', limit_reached=True),
        )
        self.assertIn('3 de 5', report['coverage_summary'])

    def test_deezer_pagination_reports_actual_total(self):
        from playlist_import import load_playlist

        client = Mock()
        client.get_json.side_effect = [
            {'title': 'List', 'nb_tracks': 5},
            {
                'data': [
                    {'id': i, 'title': str(i), 'artist': {'name': 'A'}}
                    for i in range(1, 4)
                ],
                'next': 'more',
            },
        ]
        result = load_playlist('https://www.deezer.com/playlist/1', client, limit=3)
        self.assertEqual(result['coverage']['total'], 5)
        self.assertTrue(result['coverage']['limit_reached'])

    def test_reference_compares_tracking_aliases_and_repeated_tracks(self):
        track = 'https://open.spotify.com/track/' + 'a' * 22
        report = compare(
            [{'source_url': track + '?si=shared'}],
            [{'source_url': 'spotify:track:' + 'a' * 22}] * 2,
        )
        self.assertEqual(
            (report['matched'], report['missing'], report['extra']), (1, 1, 0)
        )

    def test_reference_import_does_not_change_loaded_tracks(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'list.m3u'
            source.write_text(
                '#EXTM3U\nhttps://youtu.be/abcdefghijk\nhttps://youtu.be/ABCDEFGHIJK\n',
                encoding='utf-8',
            )
            rows = [
                {
                    'source_url': 'https://www.youtube.com/watch?v=abcdefghijk&list=unrelated'
                }
            ]
            self.assertEqual(compare_file(rows, source)['missing'], 1)
            self.assertEqual(len(rows), 1)

    def test_file_limit_is_explicit(self):
        from playlist_import import load_text

        result = load_text('https://example.com/1\nhttps://example.com/2', limit=1)
        self.assertEqual(result['coverage']['state'], 'partial')
        self.assertEqual(result['coverage']['total'], 2)


class ToolTests(unittest.TestCase):
    def test_display_preserves_details_but_shortens_ffmpeg_banners(self):
        raw = (
            'ffmpeg version 9.0.2-essentials_build-www.gyan.dev Copyright (c) 2000-2026'
        )
        report = display(
            {
                'tools': [dict(name='ffmpeg', version=raw, status='Disponível')],
                'checked_at': '2026-10-27T23:38:29+00:00',
                'restart_required': True,
            }
        )
        row = report['tools'][0]
        self.assertEqual(row['version'], '9.0.2')
        self.assertEqual(row['details'], raw)
        self.assertTrue(row['available'])
        self.assertTrue(report['restart_required'])
        self.assertIn(raw, report['details'])

    def test_display_icons_are_bundled_and_unknown_tools_are_safe(self):
        rows = [
            dict(name=name, version='1.0', status='Disponível')
            for name in (
                'Python',
                'yt-dlp',
                'gallery-dl',
                'Pillow',
                'Mutagen',
                'ffmpeg',
                'ffprobe',
                'ffplay',
                'Node.js',
                'QuickJS',
                'Custom tool',
            )
        ]
        for row in display({'tools': rows})['tools']:
            asset = (
                Path(__file__).parent
                / 'assets/tool-icons/tools'
                / (row['icon'] + '.png')
            )
            self.assertTrue(asset.is_file(), row['name'])
            self.assertTrue(asset.read_bytes().startswith(b'\x89PNG'))

    def test_missing_tool_does_not_hide_other_versions(self):
        with tempfile.TemporaryDirectory() as folder:
            result = check(
                folder,
                {
                    'Working': [sys.executable, '-c', 'print("tool 1.0")'],
                    'Missing': [str(Path(folder) / 'missing')],
                },
            )
            self.assertEqual(
                next(row for row in result['tools'] if row['name'] == 'Working')[
                    'version'
                ],
                'tool 1.0',
            )
            self.assertEqual(
                next(row for row in result['tools'] if row['name'] == 'Missing')[
                    'status'
                ],
                'Indisponível',
            )
            self.assertEqual(read(folder)['checked_at'], result['checked_at'])

    def test_update_failure_preserves_last_check_and_restart_notice(self):
        with tempfile.TemporaryDirectory() as folder:
            report = check(folder, {})
            updated(folder, True)
            updated(folder, False)
            result = check(folder, {})
            self.assertEqual(result['update_state'], 'Falha na atualização')
            self.assertTrue(result['restart_required'])
            with patch('tool_status.os.getpid', return_value=os.getpid() + 1):
                self.assertFalse(check(folder, {})['restart_required'])


class StateTests(unittest.TestCase):
    def test_platform_states_have_same_visible_labels(self):
        for pc, android in [
            ('Na fila', 'Pendente'),
            ('Em andamento', 'Baixando'),
            ('Falhou', 'Erro'),
        ]:
            self.assertEqual(label(pc), label(android))

    def test_actions_cannot_retry_completed_or_pause_failed_jobs(self):
        self.assertFalse(can_act('Concluído', 'retry'))
        self.assertFalse(can_act('Falhou', 'pause'))
        self.assertTrue(can_act('Erro', 'retry'))
        self.assertTrue(can_act('Pausado', 'resume'))


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Qt integration')
class ClarityDesktopTests(unittest.TestCase):
    from test_qt_workspace import NativeDesktopTests as Fixture

    setUpClass = classmethod(Fixture.setUpClass.__func__)
    setUp = Fixture.setUp
    tearDown = Fixture.tearDown
    settle = Fixture.settle

    def test_collection_coverage_is_kept_visible(self):
        self.ws.collection_loaded(annotate({'title': 'List', 'tracks': []}, total=8))
        self.assertIn('0 de 8', self.ws.options['collectionCoverage'])

    def test_effects_failure_stays_in_queue_and_retry_is_prepare_only(self):
        with patch.object(self.bridge, 'prepare_next_queued'):
            self.ws.accept_files('effects_queue', ['broken.wav'])
            entry = self.bridge.playlist[0]
            self.bridge.handle_event(
                0, 'queue_prepared', dict(id=entry['id'], error='Permission denied')
            )
        self.assertEqual(len(self.bridge.playlist), 1)
        self.assertEqual(entry['analysis'], 'error')
        with (
            patch.object(self.bridge, 'prepare_next_queued') as prepare,
            patch.object(self.bridge, 'playPause') as play,
        ):
            self.bridge.retryQueued(0)
            self.assertEqual(entry['analysis'], 'pending')
            prepare.assert_called_once()
            play.assert_not_called()

    def test_verification_updates_persistent_panel(self):
        with patch.object(self.ws, 'run_task') as task:
            self.ws.dispatch('verify_tools', {})
            task.call_args.args[2]({'message': 'Python 3.11 · Disponível'})
        self.assertIn('Python', self.ws.options['toolStatus'])

    def test_remote_collection_failure_keeps_metadata_and_retry_survives_reorder(self):
        failed = dict(
            source='https://example.com/broken',
            record={'title': 'Unavailable'},
            remote=True,
            error='HTTP 403',
            duration=0,
        )
        self.ws.options['effectsQueue'] = [failed]
        with patch.object(self.ws, 'run_task') as task:
            self.ws.dispatch('effects_queue_retry', {'index': 0})
            self.ws.options['effectsQueue'].insert(
                0, dict(source='other.wav', record={'title': 'Other'}, duration=3)
            )
            task.call_args.args[2](
                {'source': 'recovered.wav', 'record': failed['record']}
            )
            self.assertEqual(task.call_args.args[0], 'effects_info')
            task.call_args.args[2]({'duration': 5, 'record': failed['record']})
        recovered = self.ws.options['effectsQueue'][1]
        self.assertEqual(recovered['source'], 'recovered.wav')
        self.assertNotIn('error', recovered)
        self.assertNotIn('remote', recovered)

    def test_completed_download_does_not_return_to_pending_on_retry(self):
        self.ws.jobs = [
            dict(
                id='done',
                state='Concluído',
                url='https://example.com/done',
                checked=True,
            )
        ]
        with (
            patch.object(self.ws, 'refresh_queue'),
            patch.object(self.ws, 'save_queue'),
        ):
            self.ws.queue_action('retry', 'done')
        self.assertEqual(self.ws.jobs[0]['state'], 'Concluído')
