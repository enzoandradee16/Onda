import unittest
from unittest.mock import patch
from playlist_import import load_interactive_playlist


class LargeCollectionTests(unittest.TestCase):
    def test_album_enumeration_and_payload_are_bounded_before_ui(self):
        for playback, cap in ((False, 5000), (True, 5000)):
            with (
                self.subTest(playback=playback),
                patch(
                    'playlist_import.load_playlist',
                    return_value={'tracks': [{'title': 'Song'} for _ in range(6000)]},
                ) as load,
            ):
                result = load_interactive_playlist(
                    'https://example.com/album', object(), 5000, playback=playback
                )
                self.assertEqual(load.call_args.kwargs['limit'], cap)
                self.assertEqual(len(result['tracks']), cap)
                self.assertIn('Limite configurado', result['note'])

    def test_lower_configured_limit_is_respected_and_cancel_remains_available(self):
        with patch(
            'playlist_import.load_playlist', return_value={'tracks': []}
        ) as load:
            load_interactive_playlist('url', object(), 100, playback=True)
            self.assertEqual(load.call_args.kwargs['limit'], 100)
            with self.assertRaises(ValueError):
                load_interactive_playlist('url', object(), 100, cancelled=lambda: True)
