"""Real loopback protocol tests; no audio or access to personal preferences."""

import http.client
import json
import unittest
from remote_control import RemoteServer, local_address


class RemoteControlTests(unittest.TestCase):
    def setUp(self):
        self.server = RemoteServer('127.0.0.1')
        self.server.start()
        self.addCleanup(self.server.close)
        self.token = ''

    def request(self, path, body=None, headers=None):
        connection = http.client.HTTPConnection(
            '127.0.0.1', self.server.port, timeout=3
        )
        try:
            actual = {'Content-Type': 'application/json'}
            if self.token:
                actual['Authorization'] = 'Bearer ' + self.token
            actual.update(headers or {})
            connection.request(
                'GET' if body is None else 'POST',
                path,
                None if body is None else json.dumps(body),
                actual,
            )
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def pair(self):
        status, result = self.request('/v1/pair', {'code': self.server.code})
        self.assertEqual(status, 200)
        self.token = result['token']

    def test_state_and_commands_require_pairing(self):
        self.assertEqual(self.request('/v1/state')[0], 401)
        self.assertEqual(self.request('/v1/command', {'command': 'toggle'})[0], 401)
        self.assertTrue(self.server.commands.empty())

    def test_effects_search_and_stable_queue_moves_are_validated(self):
        self.pair()
        valid = [
            ('effects', {'speed': 85, 'reverb': 25, 'enabled': True}),
            ('jukebox', {'variation': 40, 'normal': False}),
            ('search', 'Artist song'),
            ('search_add', 'result-id'),
        ]
        for name, value in valid:
            self.assertEqual(
                self.request('/v1/command', {'command': name, 'value': value})[0], 202
            )
            self.assertEqual(self.server.commands.get_nowait(), (name, value))
        invalid = [
            ('effects', {'speed': True}),
            ('effects', {'speed': 151}),
            ('effects', {'reverb': float('nan')}),
            ('effects', {'enabled': 1}),
            ('effects', {'source': 'private.wav'}),
            ('effects', {}),
            ('jukebox', {'normal': 'false'}),
            ('jukebox', {'variation': -1}),
            ('search', ''),
            ('search', 'x' * 501),
            ('search_add', {'source': 'private.wav'}),
        ]
        for name, value in invalid:
            self.assertEqual(
                self.request('/v1/command', {'command': name, 'value': value})[0], 400
            )
        self.assertTrue(self.server.commands.empty())
        self.assertEqual(
            self.request(
                '/v1/command',
                {'command': 'queue_move_to', 'track_id': 'first', 'value': 'second'},
            )[0],
            202,
        )
        self.assertEqual(
            self.server.commands.get_nowait(),
            ('queue_move_to', {'track_id': 'first', 'value': 'second'}),
        )

    def test_playback_order_commands_validate_their_values(self):
        self.pair()
        for name, value in (('shuffle', True), ('repeat', 'Uma')):
            self.assertEqual(
                self.request('/v1/command', {'command': name, 'value': value})[0], 202
            )
            self.assertEqual(self.server.commands.get_nowait(), (name, value))
        for name, value in (
            ('shuffle', 1),
            ('shuffle', 'true'),
            ('repeat', 'invalid'),
            ('repeat', None),
        ):
            self.assertEqual(
                self.request('/v1/command', {'command': name, 'value': value})[0], 400
            )
        self.assertTrue(self.server.commands.empty())

    def test_pairing_returns_only_public_snapshot_and_queues_supported_commands(self):
        self.server.update({'protocol': 1, 'title': 'Faixa de teste', 'playing': True})
        self.pair()
        status, state = self.request('/v1/state')
        self.assertEqual(status, 200)
        self.assertEqual(state['title'], 'Faixa de teste')
        self.assertNotIn('token', state)
        for name in ('toggle', 'next', 'previous'):
            self.assertEqual(self.request('/v1/command', {'command': name})[0], 202)
            self.assertEqual(self.server.commands.get_nowait(), (name, None))
        self.assertEqual(
            self.request('/v1/command', {'command': 'volume', 'value': 23})[0], 202
        )
        self.assertEqual(self.server.commands.get_nowait(), ('volume', 23))

    def test_invalid_credentials_and_browser_origins_are_rejected(self):
        self.assertEqual(self.request('/v1/pair', {'code': 'wrong'})[0], 401)
        self.assertEqual(self.request('/v1/pair', {'code': '\u2603'})[0], 401)
        self.assertEqual(
            self.request(
                '/v1/pair',
                {'code': self.server.code},
                {'Origin': 'https://example.com'},
            )[0],
            403,
        )
        self.assertFalse(self.server.paired)

    def test_pairing_attempts_are_limited(self):
        for _ in range(5):
            self.assertEqual(self.request('/v1/pair', {'code': 'wrong'})[0], 401)
        self.assertEqual(self.request('/v1/pair', {'code': self.server.code})[0], 429)

    def test_arbitrary_operations_and_invalid_volumes_are_rejected(self):
        self.pair()
        for command in (
            {'command': 'open_file', 'path': 'anything'},
            {'command': 'volume', 'value': -1},
            {'command': 'volume', 'value': 101},
            {'command': 'volume', 'value': True},
            {'command': 'volume', 'value': 2.5},
        ):
            self.assertEqual(self.request('/v1/command', command)[0], 400)
        self.assertTrue(self.server.commands.empty())

    def test_command_queue_is_bounded(self):
        self.pair()
        for _ in range(32):
            self.server.commands.put_nowait(('toggle', None))
        self.assertEqual(self.request('/v1/command', {'command': 'next'})[0], 429)

    def test_new_sessions_reject_previous_credentials(self):
        self.pair()
        other = RemoteServer('127.0.0.1')
        other.start()
        try:
            self.assertNotEqual(self.server.token, other.token)
            connection = http.client.HTTPConnection('127.0.0.1', other.port, timeout=3)
            connection.request(
                'GET', '/v1/state', headers={'Authorization': 'Bearer ' + self.token}
            )
            self.assertEqual(connection.getresponse().status, 401)
            connection.close()
        finally:
            other.close()

    def test_only_private_ipv4_and_loopback_are_allowed(self):
        for address in ('10.1.2.3', '172.16.2.1', '192.168.0.3', '127.0.0.1'):
            self.assertTrue(local_address(address))
        for address in ('8.8.8.8', '172.32.1.1', '::1', 'invalid'):
            self.assertFalse(local_address(address))

    def test_queue_pagination_and_revisions_use_the_cached_public_rows(self):
        rows = [dict(id=str(i), title=f'Track {i}') for i in range(205)]
        self.server.update_queue(rows)
        self.pair()
        status, first = self.request('/v1/queue')
        self.assertEqual(status, 200)
        self.assertEqual(first['total'], 205)
        self.assertEqual(len(first['rows']), 100)
        status, last = self.request('/v1/queue?offset=200')
        self.assertEqual(status, 200)
        self.assertEqual(
            [row['id'] for row in last['rows']], ['200', '201', '202', '203', '204']
        )
        self.assertEqual(first['revision'], last['revision'])
        self.server.update_queue(rows[:3])
        self.assertGreater(self.request('/v1/queue')[1]['revision'], first['revision'])
        self.assertEqual(self.request('/v1/queue?offset=-1')[0], 400)

    def test_seek_and_queue_commands_validate_stable_id_and_finite_values(self):
        self.pair()
        for body in (
            {'command': 'seek', 'value': 12},
            {'command': 'seek', 'track_id': 'song', 'value': float('nan')},
            {'command': 'seek', 'track_id': 'song', 'value': float('inf')},
            {'command': 'queue_move', 'track_id': 'song', 'value': 9},
            {'command': 'queue_remove', 'track_id': ''},
        ):
            self.assertEqual(self.request('/v1/command', body)[0], 400)
        self.assertEqual(
            self.request(
                '/v1/command', {'command': 'seek', 'track_id': 'song', 'value': 12.5}
            )[0],
            202,
        )
        self.assertEqual(
            self.server.commands.get_nowait(),
            ('seek', {'track_id': 'song', 'value': 12.5}),
        )

    def test_artwork_is_authenticated_and_only_the_current_image_is_available(self):
        self.server.update_artwork('current', b'jpeg-content')
        self.assertEqual(self.request('/v1/artwork?id=current')[0], 401)
        self.pair()
        self.assertEqual(self.request('/v1/artwork?id=old')[0], 404)
        connection = http.client.HTTPConnection(
            '127.0.0.1', self.server.port, timeout=3
        )
        try:
            connection.request(
                'GET',
                '/v1/artwork?id=current',
                headers={'Authorization': 'Bearer ' + self.token},
            )
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader('Content-Type'), 'image/jpeg')
            self.assertEqual(response.read(), b'jpeg-content')
        finally:
            connection.close()
