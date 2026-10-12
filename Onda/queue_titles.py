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


def resolve_name(url, credentials, cookies):
    from metadata import MetadataClient, is_streaming_link
    if is_streaming_link(url):
        client = MetadataClient(*credentials)
        try:
            return record_name(client.resolve(url))
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
    return record_name({'title': info.get('title'), 'artists': [info['artist']] if info.get('artist') else []})


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
                name = resolve_name(url, credentials, cookies)
                if name and not self.stopped.is_set():
                    self.events.put((item, {'type': 'queue_title', 'url': url, 'title': name}))
            except Exception:
                # The normal download still works if this optional lookup fails.
                pass

    def shutdown(self):
        self.stopped.set()
