import importlib.util, json, os, tempfile, time, unittest, wave
from pathlib import Path
from unittest.mock import patch
from playlist_sync import reconcile, compare_collection, scan_folder


def track(number, title=None):
    return {
        'source_url': f'https://open.spotify.com/track/{number}',
        'title': title or f'Song {number}',
        'artists': ['Artist'],
        'album': 'Album',
        'duration_ms': 180000,
    }


class PlaylistComparisonTests(unittest.TestCase):
    def test_failed_or_cancelled_jobs_do_not_hide_missing_tracks(self):
        row = track('retry')
        for state in ('Falhou', 'Erro', 'Cancelado', 'Parado', 'Concluído'):
            with self.subTest(state=state):
                result = reconcile(
                    [row], [], [{'url': row['source_url'], 'state': state}]
                )
                self.assertEqual(result['items'][0]['state'], 'missing')
        for state in (
            'Na fila',
            'Pendente',
            'Em andamento',
            'Baixando',
            'Aguardando escolha',
            'Pausado',
        ):
            with self.subTest(state=state):
                result = reconcile(
                    [row], [], [{'url': row['source_url'], 'state': state}]
                )
                self.assertEqual(result['items'][0]['state'], 'queued')

    def test_identity_presence_missing_review_and_queue(self):
        a, b, c, d, e = [track(i) for i in range(5)]
        inventory = [
            dict(a, path='one.mp3', source_url=a['source_url'] + '?si=tracking'),
            dict(
                c,
                path='uncertain.mp3',
                source_url='',
                album='Other album',
                duration=180,
            ),
            dict(e, path='permission.mp3', uncertain=True),
        ]
        result = reconcile(
            [a, b, c, d, e], inventory, [{'url': d['source_url'], 'state': 'Na fila'}]
        )
        self.assertEqual(
            [row['state'] for row in result['items']],
            ['present', 'missing', 'review', 'queued', 'review'],
        )
        self.assertEqual(
            result['counts'], {'present': 1, 'missing': 1, 'review': 2, 'queued': 1}
        )

    def test_strict_metadata_and_filename_only_review(self):
        row = track('one')
        local = {**row, 'source_url': '', 'duration': 180, 'path': 'file.mp3'}
        self.assertEqual(reconcile([row], [local])['items'][0]['state'], 'present')
        for changes in (
            {'duration': 200},
            {'album': 'Remastered'},
            {'artists': ['Other artist']},
        ):
            self.assertEqual(
                reconcile([row], [{**local, **changes}])['items'][0]['state'], 'review'
            )
        self.assertEqual(
            reconcile(
                [row], [{'path': 'Artist - Song one.mp3', 'title': 'Artist - Song one'}]
            )['items'][0]['state'],
            'review',
        )
        row['isrc'] = 'USAAA0000001'
        self.assertEqual(
            reconcile(
                [row], [{**local, 'isrc': row['isrc'], 'title': 'Song one (Live)'}]
            )['items'][0]['state'],
            'review',
        )

    def test_snapshot_survives_restart_and_deleted_files_are_missing(self):
        with tempfile.TemporaryDirectory() as root:
            database = Path(root) / 'library.sqlite3'
            first = compare_collection(
                [track('a')],
                [],
                source='https://open.spotify.com/playlist/list?si=one',
                database=database,
            )
            self.assertFalse(first['has_previous'])
            second = compare_collection(
                [track('b')], [], source='spotify:playlist:list', database=database
            )
            self.assertTrue(second['has_previous'])
            self.assertEqual(second['new_count'], 1)
            self.assertEqual(second['removed_count'], 1)
            self.assertEqual(second['counts']['missing'], 1)
            history = [
                {
                    'path': str(Path(root) / 'deleted.mp3'),
                    'source': track('b')['source_url'],
                }
            ]
            self.assertEqual(scan_folder(root, history), [])

    def test_folder_sidecar_zero_files_and_cancellation(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'music.wav'
            with wave.open(str(path), 'wb') as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(8000)
                output.writeframes(b'\0\0' * 8000)
            path.with_suffix('.wav.metadata.json').write_text(
                json.dumps({'catalog': track('a')}), encoding='utf-8'
            )
            (Path(root) / 'empty.mp3').touch()
            inventory = scan_folder(root)
            self.assertEqual(len(inventory), 1)
            self.assertEqual(reconcile([track('a')], inventory)['counts']['present'], 1)
            with self.assertRaises(InterruptedError):
                scan_folder(root, cancelled=lambda: True)

    def test_large_collection_and_android_adapter(self):
        tracks = [track(str(i)) for i in range(1283)]
        inventory = [dict(row, path=f'{i}.mp3') for i, row in enumerate(tracks[:1113])]
        result = reconcile(tracks, inventory)
        self.assertEqual(result['counts']['present'], 1113)
        self.assertEqual(result['counts']['missing'], 170)
        source = (
            Path(__file__).parent.parent
            / 'Android/app/src/main/python/mobile_backend.py'
        )
        spec = importlib.util.spec_from_file_location(
            'sync_mobile_backend_test', source
        )
        backend = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backend)
        with tempfile.TemporaryDirectory() as root:
            actual = backend.perform(
                'collection_compare',
                {
                    'tracks': tracks,
                    'inventory': inventory,
                    'database': str(Path(root) / 'onda.sqlite3'),
                },
            )
            self.assertEqual(actual['counts'], result['counts'])


@unittest.skipUnless(os.environ.get('ONDA_UI_TESTS'), 'Tk integration')
class PlaylistComparisonUiTests(unittest.TestCase):
    def test_update_reloads_then_only_missing_is_selected_for_queue(self):
        from app import App
        from playlist_sync_ui import show, add_missing

        with (
            tempfile.TemporaryDirectory() as root,
            patch.dict(os.environ, {'LOCALAPPDATA': root}),
        ):
            app = App(show_welcome=False)
            app.clipboard_watch.shutdown()
            app.update()
            try:
                pane = app.playlist_page
                pane.url.set('https://open.spotify.com/playlist/list')
                old = track('old')
                new = track('new')
                compare_collection(
                    [old], [], source=pane.url.get(), database=app.library.path
                )
                loaded = {'title': 'Playlist', 'note': '', 'tracks': [old, new]}
                with (
                    patch('playlist_ui.load_playlist', return_value=loaded) as load,
                    patch(
                        'playlist_sync.scan_folder',
                        return_value=[dict(old, path='old.mp3')],
                    ),
                ):
                    pane.load(sync_folder=root)
                    deadline = time.monotonic() + 5
                    while pane.sync_result is None and time.monotonic() < deadline:
                        app.update()
                        time.sleep(0.01)
                load.assert_called_once()
                self.assertIsNotNone(pane.sync_result)
                self.assertEqual(pane.sync_result['new_count'], 1)
                self.assertEqual(pane.table.selection(), ('1',))
                pane.filter_text.set('old')
                pane.filter_records()
                with patch.object(pane, 'add') as add:
                    add_missing(pane)
                    add.assert_called_once_with()
                    self.assertEqual(pane.table.selection(), ('1',))
                self.assertIsNone(pane.sync_result)
            finally:
                app.destroy()


if __name__ == '__main__':
    unittest.main()
