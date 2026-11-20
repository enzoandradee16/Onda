"""Versioned text-tag transfer. Pasting never writes an audio file."""

import json
from audio_library import FIELDS

LIMIT = 256 * 1024


def validate(tags):
    if not isinstance(tags, dict) or not tags or set(tags) - set(FIELDS):
        raise ValueError('Copie as tags de uma música no ONDA primeiro.')
    for key, value in tags.items():
        if key == 'artists':
            valid = (
                isinstance(value, list)
                and len(value) <= 128
                and all(isinstance(part, str) and len(part) <= 4096 for part in value)
            )
        else:
            valid = isinstance(value, str) and len(value) <= 4096
        if not valid:
            raise ValueError('Campo de metadados inválido.')
    return tags


def encode(record):
    tags = {key: value for key, value in record.items() if key in FIELDS}
    if isinstance(tags.get('artists'), str):
        tags['artists'] = [
            part.strip() for part in tags['artists'].split(',') if part.strip()
        ]
    raw = json.dumps(
        dict(format='onda.tags', version=1, tags=validate(tags)), ensure_ascii=False
    )
    if len(raw) > LIMIT:
        raise ValueError('As tags excedem o limite de tamanho.')
    return raw


def decode(raw):
    try:
        if not isinstance(raw, str) or len(raw) > LIMIT:
            raise ValueError()
        data = json.loads(raw)
        if (
            not isinstance(data, dict)
            or data.get('format') != 'onda.tags'
            or type(data.get('version')) is not int
            or data['version'] != 1
        ):
            raise ValueError()
        return validate(data.get('tags'))
    except (ValueError, TypeError):
        raise ValueError('Copie as tags de uma música no ONDA primeiro.') from None
