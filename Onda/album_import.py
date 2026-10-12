"""Album track enumeration; all audio uses the existing YouTube workflow."""
import json
import re
from metadata import MetadataError, base_record, spotify_record, deezer_record, apple_record
from spotify_public import EmbedParser


def finish(title, rows, total, limit, note, album_artists=None):
    if not rows:raise MetadataError('Nenhuma faixa disponível neste álbum ou região.')
    if isinstance(total,int) and len(rows)<total:
        note+=f' Carregadas {len(rows)} de {total} faixas; limite ou disponibilidade do catálogo.'
    title = title or 'Álbum'
    artists = album_artists or rows[0].get('album_artists') or rows[0].get('artists') or ['Artista desconhecido']
    artist = ', '.join(name for name in artists if isinstance(name, str) and name.strip()) or 'Artista desconhecido'
    return {'title':title,'tracks':rows[:limit],'note':note,'kind':'album',
            'folder_title':f'{artist} - {title}'}


def spotify_public_album(html, identity, limit):
    parser=EmbedParser();parser.feed(html)
    try:
        entity=json.loads(''.join(parser.parts))['props']['pageProps']['state']['data']['entity']
        if entity.get('type')!='album' or entity.get('id')!=identity:raise ValueError()
        tracks=entity.get('trackList')
        if not isinstance(tracks,list):raise ValueError()
        images=(entity.get('visualIdentity') or {}).get('image') or []
        images=[image for image in images if isinstance(image,dict) and isinstance(image.get('url'),str)]
        cover=max(images,key=lambda image:image.get('maxHeight') or 0).get('url') if images else None
        records=[]
        for number,row in enumerate(tracks[:limit],1):
            if not isinstance(row,dict):continue
            match=re.fullmatch(r'spotify:track:([A-Za-z0-9]{22})',row.get('uri',''))
            if not match or not row.get('title'):continue
            record=base_record('Spotify',match[1],'https://open.spotify.com/track/'+match[1],'Spotify Embed público')
            artists=[part.strip() for part in str(row.get('subtitle') or entity.get('subtitle') or '').replace('\ufffd',' ').split(',') if part.strip()]
            if not artists:continue
            record.update(title=row['title'],artists=artists,album=entity.get('title'),duration_ms=row.get('duration'),
                          cover_url=cover,track_number=number,explicit=row.get('isExplicit'),preview_url=(row.get('audioPreview') or {}).get('url'))
            record['notes'].append('Metadados do álbum público; numeração pela ordem da lista. Alguns campos podem não estar disponíveis.')
            records.append(record)
        return finish(entity.get('title'),records,len(tracks),limit,'Álbum Spotify público. A página pública pode omitir faixas; conecte Spotify se a lista estiver incompleta.', album_artists=[entity['subtitle']] if entity.get('subtitle') else None)
    except (ValueError,KeyError,TypeError,AttributeError):
        raise MetadataError('Álbum indisponível na página pública Spotify. Tente Conectar Spotify ou use o link do mesmo álbum no Deezer/Apple.') from None


def load_album(parsed, client, limit, account=None, cancelled=lambda:False):
    if cancelled():
        raise MetadataError('Carregamento cancelado.')
    host=(parsed.hostname or '').lower()
    parts=parsed.path.strip('/').split('/')
    if host in ('deezer.com','www.deezer.com'):
        if parts and re.fullmatch('[a-z]{2}',parts[0]):parts=parts[1:]
        if not parts or parts[0]!='album':return None
        if len(parts)!=2 or not parts[1].isdigit():raise MetadataError('Use o link Deezer /album/ID.')
        identity=parts[1]
        meta=client.get_json('https://api.deezer.com/album/'+identity)
        if meta.get('error'):raise MetadataError('Álbum Deezer indisponível.')
        records,offset=[],0
        while offset<limit:
            if cancelled():raise MetadataError('Carregamento cancelado.')
            page=client.get_json(f'https://api.deezer.com/album/{identity}/tracks',params={'index':offset,'limit':min(100,limit-offset)})
            if page.get('error') or not isinstance(page.get('data'),list):raise MetadataError('Não foi possível ler as faixas do álbum Deezer.')
            rows=page['data']
            for row in rows[:limit-offset]:
                if not isinstance(row,dict) or not str(row.get('id','')).isdigit() or not row.get('title'):continue
                row={**row,'album':{'title':meta.get('title'),'cover_xl':meta.get('cover_xl')},'release_date':meta.get('release_date')}
                record=deezer_record(row,str(row['id']),'https://www.deezer.com/track/'+str(row['id']))
                records.append(record)
            offset+=len(rows)
            if not rows or not page.get('next'):break
        return finish(meta.get('title'),records,meta.get('nb_tracks'),limit,'Álbum Deezer; ordem original das faixas.', album_artists=[meta['artist']['name']] if (meta.get('artist') or {}).get('name') else None)
    if host=='open.spotify.com':
        if parts and (parts[0].startswith('intl-') or parts[0]=='embed'):parts=parts[1:]
        if not parts or parts[0]!='album':return None
        if len(parts)!=2 or not re.fullmatch('[A-Za-z0-9]{22}',parts[1]):raise MetadataError('Use o link Spotify /album/ID.')
        identity=parts[1]
        getter=None
        if account is not None and account.connected:
            getter=account.get
        elif client.client_id and client.client_secret:
            getter=lambda path,params=None:client.get_json('https://api.spotify.com/v1/'+path,params=params,headers={'Authorization':'Bearer '+client.spotify_token()})
        if getter:
            try:
                meta=getter('albums/'+identity)
                if meta.get('id')!=identity or not meta.get('name'):raise MetadataError('Resposta de álbum Spotify inválida.')
                records,offset=[],0
                while offset<limit:
                    if cancelled():raise MetadataError('Carregamento cancelado.')
                    page=getter(f'albums/{identity}/tracks',{'offset':offset,'limit':min(50,limit-offset),'market':'BR'})
                    rows=page.get('items')
                    if not isinstance(rows,list):raise MetadataError('Resposta de faixas Spotify inválida.')
                    for row in rows[:limit-offset]:
                        if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not re.fullmatch('[A-Za-z0-9]{22}',row['id']) or not row.get('name'):continue
                        record=spotify_record({**row,'album':meta},row['id'],'https://open.spotify.com/track/'+row['id'])
                        if record['artists']:records.append(record)
                    offset+=len(rows)
                    if not rows or not page.get('next'):break
                return finish(meta['name'],records,meta.get('total_tracks'),limit,'Álbum Spotify via API; ordem e edição originais.', album_artists=[artist['name'] for artist in meta.get('artists', []) if artist.get('name')])
            except MetadataError:
                if cancelled():raise
        with client.request('https://open.spotify.com/embed/album/'+identity) as response:
            if response.is_redirect:raise MetadataError('Spotify redirecionou a consulta do álbum.')
            return spotify_public_album(response.text,identity,limit)
    if host in ('music.apple.com','itunes.apple.com'):
        if len(parts)<3 or parts[1]!='album':return None
        country=parts[0].lower()
        identity=parts[-1].removeprefix('id')
        if not re.fullmatch('[a-z]{2}',country) or not identity.isdigit():raise MetadataError('Use o link Apple Music /br/album/nome/ID.')
        data=client.get_json('https://itunes.apple.com/lookup',params={'id':identity,'country':country,'entity':'song','limit':min(limit,200)})
        rows=data.get('results')
        if not isinstance(rows,list):raise MetadataError('Resposta de álbum Apple inválida.')
        album=next((row for row in rows if isinstance(row,dict) and row.get('wrapperType')=='collection' and str(row.get('collectionId'))==identity),None)
        if not album:raise MetadataError('Álbum não encontrado no catálogo público iTunes desta região.')
        songs=[row for row in rows if isinstance(row,dict) and row.get('kind')=='song' and str(row.get('collectionId'))==identity and str(row.get('trackId','')).isdigit()]
        songs.sort(key=lambda row:(row.get('discNumber') or 1,row.get('trackNumber') or 0))
        records=[apple_record({'results':[row]},str(row['trackId']),f"https://music.apple.com/{country}/song/{row['trackId']}") for row in songs[:limit]]
        return finish(album.get('collectionName'),records,album.get('trackCount'),limit,'Álbum Apple / iTunes. A API pública retorna até 200 faixas e depende da região.', album_artists=[album['artistName']] if album.get('artistName') else None)
    return None
