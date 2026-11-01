"""Real native effects and dry PCM checks, isolated from the user's music."""

import json
import math
import tempfile
import threading
import time
import wave
from array import array
from pathlib import Path
from unittest.mock import patch


def verify():
    from jukebox import Session, cache_root, prepare
    from playback_effects import PreparedEffects

    cache_root().mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='continuity-', dir=cache_root()) as folder:
        source = Path(folder) / 'tone.wav'
        samples = array('h')
        for i in range(44100 * 8):
            value = round(math.sin(i * 2 * math.pi * 440 / 44100) * 5000)
            samples.extend((value, value))
        with wave.open(str(source), 'wb') as sound:
            sound.setparams((2, 2, 44100, 0, 'NONE', ''))
            sound.writeframes(samples.tobytes())
        model = prepare(source)
        # A repeat run must exercise a cold render, not yesterday's ready fixture.
        (Path(model['cache']) / 'effects-85-25-False.wav').unlink(missing_ok=True)
        player = Session(model['cache'])
        gate = threading.Event()
        original_work = PreparedEffects._work
        effects = dict(enabled=True, speed=85, reverb=25, keep_pitch=False)

        def delayed(owner):
            gate.wait(10)
            original_work(owner)

        try:
            player.fade_in = 0
            with patch.object(PreparedEffects, '_work', delayed):
                pending = player.chunk(45, 0, 100, True, effects=effects)
                assert pending['effects_pending']
                assert pending['pcm'] == samples.tobytes()[: len(pending['pcm'])]
            player.seek(0)
            player.fade_in = 0
            dry = player.chunk(45, 0, 100, True, effects=dict(enabled=False))
            assert not dry['effects_pending']
            assert player.effect_key is None
            assert dry['pcm'] == samples.tobytes()[: len(dry['pcm'])]
            gate.set()
            player.effects.thread.join(15)
            player.seek(0)
            player.chunk(45, 0, 100, True, effects=effects)
            deadline = time.monotonic() + 20
            while player.effects.thread.is_alive() and time.monotonic() < deadline:
                time.sleep(0.02)
            assert not player.effects.error, player.effects.error
            player.seek(0)
            wet = player.chunk(45, 0, 100, True, effects=effects)
            assert not wet['effects_pending']
            assert player.effect_key == (85, 25, False)
            player.seek(0)
            player.fade_in = 0
            neutral = player.chunk(
                45, 0, 100, True, effects=dict(enabled=True, speed=100, reverb=0)
            )
            assert player.effect_key is None
            assert (
                neutral['pcm'][441 * 4 :]
                == samples.tobytes()[441 * 4 : len(neutral['pcm'])]
            )
            return json.dumps(
                dict(
                    cache=str(model["cache"]),
                    ok=True,
                    pending_keeps_original=True,
                    disabled_is_bit_exact=True,
                    neutral_is_bit_exact=True,
                )
            )
        finally:
            gate.set()
            player.close()


def verify_equalizer_gain():
    from array import array
    from jukebox_equalizer import Equalizer

    samples = array('h', range(-32768, 32768))
    player = Equalizer()
    player.gain = 10 ** (-6 / 20)
    expected = array('h', (max(-32768, min(32767, round(x * player.gain))) for x in samples))
    assert player.process(samples.tobytes()) == expected.tobytes()
    return json.dumps(dict(ok=True, samples=len(samples), bit_exact=True))
