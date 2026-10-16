"""Names already loaded are immediate; bare music links resolve off the UI thread."""
from urllib.parse import urlsplit
import queue
import threading


def record_name(record):
    title = record.get('title') if isinstance(record, dict) else None
    if not isinstance(title, str) or not title.strip() or title.startswith(('https://', 'http://', 'spotify:')):
        return None
    artists = record.get('artists') or []
    artists = [name.strip() for name in artists if isinstance(name, str) and name.strip()]
    return (( ', '.join(artists) + ' - ') if artists else '') + title.strip()


def supports_lookup(url):
    from metadata import is_streaming_link
    host = (urlsplit(url).hostname or '').lower()
    return is_streaming_link(url) or host in ('youtube.com', 'www.youtube.com', 'music.youtube.com', 'm.youtube.com', 'youtu.be')


def describe_streaming(client, url):
    """Identify the original track without selecting a download from another catalog."""
    from metadata import MetadataError, parse_link
    from urllib.parse import urlsplit
    if (urlsplit(url).hostname or '').lower() == 'spotify.link':
        url = client.resolve_short_link(url)
    # Deezer short links are resolved by fetch itself.
    if (urlsplit(url).hostname or '').lower() in ('link.deezer.com', 'deezer.page.link'):
        return client.fetch(url)
    service, track_id, _, canonical = parse_link(url)
    if service != 'spotify':
        return client.fetch(url)
    partial = None
    failure = None
    try:
        partial = client.fetch(canonical)
        if record_name(partial) and partial.get('artists'):
            return partial
    except MetadataError as error:
        failure = error
    try:
        from spotify_public import parse_public_track
        with client.request('https://open.spotify.com/embed/track/' + track_id) as response:
            if response.is_redirect:
                raise MetadataError('Spotify redirecionou a página pública.')
            embedded=parse_public_track(response.text, track_id, canonical)
            return {**(partial or {}), **{key:value for key,value in embedded.items() if value not in (None,'',[],{})}}
    except MetadataError:
        # A cover/title from oEmbed remains useful even when the embed page is unavailable.
        if record_name(partial):
            return partial
        if failure is not None:
            raise failure
        raise


def resolve_record(url, credentials, cookies,account=None):
    from metadata import MetadataClient, is_streaming_link
    if is_streaming_link(url):
        client = MetadataClient(*credentials)
        if account is not None and account.connected:client.spotify_get=account.get
        try:
            return describe_streaming(client, url)
        finally:
            client.close()
    from yt_dlp import YoutubeDL
    class QuietLogger:
        def debug(self, *_): pass
        def warning(self, *_): pass
        def error(self, *_): pass
    options = {'quiet': True, 'logger': QuietLogger(), 'skip_download': True,
               'extract_flat': True, 'noplaylist': True, 'playlistend': 1,
               'socket_timeout': 8, 'retries': 0, 'extractor_retries': 0,
               'js_runtimes': {'deno': {}, 'node': {}}}
    if cookies:
        options['cookiefile'] = cookies
    with YoutubeDL(options) as downloader:
        info = downloader.extract_info(url, download=False) or {}
    return {'title': info.get('track') or info.get('title'), 'artists': [info.get('artist') or info.get('uploader')] if info.get('artist') or info.get('uploader') else [], 'album': info.get('album'), 'cover_url': info.get('thumbnail'), 'duration_ms': int((info.get('duration') or 0)*1000), 'release_date': info.get('release_date')}


def resolve_name(url, credentials, cookies):
    return record_name(resolve_record(url, credentials, cookies))


class TitleLookup:
    def __init__(self, events):
        self.events = events
        self.requests = queue.Queue(maxsize=128)
        self.stopped = threading.Event()
        self.thread = None

    def submit(self, item, url, credentials, cookies):
        if self.stopped.is_set():
            return
        try:
            self.requests.put_nowait((item, url, credentials, cookies))
        except queue.Full:
            return
        if self.thread is None:
            self.thread = threading.Thread(target=self.run, daemon=True)
            self.thread.start()

    def run(self):
        while not self.stopped.is_set():
            try:
                item, url, credentials, cookies = self.requests.get(timeout=.5)
            except queue.Empty:
                continue
            try:
                record = resolve_record(url, credentials, cookies,account=getattr(self,"spotify_account",None))
                name = record_name(record)
                if name and not self.stopped.is_set():
                    from queue_details import queue_info
                    self.events.put((item, {'type': 'queue_title', 'url': url, 'title': name, 'queue_info': queue_info(record)}))
            except Exception:
                # The normal download still works if this optional lookup fails.
                pass

    def shutdown(self):
        self.stopped.set()
