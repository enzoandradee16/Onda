"""Two transferable decoded prefixes; queue readiness never waits for a whole song."""

import threading
import time

_lock = threading.Lock()
_entries = {}


def identity(model):
    stream = model.get('_stream') or {}
    return stream.get('source_url') or stream.get('url') or ''


def retire(cache):
    cache.cancel()
    threading.Thread(target=cache.close, name='ONDA-warmup-close', daemon=True).start()


def take(model):
    with _lock:
        cache = _entries.pop(identity(model), None)
    if cache is not None and (cache.closed or cache.error is not None):
        retire(cache)
        return None
    return cache


def keep(models):
    wanted = {identity(model) for model in models}
    with _lock:
        removed = [_entries.pop(key) for key in list(_entries) if key not in wanted]
    for cache in removed:
        retire(cache)


def prepare(model, config, cancelled, progress):
    from jukebox import check
    from progressive_audio_cache import ProgressiveAudioCache
    from online_audio import RecoveringNetworkAudio, resolve

    key = identity(model)
    with _lock:
        cache = _entries.get(key)
        if cache is None and len(_entries) >= 2:
            return
    if cache is None:
        descriptor = dict(model['_stream'])

        def refresh():
            fresh = resolve(
                config, {}, cancelled, source_url=descriptor.get('source_url', '')
            )
            descriptor.update(fresh['_stream'])
            return descriptor

        cache = ProgressiveAudioCache(
            key,
            model['duration'],
            lambda seconds: RecoveringNetworkAudio(
                descriptor, config.get('ffmpeg', ''), seconds, refresh
            ),
            automatic=config.get('automatic_cache_cleanup', True),
        )
        with _lock:
            if key in _entries or len(_entries) >= 2:
                retire(cache)
                return
            _entries[key] = cache
    try:
        cache.start()
        deadline = time.monotonic() + 6
        goal = min(3.0, model['duration'])
        while not cache.complete and cache.buffered_seconds < goal:
            check(cancelled)
            if cache.error is not None:
                raise cache.error
            if time.monotonic() >= deadline:
                break
            progress(round(min(99, 99 * cache.buffered_seconds / max(0.01, goal))))
            if cache.thread is not None:
                cache.thread.join(0.1)
        check(cancelled)
    except Exception:
        with _lock:
            if _entries.get(key) is cache:
                _entries.pop(key, None)
                retire(cache)
        raise
