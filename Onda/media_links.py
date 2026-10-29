"""Resolve public web media without treating search results as files."""

from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import parse_qs, urljoin, urlsplit, unquote


def unwrap_google(url):
    for _ in range(5):
        parsed = urlsplit(url)
        host = (parsed.hostname or '').lower()
        if not re.fullmatch(
            r'(?:www\.)?google\.(?:com|[a-z]{2}|com\.[a-z]{2}|co\.[a-z]{2})', host
        ):
            break
        query = parse_qs(parsed.query)
        keys = (
            ('imgurl',)
            if parsed.path == '/imgres'
            else ('url', 'q') if parsed.path == '/url' else ()
        )
        target = next((query[k][0] for k in keys if query.get(k)), '')
        if not target.startswith(('https://', 'http://')) or target == url:
            break
        url = target
    return url


class MediaPage(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base, self.items, self.container = base, [], None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        kind, value = None, None
        if tag in ('video', 'audio'):
            self.container = tag
            kind, value = tag, attrs.get('src')
        elif tag == 'source' and self.container:
            kind, value = self.container, attrs.get('src')
        elif tag == 'meta':
            prop = attrs.get('property', attrs.get('name', '')).lower()
            if prop in (
                'og:video',
                'og:video:url',
                'og:video:secure_url',
                'og:audio',
                'og:audio:url',
                'og:image',
                'og:image:secure_url',
            ):
                kind, value = prop.split(':')[1], attrs.get('content')
        if value:
            target = urljoin(self.base, value)
            if (
                target.startswith(('http://', 'https://'))
                and (kind, target) not in self.items
            ):
                self.items.append((kind, target))

    def handle_endtag(self, tag):
        if tag in ('video', 'audio'):
            self.container = None


def prepare_link(config, emit, ask_duplicate):
    """Return (finished, media_url). Known site extractors keep their normal flow."""
    from social_media import session_for, save_media, IMAGES
    from yt_dlp.extractor import gen_extractor_classes

    url = config['url']
    parsed = urlsplit(url)
    drive = parsed.hostname in ('drive.google.com', 'docs.google.com')
    known = any(
        cls.IE_NAME != 'generic' and cls.suitable(url)
        for cls in gen_extractor_classes()
    )
    if known and not drive:
        return False, url
    probe = url
    if drive:
        match = re.search(r'/file/d/([\w-]+)', parsed.path)
        identity = (
            match.group(1) if match else parse_qs(parsed.query).get('id', [''])[0]
        )
        if not re.fullmatch(r'[\w-]+', identity):
            return False, url
        probe = 'https://drive.google.com/uc?export=download&id=' + identity
        resource = parse_qs(parsed.query).get('resourcekey', [''])[0]
        if resource:
            from urllib.parse import urlencode

            probe += '&' + urlencode({'resourcekey': resource})
    with session_for(config.get('cookies_file', '')) as session:
        for _ in range(3):
            try:
                with session.get(probe, stream=True, timeout=(15, 20)) as response:
                    response.raise_for_status()
                    mime = (
                        response.headers.get('Content-Type', '')
                        .split(';')[0]
                        .strip()
                        .lower()
                    )
                    target = response.url
                    if mime.startswith('image/'):
                        ext = {
                            'image/jpeg': 'jpg',
                            'image/png': 'png',
                            'image/webp': 'webp',
                            'image/gif': 'gif',
                            'image/avif': 'avif',
                            'image/heic': 'heic',
                        }.get(mime)
                        if ext not in IMAGES:
                            raise ValueError(
                                'Formato de imagem ainda não suportado: ' + mime
                            )
                        filename = unquote(Path(urlsplit(target).path).name)
                        header = response.headers.get('Content-Disposition', '')
                        named = re.search(r'filename="([^"\r\n]+)"', header)
                        if named:
                            filename = named.group(1)
                        title = Path(filename).stem or 'Imagem'
                        # Close the probe before opening the actual streaming transfer.
                        response.close()
                        emit(
                            'log',
                            message='Imagem reconhecida automaticamente; preservando o arquivo original.',
                        )
                        emit(
                            'media_detected',
                            count=1,
                            photos=1,
                            videos=0,
                            selected=1,
                            mode='photos',
                        )
                        path = save_media(
                            session,
                            target,
                            {'extension': ext, 'title': title, 'user': parsed.hostname},
                            dict(config, mode='photos'),
                            emit,
                            ask_duplicate,
                            1,
                        )
                        emit('done', files=[path])
                        return True, target
                    if mime.startswith(('audio/', 'video/')) or mime in (
                        'application/vnd.apple.mpegurl',
                        'application/x-mpegurl',
                        'application/dash+xml',
                    ):
                        if config['mode'] in ('photos', 'social'):
                            config['mode'] = (
                                'original' if mime.startswith('audio/') else 'mp4'
                            )
                            emit(
                                'log',
                                message='Mídia reconhecida automaticamente: '
                                + config['mode'].upper(),
                            )
                        return False, target
                    if mime in ('text/html', 'application/xhtml+xml'):
                        content = bytearray()
                        for chunk in response.iter_content(65536):
                            content.extend(chunk)
                            if len(content) >= 1024 * 1024:
                                break
                        page = MediaPage(target)
                        page.feed(
                            content.decode(
                                response.encoding or 'utf-8', errors='replace'
                            )
                        )
                        choices = [v for k, v in page.items if k in ('video', 'audio')]
                        if not choices and config['mode'] == 'photos':
                            choices = [v for k, v in page.items if k == 'image']
                        if choices and choices[0] != probe:
                            probe = choices[0]
                            emit(
                                'stage',
                                message='Reconhecendo a mídia incorporada na página…',
                            )
                            continue
            except Exception as exc:
                # Preserve the generic extractor's authentication/recovery behavior.
                import requests

                if not isinstance(exc, requests.RequestException):
                    raise
            break
    if config['mode'] in ('photos', 'social') and not known:
        if config['mode'] == 'photos':
            raise ValueError(
                'Não foi encontrada uma imagem acessível. Cole o link original da imagem (no Google Imagens, use “Abrir imagem em nova guia”), ou um link público do arquivo. Uma pesquisa do Google não é um arquivo de mídia.'
            )
        config['mode'] = 'mp4'
    return False, url
