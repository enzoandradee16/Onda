"""Small playback queue records for the Qt interface."""

import base64
import hashlib
from pathlib import Path
import tempfile

_artwork_directory = tempfile.TemporaryDirectory(prefix='onda-queue-artwork-')


def artwork_reference(source):
    if not source.startswith('data:image/'):
        return source
    try:
        header, encoded = source.split(',', 1)
        if ';base64' not in header:
            return source
        destination = (
            Path(_artwork_directory.name)
            / hashlib.sha256(source.encode('utf-8')).hexdigest()
        )
        if not destination.exists():
            destination.write_bytes(base64.b64decode(encoded, validate=True))
        return destination.as_uri()
    except (ValueError, OSError):
        return ''


def presentation_rows(rows):
    result = []
    artwork = {}

    def reference(source):
        if source not in artwork:
            artwork[source] = artwork_reference(source)
        return artwork[source]

    fields = (
        'id',
        'title',
        'artist',
        'album',
        'duration',
        'current',
        'analysis',
        'error',
        'queueIndex',
        'section',
        'group',
        'manual',
        'collection',
    )
    for row in rows:
        item = {key: row[key] for key in fields if key in row}
        record = row.get('record') or {}
        item['cover'] = reference(row.get('cover') or '')
        item['record'] = {'cover_url': reference(record.get('cover_url') or '')}
        result.append(item)
    return result
