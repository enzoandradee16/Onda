"""Identify jobs which share YouTube's request budget."""
from urllib.parse import urlsplit


def uses_youtube(config):
    try:
        host = (urlsplit(config.get('url', '')).hostname or '').lower().rstrip('.')
    except ValueError:
        return False
    def belongs(domains):
        return any(host == name or host.endswith('.' + name) for name in domains)
    if belongs(('youtube.com', 'youtu.be', 'youtube-nocookie.com')):
        return True
    return config.get('mode') != 'flac' and belongs(
        ('spotify.com', 'spotify.link', 'deezer.com', 'page.link', 'music.apple.com', 'itunes.apple.com'))
