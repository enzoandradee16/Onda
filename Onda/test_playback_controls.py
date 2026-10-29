import unittest, threading
from array import array
from playback_controls import SleepTimer, fade_pcm
from queue_undo import QueueUndo
from silence import bounds


class PlaybackControlTests(unittest.TestCase):
    def test_sleep_fades_only_at_end_and_cancel_restores_gain(self):
        now = [100.0]
        timer = SleepTimer(lambda: now[0])
        timer.arm(60)
        self.assertEqual(timer.gain(), 1)
        now[0] = 152.5
        self.assertAlmostEqual(timer.gain(), 0.5)
        now[0] = 160
        self.assertEqual(timer.gain(), 0)
        timer.cancel()
        self.assertEqual(timer.gain(), 1)

    def test_pcm_fade_is_smooth_and_preserves_stereo(self):
        data = array('h', [10000, -10000] * 100).tobytes()
        result = array('h')
        result.frombytes(fade_pcm(data, 1, 0))
        self.assertEqual(len(result), 200)
        self.assertEqual(result[-2:], array('h', [0, 0]))
        self.assertGreater(result[0], 9000)
        self.assertTrue(all(result[i] >= result[i + 2] for i in range(0, 196, 2)))
        self.assertEqual(data, array('h', [10000, -10000] * 100).tobytes())

    def test_undo_restores_removed_jobs_without_rewinding_live_downloads(self):
        a = {'id': 'a', 'state': 'Na fila', 'percent': 0}
        b = {'id': 'b', 'state': 'Em andamento', 'percent': 10}
        history = QueueUndo()
        history.remember([a, b], 'remove', ['a'])
        b['percent'] = 85
        c = {'id': 'c', 'state': 'Na fila', 'percent': 0}
        result = history.restore([b, c], {'b': {'cancel': threading.Event()}})
        self.assertEqual([job['id'] for job in result], ['a', 'b', 'c'])
        self.assertEqual(result[1]['percent'], 85)

    def test_undo_cancel_waits_for_worker_and_is_bounded(self):
        history = QueueUndo(2)
        original = {'id': 'a', 'state': 'Em andamento', 'percent': 10}
        for _ in range(3):
            history.remember([original], 'cancel_all', ['a'])
        self.assertEqual(len(history.entries), 2)
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(ValueError):
            history.restore([original], {'a': {'cancel': cancel}})
        restored = history.restore([dict(original, state='Cancelado')], {})
        self.assertEqual(restored[0]['state'], 'Na fila')

    def test_silence_bounds_keep_internal_pauses_and_handle_all_silent(self):
        result = bounds(
            'silence_start: 0\nsilence_end: 1\nsilence_start: 2\nsilence_end: 2.5\nsilence_start: 4\nsilence_end: 5',
            5,
        )
        self.assertEqual((result['start'], result['end']), (1, 4))
        self.assertEqual(len(result['intervals']), 3)
        silent = bounds('silence_start: 0', 5)
        self.assertTrue(silent['silent'])
        self.assertEqual((silent['start'], silent['end']), (0, 5))

    def test_detection_cancellation_does_not_start_a_process(self):
        from unittest.mock import patch
        from silence import detect

        with patch('silence.subprocess.run') as probe:
            with self.assertRaises(InterruptedError):
                detect('unused.wav', cancelled=lambda: True)
            probe.assert_not_called()

    def test_undo_preserves_download_that_finishes_while_being_removed(self):
        history = QueueUndo()
        job = {'id': 'a', 'state': 'Em andamento', 'percent': 50}
        history.remember([job], 'remove', ['a'])
        history.record_finished_removal(dict(job, state='Cancelado'), True)
        restored = history.restore([], {})
        self.assertEqual(restored[0]['state'], 'Concluído')
        self.assertEqual(restored[0]['percent'], 100)
