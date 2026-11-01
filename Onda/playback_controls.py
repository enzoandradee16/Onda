"""Playback timing and click-free gain, independent of the UI and audio device."""

import math, time
from array import array


def volume_gain(value):
    """Desktop listening curve: quiet midrange and a reduced, continuous ceiling."""
    value = float(value)
    if not math.isfinite(value):
        return 0.0
    return 0.5 * (max(0.0, min(100.0, value)) / 100.0) ** 2.5


class SleepTimer:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.deadline = None
        self.fade = 15.0

    def arm(self, seconds, fade=15):
        seconds = float(seconds)
        fade = float(fade)
        if (
            not math.isfinite(seconds)
            or seconds <= 0
            or not math.isfinite(fade)
            or fade <= 0
        ):
            raise ValueError('Tempo inválido.')
        self.deadline = self.clock() + seconds
        self.fade = min(fade, seconds)

    def cancel(self):
        self.deadline = None

    def remaining(self):
        return (
            max(0.0, self.deadline - self.clock()) if self.deadline is not None else 0.0
        )

    def gain(self):
        return (
            min(1.0, self.remaining() / self.fade) if self.deadline is not None else 1.0
        )


def fade_pcm(data, start, end):
    """Ramp stereo signed 16-bit PCM across this block without altering the input."""
    start = max(0.0, min(1.0, start))
    end = max(0.0, min(1.0, end))
    if start == end:
        if end == 1:
            return data
        if end == 0:
            return bytes(len(data))
        # The steady volume path runs ten times a second; keep it out of Python's
        # per-sample loop so the UI and analysis can run alongside playback.
        try:
            import audioop
        except ImportError:
            pass
        else:
            return audioop.mul(data, 2, end)
    samples = array('h')
    samples.frombytes(data)
    frames = len(samples) // 2
    for frame in range(frames):
        gain = max(0.0, min(1.0, start + (end - start) * (frame + 1) / max(1, frames)))
        samples[frame * 2] = round(samples[frame * 2] * gain)
        samples[frame * 2 + 1] = round(samples[frame * 2 + 1] * gain)
    return samples.tobytes()
