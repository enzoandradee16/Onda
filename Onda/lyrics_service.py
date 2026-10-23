"""Explicit LRCLIB lookup using recording metadata; no page scraping."""
import json
import threading
from audio_library import read_audio
from synced_lyrics import parse_lrc



def timed_record(record):
    """Prefer validated Lyricsfile word cues, retain line LRC on bad input."""
    import yaml
    raw=record.get('lyricsfile')
    if isinstance(raw,str) and len(raw)<=1024*1024:
        try:
            depth=count=0
            for event in yaml.parse(raw):
                count+=1
                if count>50000 or isinstance(event,yaml.AliasEvent):raise ValueError('Invalid lyrics structure')
                if isinstance(event,(yaml.MappingStartEvent,yaml.SequenceStartEvent)):depth+=1
                elif isinstance(event,(yaml.MappingEndEvent,yaml.SequenceEndEvent)):depth-=1
                if depth>12:raise ValueError('Invalid lyrics structure')
            class Loader(yaml.SafeLoader):pass
            def mapping(loader,node):
                pairs=loader.construct_pairs(node)
                result={}
                for key,value in pairs:
                    if key in result:raise ValueError('Duplicate lyrics key')
                    result[key]=value
                return result
            Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
            document=yaml.load(raw,Loader=Loader)
            if not isinstance(document,dict) or str(document.get('version'))!='1.0':raise ValueError('Unsupported lyrics version')
            lines=[];word_sync=False
            for row in document.get('lines',[]):
                start=row['start_ms'];text=row['text']
                if type(start) is not int or start<0 or not isinstance(text,str):raise ValueError('Invalid lyrics timing')
                words=row.get('words') or []
                if words:
                    parts=[];last=-1
                    for word in words:
                        at=word['start_ms'];value=word['text']
                        if type(at) is not int or at<start or at<last or not isinstance(value,str):raise ValueError('Invalid word timing')
                        last=at;parts.append('<'+str(at//60000).zfill(2)+':'+format((at%60000)/1000,'06.3f')+'>'+value)
                    if ''.join(word['text'] for word in words)!=text:raise ValueError('Word text mismatch')
                    text=''.join(parts);word_sync=True
                lines.append((start/1000,text))
            if lines:return sorted(lines,key=lambda row:row[0]),word_sync
        except (yaml.YAMLError,ValueError,TypeError,KeyError,AttributeError):pass
    return parse_lrc(record.get('syncedLyrics') or ''),False

def fetch_lyrics(source,record=None,cancel=None,session=None,alternatives=False):
    import requests
    cancel=cancel or threading.Event()
    record=dict(record or {})
    try:record.update({k:v for k,v in read_audio(source).items() if v})
    except (OSError,ValueError):pass
    title=record.get('media_title') or record.get('title','')
    artists=record.get('artists') or record.get('media_artist') or record.get('artist','')
    artist=', '.join(artists) if isinstance(artists,list) else artists
    if not title or not artist:raise ValueError('Informe título e artista nos metadados antes de buscar a letra.')
    if cancel.is_set():raise ValueError('Busca de letra cancelada.')
    params={'track_name':title,'artist_name':artist}
    if not alternatives and record.get('album'):params['album_name']=record['album']
    duration=record.get('duration') or float(record.get('duration_ms') or 0)/1000
    if duration and not alternatives:params['duration']=round(float(duration))
    client=session or requests
    with client.get('https://lrclib.net/api/'+('search' if alternatives else 'get'),params=params,headers={'User-Agent':'ONDA/1.2 (https://github.com/enzoandradee16/Onda)'},timeout=(10,20),stream=True) as response:
        if response.status_code==404:raise ValueError('Letra não encontrada no LRCLIB para esta gravação.')
        response.raise_for_status()
        data=bytearray()
        for block in response.iter_content(16384):
            if cancel.is_set():raise ValueError('Busca de letra cancelada.')
            data.extend(block)
            if len(data)>1024*1024:raise ValueError('Resposta de letra muito grande.')
    result=json.loads(data)
    if alternatives:
        candidates=[]
        for row in result[:30]:
            timed,word_sync=timed_record(row)
            plain=row.get('plainLyrics') or ''
            if row.get('instrumental') or not (timed or plain):continue
            candidates.append(dict(id=str(row['id']),source_url=str(row['id']),title=str(row.get('trackName') or title)+' · '+str(row.get('artistName') or artist)+' · '+str(row.get('albumName') or '')+' · '+str(round(row.get('duration') or 0))+' s',lines=timed or [(0,plain)],synced=bool(timed),word_synced=word_sync,provider='LRCLIB'))
        return {'candidates':candidates}
    if result.get('instrumental'):raise ValueError('O LRCLIB identifica esta gravação como instrumental.')
    synced=result.get('syncedLyrics') or ''
    rows,word_sync=timed_record(result)
    plain=result.get('plainLyrics') or ''
    if not rows and not plain:raise ValueError('Letra não encontrada no LRCLIB para esta gravação.')
    return {'lines':rows or [(0,plain)],'synced':bool(rows),'word_synced':word_sync,'provider':'LRCLIB'}
