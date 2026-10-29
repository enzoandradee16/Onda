"""Resolve the same music, direct-media and collection inputs for both players."""
import re
from urllib.parse import urlsplit,parse_qs,urljoin

PLACEHOLDER='Música, artista ou link de música, álbum ou playlist'

def collection_url(value):
    text=value.strip()
    if re.fullmatch(r'spotify:(album|playlist):[A-Za-z0-9]{22}',text):
        _,kind,identity=text.split(':');return 'https://open.spotify.com/'+kind+'/'+identity
    try:
        parsed=urlsplit(text);host=(parsed.hostname or '').lower().rstrip('.')
        if parsed.scheme not in ('http','https') or parsed.username or parsed.password:return ''
        if host in ('music.apple.com','itunes.apple.com') and parse_qs(parsed.query).get('i'):return ''
        parts=parsed.path.strip('/').split('/')
        if parts and (parts[0].startswith('intl-') or re.fullmatch('[a-z]{2}',parts[0])):parts=parts[1:]
        if host in ('open.spotify.com','deezer.com','www.deezer.com','music.apple.com','itunes.apple.com') and any(kind in parts for kind in ('album','playlist')):return text
        if host in ('youtube.com','www.youtube.com','music.youtube.com','youtu.be') and parse_qs(parsed.query).get('list'):return text
    except ValueError:pass
    return ''

def resolve_input(query,client,config=None,account=None,cancelled=lambda:False):
    from metadata import is_streaming_link,MetadataError
    config=config or {};text=query.strip()
    if not text:raise MetadataError('Informe uma música, álbum, playlist ou link.')
    if cancelled():raise InterruptedError('Pesquisa cancelada.')
    if text.startswith(('http://','https://')):
        from engine import validate_url
        from media_links import unwrap_google
        text=unwrap_google(text)
        parsed=urlsplit(text)
        if parsed.username or parsed.password or any(c.isspace() for c in text):raise MetadataError('Não coloque senhas ou espaços no link.')
        if not is_streaming_link(text):text=validate_url(text)
        host=(urlsplit(text).hostname or '').lower()
        if host in ('spotify.link','deezer.page.link','link.deezer.com'):
            allowed={'spotify.link','open.spotify.com'} if host=='spotify.link' else {'deezer.page.link','link.deezer.com','deezer.com','www.deezer.com'}
            for _ in range(6):
                parsed=urlsplit(text);host=(parsed.hostname or '').lower()
                if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443) or host not in allowed:raise MetadataError('O link curto não aponta para uma página de catálogo válida.')
                if host not in ('spotify.link','deezer.page.link','link.deezer.com'):break
                with client.request(text) as response:
                    location=response.headers.get('Location')
                    if not response.is_redirect or not location:raise MetadataError('Não foi possível resolver o link curto. Copie o link completo da música, álbum ou playlist.')
                    text=urljoin(text,location)
            else:raise MetadataError('Muitos redirecionamentos. Use o link completo da música, álbum ou playlist.')
    collection=collection_url(text)
    if collection:
        from playlist_import import load_interactive_playlist
        result=load_interactive_playlist(collection,client,limit=int(config.get('playlist_limit',2000)),account=account,cancelled=cancelled,playback=True)
        from catalog_details import collection_artwork
        return dict(collection_artwork(result),is_collection=True)
    if text.startswith(('http://','https://')) and not is_streaming_link(text):
        return {'tracks':[{'title':text,'artists':[],'source_url':text,'_jukebox_direct':True}],'is_collection':False}
    from music_search import search_music
    result=search_music(client,text,config.get('catalog_provider',config.get('provider','Deezer')),account=account,automatic=True,limit=12,cancelled=cancelled)
    return dict(result,is_collection=False)
