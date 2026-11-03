"""Disposable, bounded packet-copy cache for native Android streaming."""

import hashlib
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import urlsplit

LIMIT = 256 * 1024 * 1024


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
    from audio_tools import executable
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
        if headers:
            command += [
                '-headers',
                ''.join(
                    f'{k}: {v}\r\n'
                    for k, v in headers.items()
                    if not any(c in str(k) + str(v) for c in '\r\n')
                ),
            ]
        command += [
            '-i',
            stream['url'],
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
