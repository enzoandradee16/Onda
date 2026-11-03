"""Resolve expiring audio URLs and decode a bounded network stream, without files."""

import math
import subprocess
import threading
from urllib.parse import urlsplit


def resolve(
    config, record, cancelled=lambda: False, *, source_url="", _reuse_reference=True
):
    from yt_dlp import YoutubeDL
    from engine import build_options, validate_url
    from jukebox import SearchLog, check
    from metadata import is_streaming_link

    from catalog_details import track_artwork

    record = track_artwork(record, config, cancelled)
    source = source_url or record.get('source_url') or config.get('url', '')
    options = build_options(
        dict(config, mode='original', playlist=False, playlist_limit=1)
    )
    if config.get('youtube_cookies_file'):
        options['cookiefile'] = config['youtube_cookies_file']
    logger = SearchLog(options, cancelled)
    selected = None
    remembered = False
    references = None
    if is_streaming_link(source):
        from matching import resolve_youtube
        from validated_audio import ValidatedAudioStore

        references = ValidatedAudioStore()
        selected = references.get(record) if _reuse_reference else None
        remembered = selected is not None
        if selected is None:
            selected = resolve_youtube(record, logger, lambda *_: None, automatic=True)
        source = selected['source_url']
    check(cancelled)
    options.update(
        quiet=True,
        no_warnings=True,
        noplaylist=True,
        format='bestaudio/best',
        skip_download=True,
        logger=logger,
        socket_timeout=15,
        retries=1,
    )
    host = (urlsplit(source).hostname or '').lower()
    if any(
        host == domain or host.endswith('.' + domain)
        for domain in ('youtube.com', 'youtu.be')
    ):
        # Direct media URLs may resolve successfully yet reject FFmpeg with 403.
        # Prefer the segmented audio and probe candidates before returning one.
        options.update(
            format='bestaudio[protocol^=m3u8]/bestaudio/best', check_formats='selected'
        )
    options.pop('postprocessors', None)
    try:
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(validate_url(source), download=False)
        check(cancelled)
        if selected is not None:
            from matching import revalidate_match

            revalidate_match(record, selected, info)
    except Exception as error:
        check(cancelled)
        transient = any(
            token in str(error).casefold()
            for token in (
                'not a bot',
                'confirm you',
                'too many requests',
                'http error 429',
                'http error 403',
                'timed out',
                'timeout',
                'connection reset',
                'network is unreachable',
                'name resolution',
            )
        )
        if remembered and not transient:
            references.forget(record)
            return resolve(
                config, record, cancelled, source_url=source_url, _reuse_reference=False
            )
        raise
    url = info.get('url', '')
    if urlsplit(url).scheme not in ('http', 'https'):
        raise ValueError('A fonte não disponibilizou um fluxo de áudio compatível.')
    duration = info.get('duration') or float(record.get('duration_ms') or 0) / 1000
    if (
        not isinstance(duration, (int, float))
        or not math.isfinite(duration)
        or not 0 < duration <= 1200
    ):
        raise ValueError('Use uma faixa de até 20 minutos com duração conhecida.')
    headers = {
        str(k): str(v)
        for k, v in (info.get('http_headers') or {}).items()
        if not any(c in str(k) + str(v) for c in '\r\n')
    }
    if references is not None:
        references.set(record, selected)
    return dict(
        _stream=dict(
            url=url,
            headers=headers,
            source_url=source,
            protocol=info.get('protocol') or '',
        ),
        cache='',
        source='',
        title=record.get('title') or info.get('title') or 'ONDA',
        media_title=record.get('title') or info.get('title') or 'ONDA',
        media_artist=', '.join(
            record.get('artists') or [info.get('artist') or info.get('uploader') or '']
        ),
        album=record.get('album') or '',
        cover_url=record.get('cover_url') or info.get('thumbnail') or '',
        duration=float(duration),
        beats=[0.0, float(duration)],
        neighbors=[[]],
        links=0,
    )


class StreamUnavailableError(ValueError):
    """The remote decoder failed; the same track can be resolved again once."""


class NetworkAudio:
    """FFmpeg is backpressured by a pipe; neither source nor PCM is saved to disk."""

    def __init__(self, stream, folder='', start=0):
        from audio_tools import executable

        if urlsplit(stream.get('url', '')).scheme not in ('http', 'https'):
            raise ValueError('A fonte não disponibilizou um fluxo de áudio compatível.')
        self.lock = threading.Lock()
        self.process = None
        self.closed = False
        command = [
            executable('ffmpeg', folder),
            '-nostdin',
            '-v',
            'error',
            '-rw_timeout',
            '15000000',
        ]
        headers = stream.get('headers') or {}
        if headers:
            command += [
                '-headers',
                ''.join(
                    f'{k}: {v}\r\n'
                    for k, v in headers.items()
                    if not any(c in str(k) + str(v) for c in '\r\n')
                ),
            ]
        # Input seeking can use HTTP ranges instead of decoding from the start.
        if start:
            command += ['-ss', str(max(0, float(start)))]
        command += ['-i', stream['url']]
        command += [
            '-vn',
            '-ac',
            '2',
            '-ar',
            '44100',
            '-c:a',
            'pcm_s16le',
            '-f',
            's16le',
            'pipe:1',
        ]
        self._fallback_command = None
        if start:
            fallback = list(command)
            at = fallback.index('-ss')
            del fallback[at : at + 2]
            at = fallback.index('-i') + 2
            fallback[at:at] = ['-ss', str(max(0, float(start)))]
            self._fallback_command = fallback
        self.process = self._open(command)

    @staticmethod
    def _open(command):
        from audio_tools import process_options

        return subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            **process_options(),
        )

    def read(self):
        data = self.process.stdout.read(4410 * 4)
        if data:
            self._fallback_command = None
        elif self._fallback_command is not None and not self.closed:
            # Some servers ignore Range requests and FFmpeg returns no PCM.
            # Retry once with decode-and-discard seeking for those sources.
            self.process.wait(timeout=5)
            self.process.stdout.close()
            with self.lock:
                if self.closed:
                    return b''
                command, self._fallback_command = self._fallback_command, None
                self.process = self._open(command)
            return self.read()
        if not data and not self.closed and self.process.wait(timeout=5) != 0:
            raise StreamUnavailableError(
                'Não foi possível reproduzir o áudio online. Tente abrir a música novamente.'
            )
        return data

    def cancel(self):
        with self.lock:
            self.closed = True
            if self.process and self.process.poll() is None:
                self.process.kill()

    def close(self):
        self.cancel()
        if self.process:
            self.process.wait(timeout=5)
            self.process.stdout.close()


class RecoveringNetworkAudio:
    """Refresh one expired/denied source, continuing after the PCM already read."""

    def __init__(self, stream, folder='', start=0, refresh=None):
        self.folder, self.start, self.refresh = folder, start, refresh
        self.reader = NetworkAudio(stream, folder, start)
        self.frames = 0
        self.retried = False
        self.cancelled = threading.Event()
        self.lock = threading.Lock()

    def read(self):
        try:
            data = self.reader.read()
        except StreamUnavailableError:
            if self.retried or self.refresh is None or self.cancelled.is_set():
                raise
            self.retried = True
            self.reader.close()
            stream = self.refresh()
            with self.lock:
                if self.cancelled.is_set():
                    return b''
                self.reader = NetworkAudio(
                    stream, self.folder, self.start + self.frames / 44100
                )
            data = self.reader.read()
        self.frames += len(data) // 4
        return data

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            self.reader.cancel()

    def close(self):
        self.cancel()
        self.reader.close()


class ReadAheadAudio:
    """A bounded raw-PCM reserve; live gain/EQ stay at the output, after buffering."""

    def __init__(self, reader, blocks=120):
        import queue

        self.reader = reader
        self.blocks = queue.Queue(maxsize=max(1, min(120, int(blocks))))
        self.warmup_blocks = min(4, self.blocks.maxsize)
        self.ready = threading.Event()
        self.primed = False
        from collections import deque

        self.history = deque()
        self.cursor = 0
        self.frontier = 0
        self.history_limit = 44100 * 4 * 10
        self.cancelled = threading.Event()
        self.finished = False
        self.thread = threading.Thread(
            target=self._produce, name='ONDA-stream-read-ahead', daemon=True
        )
        self.thread.start()

    def _put(self, value):
        import queue

        while not self.cancelled.is_set():
            try:
                self.blocks.put(value, timeout=0.05)
                if (
                    self.blocks.qsize() >= self.warmup_blocks
                    or not value[0]
                    or value[1] is not None
                ):
                    self.ready.set()
                return
            except queue.Full:
                pass

    def _produce(self):
        try:
            while not self.cancelled.is_set():
                data = self.reader.read()
                self._put((data, None))
                if not data:
                    return
        except Exception as error:
            self._put((b'', error))

    def _remember(self, data):
        if not data:
            return
        self.history.append((self.frontier, data))
        self.frontier += len(data)
        while (
            len(self.history) > 1
            and self.history[0][0] + len(self.history[0][1])
            <= self.frontier - self.history_limit
        ):
            self.history.popleft()

    def seek(self, seconds):
        """Worker-owned seek into recent PCM or the already fetched forward reserve."""
        target = round(seconds * 44100) * 4
        oldest = self.history[0][0] if self.history else self.frontier
        if self.cancelled.is_set() or target < oldest:
            return False
        with self.blocks.mutex:
            available = 0
            for data, error in self.blocks.queue:
                if error is not None or not data:
                    break
                available += len(data)
        if target > self.frontier + available:
            return False
        while self.frontier < target:
            data, error = self.blocks.get_nowait()
            self._remember(data)
        self.cursor = target
        return True

    def read(self, interrupted=lambda: False):
        import queue
        import time

        if interrupted():
            raise InterruptedError()
        if self.cancelled.is_set():
            return b''
        if self.cursor < self.frontier:
            for start, data in self.history:
                if start <= self.cursor < start + len(data):
                    result = data[self.cursor - start :]
                    self.cursor += len(result)
                    return result

        if not self.primed:
            import time

            deadline = time.monotonic() + 5
            while not self.ready.wait(0.05):
                if self.cancelled.is_set():
                    return b''
                if interrupted():
                    raise InterruptedError()
                if time.monotonic() >= deadline:
                    break
            self.primed = True
        deadline = time.monotonic() + 25
        while not self.finished and not self.cancelled.is_set():
            if time.monotonic() >= deadline:
                self.cancel()
                raise StreamUnavailableError(
                    'Não foi possível reproduzir o áudio online. Tente abrir a música novamente.'
                )
            if interrupted():
                raise InterruptedError()
            try:
                data, error = self.blocks.get(timeout=0.05)
            except queue.Empty:
                continue
            if error is not None:
                self.finished = True
                raise error
            if not data:
                self.finished = True
            self._remember(data)
            self.cursor = self.frontier
            return data
        return b''

    def cancel(self):
        self.cancelled.set()
        self.ready.set()
        self.reader.cancel()

    def close(self):
        self.cancel()
        self.thread.join(timeout=1)
        self.reader.close()


def prepare_stream(model, config, cancelled=lambda: False, progress=lambda _: None):
    """Cache the exact resolved audio, avoiding a second catalog/video search."""
    import tempfile
    import wave
    from pathlib import Path
    from jukebox import cache_root, check, prepare, Cancelled

    root = cache_root()
    root.mkdir(parents=True, exist_ok=True)
    check(cancelled)
    from stream_file_cache import lookup

    cached_file = lookup(model)
    if cached_file:
        try:
            prepared = prepare(
                cached_file['path'], config.get('ffmpeg', ''), cancelled, progress
            )
        except Cancelled:
            raise
        except (OSError, ValueError):
            # A deleted or damaged optional cache must not prevent preparation
            # from the already resolved stream.
            pass
        else:
            return _retain_stream_metadata(prepared, model)
    with tempfile.TemporaryDirectory(prefix='stream-effects-', dir=root) as temporary:
        source = Path(temporary) / 'audio.wav'
        from progressive_audio_cache import ProgressiveAudioCache

        pcm_cache = None
        try:
            stream = model['_stream']
            pcm_cache = ProgressiveAudioCache(
                stream.get('source_url') or stream['url'],
                model['duration'],
                lambda _: None,
                existing_only=True,
            )
            reader = pcm_cache.reader()
        except (OSError, ValueError):
            if pcm_cache is not None:
                pcm_cache.close()
                pcm_cache = None
            reader = NetworkAudio(model['_stream'], config.get('ffmpeg', ''))
        try:
            with wave.open(str(source), 'wb') as sound:
                sound.setparams((2, 2, 44100, 0, 'NONE', ''))
                frames = 0
                while True:
                    check(cancelled)
                    block = reader.read()
                    if not block:
                        break
                    frames += len(block) // 4
                    if frames > 1201 * 44100:
                        raise ValueError(
                            'Use uma faixa de até 20 minutos com duração conhecida.'
                        )
                    sound.writeframesraw(block)
                    progress(min(40, int(frames / 44100 / model['duration'] * 40)))
        finally:
            reader.close()
            if pcm_cache is not None:
                pcm_cache.close()
        check(cancelled)
        prepared = prepare(
            source,
            config.get('ffmpeg', ''),
            cancelled,
            lambda value: progress(40 + int(value * 0.5)),
        )
        return _retain_stream_metadata(prepared, model)


def _retain_stream_metadata(prepared, model):
    for key in ('media_title', 'media_artist', 'album', 'cover_url', '_cover'):
        if key in model:
            prepared[key] = model[key]
    prepared['source'] = ''
    prepared['title'] = model['title']
    return prepared


def prefetch_stream(model, config, cancelled=lambda: False, progress=lambda _: None):
    """Only report a queued stream ready once its decoded audio is cached."""
    if config.get('_queue_warmup'):
        from stream_warmup import prepare

        return prepare(model, config, cancelled, progress)
    from progressive_audio_cache import ProgressiveAudioCache
    from jukebox import check

    descriptor = dict(model['_stream'])

    def refresh():
        fresh = resolve(
            config, {}, cancelled, source_url=descriptor.get('source_url', '')
        )
        descriptor.update(fresh['_stream'])
        model['_stream'] = dict(descriptor)
        return descriptor

    cache = ProgressiveAudioCache(
        descriptor.get('source_url') or descriptor['url'],
        model['duration'],
        lambda seconds: RecoveringNetworkAudio(
            descriptor, config.get('ffmpeg', ''), seconds, refresh
        ),
        automatic=config.get('automatic_cache_cleanup', True),
    )
    try:
        cache.start()
        while not cache.complete:
            check(cancelled)
            if cache.error is not None:
                raise cache.error
            progress(round(99 * cache.buffered_seconds / model['duration']))
            if cache.thread is not None:
                cache.thread.join(0.1)
        check(cancelled)
    finally:
        cache.close()
