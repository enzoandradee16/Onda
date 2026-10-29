"""Bounded metadata completion; a failed lookup never replaces the selected track."""

import threading, time
from collections import OrderedDict

_cache = OrderedDict()
_lock = threading.Lock()


def complete_record(record, client, cancelled=lambda: False):
    from metadata import is_streaming_link

    result = dict(record)
    url = result.get('source_url', '')
    if not url or not is_streaming_link(url) or result.get('_details_checked'):
        return result
    with _lock:
        cached = _cache.get(url)
        if cached and time.monotonic() - cached[0] < 300:
            return dict(result, **cached[1])
    if cancelled():
        return result
    try:
        fetched = client.fetch(url)
        for field in (
            'cover_url',
            'release_date',
            'album',
            'album_artists',
            'duration_ms',
            'preview_url',
        ):
            if fetched.get(field):
                result[field] = fetched[field]
    except Exception:
        if cancelled():
            raise
    result['_details_checked'] = True
    with _lock:
        _cache[url] = (
            time.monotonic(),
            {
                key: result[key]
                for key in (
                    'cover_url',
                    'release_date',
                    'album',
                    'album_artists',
                    'duration_ms',
                    'preview_url',
                    '_details_checked',
                )
                if result.get(key)
            },
        )
        _cache.move_to_end(url)
        while len(_cache) > 256:
            _cache.popitem(last=False)
    return result


def collection_artwork(result):
    cover = result.get('cover_url')
    if cover:
        for row in result.get('tracks', []):
            if not row.get('cover_url'):
                row['cover_url'] = cover
    return result
