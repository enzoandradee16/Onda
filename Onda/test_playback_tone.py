"""Independent tone transposition, cache isolation and original-file preservation."""

import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave
from unittest.mock import patch

from audio_tools import effects_filter
from effects_export import export_config
from playback_effects import PreparedEffects, active, clean


class ToneOptionsTests(unittest.TestCase):
    def test_independent_tone_and_neutral_defaults(self):
        self.assertEqual(effects_filter(), 'anull')
        self.assertFalse(active({'enabled': False, 'speed': 50, 'reverb': 100}))
        self.assertTrue(active({'enabled': False, 'pitch_shift': 3}))
        self.assertEqual(clean({'pitch_shift': 99})['pitch_shift'], 12)
        self.assertEqual(clean({'pitch_shift': -99})['pitch_shift'], -12)
        self.assertEqual(clean({})['pitch_shift'], 0)

    def test_pitch_filter_rejects_invalid_ranges(self):
        for value in (-13, 13, float('nan'), float('inf')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                effects_filter(pitch_shift=value)

    def test_export_keeps_tone_when_slowed_is_disabled(self):
        with patch('audio_library.read_audio', return_value={}):
            value = export_config(
                'source.wav', enabled=False, speed=70, reverb=50, pitch_shift=4
            )
        self.assertEqual(value['speed'], 100)
        self.assertEqual(value['reverb'], 0)
        self.assertEqual(value['pitch_shift'], 4)
        self.assertIn('Tom +4 st', value['export_name'])
        self.assertNotIn('Slowed', value['export_name'])


@unittest.skipUnless(os.environ.get('ONDA_FFMPEG'), 'FFmpeg integration')
class ToneAudioTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ffmpeg = str(Path(os.environ['ONDA_FFMPEG']) / 'ffmpeg.exe')
        self.source = self.root / 'tone.wav'
        self.run_audio(
            [
                '-f',
                'lavfi',
                '-i',
                'sine=frequency=440:duration=5:sample_rate=44100',
                '-ac',
                '2',
                str(self.source),
            ]
        )
        self.original = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def run_audio(self, args):
        subprocess.run(
            [self.ffmpeg, '-y', '-v', 'error', *args],
            capture_output=True,
            check=True,
            timeout=30,
        )

    def measure(self, path):
        from test_playback_pitch import measured_frequency

        with wave.open(str(path), 'rb') as audio:
            duration = audio.getnframes() / audio.getframerate()
            audio.setpos(audio.getframerate())
            frequency = measured_frequency(
                audio.readframes(audio.getframerate() * 2), rate=audio.getframerate()
            )
        return duration, frequency

    def test_actual_frequency_and_duration_at_independent_speeds(self):
        for shift, speed, keep_pitch in [
            (-12, 100, False),
            (12, 100, False),
            (5, 85, True),
            (5, 85, False),
        ]:
            with self.subTest(shift=shift, speed=speed, keep_pitch=keep_pitch):
                output = self.root / f'{shift}-{speed}-{keep_pitch}.wav'
                self.run_audio(
                    [
                        '-i',
                        str(self.source),
                        '-af',
                        effects_filter(speed, 0, keep_pitch, shift),
                        '-ar',
                        '44100',
                        '-ac',
                        '2',
                        str(output),
                    ]
                )
                duration, frequency = self.measure(output)
                self.assertAlmostEqual(duration, 5 * 100 / speed, delta=0.08)
                expected = 440 * 2 ** (shift / 12) * (1 if keep_pitch else speed / 100)
                self.assertAlmostEqual(frequency, expected, delta=1)
        self.assertEqual(
            hashlib.sha256(self.source.read_bytes()).hexdigest(), self.original
        )

    def test_prepared_tone_has_a_distinct_cache_and_can_return_to_original(self):
        folder = self.root / 'cache'
        folder.mkdir()
        (folder / 'audio.wav').write_bytes(self.source.read_bytes())
        settings = dict(enabled=False, speed=70, reverb=50, pitch_shift=12)
        with patch.dict(os.environ, {'ONDA_FFMPEG': os.environ['ONDA_FFMPEG']}):
            prepared = PreparedEffects(folder)
            self.addCleanup(prepared.close)
            key = prepared.configure(settings)
            prepared.thread.join(30)
            self.assertEqual(prepared.error, '')
            self.assertEqual(prepared.ready, key)
            self.assertEqual(key, (100, 0, False, 12))
            self.assertAlmostEqual(self.measure(prepared.path(key))[1], 880, delta=1)
            self.assertIsNone(prepared.configure(dict(settings, pitch_shift=0)))
            self.assertEqual(prepared.path(None), folder / 'audio.wav')
            self.assertEqual(
                hashlib.sha256((folder / 'audio.wav').read_bytes()).hexdigest(),
                self.original,
            )

    def test_export_renders_tone_without_changing_speed_or_source(self):
        from effects_worker import render

        config = export_config(
            self.source, enabled=False, speed=65, reverb=50, pitch_shift=-12
        )
        output = self.root / 'export.wav'
        config.update(output=str(output), ffmpeg=os.environ['ONDA_FFMPEG'])
        with patch('effects_worker.emit'):
            render(config)
        duration, frequency = self.measure(output)
        self.assertAlmostEqual(duration, 5, delta=0.08)
        self.assertAlmostEqual(frequency, 220, delta=1)
        self.assertEqual(
            hashlib.sha256(self.source.read_bytes()).hexdigest(), self.original
        )
