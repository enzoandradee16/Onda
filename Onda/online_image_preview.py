"""Read-only post discovery and bounded, lazy thumbnail cache shared by both UIs."""

import copy, io, threading, time, uuid
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlsplit

_sessions = OrderedDict()
_lock = threading.RLock()
MAX_BYTES = 16 * 1024 * 1024


def can_preview(config):
    """Offer image galleries for image inputs, never audio/video downloads or covers."""
    path = urlsplit(str(config.get('url', '')).strip()).path.lower()
    if path.endswith(
        ('.mp4', '.mkv', '.webm', '.mov', '.mp3', '.m4a', '.flac', '.wav', '.ogg')
    ):
        return False
    return config.get('mode') in ('photos', 'social') or path.endswith(
        (
            '.jpg',
            '.jpeg',
            '.png',
            '.gif',
            '.webp',
            '.avif',
            '.bmp',
            '.tif',
            '.tiff',
            '.svg',
        )
    )


def check(cancelled):
    if cancelled():
        raise InterruptedError('Prévia cancelada.')


def candidates(url, session, cookies, cancelled):
    from social_media import is_social, kwai_images
    from engine import Logger
    from instagram_media import is_instagram, instagram_items
    from twitter_media import is_twitter, twitter_items

    check(cancelled)
    if is_instagram(url):
        return instagram_items(url, session, cookies, Logger())
    if is_twitter(url):
        return twitter_items(url, session, cookies, Logger())
    host = (urlsplit(url).hostname or '').lower()
    if is_social(url):
        if (
            host.startswith(('vt.', 'vm.', 'k.', 's.'))
            or host in ('kwai-video.com', 'kw.ai')
            or '/share/' in url
        ):
            with session.get(url, stream=True, timeout=(10, 20)) as response:
                response.raise_for_status()
                url = response.url
        check(cancelled)
        host = (urlsplit(url).hostname or '').lower()
        if host == 'tiktok.com' or host.endswith('.tiktok.com'):
            from tiktok_media import tiktok_items

            return tiktok_items(url, session, cookies, Logger())
        if any(
            host == name or host.endswith('.' + name)
            for name in ('kwai.com', 'kwai-video.com', 'kw.ai', 'kuaishou.com')
        ):
            with session.get(url, stream=True, timeout=(10, 20)) as response:
                response.raise_for_status()
                body = read_limited(response, cancelled, 2 * 1024 * 1024)
                return list(
                    kwai_images(
                        body.decode(response.encoding or 'utf-8', errors='replace'),
                        response.url,
                    )
                )
    from gallery_dl import extractor
    from gallery_dl.extractor.common import Message

    source = extractor.find(url)
    if source is not None and getattr(source, 'category', '') != 'directlink':
        if source.subcategory not in (
            'post',
            'reel',
            'image',
            'gallery',
            'album',
            'pin',
            'submission',
            'status',
        ):
            raise ValueError(
                'Cole o link de uma publicação ou carrossel, em vez do perfil completo.'
            )
        # Instance options preserve concurrent downloads' configuration and cookies.
        original = source.config
        options = {
            'timeout': 20,
            'retries': 1,
            'audio': False,
            'videos': False,
            'covers': False,
            'previews': False,
            'cookies': cookies or None,
        }
        source.config = lambda key, default=None: (
            options[key] if key in options else original(key, default)
        )
        from social_media import GalleryLogger

        source.log = GalleryLogger(lambda *args, **kwargs: check(cancelled))
        rows = []
        try:
            for message in source:
                check(cancelled)
                if message[0] != Message.Url:
                    continue
                metadata = dict(message[2])
                headers = dict(source.session.headers or {}) if source.session else {}
                headers.update(metadata.get('_http_headers') or {})
                metadata['_http_headers'] = headers
                rows.append((message[1], metadata))
                if len(rows) >= 100:
                    break
            if source.session:
                session.cookies.update(source.session.cookies)
        finally:
            if source.session:
                source.session.close()
        return rows
    # Probe headers only for direct images. HTML is bounded and never downloaded as media.
    with session.get(url, stream=True, timeout=(10, 20)) as response:
        response.raise_for_status()
        mime = response.headers.get('Content-Type', '').split(';')[0].lower()
        if mime.startswith('image/'):
            return [
                (
                    response.url,
                    {
                        'extension': mime.split('/')[-1],
                        'title': Path(urlsplit(response.url).path).name or 'Imagem',
                    },
                )
            ]
        if mime in ('text/html', 'application/xhtml+xml'):
            from media_links import MediaPage

            body = read_limited(response, cancelled, 2 * 1024 * 1024)
            page = MediaPage(response.url)
            page.feed(body.decode(response.encoding or 'utf-8', errors='replace'))
            return [
                (
                    target,
                    {
                        'extension': 'jpg',
                        'title': 'Imagem',
                        '_http_headers': {'Referer': response.url},
                    },
                )
                for kind, target in page.items
                if kind == 'image'
            ]
    return []


def read_limited(response, cancelled, limit=MAX_BYTES):
    result = bytearray()
    for block in response.iter_content(65536):
        check(cancelled)
        result.extend(block)
        if len(result) > limit:
            raise ValueError(
                'A imagem excede o limite da prévia. Baixe o arquivo para abrir no tamanho original.'
            )
    check(cancelled)
    return bytes(result)


def discard(entry):
    folder = entry['folder']
    for file in folder.glob('*.jpg'):
        try:
            file.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        folder.rmdir()
    except OSError:
        pass


def discover(config, cancelled=lambda: False):
    from engine import validate_url
    from social_media import session_for, IMAGES

    values = [
        line.strip() for line in str(config.get('url', '')).splitlines() if line.strip()
    ]
    if len(values) != 1:
        raise ValueError('Informe um link por vez para visualizar as imagens.')
    url = validate_url(values[0])
    check(cancelled)
    cookies = config.get('cookies_file', '')
    with session_for(cookies) as session:
        rows = candidates(url, session, cookies, cancelled)
        images = []
        seen = set()
        for source, metadata in rows:
            check(cancelled)
            extension = str(
                metadata.get('extension')
                or Path(urlsplit(source).path).suffix.lstrip('.')
            ).lower()
            if (
                extension not in IMAGES | {'svg', 'bmp', 'tiff', 'tif'}
                or source in seen
            ):
                continue
            validate_url(source)
            seen.add(source)
            images.append(
                {
                    'source': source,
                    'headers': dict(metadata.get('_http_headers') or {}),
                    'name': str(metadata.get('title') or 'Imagem'),
                }
            )
            if len(images) >= 100:
                break
        if not images:
            raise ValueError(
                'Nenhuma imagem disponível para prévia neste link. Confira o acesso à publicação ou use o link direto da imagem.'
            )
        check(cancelled)
        token = uuid.uuid4().hex
        folder = Path(config['_root']) / 'online-image-preview' / token
        folder.mkdir(parents=True, exist_ok=True)
        entry = {
            'items': images,
            'cookies': copy.copy(session.cookies),
            'created': time.monotonic(),
            'folder': folder,
            'source': url,
        }
    with _lock:
        for key in list(_sessions):
            if time.monotonic() - _sessions[key]['created'] > 900:
                discard(_sessions.pop(key))
        while len(_sessions) >= 3:
            discard(_sessions.popitem(last=False)[1])
        _sessions[token] = entry
    return {
        'token': token,
        'source_url': url,
        'images': [
            {'id': str(i), 'name': row['name'], 'url': '', 'path': ''}
            for i, row in enumerate(images)
        ],
    }


def thumbnail(token, index, cancelled=lambda: False):
    from social_media import session_for
    from PIL import Image, ImageOps

    check(cancelled)
    with _lock:
        entry = _sessions.get(token)
        if not entry or time.monotonic() - entry['created'] > 900:
            raise ValueError('A prévia expirou. Abra o link novamente.')
        if type(index) is not int or not 0 <= index < len(entry['items']):
            raise ValueError('Imagem inválida para prévia.')
        row = entry['items'][index]
        target = entry['folder'] / (str(index) + '.jpg')
        if target.is_file():
            return {'path': str(target)}
    headers = {
        str(k): str(v)
        for k, v in row['headers'].items()
        if '\n' not in str(k) + str(v) and '\r' not in str(k) + str(v)
    }
    headers.setdefault('Referer', entry['source'])
    with session_for() as session:
        session.cookies.update(entry['cookies'])
        with session.get(
            row['source'], headers=headers, stream=True, timeout=(10, 20)
        ) as response:
            response.raise_for_status()
            data = read_limited(response, cancelled)
    with Image.open(io.BytesIO(data)) as image:
        if image.width * image.height > 40_000_000:
            raise ValueError(
                'A imagem excede o limite da prévia. Baixe o arquivo para abrir no tamanho original.'
            )
        image.thumbnail((1280, 1280))
        picture = ImageOps.exif_transpose(image).convert('RGB')
        check(cancelled)
        # A closed/evicted preview must never recreate its cache directory.
        with _lock:
            if _sessions.get(token) is not entry:
                raise ValueError('A prévia expirou. Abra o link novamente.')
            picture.save(target, 'JPEG', quality=82, optimize=True)
    return {'path': str(target)}


def clear_cache():
    with _lock:
        while _sessions:
            discard(_sessions.popitem(last=False)[1])
