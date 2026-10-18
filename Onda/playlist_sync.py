"""Conservative, offline collection reconciliation shared by desktop and Android."""
import json
import math
import re
import sqlite3
import unicodedata
from pathlib import Path
from collections import defaultdict
from contextlib import closing
from duplicate_links import source_key,job_source

MEDIA_EXTENSIONS={'.mp3','.m4a','.flac','.wav','.ogg','.opus','.aac','.mp4','.mkv','.webm','.mov'}

def normalized(value):
    return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',str(value or '')).casefold()))

def duration(record):
    try:
        value=float(record.get('duration') or float(record.get('duration_ms') or 0)/1000)
        return value if math.isfinite(value) and value>0 else 0
    except (TypeError,ValueError):return 0

def reconcile(tracks,inventory,queued=(),previous=None):
    sources=defaultdict(list);codes=defaultdict(list);titles=defaultdict(list);names=defaultdict(list)
    for item in inventory:
        if item.get('source_url'):sources[source_key(item['source_url'])].append(item)
        if item.get('isrc'):codes[normalized(item['isrc'])].append(item)
        if item.get('title'):titles[normalized(item['title'])].append(item)
        filename=item.get('filename') or Path(item.get('path','')).name
        if filename:names[normalized(Path(filename).stem)].append(item)
    queue={job_source(item) for item in queued if item.get('state') not in ('Concluído','Concluido')}
    old={source_key(url) for url in previous or []}
    result=[]
    counts={key:0 for key in ('present','missing','review','queued')}
    for index,record in enumerate(tracks):
        key=source_key(record.get('source_url'))
        exact=sources.get(key,[]) if key else []
        filename_matches=list(names.get(normalized(record.get('title')),[]))
        for artist in record.get('artists',[]):
            filename_matches+=names.get(normalized(artist+' - '+str(record.get('title') or '')),[])
        candidates=exact or codes.get(normalized(record.get('isrc')),[]) or titles.get(normalized(record.get('title')),[]) or filename_matches
        confirmed=[];uncertain=[]
        for item in candidates:
            if item.get('uncertain'):
                uncertain.append(item);continue
            if item in exact:
                confirmed.append(item);continue
            same_title=normalized(record.get('title'))==normalized(item.get('title'))
            artists={normalized(a) for a in record.get('artists',[]) if a}
            local_artists={normalized(a) for a in item.get('artists',[]) if a}
            same_album=bool(record.get('album')) and normalized(record['album'])==normalized(item.get('album'))
            length=duration(record);local_length=duration(item)
            same_duration=bool(length and local_length and abs(length-local_length)<=2)
            if same_title and artists and artists==local_artists and same_album and same_duration:
                confirmed.append(item)
            else:uncertain.append(item)
        if confirmed:state='present';reason='Origem ou metadados confirmados';files=confirmed
        elif key and key in queue:state='queued';reason='Já existe na fila; confira o estado do item';files=[]
        elif uncertain:state='review';reason='Identidade, edição ou acesso ao arquivo exige revisão';files=uncertain
        else:state='missing';reason='Nenhum arquivo correspondente encontrado';files=[]
        counts[state]+=1
        result.append({'index':index,'state':state,'reason':reason,'is_new':previous is not None and bool(key) and key not in old,
                       'paths':[item.get('path','') for item in files]})
    return {'items':result,'counts':counts,'has_previous':previous is not None,
            'new_count':sum(row['is_new'] for row in result),
            'removed_count':len(old-{source_key(row.get('source_url')) for row in tracks})}

def compare_collection(tracks,inventory,queued=(),source='',database=None):
    # Snapshots track collection membership, never imply a file was downloaded.
    key=source_key(source);previous=None
    if key and database:
        with closing(sqlite3.connect(str(database),timeout=5)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS collection_snapshots (source TEXT PRIMARY KEY, tracks TEXT NOT NULL)')
            row=db.execute('SELECT tracks FROM collection_snapshots WHERE source=?',(key,)).fetchone()
            if row:previous=json.loads(row[0])
    result=reconcile(tracks,inventory,queued,previous)
    if key and database:
        with closing(sqlite3.connect(str(database),timeout=5)) as db, db:
            db.execute('INSERT OR REPLACE INTO collection_snapshots VALUES (?,?)',(key,json.dumps([row.get('source_url','') for row in tracks])))
    return result

def scan_folder(folder,history=(),cancelled=lambda:False):
    from audio_library import read_audio,AUDIO_TYPES
    root=Path(folder).resolve()
    if not root.is_dir():raise ValueError('Escolha uma pasta de músicas acessível.')
    paths={};inventory=[]
    for row in history:
        path=Path(row['path'])
        try:
            if not path.is_file() or path.stat().st_size==0:continue
        except OSError:
            inventory.append({'path':str(path),'source_url':row.get('source',''),'uncertain':True});continue
        paths.setdefault(str(path.resolve()),{'path':str(path),'source_url':row.get('source','')})
    import os
    def fail(error):raise error
    for base,dirs,files in os.walk(root,onerror=fail,followlinks=False):
        dirs[:]=[name for name in dirs if name not in ('.onda-work','.git','_runtime') and not Path(base,name).is_symlink()]
        for name in files:
            if cancelled():raise InterruptedError('Conferência cancelada.')
            path=Path(base,name)
            if path.suffix.lower() not in MEDIA_EXTENSIONS or path.is_symlink():continue
            if path.stat().st_size==0:continue
            paths.setdefault(str(path.resolve()),{'path':str(path)})
    for item in paths.values():
        if cancelled():raise InterruptedError('Conferência cancelada.')
        path=Path(item['path'])
        item['title']=path.stem
        try:
            if path.suffix.lower() in AUDIO_TYPES:item.update(read_audio(path))
            sidecar=path.with_suffix(path.suffix+'.metadata.json')
            if sidecar.is_file() and sidecar.stat().st_size<=1024*1024:
                record=json.loads(sidecar.read_text(encoding='utf-8')).get('catalog',{})
                if isinstance(record,dict):
                    for key in ('source_url','isrc','title','artists','album','duration'):
                        if record.get(key):item[key]=record[key]
        except (OSError,ValueError,TypeError):
            item['uncertain']=True
        inventory.append(item)
    return inventory
