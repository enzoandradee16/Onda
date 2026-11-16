import os
from pathlib import Path
import tempfile
import unittest

from playback_cache_budget import mark_played, model_paths, prune


class PlaybackBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def track(self, index, played=0):
        path = self.root / f'{index:064x}'
        path.mkdir()
        (path / 'audio.wav').write_bytes(b'x' * 100)
        (path / 'analysis.json').write_text('{}')
        if played:
            mark_played(path)
        for child in path.iterdir():
            os.utime(child, (played or index, played or index))
        os.utime(path, (index, index))
        return path

    def trim(self, **kwargs):
        return prune(self.root, now=10000, grace=0, **kwargs)

    def test_current_and_three_previous_survive_new_prefetches(self):
        tracks = [self.track(i, played=i) for i in range(1, 7)]
        ahead = self.track(7)
        result = self.trim(max_bytes=0, protected=[ahead])
        self.assertFalse(tracks[0].exists())
        self.assertFalse(tracks[1].exists())
        self.assertTrue(all(p.exists() for p in tracks[2:] + [ahead]))
        self.assertTrue(result['over_budget'])

    def test_active_analysis_and_stream_are_never_removed(self):
        import jukebox
        import progressive_audio_cache as streaming
        active = self.track(1)
        stream_root = self.root / 'streaming'
        stream_root.mkdir()
        stream = stream_root / ('a' * 64 + '.12345678')
        stream.mkdir()
        (stream / 'audio.pcm').write_bytes(b'x' * 100)
        old = self.track(2)
        jukebox._active[str(active.resolve())] += 1
        streaming._active[stream.resolve()] += 1
        try:
            self.trim(max_bytes=0)
            self.assertTrue(active.exists())
            self.assertTrue(stream.exists())
            self.assertFalse(old.exists())
        finally:
            jukebox._active.pop(str(active.resolve()))
            streaming._active.pop(stream.resolve())

    def test_whole_group_eviction_preserves_unknown_and_source_files(self):
        old = self.track(1)
        (old / 'effects-85-25-False.wav').write_bytes(b'x' * 100)
        os.utime(old / 'effects-85-25-False.wav', (1, 1))
        os.utime(old, (1, 1))
        source = self.root / 'music.mp3'
        source.write_bytes(b'original')
        unknown = self.root / 'accounts'
        unknown.mkdir()
        (unknown / 'secret').write_text('preserve')
        self.trim(max_bytes=0)
        self.assertFalse(old.exists())
        self.assertEqual(source.read_bytes(), b'original')
        self.assertTrue((unknown / 'secret').exists())

    def test_protected_source_protects_entire_group(self):
        track = self.track(1)
        self.trim(max_bytes=0, protected=model_paths([{'source': str(track / 'audio.wav')}]))
        self.assertTrue(track.exists())

    def test_handoff_grace_and_unknown_nested_directories(self):
        fresh = self.track(1)
        os.utime(fresh, (9990, 9990))
        unknown = self.track(2)
        (unknown / 'nested').mkdir()
        prune(self.root, max_bytes=0, now=10000)
        self.assertTrue(fresh.exists())
        self.assertTrue(unknown.exists())

    def test_packet_cache_recent_history_survives(self):
        root = self.root / 'stream-files'
        root.mkdir()
        paths = []
        for i in range(6):
            path = root / (f'{i:064x}.mka')
            path.write_bytes(b'x' * 100)
            mark_played(path)
            marker = path.with_name(path.name + '.played')
            os.utime(path, (1, 1))
            os.utime(marker, (i + 1, i + 1))
            paths.append(path)
        self.trim(max_bytes=0)
        self.assertFalse(paths[0].exists())
        self.assertFalse(paths[1].exists())
        self.assertTrue(all(p.exists() for p in paths[2:]))

    def test_failed_session_does_not_leave_active_pin(self):
        import jukebox
        from unittest.mock import patch
        track = self.track(1)
        with patch('jukebox.cache_root', return_value=self.root):
            with self.assertRaises((ValueError, KeyError)):
                jukebox.Session(track)
        self.assertNotIn(str(track.resolve()), jukebox._active)

    def test_effect_worker_pins_cache_even_when_render_fails(self):
        import jukebox
        from playback_effects import PreparedEffects
        from unittest.mock import patch
        track = self.track(1)
        effects = PreparedEffects(track)

        def render():
            self.trim(max_bytes=0)
            self.assertTrue(track.exists())
            raise ValueError('render failed')

        with patch.object(effects, '_render', side_effect=render):
            with self.assertRaises(ValueError):
                effects._work()
        self.assertNotIn(str(track.resolve()), jukebox._active)

    def test_stream_local_limit_also_preserves_recent_tracks(self):
        from progressive_audio_cache import prune as stream_prune
        from unittest.mock import patch
        root = self.root / 'streaming'
        root.mkdir()
        paths = []
        for i in range(6):
            path = root / (f'{i:064x}.12345678')
            path.mkdir()
            (path / 'audio.pcm').write_bytes(b'x' * 100)
            mark_played(path)
            os.utime(path / '.played', (i + 1, i + 1))
            os.utime(path, (i + 1, i + 1))
            paths.append(path)
        with patch('progressive_audio_cache.LIMIT', 0):
            stream_prune(root)
        self.assertFalse(paths[0].exists())
        self.assertFalse(paths[1].exists())
        self.assertTrue(all(p.exists() for p in paths[2:]))


if __name__ == '__main__':
    unittest.main()
