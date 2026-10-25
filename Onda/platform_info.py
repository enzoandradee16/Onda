"""Offline platform identity for catalog, queue and history cards."""
from functools import lru_cache
import json,re
from pathlib import Path
from urllib.parse import urlsplit

@lru_cache(maxsize=1)
def platforms():
    return json.loads((Path(__file__).parent/'settings_schema/platforms.json').read_text(encoding='utf-8'))

def platform_info(source='',name=''):
    rows=platforms();alias=str(name or '').strip().casefold()
    for row in rows:
        if alias and alias in [value.casefold() for value in [row['key'],row['label'],*row['aliases']]]:return {'platform_key':row['key'],'platform':row['label']}
    value=str(source or '').strip()
    if re.match(r'^(spotify|deezer|youtube):(?:track|album|playlist|video):',value,re.I):return platform_info(name=value.split(':',1)[0])
    try:
        parsed=urlsplit(value)
        if parsed.scheme.lower() not in ('http','https') or parsed.username or parsed.password:return {'platform_key':'','platform':''}
        host=(parsed.hostname or '').lower().rstrip('.')
        if not host:return {'platform_key':'','platform':''}
        for row in rows:
            if any(host==domain or host.endswith('.'+domain) for domain in row['domains']):return {'platform_key':row['key'],'platform':row['label']}
        return {'platform_key':'link','platform':host.removeprefix('www.')}
    except ValueError:return {'platform_key':'','platform':''}

def history_kind(mode,path=''):
    audio={'mp3','m4a','aac','flac','wav','ogg','oga','opus','wma','aiff','aif','alac','m4b'}
    images={'jpg','jpeg','png','webp','svg','gif','avif','heic','heif','bmp','tif','tiff'}
    video={'mp4','mkv','webm','mov','m4v','avi','flv','wmv','mpg','mpeg','3gp','ts'}
    ext=Path(str(path)).suffix.lower().lstrip('.')
    kind=ext if ext in audio|images|video else str(mode).lower().lstrip('.')
    if kind in audio|{'original','audio'}:return 'Áudio'
    if kind in images|{'photos','image','images'}:return 'Imagens'
    return 'Vídeo'
