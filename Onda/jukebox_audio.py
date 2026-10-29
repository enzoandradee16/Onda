"""Small bounded PCM output for Windows: two queued buffers, no per-beat players."""

import ctypes as c
from ctypes import wintypes as w
from collections import deque
import time
from jukebox import RATE, CHANNELS, Cancelled


class WaveFormat(c.Structure):
    _pack_ = 1
    _fields_ = [
        ('tag', w.WORD),
        ('channels', w.WORD),
        ('rate', w.DWORD),
        ('bytes_per_second', w.DWORD),
        ('align', w.WORD),
        ('bits', w.WORD),
        ('extra', w.WORD),
    ]


class WaveHeader(c.Structure):
    _fields_ = [
        ('data', c.c_void_p),
        ('length', w.DWORD),
        ('recorded', w.DWORD),
        ('user', c.c_size_t),
        ('flags', w.DWORD),
        ('loops', w.DWORD),
        ('next', c.c_void_p),
        ('reserved', c.c_size_t),
    ]


class WaveTime(c.Structure):
    _fields_ = [('type', w.DWORD), ('data', w.DWORD * 2)]


class PcmOutput:
    def __init__(self, progress=None):
        self.api = c.WinDLL('winmm')
        self.handle = w.HANDLE()
        self.buffers = deque()
        self.played = 0
        self.paused = False
        self.progress = progress
        self.last_notify = 0
        self.last_frame = -1
        self.gain = None
        self.last_gain = 1.0
        self.api.waveOutOpen.argtypes = [
            c.POINTER(w.HANDLE),
            w.UINT,
            c.POINTER(WaveFormat),
            c.c_size_t,
            c.c_size_t,
            w.DWORD,
        ]
        self.api.waveOutOpen.restype = w.UINT
        for name in ('waveOutPrepareHeader', 'waveOutWrite', 'waveOutUnprepareHeader'):
            getattr(self.api, name).argtypes = [w.HANDLE, c.POINTER(WaveHeader), w.UINT]
        for name in ('waveOutPause', 'waveOutRestart', 'waveOutReset', 'waveOutClose'):
            getattr(self.api, name).argtypes = [w.HANDLE]
        if progress:
            self.api.waveOutGetPosition.argtypes = [
                w.HANDLE,
                c.POINTER(WaveTime),
                w.UINT,
            ]
            self.api.waveOutGetPosition.restype = w.UINT
        fmt = WaveFormat(1, CHANNELS, RATE, RATE * CHANNELS * 2, CHANNELS * 2, 16, 0)
        self._check(
            self.api.waveOutOpen(
                c.byref(self.handle), 0xFFFFFFFF, c.byref(fmt), 0, 0, 0
            )
        )

    @staticmethod
    def _check(code):
        if code:
            raise ValueError('Não foi possível abrir a saída de áudio do Windows.')

    def control(self, cancelled, paused):
        if cancelled():
            raise Cancelled('Reprodução encerrada.')
        value = paused()
        if value != self.paused:
            self._check(
                (self.api.waveOutPause if value else self.api.waveOutRestart)(
                    self.handle
                )
            )
            self.paused = value
        self.notify()
        return value

    def notify(self):
        if self.progress is None:
            return
        now = time.monotonic()
        if now - self.last_notify < 0.04:
            return
        self.last_notify = now
        position = WaveTime()
        position.type = 2  # TIME_SAMPLES: samples actually played by the device.
        code = self.api.waveOutGetPosition(
            self.handle, c.byref(position), c.sizeof(position)
        )
        frames = (
            position.data[0]
            if not code and position.type == 2
            else (
                position.data[0] // (CHANNELS * 2)
                if not code and position.type == 4
                else self.played
            )
        )
        frames = max(self.last_frame, frames)
        if frames != self.last_frame:
            self.last_frame = frames
            self.progress(frames)

    def _drain(self, cancelled, paused):
        while self.buffers:
            self.control(cancelled, paused)
            header, buffer = self.buffers[0]
            if not header.flags & 1:
                time.sleep(0.005)
                continue
            self._check(
                self.api.waveOutUnprepareHeader(
                    self.handle, c.byref(header), c.sizeof(header)
                )
            )
            self.buffers.popleft()
            self.played += header.length // (CHANNELS * 2)
            break

    def write(self, data, cancelled, paused):
        # Bound both latency and RAM independently of song duration.
        block = RATE // 10 * CHANNELS * 2
        for offset in range(0, len(data), block):
            while self.control(cancelled, paused):
                time.sleep(0.02)
            payload = data[offset : offset + block]
            if self.gain is not None:
                from playback_controls import fade_pcm

                gain = self.gain()
                payload = fade_pcm(payload, self.last_gain, gain)
                self.last_gain = gain
            buffer = c.create_string_buffer(payload)
            header = WaveHeader(
                c.cast(buffer, c.c_void_p), len(payload), 0, 0, 0, 0, None, 0
            )
            self._check(
                self.api.waveOutPrepareHeader(
                    self.handle, c.byref(header), c.sizeof(header)
                )
            )
            try:
                self._check(
                    self.api.waveOutWrite(
                        self.handle, c.byref(header), c.sizeof(header)
                    )
                )
            except BaseException:
                self.api.waveOutUnprepareHeader(
                    self.handle, c.byref(header), c.sizeof(header)
                )
                raise
            self.buffers.append((header, buffer))
            if len(self.buffers) >= 3:
                self._drain(cancelled, paused)

    def close(self):
        if not self.handle:
            return
        self.api.waveOutReset(self.handle)
        while self.buffers:
            header, buffer = self.buffers.popleft()
            self.api.waveOutUnprepareHeader(
                self.handle, c.byref(header), c.sizeof(header)
            )
        self.api.waveOutClose(self.handle)
        self.handle = w.HANDLE()
