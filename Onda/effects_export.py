"""Snapshot playback metadata and effects before exporting an untagged PCM cache."""
import base64
import io
from pathlib import Path
import re
import tempfile

from audio_tools import effect_name


def export_config(source,record=None,*,speed=100,reverb=0,keep_pitch=False,enabled=True,cover_data=''):
    from audio_library import read_audio,FIELDS
    record=dict(record or {})
    try:local=read_audio(source)
    except (OSError,ValueError):local={}
    metadata={key:record.get(key) or local.get(key) for key in FIELDS}
    metadata['title']=record.get('media_title') or record.get('title') or local.get('title') or Path(source).stem
    artists=record.get('artists') or record.get('media_artist') or record.get('artist') or local.get('artists') or []
    metadata['artists']=[artists] if isinstance(artists,str) else [str(value) for value in artists]
    metadata={key:value for key,value in metadata.items() if value not in (None,'',[])}
    metadata={key:value if key=='artists' else str(value) for key,value in metadata.items()}
    speed=float(speed) if enabled else 100;reverb=float(reverb) if enabled else 0
    effect=effect_name(speed,reverb)
    name=' - '.join(filter(None,[', '.join(metadata.get('artists',[])),metadata['title'],effect]))
    name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',name).strip(' .')[:200].rstrip(' .') or 'ONDA'
    return dict(source=str(source),speed=speed,reverb=reverb,keep_pitch=bool(keep_pitch),record=metadata,
                cover_data=cover_data,cover_url=record.get('cover_url') or '',export_name=name)


def apply_export_metadata(output,config):
    from audio_library import write_audio,read_audio
    from mutagen import File
    from mutagen.id3 import ID3
    from PIL import Image
    metadata=dict(config.get('record') or {})
    effect=effect_name(config.get('speed',100),config.get('reverb',0))
    if metadata.get('title') and effect:metadata['title']+=' - '+effect
    audio=File(output)
    tags=audio.tags or {}
    has_cover=bool(tags.getall('APIC') if isinstance(tags,ID3) else tags.get('covr') or getattr(audio,'pictures',None) or tags.get('metadata_block_picture'))
    # Preserve full-resolution native artwork when FFmpeg/preserve_tags already kept it.
    data=b''
    if not has_cover:
        encoded=config.get('cover_data') or ''
        if encoded and not encoded.startswith(('https://','http://')):
            data=base64.b64decode(encoded.partition(',')[2] if encoded.startswith('data:') else encoded,validate=True)
        url=config.get('cover_url') or (encoded if encoded.startswith(('https://','http://')) else '')
        if not data and url:
            import requests
            with requests.get(url,stream=True,timeout=15) as response:
                response.raise_for_status()
                for block in response.iter_content(65536):
                    data+=block
                    if len(data)>10*1024*1024:raise ValueError('Capa muito grande.')
    with tempfile.TemporaryDirectory(prefix='onda-export-tags-') as folder:
        cover=''
        if data:
            if len(data)>10*1024*1024:raise ValueError('Capa muito grande.')
            cover=str(Path(folder)/'cover.png')
            with Image.open(io.BytesIO(data)) as image:image.convert('RGB').save(cover,'PNG')
        current=read_audio(output)
        metadata={key:value for key,value in metadata.items() if current.get(key)!=value}
        if metadata or cover:write_audio(output,metadata,cover_path=cover)
