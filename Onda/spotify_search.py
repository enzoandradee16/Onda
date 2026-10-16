"""Authenticated Spotify catalog search, paginated with fixed API paths."""
import re
from metadata import MetadataError, spotify_record, parse_link, base_record


def search_tracks(query, get, country='br', limit=25):
    if type(limit) is not int or not 1 <= limit <= 50:
        raise MetadataError('Use um limite de busca entre 1 e 50 músicas.')
    records, seen, offset = [], set(), 0
    while offset < limit:
        data = get('search', {'q':query, 'type':'track', 'market':country.upper(), 'limit':min(10, limit-offset), 'offset':offset})
        tracks=data.get('tracks') if isinstance(data,dict) else None
        rows=tracks.get('items') if isinstance(tracks,dict) else None
        if not isinstance(rows,list):
            raise MetadataError('Resposta de busca Spotify inválida.')
        for row in rows[:limit-offset]:
            if not isinstance(row,dict) or row.get('is_local') or row.get('type','track') != 'track':continue
            identity=row.get('id','')
            if not isinstance(identity,str) or not re.fullmatch(r'[A-Za-z0-9]{22}',identity) or identity in seen or not row.get('name'):continue
            record=spotify_record(row,identity,'https://open.spotify.com/track/'+identity)
            if not record['artists']:continue
            seen.add(identity)
            record['preview_url']=row.get('preview_url') if isinstance(row.get('preview_url'),str) and row['preview_url'].startswith('https://') else None
            records.append(record)
        offset+=len(rows)
        if not rows or not tracks.get('next'):break
    return records[:limit]


def cached_record(value, url):
    """Keep only normalized catalog fields, never tokens or account data."""
    if not isinstance(value,dict):
        raise MetadataError('Metadados da busca Spotify inválidos.')
    service,identity,_,canonical=parse_link(url)
    if service!='spotify' or value.get('source_url')!=canonical or value.get('id')!=identity or value.get('platform')!='Spotify' or not isinstance(value.get('title'),str) or not value['title'].strip() or not isinstance(value.get('artists'),list) or not value['artists'] or not all(isinstance(a,str) and a.strip() for a in value['artists']):
        raise MetadataError('Os metadados selecionados não correspondem à faixa Spotify.')
    record=base_record('Spotify',identity,canonical,'Spotify Web API')
    for key in record.keys():
        if key in value:record[key]=value[key]
    # Provenance contains only provider names, public links and field names.
    from spotify_metadata import FIELDS
    sources=value.get('metadata_sources')
    if isinstance(sources,dict):
        record['metadata_sources']={key:{k:row[k] for k in ('platform','source_url') if isinstance(row.get(k),str)} for key,row in sources.items() if key in FIELDS and isinstance(row,dict)}
    supplements=value.get('metadata_supplements')
    if isinstance(supplements,list):
        record['metadata_supplements']=[{'platform':row.get('platform'),'source_url':row.get('source_url'),'fields':[key for key in row.get('fields',[]) if key in FIELDS]} for row in supplements if isinstance(row,dict) and isinstance(row.get('fields'),list)]
    return record
