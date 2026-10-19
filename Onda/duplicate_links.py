"""Stable source identities: ignore sharing parameters, never guess by title."""
import re
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit


def source_key(value):
    value = str(value or '').strip()
    match = re.fullmatch(r'spotify:(track|album|playlist):([A-Za-z0-9]+)', value)
    if match:
        return 'spotify:' + match[1] + ':' + match[2]
    try:
        url = urlsplit(value)
        host = (url.hostname or '').lower().removeprefix('www.').removeprefix('m.')
        path = url.path.rstrip('/')
        query = parse_qs(url.query)
        if host == 'open.spotify.com':
            match = re.fullmatch(r'(?:/intl-[^/]+)?/(track|album|playlist)/([A-Za-z0-9]+)', path)
            if match:
                return 'spotify:' + match[1] + ':' + match[2]
        if host in ('youtu.be', 'youtube.com', 'music.youtube.com'):
            video = path.lstrip('/') if host == 'youtu.be' else query.get('v', [''])[0]
            if not video and path.startswith(('/shorts/', '/embed/', '/live/')):
                video = path.split('/')[2]
            if video:
                return 'youtube:video:' + video
            if query.get('list'):
                return 'youtube:playlist:' + query['list'][0]
        if host in ('deezer.com', 'deezer.page.link'):
            match = re.fullmatch(r'(?:/[a-z]{2})?/(track|album|playlist)/(\d+)', path)
            if match:
                return 'deezer:' + match[1] + ':' + match[2]
        tracking = {'si', 'fbclid', 'gclid', 'igsh', 'igshid'}
        pairs = sorted((k, v) for k, v in parse_qsl(url.query, keep_blank_values=True)
                       if k.lower() not in tracking and not k.lower().startswith('utm_'))
        if url.scheme in ('http', 'https') and host:
            # Unknown providers may distinguish scheme, subdomain, credentials and trailing slash.
            return urlunsplit((url.scheme, url.netloc, url.path, urlencode(pairs), ''))
    except ValueError:
        pass
    return value


def job_source(job):
    if job.get('playlist'):
        try:
            url = urlsplit(job.get('url', ''))
            host = (url.hostname or '').lower().removeprefix('www.').removeprefix('m.')
            query = parse_qs(url.query)
        except ValueError:
            query, host = {}, ''
        if host in ('youtu.be', 'youtube.com', 'music.youtube.com') and query.get('list'):
            return 'youtube:playlist:' + query['list'][0]
    return source_key(job.get('selected_catalog_url') or job.get('url'))


def duplicate_job(first, second):
    # Different formats, playlists, exports and selected catalog versions remain independent.
    return (not first.get('_operation') and not second.get('_operation')
            and bool(job_source(first)) and job_source(first) == job_source(second)
            and str(first.get('mode', '')).lower() == str(second.get('mode', '')).lower()
            and bool(first.get('playlist')) == bool(second.get('playlist'))
            and first.get('playlist_title', '') == second.get('playlist_title', '')
            and all(first.get(key) == second.get(key) for key in ('audio_quality', 'height', 'fps', 'image_options')))


def queue_duplicate_key(job):
    """Hashable equivalent of duplicate_job, built once per queued item in a batch."""
    if job.get('_operation'):return None
    source=job_source(job)
    if not source:return None
    def freeze(value):
        if isinstance(value,dict):return ('dict',frozenset((key,freeze(item)) for key,item in value.items()))
        if isinstance(value,list):return ('list',tuple(map(freeze,value)))
        if isinstance(value,tuple):return ('tuple',tuple(map(freeze,value)))
        return value
    return (source,str(job.get('mode','')).lower(),bool(job.get('playlist')),freeze(job.get('playlist_title','')),
            *(freeze(job.get(key)) for key in ('audio_quality','height','fps','image_options')))
