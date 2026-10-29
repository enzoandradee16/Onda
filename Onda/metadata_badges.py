"""Offline monochrome metadata-provider badges; never infer from audio download URLs."""

from functools import lru_cache
from pathlib import Path

NAMES = {
    'spotify': 'Spotify',
    'deezer': 'Deezer',
    'apple_music': 'Apple Music',
    'musicbrainz': 'MusicBrainz',
    'youtube': 'YouTube',
    'tidal': 'TIDAL',
    'qobuz': 'Qobuz',
    'bandcamp': 'Bandcamp',
}


def provider(record):
    if not isinstance(record, dict):
        return ''
    value = str(record.get('platform') or '').strip().lower()
    return {
        'apple / itunes': 'apple_music',
        'applemusic': 'apple_music',
        'apple music': 'apple_music',
        'itunes': 'apple_music',
        'apple': 'apple_music',
        'youtube music': 'youtube',
    }.get(value, value if value in NAMES else '')


def apply_badge(widget, record, text=None):
    from tkinter import ttk
    from PIL import ImageTk

    key = provider(record)
    color = (
        ttk.Style(widget).lookup(widget.cget('style') or 'TLabel', 'foreground')
        or '#9baec5'
    )
    rgb = tuple(v // 257 for v in widget.winfo_rgb(color))
    if getattr(widget, '_metadata_signature', None) == (key, rgb):
        if text is not None:
            widget.configure(text=text)
        return
    widget._metadata_signature = (key, rgb)
    if key:
        photo = ImageTk.PhotoImage(_tinted(key, rgb), master=widget)
        widget._metadata_icon = photo
        widget.configure(image=photo, compound='left')
    else:
        widget.configure(image='')
        widget._metadata_icon = None
    if text is not None:
        widget.configure(text=text)


@lru_cache(maxsize=64)
def _tinted(key, rgb):
    from PIL import Image

    with Image.open(
        Path(__file__).parent / 'assets' / 'platforms' / (key + '.png')
    ) as source:
        result = Image.new('RGBA', source.size, (*rgb, 255))
        result.putalpha(source.getchannel('A'))
        return result


def apply_tree_badge(tree, item, record):
    from tkinter import ttk
    from PIL import ImageTk

    key = provider(record)
    if not key:
        tree.item(item, image='')
        return
    color = ttk.Style(tree).lookup('Treeview', 'foreground') or '#9baec5'
    rgb = tuple(v // 257 for v in tree.winfo_rgb(color))
    cache = getattr(tree, '_metadata_icons', None)
    if cache is None:
        cache = tree._metadata_icons = {}
    if (key, rgb) not in cache:
        from PIL import Image

        cache[key, rgb] = ImageTk.PhotoImage(
            _tinted(key, rgb).resize((18, 18), Image.Resampling.LANCZOS), master=tree
        )
    tree.item(item, image=cache[key, rgb])
