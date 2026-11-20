"""Lossless native tag transfer where formats agree, portable text/art otherwise."""

import base64
import io
import json
from pathlib import Path

from audio_library import FIELDS, read_audio

MIME = 'application/vnd.onda.tags+json'
LIMIT = 24 * 1024 * 1024
ID3_FIELDS = dict(
    zip(
        (
            'TIT2',
            'TPE1',
            'TALB',
            'TCON',
            'TDRC',
            'TRCK',
            'TPOS',
            'TSRC',
            'TPE2',
            'TCOM',
            'COMM',
        ),
        FIELDS,
    )
)
MP4_FIELDS = dict(
    zip(
        (
            '\xa9nam',
            '\xa9ART',
            '\xa9alb',
            '\xa9gen',
            '\xa9day',
            'trkn',
            'disk',
            '----:com.apple.iTunes:ISRC',
            'aART',
            '\xa9wrt',
            '\xa9cmt',
        ),
        FIELDS,
    )
)
VORBIS_FIELDS = {value: key for key, value in FIELDS.items()}


def _pack(value):
    if isinstance(value, bytes):
        return {
            'bytes': base64.b64encode(value).decode('ascii'),
            'format': int(getattr(value, 'dataformat', 1)),
            'version': int(getattr(value, 'version', 0)),
        }
    if isinstance(value, tuple):
        return {'tuple': [_pack(v) for v in value]}
    if isinstance(value, list):
        return [_pack(v) for v in value]
    if isinstance(value, (str, int, bool)):
        return value
    return str(value)


def _unpack(value, depth=0):
    if depth > 8:
        raise ValueError('Campo de metadados inválido.')
    if isinstance(value, list):
        return [_unpack(v, depth + 1) for v in value]
    if isinstance(value, dict):
        if 'bytes' in value:
            from mutagen.mp4 import MP4FreeForm

            return MP4FreeForm(
                base64.b64decode(value['bytes'], validate=True),
                dataformat=int(value.get('format', 1)),
                version=int(value.get('version', 0)),
            )
        if 'tuple' in value:
            return tuple(_unpack(v, depth + 1) for v in value['tuple'])
        raise ValueError('Campo de metadados inválido.')
    if not isinstance(value, (str, int, bool)):
        raise ValueError('Campo de metadados inválido.')
    return value


def family(audio):
    from mutagen.id3 import ID3
    from mutagen.mp4 import MP4

    return (
        'id3'
        if isinstance(audio.tags, ID3) or audio.__class__.__name__ in ('WAVE', 'MP3')
        else 'mp4' if isinstance(audio, MP4) else 'vorbis'
    )


def snapshot(source, record=None, cover_path='', cover_url='', lyrics_path=''):
    from mutagen import File
    from mutagen.id3 import ID3
    from mutagen.flac import Picture
    from metadata_clipboard import validate

    audio = File(source)
    common = {k: v for k, v in read_audio(source).items() if k in FIELDS}
    original = dict(common)
    common.update({k: v for k, v in (record or {}).items() if k in FIELDS})
    common.pop('comment', None)
    original.pop('comment', None)
    if isinstance(common.get('artists'), str):
        common['artists'] = [
            s.strip() for s in common['artists'].split(',') if s.strip()
        ]
    payload = dict(
        format='onda.tags',
        version=2,
        tags=validate(common),
        native={'family': family(audio), 'tags': original},
        portable={},
        artwork=[],
    )
    native, portable, pictures = (
        payload['native'],
        payload['portable'],
        payload['artwork'],
    )

    def picture(data, mime, kind=3, description=''):
        pictures.append(
            dict(
                data=base64.b64encode(data).decode('ascii'),
                mime=mime,
                type=int(kind),
                description=description,
            )
        )

    if native['family'] == 'id3':
        source_tags = audio.tags or ID3()
        tags = ID3()
        for frame in source_tags.values():
            if frame.FrameID == 'APIC':
                picture(frame.data, frame.mime, frame.type, frame.desc)
            else:
                tags.add(frame)
                if frame.FrameID == 'TXXX':
                    portable[frame.desc] = [str(v) for v in frame.text]
                elif frame.FrameID in ('USLT', 'COMM'):
                    portable['lyrics' if frame.FrameID == 'USLT' else 'comment'] = [
                        str(v)
                        for v in (
                            frame.text if isinstance(frame.text, list) else [frame.text]
                        )
                    ]
        tags.unknown_frames = list(source_tags.unknown_frames)
        output = io.BytesIO()
        tags.save(output)
        native['data'] = base64.b64encode(output.getvalue()).decode('ascii')
    else:
        values = dict(audio.tags or {})
        for cover in values.pop('covr', []):
            picture(
                bytes(cover),
                'image/png' if bytes(cover).startswith(b'\x89PNG') else 'image/jpeg',
            )
        for cover in getattr(audio, 'pictures', []):
            picture(cover.data, cover.mime, cover.type, cover.desc)
        for encoded in values.pop('metadata_block_picture', []):
            cover = Picture(base64.b64decode(encoded))
            picture(cover.data, cover.mime, cover.type, cover.desc)
        native['values'] = {k: _pack(v) for k, v in values.items()}
        mapping = MP4_FIELDS if native['family'] == 'mp4' else VORBIS_FIELDS
        for key, value in values.items():
            if key not in mapping or mapping[key] == 'comment':
                label = (
                    'lyrics'
                    if key == '\xa9lyr'
                    else (
                        'comment'
                        if key == '\xa9cmt'
                        else key.removeprefix('----:com.apple.iTunes:')
                    )
                )
                texts = [
                    (
                        v.decode('utf-8', errors='replace')
                        if isinstance(v, bytes)
                        else str(v)
                    )
                    for v in (value if isinstance(value, (list, tuple)) else [value])
                    if isinstance(v, (str, bytes))
                ]
                if texts:
                    portable[label] = texts
    if cover_path or cover_url:
        from tagging import fetch_cover
        from review import local_cover

        if not cover_path and cover_url.startswith('data:image/'):
            mime = cover_url.split(';', 1)[0][5:]
            data = base64.b64decode(cover_url.split(',', 1)[1], validate=True)
        else:
            data, mime = (
                local_cover(cover_path) if cover_path else fetch_cover(cover_url)
            )
        pictures.clear()
        picture(data, mime)
    if lyrics_path:
        from audio_library import lyrics_text

        payload['lyrics_override'] = lyrics_text(lyrics_path)
    decode(encode(payload))
    return payload


def copy_snapshot(config):
    base = config.get('base_transfer')
    if config.get('base_transfer_path'):
        path = Path(config['base_transfer_path'])
        if path.stat().st_size > LIMIT:
            raise ValueError('As tags excedem o limite de tamanho.')
        base = decode(path.read_text(encoding='utf-8'))
    if not base or base.get('version') == 1:
        return snapshot(
            config['source'],
            config.get('record'),
            config.get('cover_path', ''),
            config.get('cover_url', ''),
            config.get('lyrics_path', ''),
        )
    result = decode(encode(base))
    result['tags'].update(
        {
            k: v
            for k, v in (config.get('record') or {}).items()
            if k in FIELDS and k != 'comment'
        }
    )
    if isinstance(result['tags'].get('artists'), str):
        result['tags']['artists'] = [
            s.strip() for s in result['tags']['artists'].split(',') if s.strip()
        ]
    if config.get('cover_path') or config.get('cover_url'):
        fresh = snapshot(
            config['source'],
            config.get('record'),
            config.get('cover_path', ''),
            config.get('cover_url', ''),
        )
        result['artwork'] = fresh['artwork']
    if config.get('lyrics_path'):
        from audio_library import lyrics_text

        result['lyrics_override'] = lyrics_text(config['lyrics_path'])
    return decode(encode(result))


def encode(payload):
    raw = json.dumps(payload, ensure_ascii=False)
    if len(raw) > LIMIT:
        raise ValueError('As tags excedem o limite de tamanho.')
    return raw


def decode(raw):
    from metadata_clipboard import validate

    try:
        if not isinstance(raw, str) or len(raw) > LIMIT:
            raise ValueError()
        data = json.loads(raw)
        if data.get('format') != 'onda.tags' or data.get('version') not in (1, 2):
            raise ValueError()
        validate(data['tags'])
        if data['version'] == 1:
            return dict(data, native={}, portable={}, artwork=[])
        native = data.get('native', {})
        if native.get('family') not in ('id3', 'mp4', 'vorbis'):
            raise ValueError()
        if (
            len(base64.b64decode(native.get('data', ''), validate=True))
            > 4 * 1024 * 1024
        ):
            raise ValueError()
        if not isinstance(data.get('portable'), dict) or not isinstance(
            data.get('artwork'), list
        ):
            raise ValueError()
        size = 0
        for image in data['artwork']:
            size += len(base64.b64decode(image['data'], validate=True))
            if size > 10 * 1024 * 1024 or not 0 <= int(image.get('type', 3)) <= 20:
                raise ValueError()
        return data
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ValueError('Copie as tags de uma música no ONDA primeiro.') from None


def apply(source, payload, changes, include_art=True, include_extras=True):
    from mutagen import File
    from mutagen.id3 import ID3, APIC, TXXX, USLT, COMM
    from mutagen.mp4 import MP4Cover
    from mutagen.flac import Picture

    payload = decode(encode(payload))
    target = File(source)
    if target.tags is None:
        target.add_tags()
    kind, native = family(target), payload.get('native', {})
    remaining = dict(changes)
    copied = native.get('tags', payload['tags'])
    if native.get('family') == kind:
        mapping = (
            ID3_FIELDS
            if kind == 'id3'
            else MP4_FIELDS if kind == 'mp4' else VORBIS_FIELDS
        )
        values = (
            ID3(fileobj=io.BytesIO(base64.b64decode(native['data'])))
            if kind == 'id3'
            else native.get('values', {})
        )
        for key, value in values.items():
            field = mapping.get(
                value.FrameID
                if kind == 'id3'
                else key.lower() if kind == 'vorbis' else key
            )
            if (not field or field == 'comment') and not include_extras:
                continue
            if (
                field
                and field != 'comment'
                and (field not in changes or changes[field] != copied.get(field))
            ):
                continue
            if kind == 'id3':
                target.tags.delall(value.HashKey)
                target.tags.add(value)
            else:
                target.tags[key] = _unpack(value)
            if field and changes.get(field) == copied.get(field):
                remaining.pop(field, None)
        if kind == 'id3' and include_extras:
            target.tags.unknown_frames = list(
                dict.fromkeys(target.tags.unknown_frames + values.unknown_frames)
            )
    else:
        for label, texts in payload.get('portable', {}).items():
            if not include_extras:
                continue
            if (
                not isinstance(label, str)
                or not isinstance(texts, list)
                or not all(isinstance(v, str) for v in texts)
            ):
                raise ValueError('Campo de metadados inválido.')
            if kind == 'id3':
                frame = (
                    USLT(encoding=3, lang='eng', text='\n'.join(texts))
                    if label == 'lyrics'
                    else (
                        COMM(encoding=3, lang='eng', text=texts)
                        if label == 'comment'
                        else TXXX(encoding=3, desc=label, text=texts)
                    )
                )
                target.tags.delall(frame.HashKey)
                target.tags.add(frame)
            elif kind == 'mp4':
                from mutagen.mp4 import MP4FreeForm

                key = (
                    '\xa9lyr'
                    if label == 'lyrics'
                    else (
                        '\xa9cmt'
                        if label == 'comment'
                        else '----:com.apple.iTunes:' + label
                    )
                )
                target.tags[key] = (
                    texts
                    if label in ('lyrics', 'comment')
                    else [MP4FreeForm(v.encode()) for v in texts]
                )
            else:
                import re

                target.tags[re.sub(r'[^\x20-\x3C\x3E-\x7D]', '_', label)] = texts
    if include_extras and payload.get('lyrics_override') is not None:
        text = payload['lyrics_override']
        if kind == 'id3':
            target.tags.delall('USLT')
            target.tags.add(USLT(encoding=3, lang='eng', text=text))
        else:
            target.tags['\xa9lyr' if kind == 'mp4' else 'lyrics'] = [text]
    if include_art and payload.get('artwork'):
        if kind == 'id3':
            target.tags.delall('APIC')
        elif kind == 'mp4':
            target.tags.pop('covr', None)
        elif hasattr(target, 'clear_pictures'):
            target.clear_pictures()
        elif 'metadata_block_picture' in target.tags:
            del target.tags['metadata_block_picture']
        for image in payload['artwork']:
            data = base64.b64decode(image['data'])
            if kind == 'id3':
                target.tags.add(
                    APIC(
                        encoding=3,
                        mime=image['mime'],
                        type=image['type'],
                        desc=image.get('description', ''),
                        data=data,
                    )
                )
            elif kind == 'mp4':
                target.tags['covr'] = list(target.tags.get('covr', [])) + [
                    MP4Cover(
                        data,
                        imageformat=(
                            MP4Cover.FORMAT_PNG
                            if image['mime'] == 'image/png'
                            else MP4Cover.FORMAT_JPEG
                        ),
                    )
                ]
            else:
                picture = Picture()
                picture.data = data
                picture.mime = image['mime']
                picture.type = image['type']
                picture.desc = image.get('description', '')
                if hasattr(target, 'add_picture'):
                    target.add_picture(picture)
                else:
                    target.tags['metadata_block_picture'] = list(
                        target.tags.get('metadata_block_picture', [])
                    ) + [base64.b64encode(picture.write()).decode()]
    target.save()
    return remaining


def cover_file(payload, folder):
    import tempfile
    from cache_cleanup import linked

    pictures = payload.get('artwork') or []
    if not pictures:
        return ''
    image = next((p for p in pictures if p.get('type') == 3), pictures[0])
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    if linked(folder):
        raise ValueError('Pasta temporária inválida.')
    with tempfile.NamedTemporaryFile(
        prefix='tag-cover-',
        suffix='.png' if image['mime'] == 'image/png' else '.jpg',
        dir=folder,
        delete=False,
    ) as stream:
        stream.write(base64.b64decode(image['data']))
        return stream.name
