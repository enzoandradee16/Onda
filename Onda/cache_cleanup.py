"""Explicitly scoped reconstructible caches. Never traverse links or application data."""

from pathlib import Path
from contextlib import closing
import os, sys, stat, sqlite3


def root_path():
    if os.environ.get('ONDA_ALIAS_CACHE_ROOT'):
        return Path(os.environ['ONDA_ALIAS_CACHE_ROOT'])
    return Path(os.environ.get('LOCALAPPDATA') or Path.home() / '.cache') / 'Onda'


def linked(path):
    try:
        info = path.lstat()
        return stat.S_ISLNK(info.st_mode) or bool(
            getattr(info, 'st_file_attributes', 0) & 0x400
        )
    except OSError:
        return True


def cache_files(root):
    import re

    root = Path(root)
    if linked(root):
        return
    for folder in (
        'extractor-cache',
        'image-preview',
        'online-image-preview',
        'jukebox',
    ):
        base = root / folder
        if linked(base):
            continue
        for directory, dirs, files in os.walk(base, followlinks=False):
            from jukebox import cache_in_use

            dirs[:] = [
                name
                for name in dirs
                if not name.startswith('jukebox-download-')
                and not linked(Path(directory) / name)
            ]
            for name in files:
                path = Path(directory) / name
                if (
                    not linked(path)
                    and path.resolve().is_relative_to(base.resolve())
                    and not cache_in_use(path)
                ):
                    yield path
    for path in root.glob('preview-*.mp3'):
        if (
            re.fullmatch(r'preview-(?:default|[0-9a-f-]+)\.mp3', path.name)
            and not linked(path)
            and path.is_file()
        ):
            yield path


def cache_info(root=None):
    root = Path(root) if root is not None else root_path()
    size = 0
    for path in cache_files(root):
        try:
            size += path.stat().st_size
        except OSError:
            pass
    alias = root / 'artist-aliases.sqlite3'
    if not linked(root) and not linked(alias):
        try:
            size += alias.stat().st_size
        except OSError:
            pass
    return {'bytes': size}


def clear_cache(root=None):
    root = Path(root) if root is not None else root_path()
    before = cache_info(root)['bytes']
    failed = 0
    for path in cache_files(root):
        try:
            path.unlink()
        except OSError:
            failed += 1
    alias = root / 'artist-aliases.sqlite3'
    if not linked(root) and alias.is_file() and not linked(alias):
        try:
            with closing(sqlite3.connect(alias, timeout=3)) as db:
                db.execute('DELETE FROM aliases')
                db.commit()
                db.execute('VACUUM')
        except sqlite3.Error:
            failed += 1
    # Clear only reconstructible in-memory results; user-confirmed choices are kept.
    for module, function in [
        ('online_image_preview', 'clear_cache'),
        ('music_search', 'clear_cache'),
        ('catalog_ui', 'cached_cover_png'),
        ('history_details', '_cached_details'),
    ]:
        loaded = sys.modules.get(module)
        target = getattr(loaded, function, None) if loaded else None
        if target:
            if hasattr(target, 'cache_clear'):
                target.cache_clear()
            else:
                target()
    after = cache_info(root)['bytes']
    return {'bytes': after, 'removed': max(0, before - after), 'failed': failed}


def automatic_cleanup(
    root=None, *, now=None, max_bytes=512 * 1024 * 1024, max_age=7 * 86400
):
    """Bound disposable caches only; never remove partial downloads or playback audio.

    Recent files have a one-hour lease, including when the size limit is exceeded.
    Run on startup/idle, not during a gallery or rendering operation.
    """
    import time

    root = Path(root) if root is not None else root_path()
    now = time.time() if now is None else now
    candidates = []
    for path in cache_files(root):
        try:
            relative = path.relative_to(root)
            if relative.parts[0] == 'jukebox':
                continue
            info = path.stat()
            candidates.append((info.st_mtime, path, info.st_size))
        except OSError:
            continue
    total = sum(size for _, _, size in candidates)
    removed = failed = 0
    for modified, path, size in sorted(candidates):
        age = now - modified
        if age < 3600 or age < max_age and total <= max_bytes:
            continue
        try:
            path.unlink()
            removed += size
            total -= size
        except OSError:
            failed += 1
    return {'bytes': total, 'removed': removed, 'failed': failed}
