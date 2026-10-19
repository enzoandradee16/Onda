"""Resolve recorded download identities into browser links, never local commands."""
import re
from urllib.parse import urlsplit

def history_origin(value):
    value=str(value or '').strip()
    match=re.fullmatch(r'(spotify|deezer):(track|album|playlist):([A-Za-z0-9_-]+)',value)
    if match:
        platform,kind,identifier=match.groups()
        return ('https://open.spotify.com/' if platform=='spotify' else 'https://www.deezer.com/')+kind+'/'+identifier
    match=re.fullmatch(r'youtube:(video|playlist):([A-Za-z0-9_-]+)',value)
    if match:return 'https://www.youtube.com/'+('watch?v=' if match[1]=='video' else 'playlist?list=')+match[2]
    try:
        url=urlsplit(value)
        if url.scheme in ('http','https') and url.hostname and not url.username and not url.password:return value
    except ValueError:pass
    return ''
