"""Prepare bounded, reusable effect audio without changing the original beat analysis."""

import os
from pathlib import Path
import subprocess
import threading
import time
import uuid
from contextlib import contextmanager

_render_lock = threading.Lock()


@contextmanager
def render_slot(owner, key):
    # One FFmpeg effect job at a time, shared by audible playback and preloading.
    while not _render_lock.acquire(timeout=0.05):
        if owner.closed or owner.request != key:
            yield False
            return
    try:
        yield not owner.closed and owner.request == key
    finally:
        _render_lock.release()


def clean(value=None):
    value = value if isinstance(value, dict) else {}

    def number(key, default, low, high):
        try:
            return max(low, min(high, int(value.get(key, default))))
        except (ValueError, TypeError, OverflowError):
            return default

    return dict(
        enabled=value.get('enabled', False) is True,
        speed=number('speed', 85, 50, 150),
        reverb=number('reverb', 25, 0, 100),
        keep_pitch=bool(value.get('keep_pitch', False)),
    )


def prepare(cache, value, cancelled=lambda: False):
    from jukebox import cache_root, Cancelled

    base = Path(cache).resolve()
    if base.parent != cache_root().resolve():
        raise ValueError('Cache inválido.')
    prepared = PreparedEffects(base)
    try:
        prepared.configure(value)
        while prepared.thread and prepared.thread.is_alive():
            if cancelled():
                raise Cancelled('Preparação cancelada.')
            prepared.thread.join(0.05)
        return prepared.error
    finally:
        prepared.close()


class PreparedEffects:
    """One worker per live track, latest request wins; playback keeps its old audio."""

    def __init__(self, base):
        self.base = Path(base)
        self.request = None
        self.ready = None
        self.error = ''
        self.closed = False
        self.thread = None
        self.lock = threading.Lock()

    def configure(self, value):
        value = clean(value)
        key = (
            (value['speed'], value['reverb'], value['keep_pitch'])
            if value['enabled']
            else None
        )
        with self.lock:
            if key != self.request:
                self.request = key
                self.error = ''
            if key is not None and self.path(key).is_file():
                self.ready = key
            if (
                key is not None
                and self.ready != key
                and not self.error
                and not (self.thread and self.thread.is_alive())
            ):
                self.thread = threading.Thread(target=self._work, daemon=True)
                self.thread.start()
        return key

    def path(self, key):
        return (
            self.base / ('effects-%s-%s-%s.wav' % key)
            if key is not None
            else self.base / 'audio.wav'
        )

    def _work(self):
        from audio_tools import executable, effects_filter, process_options

        while not self.closed:
            with self.lock:
                key = self.request
            if key is None:
                return
            target = self.path(key)
            temporary = target.with_name(
                '.' + target.name + '.' + uuid.uuid4().hex + '.wav'
            )
            try:
                with render_slot(self, key) as active:
                    if not active:
                        return
                    if not target.is_file():
                        command = [
                            executable('ffmpeg', os.environ.get('ONDA_FFMPEG', '')),
                            '-y',
                            '-v',
                            'error',
                            '-i',
                            str(self.base / 'audio.wav'),
                            '-af',
                            effects_filter(*key),
                            '-ac',
                            '2',
                            '-ar',
                            '44100',
                            '-c:a',
                            'pcm_s16le',
                            str(temporary),
                        ]
                        # File-backed stderr cannot deadlock while preparing long songs.
                        import tempfile

                        with tempfile.TemporaryFile() as errors:
                            process = subprocess.Popen(
                                command,
                                stdout=subprocess.DEVNULL,
                                stderr=errors,
                                **process_options(),
                            )
                            started = time.monotonic()
                            try:
                                while process.poll() is None:
                                    if (
                                        self.closed
                                        or self.request != key
                                        or time.monotonic() - started > 300
                                    ):
                                        process.kill()
                                        process.wait()
                                        break
                                    time.sleep(0.05)
                                if self.closed or self.request != key:
                                    return
                                if process.returncode:
                                    raise ValueError(
                                        'Não foi possível preparar os efeitos desta música.'
                                    )
                            finally:
                                if process.poll() is None:
                                    process.kill()
                                    process.wait()
                        if not target.is_file():
                            temporary.replace(target)
                        # Keep a small per-track cache even after extensive slider changes.
                        old = sorted(
                            self.base.glob('effects-*.wav'),
                            key=lambda path: path.stat().st_mtime,
                            reverse=True,
                        )
                        for path in old[3:]:
                            if path != target:
                                try:
                                    path.unlink()
                                except OSError:
                                    pass  # An older live session may still have it open.
                with self.lock:
                    self.ready = key
                if self.request == key:
                    return
            except Exception as error:
                with self.lock:
                    self.error = str(error)
                return
            finally:
                temporary.unlink(missing_ok=True)

    def close(self):
        self.closed = True
        if self.thread and self.thread is not threading.current_thread():
            self.thread.join(2)
