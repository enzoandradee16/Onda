import tempfile, unittest, json
from pathlib import Path
from metadata_badges import provider, _tinted


class MetadataBadgeTests(unittest.TestCase):
    def test_only_metadata_provider_is_used(self):
        self.assertEqual(
            provider(
                {'platform': 'Spotify', 'source_url': 'https://youtube.com/watch?v=x'}
            ),
            'spotify',
        )
        for name in ('iTunes', 'Apple / iTunes', 'AppleMusic', 'Apple Music'):
            self.assertEqual(provider({'platform': name}), 'apple_music')
        self.assertEqual(provider({'platform': 'MusicBrainz'}), 'musicbrainz')
        self.assertEqual(provider({'url': 'https://spotify.com/track/x'}), '')
        self.assertEqual(provider({'platform': 'unknown'}), '')

    def test_icons_are_transparent_monochrome_and_tinted(self):
        for key in (
            'spotify',
            'deezer',
            'apple_music',
            'musicbrainz',
            'youtube',
            'tidal',
            'qobuz',
            'bandcamp',
        ):
            image = _tinted(key, (12, 34, 56))
            self.assertEqual(image.size, (24, 24))
            self.assertTrue(any(p[3] == 0 for p in image.get_flattened_data()))
            self.assertEqual(
                {p[:3] for p in image.get_flattened_data() if p[3]}, {(12, 34, 56)}
            )

    def test_history_origin_reads_catalog_not_audio_source(self):
        from history_details import _cached_details

        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'audio.mp3'
            path.write_bytes(b'not tagged')
            Path(str(path) + '.metadata.json').write_text(
                json.dumps(
                    {
                        'catalog': {'platform': 'Deezer'},
                        'audio_source': 'https://youtube.com/watch?v=x',
                    }
                )
            )
            result = _cached_details(str(path), 1, 10)
            self.assertEqual(result['platform'], 'Deezer')
