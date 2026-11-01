"""Measure actual PCM pitch across decoding and effect enable/disable cycles."""

from array import array
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave
from unittest.mock import patch


def measured_frequency(pcm, rate=44100):
    samples = array('h')
    samples.frombytes(pcm)
    mono = samples[::2]
    crossings = [
        i - 1 + (-mono[i - 1]) / (mono[i] - mono[i - 1])
        for i in range(1, len(mono))
        if mono[i - 1] <= 0 < mono[i]
    ]
    return (len(crossings) - 1) * rate / (crossings[-1] - crossings[0])


@unittest.skipUnless(os.environ.get('ONDA_FFMPEG'), 'FFmpeg integration')
class PlaybackPitchTests(unittest.TestCase):
    def test_100_percent_preserves_pitch_and_neutral_pcm_for_both_pitch_modes(self):
        from audio_tools import executable
        from jukebox import prepare, Session

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {'ONDA_ALIAS_CACHE_ROOT': directory}),
        ):
            source = Path(directory) / 'tone.wav'
            subprocess.run(
                [
                    executable('ffmpeg'),
                    '-y',
                    '-v',
                    'error',
                    '-f',
                    'lavfi',
                    '-i',
                    'sine=frequency=440:duration=4:sample_rate=48000',
                    str(source),
                ],
                check=True,
                capture_output=True,
            )
            model = prepare(source, os.environ['ONDA_FFMPEG'])
            with wave.open(str(Path(model['cache']) / 'audio.wav'), 'rb') as sound:
                original = sound.readframes(sound.getnframes())
            for keep_pitch in (False, True):
                for reverb in (0, 25, 50):
                    with self.subTest(keep_pitch=keep_pitch, reverb=reverb):
                        session = Session(model['cache'])
                        settings = dict(
                            enabled=True,
                            speed=100,
                            reverb=reverb,
                            keep_pitch=keep_pitch,
                        )
                        try:
                            session.effects.configure(settings)
                            if session.effects.thread:
                                session.effects.thread.join(30)
                            self.assertFalse(session.effects.error)
                            parts = []
                            while True:
                                part = session.chunk(0, 0, 100, True, effects=settings)
                                parts.append(part['pcm'])
                                if part['finished']:
                                    break
                            pcm = b''.join(parts)
                            # Both dry and reverberated playback retain a 4 s
                            # timeline and the original 440 Hz fundamental.
                            self.assertEqual(len(pcm), len(original))
                            self.assertAlmostEqual(
                                measured_frequency(pcm[88200 * 4 : 132300 * 4]),
                                440,
                                delta=0.1,
                            )
                            if not reverb:
                                self.assertEqual(pcm, original)
                                self.assertIsNone(session.effect_key)
                        finally:
                            session.close()

    def test_original_pitch_survives_resampling_and_disabling_slowed(self):
        from audio_tools import executable
        from jukebox import prepare, Session

        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(os.environ, {'ONDA_ALIAS_CACHE_ROOT': directory}),
        ):
            for rate in (44100, 48000, 96000):
                with self.subTest(sample_rate=rate):
                    source = Path(directory) / f'tone-{rate}.wav'
                    subprocess.run(
                        [
                            executable('ffmpeg'),
                            '-y',
                            '-v',
                            'error',
                            '-f',
                            'lavfi',
                            '-i',
                            f'sine=frequency=440:duration=4:sample_rate={rate}',
                            str(source),
                        ],
                        check=True,
                        capture_output=True,
                    )
                    model = prepare(source, os.environ['ONDA_FFMPEG'])
                    session = Session(model['cache'])
                    dry = dict(enabled=False, speed=85, reverb=25, keep_pitch=False)
                    wet = dict(dry, enabled=True, reverb=0)

                    def render(settings):
                        session.seek(0)
                        parts = []
                        while True:
                            part = session.chunk(0, 0, 100, True, effects=settings)
                            parts.append(part['pcm'])
                            if part['finished']:
                                break
                        return b''.join(parts)[4410 * 4 :]

                    try:
                        self.assertAlmostEqual(
                            measured_frequency(render(dry)), 440, delta=0.1
                        )
                        session.effects.configure(wet)
                        if session.effects.thread:
                            session.effects.thread.join(30)
                        self.assertFalse(session.effects.error)
                        self.assertAlmostEqual(
                            measured_frequency(render(wet)), 374, delta=0.2
                        )
                        # Original must bypass the old slowed cache immediately,
                        # even if no new rendering worker can start.
                        original = dict(wet, speed=100, reverb=0)
                        with patch('playback_effects.threading.Thread') as worker:
                            worker.return_value.is_alive.return_value = False
                            self.assertAlmostEqual(
                                measured_frequency(render(original)), 440, delta=0.1
                            )
                            worker.assert_not_called()
                        self.assertIsNone(session.effect_key)
                        self.assertAlmostEqual(
                            measured_frequency(render(dry)), 440, delta=0.1
                        )
                        self.assertIsNone(session.effect_key)
                    finally:
                        session.close()
