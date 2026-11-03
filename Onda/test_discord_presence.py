"""Exercise real Qt local IPC without publishing to a Discord account."""

import json
import struct
import time
import unittest
import uuid

from PySide6.QtNetwork import QLocalServer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from discord_presence import APPLICATION_ID, DiscordPresence, public_cover


class PresenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.name = 'onda-discord-test-' + uuid.uuid4().hex
        self.server = QLocalServer()
        self.assertTrue(self.server.listen(self.name))
        self.frames = []
        self.buffer = bytearray()
        self.peer = None
        self.auto_ack = True
        self.playback = dict(
            playing=True,
            title='Digital Love',
            artist='Daft Punk',
            album='Discovery',
            position=30,
            duration=300,
            cover_url='https://example.com/album.jpg',
            track_id='track',
        )
        self.now = 1700000000
        self.client = DiscordPresence(
            lambda: dict(self.playback), names=[self.name], clock=lambda: self.now
        )
        self.server.newConnection.connect(self.accept)

    def tearDown(self):
        self.client.close()
        QTest.qWait(20)
        if self.peer:
            self.peer.close()
        self.server.close()
        self.client.deleteLater()
        self.server.deleteLater()
        self.app.processEvents()

    def wait(self, condition):
        deadline = time.monotonic() + 3
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(10)
        self.assertTrue(condition(), self.frames)

    def accept(self):
        self.peer = self.server.nextPendingConnection()
        self.peer.readyRead.connect(self.read)

    def send(self, opcode, payload, fragmented=False):
        raw = json.dumps(payload).encode()
        frame = struct.pack('<II', opcode, len(raw)) + raw
        if fragmented:
            self.peer.write(frame[:5])
            self.peer.flush()
            self.app.processEvents()
            self.peer.write(frame[5:])
        else:
            self.peer.write(frame)
        self.peer.flush()

    def read(self):
        self.buffer.extend(bytes(self.peer.readAll()))
        while len(self.buffer) >= 8:
            opcode, size = struct.unpack('<II', self.buffer[:8])
            if len(self.buffer) < size + 8:
                return
            frame = json.loads(self.buffer[8 : 8 + size])
            del self.buffer[: 8 + size]
            self.frames.append((opcode, frame))
            if opcode == 0:
                self.send(1, {'evt': 'READY', 'data': {}}, fragmented=True)
            elif opcode == 1 and self.auto_ack:
                self.send(
                    1, {'cmd': 'SET_ACTIVITY', 'nonce': frame['nonce'], 'data': {}}
                )

    def activities(self):
        return [p['args']['activity'] for op, p in self.frames if op == 1]

    def connect(self):
        self.client.configure(True)
        self.wait(lambda: bool(self.activities()) and self.client.pending_nonce is None)

    def change(self, **values):
        count = len(self.activities())
        self.playback.update(values)
        self.client.last_sent -= 6
        self.client.publish()
        self.wait(
            lambda: len(self.activities()) > count and self.client.pending_nonce is None
        )

    def test_disabled_never_connects_and_public_application_id_is_used(self):
        QTest.qWait(30)
        self.assertFalse(self.frames)
        self.assertFalse(self.client.refresh.isActive())
        self.connect()
        self.assertEqual(self.frames[0], (0, {'v': 1, 'client_id': APPLICATION_ID}))

    def test_metadata_time_artwork_and_seek_with_slowed(self):
        self.playback['speed'] = 0.5
        self.connect()
        activity = self.activities()[-1]
        self.assertEqual(activity['type'], 2)
        self.assertEqual(activity['details'], 'Digital Love')
        self.assertEqual(activity['state'], 'Daft Punk')
        self.assertEqual(activity['assets']['large_text'], 'Discovery')
        self.assertEqual(
            activity['timestamps'], {'start': self.now - 60, 'end': self.now + 540}
        )
        self.change(position=120)
        self.assertEqual(self.activities()[-1]['timestamps']['start'], self.now - 240)

    def test_progress_coalesces_without_resending_each_second(self):
        self.connect()
        count = len(self.frames)
        for _ in range(60):
            self.now += 1
            self.playback['position'] += 1
            self.client.publish()
        self.assertEqual(len(self.frames), count)
        self.playback['title'] = 'One More Time'
        self.client.publish()
        self.assertEqual(len(self.frames), count)
        self.client.last_sent -= 6
        self.client.publish()
        self.wait(lambda: self.activities()[-1]['details'] == 'One More Time')

    def test_pause_freezes_timer_resume_and_stop_clears(self):
        self.connect()
        self.change(paused=True, paused_label='Paused')
        self.assertNotIn('timestamps', self.activities()[-1])
        self.assertEqual(self.activities()[-1]['state'], 'Paused · Daft Punk')
        self.change(paused=False)
        self.assertIn('timestamps', self.activities()[-1])
        self.change(playing=False)
        self.assertIsNone(self.activities()[-1])

    def test_disable_and_shutdown_send_clear_without_waiting(self):
        self.connect()
        start = time.monotonic()
        self.client.configure(False)
        self.assertLess(time.monotonic() - start, 0.1)
        self.wait(lambda: self.activities()[-1] is None)
        self.assertFalse(self.client.retry.isActive())
        self.assertFalse(self.client.refresh.isActive())

    def test_stop_clears_even_when_a_previous_update_has_no_ack(self):
        self.connect()
        self.auto_ack = False
        self.client.last_sent -= 6
        self.playback['title'] = 'New track'
        self.client.publish()
        self.wait(lambda: len(self.activities()) == 2)
        self.playback['playing'] = False
        self.client.publish()
        self.wait(lambda: self.activities()[-1] is None)

    def test_discord_absent_is_nonblocking_and_retries(self):
        self.server.close()
        start = time.monotonic()
        self.client.configure(True)
        self.assertLess(time.monotonic() - start, 0.1)
        self.wait(self.client.retry.isActive)
        self.assertIsNone(self.client.socket)
        self.assertFalse(self.client.ready)

    def test_fragmented_handshake_ping_and_rejected_activity(self):
        self.connect()
        self.send(3, {'test': 'ping'})
        self.wait(lambda: any(op == 4 for op, _ in self.frames))
        self.send(1, {'evt': 'ERROR', 'data': {'message': 'fixture'}})
        self.wait(self.client.retry.isActive)
        self.assertFalse(self.client.ready)

    def test_unresponsive_ack_and_oversized_frame_recover(self):
        self.connect()
        self.auto_ack = False
        self.client.last_sent -= 6
        self.playback['title'] = 'Another song'
        self.client.publish()
        self.wait(lambda: len(self.activities()) == 2)
        self.assertTrue(self.client.timeout.isActive())
        self.peer.write(struct.pack('<II', 1, 1000000))
        self.peer.flush()
        self.wait(self.client.retry.isActive)
        self.assertLess(len(self.client.buffer), 65536)

    def test_public_cover_rejects_local_private_and_credentials(self):
        for value in (
            'file:///C:/music/cover.jpg',
            'data:image/png;base64,AAAA',
            'https://127.0.0.1/a',
            'https://192.168.0.1/a',
            'https://localhost/a',
            'https://user:secret@example.com/a',
        ):
            self.assertEqual(public_cover(value), '')
        self.assertEqual(
            public_cover('https://example.com/cover.jpg?token=secret#x'),
            'https://example.com/cover.jpg',
        )

    def test_preference_is_opt_in_and_persists(self):
        from preferences import PreferenceStore

        self.assertNotIn('discord_presence_enabled', PreferenceStore.clean({}))
        self.assertFalse(
            PreferenceStore.clean({'discord_presence_enabled': False})[
                'discord_presence_enabled'
            ]
        )
        self.assertTrue(
            PreferenceStore.clean({'discord_presence_enabled': True})[
                'discord_presence_enabled'
            ]
        )
        self.assertNotIn(
            'discord_presence_enabled',
            PreferenceStore.clean({'discord_presence_enabled': 'true'}),
        )


class DesktopPresenceTests(unittest.TestCase):
    from test_qt_playback_queue import PlaybackQueueDrawerTests as Fixture

    setUp = Fixture.setUp
    tearDown = Fixture.tearDown
    settle = Fixture.settle

    def test_setting_and_snapshot_follow_current_track_and_reset_clears_opt_in(self):
        client = self.ws.discord_presence
        self.assertFalse(client.enabled)
        self.assertTrue(
            any(f['key'] == 'discord_presence_enabled' for f in self.ws.settingsFields)
        )
        self.bridge.model = dict(
            _stream={'url': 'https://example.com/audio'},
            duration=300,
            beats=[0, 300],
            neighbors=[[]],
            links=0,
            album='Discovery',
            cover_url='https://example.com/album.jpg',
        )
        self.bridge.online.position = 42
        self.bridge.playlist = [dict(id='song', record={})]
        self.bridge.queue_index = 0
        self.bridge._state.update(
            playing=True, paused=False, title='Digital Love', artist='Daft Punk'
        )
        self.ws.options.update(effectsEnabled=False, speed=85)
        snapshot = self.ws.discord_snapshot()
        self.assertEqual(snapshot['track_id'], 'song')
        self.assertEqual(snapshot['position'], 42)
        self.assertEqual(snapshot['duration'], 300)
        self.assertEqual(snapshot['speed'], 1)
        self.assertEqual(snapshot['cover_url'], 'https://example.com/album.jpg')
        client.names = ['onda-absent-' + uuid.uuid4().hex]
        self.ws.setSetting('discord_presence_enabled', True)
        self.assertTrue(client.enabled)
        self.ws.settings['discord_presence_enabled'] = False
        self.ws.settingsChanged.emit()
        self.assertFalse(client.enabled)
        self.assertFalse(client.refresh.isActive())
        self.bridge._state['playing'] = False
