"""Read local history details without a network request or changing files."""

from pathlib import Path
from functools import lru_cache
from audio_library import read_audio, cover_preview


def history_details(path):
    source = Path(path)
    if not source.is_file():
        return {'note': 'Arquivo movido ou removido.', 'cover': ''}
    stat = source.stat()
    return _cached_details(str(source), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=64)
def _cached_details(path, modified, size):
    source = Path(path)
    result = {'size': size, 'cover': ''}
    result['platform'] = history_platform(path)
    try:
        result.update(read_audio(source))
        result['cover'] = cover_preview(str(source))
    except Exception:
        result['note'] = 'Metadados indisponíveis para este arquivo.'
    return result


def detail_lines(record, translate=lambda text: text):
    lines = []
    for key, label in (
        ('album', 'Álbum / single'),
        ('release_date', 'Lançamento'),
        ('genre', 'Gênero'),
        ('track_number', 'Faixa'),
        ('disc_number', 'Disco'),
    ):
        if record.get(key):
            lines.append(f"{translate(label)}: {record[key]}")
    seconds = int(record.get('duration') or 0)
    if seconds:
        lines.append(f'{translate("Duração")}: {seconds//60}:{seconds%60:02d}')
    if record.get('size') is not None:
        lines.append(f"{translate('Tamanho')}: {record['size']/1048576:.1f} MB")
    if record.get('note'):
        lines.append(translate(record['note']))
    return ' · '.join(lines)


def history_platform(path):
    """Read only provenance for compact rows; no audio decoding or artwork loading."""
    import json

    try:
        sidecar = Path(str(path) + '.metadata.json')
        if sidecar.is_file() and sidecar.stat().st_size < 2_000_000:
            data = json.loads(sidecar.read_text(encoding='utf-8'))
            catalog = data.get('catalog', {}) if isinstance(data, dict) else {}
            if isinstance(catalog, dict):
                return str(catalog.get('platform') or '')
    except (ValueError, OSError):
        pass
    return ''
