"""Read local history details without a network request or changing files."""
from pathlib import Path
from functools import lru_cache
from audio_library import read_audio, cover_preview

def history_details(path):
    source=Path(path)
    if not source.is_file():
        return {'note':'Arquivo movido ou removido.', 'cover':''}
    stat=source.stat()
    return _cached_details(str(source),stat.st_mtime_ns,stat.st_size)


@lru_cache(maxsize=64)
def _cached_details(path, modified, size):
    source=Path(path)
    result={'size':size,'cover':''}
    try:
        result.update(read_audio(source))
        result['cover']=cover_preview(str(source))
    except Exception:
        result['note']='Metadados indisponíveis para este arquivo.'
    return result

def detail_lines(record):
    lines=[]
    for key,label in (('album','Álbum / single'),('release_date','Lançamento'),('genre','Gênero'),('track_number','Faixa'),('disc_number','Disco')):
        if record.get(key):lines.append(f"{label}: {record[key]}")
    seconds=int(record.get('duration') or 0)
    if seconds:lines.append(f'Duração: {seconds//60}:{seconds%60:02d}')
    if record.get('size') is not None:lines.append(f"Tamanho: {record['size']/1048576:.1f} MB")
    if record.get('note'):lines.append(record['note'])
    return ' · '.join(lines)
