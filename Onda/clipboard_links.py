"""Offline clipboard URL recognition using the application's existing validators."""

import hashlib
import re
from urllib.parse import urlsplit
from duplicate_links import source_key
from media_links import unwrap_google


def recognize_link(text):
    if not isinstance(text, str) or len(text) > 16384:
        return None
    for match in re.finditer(
        r"https?://[^\s<>\"']+|spotify:(?:track|album|playlist):[A-Za-z0-9]+",
        text,
        re.I,
    ):
        url = match[0].rstrip('.,;!?)]}')
        try:
            url = unwrap_google(url)
            if url.startswith("spotify:"):
                _, kind, identity = url.split(":")
                url = "https://open.spotify.com/" + kind + "/" + identity
            from metadata import is_streaming_link, parse_link
            from engine import validate_url

            parsed = urlsplit(url)
            host = (parsed.hostname or '').lower().rstrip('.')
            collection = False
            if is_streaming_link(url):
                if (
                    parsed.username
                    or parsed.password
                    or parsed.port not in (None, 80, 443)
                ):
                    continue
                key = source_key(url)
                collection = bool(
                    re.match(r'(?:spotify|deezer):(album|playlist):', key)
                    or (
                        host in ('music.apple.com', 'itunes.apple.com')
                        and '/album/' in parsed.path
                        and 'i=' not in parsed.query
                    )
                )
                if (
                    collection
                    and host == "open.spotify.com"
                    and not re.fullmatch(
                        r"[A-Za-z0-9]{22}", parsed.path.rstrip("/").split("/")[-1]
                    )
                ):
                    continue
                if not collection and host not in (
                    'spotify.link',
                    'deezer.page.link',
                    'link.deezer.com',
                ):
                    parse_link(url)
            else:
                url = validate_url(url)
                from social_media import is_social

                if is_social(url) and not parsed.path.strip("/") and not parsed.query:
                    continue
                if not is_social(url):
                    from yt_dlp.extractor import gen_extractor_classes

                    media = re.search(
                        r'\.(?:mp4|mkv|webm|mov|m4v|mp3|m4a|aac|flac|wav|ogg|opus|jpg|jpeg|png|webp|gif|avif|m3u8|mpd)$',
                        parsed.path,
                        re.I,
                    )
                    if not media and not any(
                        cls.IE_NAME != 'generic' and cls.suitable(url)
                        for cls in gen_extractor_classes()
                    ):
                        continue
            return {
                'url': url,
                'key': hashlib.sha256(source_key(url).encode()).hexdigest(),
                'collection': collection,
            }
        except (ValueError, TypeError, AttributeError):
            continue
    return None
