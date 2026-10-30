"""Exercise real HTTP commands through the Qt adapter, without audible playback."""

import http.client
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


@unittest.skipUnless(os.environ.get('ONDA_QT_TESTS'), 'Optional Qt remote tests')
class QtRemoteTests(unittest.TestCase):
    def setUp(self):
        from qt_desktop_ui import create_application

        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.environment = patch.dict(
            os.environ,
            {
                'LOCALAPPDATA': self.temporary.name,
                'ONDA_ALIAS_CACHE_ROOT': str(Path(self.temporary.name) / 'cache'),
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.app, self.engine, self.bridge = create_application(complete=False)
        self.remote = self.engine.workspace.remote_control

    def tearDown(self):
        from qt_desktop_ui import close_application

        close_application(self.engine, self.bridge)

    def request(self, path, token='', body=None):
        connection = http.client.HTTPConnection(
            '127.0.0.1', self.remote.server.port, timeout=3
        )
        try:
            connection.request(
                'GET' if body is None else 'POST',
                path,
                None if body is None else json.dumps(body),
                {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + token,
                },
            )
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def test_server_is_disabled_until_explicitly_enabled(self):
        self.assertFalse(self.remote.state['enabled'])
        self.assertIsNone(self.remote.server)

    def test_remote_search_publishes_background_results_without_stopping_playback(self):
        from PySide6.QtCore import QEventLoop, QTimer
        from remote_control import RemoteServer

        with patch(
            'qt_remote_ui.RemoteServer', side_effect=lambda: RemoteServer('127.0.0.1')
        ):
            self.remote.start()
        self.bridge.update_state(playing=True, paused=False)
        with patch(
            'qt_operations_ui.perform',
            return_value=dict(
                tracks=[dict(title='Song', artists=['Artist'], duration_ms=120000)]
            ),
        ) as resolve:
            self.remote.search('Artist song')
            loop = QEventLoop()
            QTimer.singleShot(300, loop.quit)
            loop.exec()
        resolve.assert_called_once()
        self.assertTrue(self.bridge.state['playing'])
        self.assertFalse(self.remote._search_state['busy'])
        self.assertEqual(self.remote._search_state['rows'][0]['duration'], 120)

    def test_remote_effects_update_the_same_workspace_and_jukebox_settings(self):
        from remote_control import RemoteServer

        with patch(
            'qt_remote_ui.RemoteServer', side_effect=lambda: RemoteServer('127.0.0.1')
        ):
            self.remote.start()
        self.remote.server.commands.put(
            ('effects', dict(enabled=True, speed=90, reverb=30, keep_pitch=True))
        )
        self.remote.server.commands.put(
            ('jukebox', dict(variation=42, smooth=70, normal=False))
        )
        self.remote.tick()
        state = self.remote.server.snapshot
        self.assertEqual(self.engine.workspace.options['speed'], 90)
        self.assertEqual(
            state['effects'], dict(enabled=True, speed=90, reverb=30, keep_pitch=True)
        )
        self.assertEqual(state['jukebox'], dict(variation=42, smooth=70, normal=False))
        # A desktop edit is published to the phone as well.
        self.engine.workspace.setOption('speed', 110)
        self.remote.tick()
        self.assertEqual(self.remote.server.snapshot['effects']['speed'], 110)

    def test_search_results_stay_on_the_pc_and_can_only_be_added_by_identity(self):
        from remote_control import RemoteServer

        with patch(
            'qt_remote_ui.RemoteServer', side_effect=lambda: RemoteServer('127.0.0.1')
        ):
            self.remote.start()
        self.remote._search_revision = 7
        record = dict(
            title='Track',
            artists=['Artist'],
            source_url='https://example.com/music',
            _private='not public',
        )
        self.remote.search_finished((6, dict(tracks=[record])))
        self.assertEqual(self.remote._search_state['rows'], [])
        self.remote.search_finished((7, dict(tracks=[record])))
        row = self.remote._search_state['rows'][0]
        self.assertNotIn('source_url', row)
        self.assertNotIn('_private', row)
        with patch.object(self.bridge, 'enqueueRecords') as enqueue:
            self.remote.server.commands.put(('search_add', row['id']))
            self.remote.server.commands.put(('search_add', row['id']))
            self.remote.tick()
        enqueue.assert_called_once_with([record])
        self.assertEqual(self.remote._search_state['rows'], [])

    def test_order_controls_and_device_name_are_published(self):
        from remote_control import RemoteServer

        with patch(
            'qt_remote_ui.RemoteServer', side_effect=lambda: RemoteServer('127.0.0.1')
        ):
            self.remote.start()
        token = self.request('/v1/pair', body={'code': self.remote.server.code})[1][
            'token'
        ]
        for name, value in (('shuffle', True), ('repeat', 'Uma')):
            self.assertEqual(
                self.request('/v1/command', token, {'command': name, 'value': value})[
                    0
                ],
                202,
            )
        self.remote.tick()
        snapshot = self.request('/v1/state', token)[1]
        self.assertTrue(self.bridge.queueShuffle)
        self.assertEqual(self.bridge.queueRepeat, 'Uma')
        self.assertTrue(snapshot['shuffle'])
        self.assertEqual(snapshot['repeat'], 'Uma')
        self.assertEqual(snapshot['device_name'], self.remote.server.name)

    def test_queue_changes_are_coalesced_before_publishing_the_next_snapshot(self):
        from PySide6.QtCore import QEventLoop, QTimer
        from remote_control import RemoteServer

        with patch(
            'qt_remote_ui.RemoteServer', side_effect=lambda: RemoteServer('127.0.0.1')
        ):
            self.remote.start()
        revision = self.remote.server.queue_revision
        self.bridge.playlist = [
            dict(
                id='item',
                title='Track',
                artist='Artist',
                source='private.wav',
                kind='file',
                analysis='pending',
                record={},
            )
        ]
        for _ in range(10):
            self.bridge.queueChanged.emit()
        self.assertEqual(self.remote.server.queue_revision, revision)
        loop = QEventLoop()
        QTimer.singleShot(250, loop.quit)
        loop.exec()
        self.assertEqual(self.remote.server.queue_revision, revision + 1)
        self.assertEqual(self.remote.server.queue_rows[0]['id'], 'item')

    def test_play_and_pause_are_idempotent_and_publish_the_actual_paused_state(self):
        from PySide6.QtCore import QEventLoop, QTimer
        from remote_control import RemoteServer

        self.bridge.update_state(playing=True, paused=True)
        with patch(
            'qt_remote_ui.RemoteServer', side_effect=lambda: RemoteServer('127.0.0.1')
        ):
            self.remote.start()
        token = self.request('/v1/pair', body={'code': self.remote.server.code})[1][
            'token'
        ]
        self.assertFalse(self.request('/v1/state', token)[1]['playing'])

        def toggle():
            self.bridge.update_state(paused=not self.bridge.state['paused'])

        with patch.object(self.bridge, 'playPause', side_effect=toggle) as action:
            for name in ('play', 'play'):
                self.request('/v1/command', token, {'command': name})
            loop = QEventLoop()
            QTimer.singleShot(250, loop.quit)
            loop.exec()
            self.assertTrue(self.request('/v1/state', token)[1]['playing'])
            for name in ('pause', 'pause'):
                self.request('/v1/command', token, {'command': name})
            QTimer.singleShot(250, loop.quit)
            loop.exec()
            self.assertFalse(self.request('/v1/state', token)[1]['playing'])
            self.assertEqual(action.call_count, 2)
        self.bridge.update_state(playing=False)

    def test_seek_uses_current_track_identity_and_queue_commands_resolve_ids(self):
        from PySide6.QtCore import QEventLoop, QTimer
        from remote_control import RemoteServer

        self.bridge.playlist = [
            dict(
                id='a',
                title='A',
                artist='Artist',
                source='private-a.wav',
                kind='file',
                analysis='pending',
                record={},
            ),
            dict(
                id='b',
                title='B',
                artist='Artist',
                source='private-b.wav',
                kind='file',
                analysis='pending',
                record={},
            ),
        ]
        self.bridge.queue_index = 0
        self.bridge.model = dict(
            duration=90,
            beats=[0, 30, 60, 90],
            neighbors=[[], [], []],
            source='private-a.wav',
        )
        self.bridge._position = 1
        self.bridge._phase = 0.5
        with patch(
            'qt_remote_ui.RemoteServer', side_effect=lambda: RemoteServer('127.0.0.1')
        ):
            self.remote.start()
        token = self.request('/v1/pair', body={'code': self.remote.server.code})[1][
            'token'
        ]
        page = self.request('/v1/queue', token)[1]
        self.assertEqual([row['id'] for row in page['rows']], ['a', 'b'])
        self.assertNotIn('source', page['rows'][0])
        with (
            patch.object(self.bridge, 'seekSeconds') as seek,
            patch.object(self.bridge, 'removeQueued') as remove,
        ):
            self.request(
                '/v1/command', token, dict(command='seek', track_id='a', value=12)
            )
            self.request(
                '/v1/command', token, dict(command='queue_remove', track_id='b')
            )
            # The PC changes songs and reorders its queue before handling the requests.
            self.bridge.playlist.reverse()
            self.bridge.queue_index = 0
            loop = QEventLoop()
            QTimer.singleShot(250, loop.quit)
            loop.exec()
            seek.assert_not_called()
            remove.assert_called_once_with(0)
            self.request(
                '/v1/command', token, dict(command='seek', track_id='b', value=44)
            )
            QTimer.singleShot(250, loop.quit)
            loop.exec()
            seek.assert_called_once_with(44)
        state = self.request('/v1/state', token)[1]
        self.assertEqual(state['position'], 45)
        self.assertEqual(state['duration'], 90)

    def test_artwork_is_a_bounded_jpeg_without_exposing_a_local_filename(self):
        import base64
        from PySide6.QtCore import QByteArray, QBuffer, QIODevice
        from PySide6.QtGui import QImage
        from remote_control import RemoteServer

        image = QImage(32, 32, QImage.Format_RGB32)
        image.fill(0xFF4488AA)
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.WriteOnly)
        image.save(buffer, 'PNG')
        self.bridge.update_state(
            cover='data:image/png;base64,' + base64.b64encode(bytes(data)).decode()
        )
        with patch(
            'qt_remote_ui.RemoteServer', side_effect=lambda: RemoteServer('127.0.0.1')
        ):
            self.remote.start()
        token = self.request('/v1/pair', body={'code': self.remote.server.code})[1][
            'token'
        ]
        state = self.request('/v1/state', token)[1]
        self.assertTrue(state['artwork_id'])
        connection = http.client.HTTPConnection(
            '127.0.0.1', self.remote.server.port, timeout=3
        )
        try:
            connection.request(
                'GET',
                '/v1/artwork?id=' + state['artwork_id'],
                headers={'Authorization': 'Bearer ' + token},
            )
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            jpeg = response.read()
            self.assertTrue(jpeg.startswith(b'\xff\xd8'))
            self.assertLess(len(jpeg), 2 * 1024 * 1024)
        finally:
            connection.close()

    def test_http_controls_reach_player_on_main_thread_and_update_volume(self):
        from PySide6.QtCore import QEventLoop, QTimer, QThread
        from remote_control import RemoteServer

        with patch(
            'qt_remote_ui.RemoteServer', side_effect=lambda: RemoteServer('127.0.0.1')
        ):
            self.remote.start()
        status, paired = self.request(
            '/v1/pair', body={'code': self.remote.server.code}
        )
        self.assertEqual(status, 200)
        calls = []

        def command(name):
            self.assertEqual(QThread.currentThread(), self.app.thread())
            calls.append(name)

        with (
            patch.object(
                self.bridge, 'playPause', side_effect=lambda: command('toggle')
            ),
            patch.object(self.bridge, 'nextTrack', side_effect=lambda: command('next')),
            patch.object(
                self.bridge, 'previousTrack', side_effect=lambda: command('previous')
            ),
        ):
            for name in ('toggle', 'next', 'previous'):
                self.assertEqual(
                    self.request('/v1/command', paired['token'], {'command': name})[0],
                    202,
                )
            self.assertEqual(
                self.request(
                    '/v1/command', paired['token'], {'command': 'volume', 'value': 17}
                )[0],
                202,
            )
            loop = QEventLoop()
            QTimer.singleShot(350, loop.quit)
            loop.exec()
        self.assertEqual(calls, ['toggle', 'next', 'previous'])
        self.assertEqual(self.request('/v1/state', paired['token'])[1]['volume'], 17)
        self.remote.stop()
        self.assertFalse(self.remote.state['enabled'])
