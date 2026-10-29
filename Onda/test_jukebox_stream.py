import unittest
from array import array
from unittest.mock import patch
from jukebox import RATE
from jukebox_stream import Stream


class FakeSession:
    instances = []

    def __init__(self, cache):
        if cache == 'bad':
            raise ValueError('Missing cache')
        self.cache = cache
        self.index = 0
        self.closed = False
        self.instances.append(self)

    def seek(self, index):
        self.index = index

    def chunk(self, *args, **kwargs):
        frames = RATE // 4 if self.cache == 'old' else RATE * 3 // 10
        level = 1000 if self.cache == 'old' else 3000
        index = self.index
        self.index += 1
        return dict(
            pcm=array('h', [level, level] * frames).tobytes(),
            index=index,
            next=index + 1,
            jumped=False,
            jumps=0,
            seconds=frames / RATE,
        )

    def close(self):
        self.closed = True


class CrossfadeTests(unittest.TestCase):
    def setUp(self):
        FakeSession.instances = []
        self.patch = patch('jukebox_stream.Session', FakeSession)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_resume_starts_inside_the_saved_beat_not_at_its_beginning(self):
        stream = Stream('old')
        try:
            self.assertTrue(stream.seek(3, phase=0.5))
            first = stream.chunk()
            self.assertEqual(first['index'], 3)
            self.assertAlmostEqual(first['phase_start'], 0.5, delta=1 / (RATE // 4))
            self.assertAlmostEqual(first['seconds'], 0.125, delta=1 / RATE)
            second = stream.chunk()
            self.assertEqual(second['index'], 4)
            self.assertEqual(second['phase_start'], 0)
        finally:
            stream.close()

    def test_seek_from_previous_track_cannot_seek_incoming_song(self):
        stream = Stream('old')
        stream.chunk()
        stream.switch('new', 1)
        try:
            self.assertFalse(stream.seek(100, expected_cache='old'))
            self.assertTrue(stream.transitioning)
            self.assertEqual(stream.incoming.session.index, 0)
            self.assertTrue(stream.seek(3, expected_cache='new'))
            self.assertFalse(stream.transitioning)
            self.assertEqual(stream.current.session.index, 3)
        finally:
            stream.close()

    def test_overlap_has_both_tracks_without_gap_and_keeps_incoming_position(self):
        stream = Stream('old')
        stream.chunk()
        stream.switch('new', 1)
        parts = []
        while stream.transitioning:
            parts.append(stream.chunk())
        samples = array('h', b''.join(p['pcm'] for p in parts))
        self.assertEqual(len(samples), RATE * 2)
        self.assertGreaterEqual(min(samples), 1000)
        self.assertLessEqual(max(samples), 3000)
        self.assertAlmostEqual(samples[RATE], 2000, delta=2)
        self.assertEqual(samples[-1], 3000)
        self.assertEqual(sum('track_changed' in p for p in parts), 1)
        self.assertTrue(FakeSession.instances[0].closed)
        self.assertFalse(FakeSession.instances[1].closed)
        # Incoming 300 ms beats: 1 s consumed, so continue 100 ms into beat 3.
        next_part = stream.chunk()
        self.assertEqual(next_part['index'], 3)
        self.assertAlmostEqual(next_part['phase_start'], 1 / 3)
        self.assertEqual(sum(p['edge_completed'] for p in parts), 3)
        stream.close()
        self.assertTrue(FakeSession.instances[1].closed)

    def test_disabled_transition_switches_without_crossfade(self):
        stream = Stream('old')
        stream.switch('new', 0)
        part = stream.chunk()
        self.assertFalse(stream.transitioning)
        self.assertEqual(set(array('h', part['pcm'])), {3000})
        self.assertEqual(part['track_changed'], 'new')
        self.assertNotIn('track_changed', stream.chunk())
        stream.close()

    def test_failed_next_track_keeps_current_session(self):
        stream = Stream('old')
        with self.assertRaises(ValueError):
            stream.switch('bad', 2)
        self.assertEqual(set(array('h', stream.chunk()['pcm'])), {1000})
        stream.close()

    def test_duration_in_seconds_controls_exact_overlap_frame_count(self):
        for seconds in (1, 2, 7, 10):
            stream = Stream('old')
            stream.switch('new', seconds)
            frames = 0
            while stream.transitioning:
                frames += len(stream.chunk()['pcm']) // 4
            self.assertEqual(frames, RATE * seconds)
            stream.close()
