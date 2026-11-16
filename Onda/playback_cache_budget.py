"""Evict whole disposable playback caches, retaining active/prepared/recent audio."""
from contextlib import ExitStack
from pathlib import Path
import re
import shutil
import threading
import time

MIB = 1024*1024
DESKTOP_LIMIT = 1024*MIB
ANDROID_LIMIT = 384*MIB  # Native Android segments have a separate 128 MiB budget.
_scan_lock = threading.Lock()
_schedule_lock = threading.Lock()
_last_schedule = 0.0
_HASH = r'[0-9a-f]{64}'


def model_paths(models):
    result = []
    for model in models:
        if not isinstance(model, dict):
            continue
        for key in ('cache', 'source', '_stream_file'):
            value = model.get(key)
            if isinstance(value, str) and value and not value.startswith(('http:', 'https:')):
                result.append(value)
    return result


def mark_played(path):
    """Called when audio is actually opened, never merely when it is prefetched."""
    from cache_cleanup import linked
    path = Path(path)
    try:
        if linked(path):
            return
        marker = path / '.played' if path.is_dir() else path.with_name(path.name+'.played')
        marker.touch()
    except OSError:
        pass


def _modified(path):
    files = list(path.iterdir()) if path.is_dir() else [path]
    marker = path.with_name(path.name + '.played')
    if not path.is_dir() and marker.exists():
        files.append(marker)
    return max([path.stat().st_mtime] + [p.stat().st_mtime for p in files])


def _entries(root):
    from cache_cleanup import linked
    if not root.is_dir() or linked(root):
        return
    candidates = []
    for path in root.iterdir():
        if path.is_dir() and re.fullmatch(_HASH+r'|effects-[0-9a-f]{32}', path.name):
            candidates.append(path)
    streaming = root/'streaming'
    if streaming.is_dir() and not linked(streaming):
        candidates.extend(p for p in streaming.iterdir() if p.is_dir() and re.fullmatch(_HASH+r'\.[0-9a-f]{8}',p.name))
    packets = root/'stream-files'
    if packets.is_dir() and not linked(packets):
        candidates.extend(p for p in packets.iterdir() if p.is_file() and re.fullmatch(_HASH+r'\.mka',p.name))
    for path in candidates:
        if linked(path) or not path.resolve().is_relative_to(root.resolve()):
            continue
        try:
            files = list(path.iterdir()) if path.is_dir() else [path]
            # Cache groups are flat. Unknown directories/links are never traversed.
            if any(linked(p) or not p.is_file() for p in files):
                continue
            size = sum(p.stat().st_size for p in files)
            modified = _modified(path)
            marker = path/'.played' if path.is_dir() else path.with_name(path.name+'.played')
            played = marker.stat().st_mtime if marker.is_file() and not linked(marker) else 0
            yield (played or modified, modified, played, size, path)
        except OSError:
            continue


def prune(root=None, *, protected=(), max_bytes=DESKTOP_LIMIT, now=None, keep_recent=4, grace=120):
    """Soft budget: protected audio always wins over the target size.

    Keep current + three actually played tracks, not just the newest prefetches.
    Call off the UI/audio threads with a snapshot of pending/current models.
    """
    from jukebox import cache_root, _active_lock, _active
    from progressive_audio_cache import _lock, _active as active_streams
    from cache_cleanup import linked
    root = Path(root) if root is not None else cache_root()
    if not _scan_lock.acquire(blocking=False):
        return {'busy': True, 'removed': 0}
    try:
        now = time.time() if now is None else now
        entries = list(_entries(root))
        total = sum(row[3] for row in entries)
        before = total
        protected = [Path(p).resolve() for p in protected]
        recent = {row[4] for row in sorted(
            (row for row in entries if row[2] > 0),
            key=lambda row: row[2], reverse=True)[:keep_recent]}
        failed = 0
        for _, modified, _, size, path in sorted(entries):
            if total <= max_bytes:
                break
            if path in recent or now-modified < grace:
                continue
            resolved = path.resolve()
            if any(p==resolved or p.is_relative_to(resolved) or resolved.is_relative_to(p) for p in protected):
                continue
            # Coordinate with readers/analysis registration before unlinking a group.
            with ExitStack() as locks:
                locks.enter_context(_active_lock)
                locks.enter_context(_lock)
                active = [Path(p).resolve() for p in _active]+list(active_streams)
                if any(p==resolved or p.is_relative_to(resolved) or resolved.is_relative_to(p) for p in active):
                    continue
                try:
                    if linked(path) or not resolved.is_relative_to(root.resolve()):
                        continue
                    # A newly touched/reused cache gets a fresh lease.
                    if _modified(path) > modified:
                        continue
                    if path.is_dir():
                        if any(linked(p) or not p.is_file() for p in path.iterdir()):
                            continue
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                        path.with_name(path.name+'.played').unlink(missing_ok=True)
                    total -= size
                except OSError:
                    failed += 1
        return {'bytes':total,'removed':before-total,'failed':failed,'over_budget':total>max_bytes}
    finally:
        _scan_lock.release()


def recent_paths(root, count=4):
    return {row[4] for row in sorted(
        (row for row in _entries(Path(root)) if row[2] > 0),
        key=lambda row: row[2], reverse=True)[:count]}


def schedule(models, *, protected=(), max_bytes=DESKTOP_LIMIT):
    """Snapshot on the caller thread; disk work is serialized in the background."""
    global _last_schedule
    with _schedule_lock:
        if time.monotonic() - _last_schedule < 30:
            return
        _last_schedule = time.monotonic()
    paths = model_paths(models) + list(protected)
    threading.Thread(target=prune, kwargs=dict(protected=paths, max_bytes=max_bytes),
                     daemon=True, name='playback-cache-trim').start()
