"""Disposable, bounded packet-copy cache for native Android streaming."""

import hashlib
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlsplit

LIMIT = 256 * 1024 * 1024


def _download_android_hls(stream, target, limit, cancelled):
    """Use the existing verified Python HTTPS transport for HLS segments."""
    from yt_dlp import YoutubeDL
    from yt_dlp.downloader.hls import HlsFD
    from jukebox import check

    def progress(value):
        check(cancelled)
        if value.get('downloaded_bytes', 0) > limit:
            raise ValueError('O áudio excedeu o limite do cache de streaming.')

    class Log:
        def debug(self, message):
            pass

        warning = debug

        def error(self, message):
            pass

    options = dict(
        quiet=True,
        no_warnings=True,
        noprogress=True,
        cachedir=False,
        socket_timeout=15,
        retries=1,
        fragment_retries=1,
        concurrent_fragment_downloads=1,
        skip_unavailable_fragments=False,
        max_filesize=limit,
        logger=Log(),
    )
    with YoutubeDL(options) as downloader:
        native = HlsFD(downloader, options)
        native.add_progress_hook(progress)
        result = native.download(
            str(target),
            dict(
                id=hashlib.sha256(stream['url'].encode()).hexdigest()[:16],
                url=stream['url'],
                protocol='m3u8_native',
                ext='m4a',
                http_headers=stream.get('headers') or {},
            ),
        )
        check(cancelled)
        if not result[0]:
            raise ValueError('Não foi possível obter o áudio para o cache.')


def lookup(model, limit=LIMIT):
    from jukebox import cache_root
    from cache_cleanup import linked

    stream = model['_stream']
    key = hashlib.sha256(
        (stream.get('source_url') or stream['url']).encode()
    ).hexdigest()
    path = cache_root() / 'stream-files' / (key + '.mka')
    try:
        if path.is_file() and not linked(path):
            size = path.stat().st_size
            if 128 < size < limit:
                os.utime(path, None)
                return dict(path=str(path), bytes=size)
    except OSError:
        # Cleanup can evict an inactive file between discovery and inspection.
        pass
    return None


def prepare(model, config, cancelled=lambda: False):
    from audio_tools import executable, network_input_options
    from jukebox import cache_root, check, _run
    from cache_cleanup import linked

    limit = min(LIMIT, max(1024, int(config.get('_stream_cache_limit', LIMIT))))
    stream = model['_stream']
    if urlsplit(stream['url']).scheme not in ('http', 'https'):
        raise ValueError('A fonte não disponibilizou um fluxo de áudio compatível.')
    root = cache_root() / 'stream-files'
    root.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(
        (stream.get('source_url') or stream['url']).encode()
    ).hexdigest()
    target = root / (key + '.mka')
    protected = {
        str(Path(p).resolve()) for p in config.get('_stream_cache_protected', [])
    }

    from playback_cache_budget import recent_paths

    recent = recent_paths(root.parent)

    def prune(reserve=0):
        entries = []
        for path in root.glob('*.mka'):
            if re.fullmatch(r'[0-9a-f]{64}\.mka', path.name) and not linked(path):
                info = path.stat()
                entries.append((info.st_mtime, info.st_size, path))
        total = sum(row[1] for row in entries)
        for modified, size, path in sorted(entries):
            expired = (
                config.get('automatic_cache_cleanup', True)
                and modified < time.time() - 7 * 86400
            )
            if (
                (expired or total + reserve > limit)
                and str(path.resolve()) not in protected
                and path != target
                and path not in recent
            ):
                try:
                    path.unlink()
                    total -= size
                except OSError:
                    pass
        return total

    check(cancelled)
    if target.is_file() and not linked(target) and 128 < target.stat().st_size < limit:
        os.utime(target, None)
        prune()
        return dict(path=str(target), bytes=target.stat().st_size)
    with tempfile.TemporaryDirectory(
        prefix='jukebox-download-stream-', dir=root
    ) as temporary:
        output = Path(temporary) / 'audio.mka'
        command = [
            executable('ffmpeg', config.get('ffmpeg', '')),
            '-nostdin',
            '-v',
            'error',
            '-rw_timeout',
            '15000000',
        ]
        headers = stream.get('headers') or {}
        import sys

        hls = (
            stream.get('protocol', '').startswith('m3u8')
            or '/hls_playlist/' in stream['url']
            or urlsplit(stream['url']).path.endswith('.m3u8')
        )
        local = None
        if hasattr(sys, 'getandroidapilevel') and hls:
            local = Path(temporary) / 'source.media'
            _download_android_hls(stream, local, limit, cancelled)
            # Only local remuxing uses FFmpeg: HLS subrequests otherwise lose
            # its CA-file option on the current native build.
            headers = {}
        if headers:
            command += [
                '-headers',
                ''.join(
                    f'{k}: {v}\r\n'
                    for k, v in headers.items()
                    if not any(c in str(k) + str(v) for c in '\r\n')
                ),
            ]
        command += network_input_options(stream['url']) if local is None else []
        command += [
            '-i',
            str(local) if local is not None else stream['url'],
            '-map',
            '0:a:0',
            '-vn',
            '-c:a',
            'copy',
            '-fs',
            str(limit),
            '-f',
            'matroska',
            '-y',
            str(output),
        ]
        _run(command, cancelled)
        check(cancelled)
        size = output.stat().st_size
        if not 128 < size < limit or prune(size) + size > limit:
            raise ValueError(
                'Não foi possível preparar o áudio. Confira o arquivo e o FFmpeg.'
            )
        os.replace(output, target)
    return dict(path=str(target), bytes=size)
