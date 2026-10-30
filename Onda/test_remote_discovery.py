"""Discovery advertises an endpoint, never pairing secrets or music metadata."""

import json
import unittest

from remote_discovery import discovery_reply


class DiscoveryTests(unittest.TestCase):
    def test_matching_nonce_and_public_device_fields(self):
        request = json.dumps(dict(type='onda-discover', nonce='a' * 32)).encode()
        result = json.loads(discovery_reply(request, '192.168.1.2', 12345, 'Desktop'))
        self.assertEqual(
            result,
            dict(
                type='onda-device',
                nonce='a' * 32,
                port=12345,
                name='Desktop',
                protocol=1,
            ),
        )

    def test_invalid_request_or_non_local_sender_does_not_get_a_response(self):
        valid = json.dumps(dict(type='onda-discover', nonce='a' * 32)).encode()
        for address in ('8.8.8.8', '127.0.0.1', '::1', 'invalid'):
            self.assertIsNone(discovery_reply(valid, address, 12345, 'Desktop'))
        for request in (b'broken', b'[]', b'{}', b'{"type":"onda-discover","nonce":2}'):
            self.assertIsNone(discovery_reply(request, '192.168.1.2', 12345, 'Desktop'))
