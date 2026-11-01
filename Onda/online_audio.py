"""Resolve expiring audio URLs and decode a bounded network stream, without files."""

import math
import subprocess
import threading
from urllib.parse import urlsplit


def resolve(config, record, cancelled=lambda: False):
    from yt_dlp import YoutubeDL
    from engine import build_options, validate_url
    from jukebox import SearchLog, check
    from metadata import is_streaming_link

    source = record.get('source_url') or config.get('url', '')
    options = build_options(
        dict(config, mode='original', playlist=False, playlist_limit=1)
    )
    if config.get('youtube_cookies_file'):
        options['cookiefile'] = config['youtube_cookies_file']
    logger = SearchLog(options, cancelled)
    if is_streaming_link(source):
        from matching import resolve_youtube

        source = resolve_youtube(record, logger, lambda *_: None, automatic=True)[
            'source_url'
        ]
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
    options.pop('postprocessors', None)
    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(validate_url(source), download=False)
    check(cancelled)
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
    return dict(
        _stream=dict(url=url, headers=headers),
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
            raise ValueError(
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


class ReadAheadAudio:
    """A bounded raw-PCM reserve; live gain/EQ stay at the output, after buffering."""

    def __init__(self, reader, blocks=12):
        import queue

        self.reader = reader
        self.blocks = queue.Queue(maxsize=max(1, min(30, int(blocks))))
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

    def read(self):
        import queue

        while not self.finished and not self.cancelled.is_set():
            try:
                data, error = self.blocks.get(timeout=0.05)
            except queue.Empty:
                continue
            if error is not None:
                self.finished = True
                raise error
            if not data:
                self.finished = True
            return data
        return b''

    def cancel(self):
        self.cancelled.set()
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
    from jukebox import cache_root, check, prepare

    root = cache_root()
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='stream-effects-', dir=root) as temporary:
        source = Path(temporary) / 'audio.wav'
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
        check(cancelled)
        prepared = prepare(
            source,
            config.get('ffmpeg', ''),
            cancelled,
            lambda value: progress(40 + int(value * 0.5)),
        )
        for key in ('media_title', 'media_artist', 'album', 'cover_url', '_cover'):
            if key in model:
                prepared[key] = model[key]
        prepared['source'] = ''
        prepared['title'] = model['title']
        return prepared
