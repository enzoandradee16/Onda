"""Bounded temporary PCM cache; playback can consume the prefix as it arrives."""

from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import threading
import time
import uuid

RATE = 44100
FRAME = 4
LIMIT = 256 * 1024 * 1024
_active = Counter()
_lock = threading.Lock()


def sufficient_audio(size, duration):
    tolerance = max(1.0, min(3.0, duration * 0.01))
    return size >= max(0.001, duration - tolerance) * RATE * FRAME


def in_use(path):
    path = Path(path).resolve()
    with _lock:
        return any(path.is_relative_to(base) for base in _active)


def prune(root, reserve=0, expire=True):
    from cache_cleanup import linked

    root = Path(root).resolve()
    entries = []
    for folder in root.iterdir():
        if (
            not re.fullmatch(r'[0-9a-f]{64}\.[0-9a-f]{8}', folder.name)
            or linked(folder)
            or not folder.resolve().is_relative_to(root)
        ):
            continue
        try:
            size = sum(
                p.stat().st_size
                for p in folder.iterdir()
                if p.is_file() and not linked(p)
            )
            entries.append((folder.stat().st_mtime, size, folder))
        except OSError:
            pass
    size = sum(row[1] for row in entries)
    for modified, amount, folder in sorted(entries):
        if size + reserve <= LIMIT and (
            not expire or modified > time.time() - 7 * 86400
        ):
            continue
        if in_use(folder):
            continue
        try:
            shutil.rmtree(folder)
            size -= amount
        except OSError:
            pass


class CacheReadError(OSError):
    pass


class ProgressiveAudioCache:
    def __init__(
        self,
        identity,
        duration,
        factory,
        root=None,
        progress=lambda value: None,
        automatic=True,
        existing_only=False,
    ):
        if not math.isfinite(duration) or not 0 < duration <= 1200:
            raise ValueError('Use uma faixa de até 20 minutos com duração conhecida.')
        if root is None:
            from jukebox import cache_root

            root = cache_root() / 'streaming'
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.key = hashlib.sha256(identity.encode()).hexdigest()
        self.duration = duration
        self.automatic = automatic
        self.factory = factory
        self.progress = progress
        self.last_progress = 0
        self.condition = threading.Condition()
        self.cancelled = threading.Event()
        self.complete = False
        self.error = None
        self.written = 0
        self.decoder = None
        self.thread = None
        self.closed = False
        self.folder = None
        for folder in sorted(
            self.root.glob(self.key + '.*'),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        ):
            try:
                from cache_cleanup import linked

                if linked(folder):
                    continue
                info = json.loads((folder / 'ready.json').read_text(encoding='utf-8'))
                size = (folder / 'audio.pcm').stat().st_size
                if (
                    info.get('key') == self.key
                    and info.get('bytes') == size
                    and 0 < size <= LIMIT
                    and size % FRAME == 0
                    and sufficient_audio(size, duration)
                ):
                    self.folder, self.written, self.complete = folder, size, True
                    os.utime(folder, None)
                    break
            except (OSError, ValueError, TypeError):
                pass
        if self.folder is None:
            if existing_only:
                raise FileNotFoundError('No complete audio cache')
            prune(self.root, round(duration * RATE * FRAME), expire=self.automatic)
            self.folder = self.root / (self.key + '.' + uuid.uuid4().hex[:8])
            self.folder.mkdir()
            (self.folder / 'audio.pcm').touch()
        with _lock:
            _active[self.folder.resolve()] += 1

    @property
    def buffered_seconds(self):
        with self.condition:
            return min(self.duration, self.written / (RATE * FRAME))

    def covers(self, seconds):
        with self.condition:
            return seconds >= 0 and (
                seconds * RATE * FRAME < self.written
                or self.complete
                and seconds <= self.written / (RATE * FRAME)
            )

    def start(self):
        with self.condition:
            if self.complete or self.thread is not None or self.cancelled.is_set():
                return
            self.thread = threading.Thread(
                target=self._produce, name='ONDA-audio-cache', daemon=True
            )
            self.thread.start()

    def _produce(self):
        decoder = None
        try:
            decoder = self.factory(0)
            with self.condition:
                self.decoder = decoder
                if self.cancelled.is_set():
                    decoder.cancel()
                    return
            with (self.folder / 'audio.pcm').open('wb', buffering=0) as output:
                while not self.cancelled.is_set():
                    data = decoder.read()
                    if not data:
                        if not self.written and not self.cancelled.is_set():
                            raise CacheReadError('Empty audio stream')
                        if not self.cancelled.is_set() and not sufficient_audio(
                            self.written, self.duration
                        ):
                            raise CacheReadError(
                                'O áudio recebido terminou antes do esperado.'
                            )
                        with self.condition:
                            if not self.cancelled.is_set() and self.written:
                                info = dict(key=self.key, bytes=self.written)
                                (self.folder / 'ready.json').write_text(
                                    json.dumps(info), encoding='utf-8'
                                )
                                self.complete = True
                                self.condition.notify_all()
                        self.progress(self.buffered_seconds)
                        return
                    if self.written + len(data) > LIMIT:
                        raise CacheReadError('Cache temporário cheio.')
                    output.write(data)
                    with self.condition:
                        self.written += len(data)
                        self.condition.notify_all()
                    now = time.monotonic()
                    if now - self.last_progress >= 0.25:
                        self.last_progress = now
                        self.progress(self.buffered_seconds)
        except Exception as error:
            with self.condition:
                self.error = error
                self.condition.notify_all()
        finally:
            if decoder:
                decoder.close()
            with self.condition:
                self.decoder = None
                self.condition.notify_all()

    def reader(self, seconds=0):
        return CachedPcmReader(self, seconds)

    def cancel(self):
        self.cancelled.set()
        with self.condition:
            if self.decoder:
                self.decoder.cancel()
            self.condition.notify_all()

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.cancel()
        if self.thread:
            self.thread.join(timeout=2)
        with _lock:
            key = self.folder.resolve()
            _active[key] -= 1
            if _active[key] <= 0:
                _active.pop(key, None)
        if (
            not self.complete
            and (self.thread is None or not self.thread.is_alive())
            and not in_use(self.folder)
        ):
            try:
                if self.folder.resolve().is_relative_to(self.root.resolve()):
                    shutil.rmtree(self.folder)
            except OSError:
                pass
        prune(self.root, expire=self.automatic)


class CachedPcmReader:
    def __init__(self, cache, seconds):
        self.cache = cache
        self.position = round(seconds * RATE) * FRAME
        self.cancelled = threading.Event()
        self.file = (cache.folder / 'audio.pcm').open('rb', buffering=0)

    def read(self):
        with self.cache.condition:
            while self.position >= self.cache.written:
                if self.cancelled.is_set() or self.cache.cancelled.is_set():
                    return b''
                if self.cache.error is not None:
                    raise CacheReadError() from self.cache.error
                if self.cache.complete:
                    return b''
                self.cache.condition.wait(0.05)
            amount = min(17640, self.cache.written - self.position)
        if self.cancelled.is_set():
            return b''
        self.file.seek(self.position)
        data = self.file.read(amount)
        self.position += len(data)
        return data

    def cancel(self):
        self.cancelled.set()
        with self.cache.condition:
            self.cache.condition.notify_all()

    def close(self):
        self.cancel()
        self.file.close()
