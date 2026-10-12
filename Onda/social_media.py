"""Photo and mixed-post downloads through gallery-dl, sharing Onda's queue IPC."""
import hashlib
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

import requests

IMAGES = {"jpg", "jpeg", "png", "webp", "gif", "avif", "heic"}
VIDEOS = {"mp4", "webm", "mov", "m4v"}
SOCIAL = ("twitter.com", "x.com", "instagram.com", "tiktok.com", "kwai.com", "kwai-video.com", "kw.ai", "kuaishou.com")


class GalleryLogger:
    """gallery-dl expects an adapter with traceback(), not a bare Logger."""
    def __init__(self, emit):
        self.emit = emit
        self.errors = []

    def debug(self, message, *args, **kwargs):
        pass

    def info(self, message, *args, **kwargs):
        self.emit("log", message=message % args if args else str(message))

    def warning(self, message, *args, **kwargs):
        self.info("Aviso: " + message, *args)

    def error(self, message, *args, **kwargs):
        value = message % args if args else str(message)
        self.errors.append(value)
        self.emit("log", message="Erro no extrator: " + value)

    def traceback(self, exc):
        # Preserve the cause without dumping request state or cookies.
        self.emit("log", message=f"Detalhe do extrator: {type(exc).__name__}: {exc}")


def is_social(url):
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return any(host == name or host.endswith("." + name) for name in SOCIAL)


def session_for(cookies=""):
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0", "Accept-Encoding": "gzip, deflate"})
    if cookies:
        import http.cookiejar
        jar = http.cookiejar.MozillaCookieJar(cookies)
        try:
            jar.load(ignore_discard=True, ignore_expires=False)
        except (OSError, http.cookiejar.LoadError) as exc:
            session.close()
            raise ValueError("Não foi possível ler cookies.txt no formato Netscape.") from exc
        session.cookies.update(jar)
    return session


class PageData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts, self.current = [], None

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.current = []

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.current is not None:
            self.scripts.append("".join(self.current))
            self.current = None


def kwai_images(html, url):
    """Use only an explicit post atlas; never download a cover as a photo."""
    page = PageData()
    page.feed(html)
    photo_id = (parse_qs(urlsplit(url).query).get("photoId") or [urlsplit(url).path.rstrip("/").split("/")[-1]])[0]
    def walk(value):
        if isinstance(value, dict):
            yield value
            for item in value.values():
                yield from walk(item)
        elif isinstance(value, list):
            for item in value:
                yield from walk(item)
    roots = []
    for script in page.scripts:
        try:
            roots.append(json.loads(script))
        except ValueError:
            for match in re.finditer(r"(?:window\.)?__(?:INIT_STATE|INITIAL_STATE|NEXT_DATA)__\s*=\s*", script):
                try:
                    roots.append(json.JSONDecoder().raw_decode(script[match.end():])[0])
                except ValueError:
                    pass
    for root in roots:
        for node in walk(root):
            if str(node.get("photoId") or node.get("id") or "") != photo_id:
                continue
            atlas = node.get("atlas") or node.get("imagePost") or {}
            images = atlas.get("images") or atlas.get("list") or []
            if not isinstance(images, list):
                continue
            for index, image in enumerate(images, 1):
                value = image if isinstance(image, str) else image.get("url") or image.get("imageUrl") or ""
                if isinstance(value, str) and urlsplit(value).scheme in ("https", "http"):
                    yield value, {"extension": Path(urlsplit(value).path).suffix.lstrip(".") or "jpg",
                                  "title": node.get("caption") or "Publicação Kwai", "id": photo_id, "num": index}
            return


def save_media(session, url, metadata, config, emit, ask_duplicate, index):
    from file_output import component, publish
    extension = str(metadata.get("extension") or Path(urlsplit(url).path).suffix.lstrip(".")).lower()
    if extension not in IMAGES | VIDEOS:
        return None
    if config["mode"] == "photos" and extension not in IMAGES:
        return None
    folder = Path(config["folder"]).expanduser().resolve()
    identity = hashlib.sha256(config["url"].encode()).hexdigest()[:20]
    staging = folder / ".onda-work" / identity
    staging.mkdir(parents=True, exist_ok=True)
    user = metadata.get("user") or metadata.get("username") or metadata.get("uploader") or "Publicação"
    if isinstance(user, dict):
        user = user.get("username") or user.get("name") or "Publicação"
    title = metadata.get("title") or metadata.get("description") or metadata.get("post_id") or metadata.get("id") or "Foto"
    name = f"{component(user)[:50]} - {component(title)[:100]} - {index:02d}.{extension}"
    path = staging / name
    partial = path.with_suffix(path.suffix + ".part")
    headers = dict(metadata.get("_http_headers") or {})
    headers["Accept-Encoding"] = "identity"
    headers.setdefault("Referer", config["url"])
    started, last, size = time.monotonic(), 0, 0
    with session.get(url, headers=headers, stream=True, timeout=(20, 30)) as response:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "text/" in content_type or "json" in content_type:
            raise ValueError("A plataforma devolveu uma página de acesso em vez da mídia.")
        total = int(response.headers.get("Content-Length") or 0) or None
        emit("estimate", size=total, title=str(title), playlist=True, reason="Tamanho informado pelo servidor; por arquivo")
        with partial.open("wb") as output:
            for chunk in response.iter_content(128 * 1024):
                if not chunk:
                    continue
                output.write(chunk)
                size += len(chunk)
                now = time.monotonic()
                if now - last > .15:
                    speed = size / max(now - started, .001)
                    emit("progress", status="downloading", title=str(title), downloaded=size, total=total,
                         speed=speed, eta=(total-size)/speed if total else None, index=index)
                    last = now
        if not size or (total is not None and size != total):
            raise ValueError("Transferência incompleta; tente baixar a publicação novamente.")
    partial.replace(path)
    final, skipped = publish(path, folder, config.get("duplicate_policy", "keep"), ask_duplicate)
    if skipped:
        path.unlink(missing_ok=True)
    emit("progress", status="finished", title=str(title), downloaded=size, total=size, index=index)
    emit("file", path=final, size=Path(final).stat().st_size, skipped=skipped, mode=extension.upper())
    try:
        staging.rmdir()
        staging.parent.rmdir()
    except OSError:
        pass
    return final


def media_candidates(items):
    return [{"id": str(index), "number": metadata.get("num") or index,
             "kind": "Vídeo" if metadata.get("extension") in VIDEOS else "Foto",
             "title": str(metadata.get("title") or metadata.get("description") or "Publicação")[:120],
             "thumbnail": metadata.get("thumbnail") or metadata.get("display_url") or (url if metadata.get("extension") in IMAGES else None),
             "width": metadata.get("width"), "height": metadata.get("height")}
            for index, (url, metadata) in enumerate(items, 1)]


def download_selected(items, session, config, emit, ask_duplicate, choose=None):
    available = [(url, metadata) for url, metadata in items if metadata.get("extension") in IMAGES | VIDEOS]
    has_photos = any(metadata.get("extension") in IMAGES for _, metadata in available)
    has_videos = any(metadata.get("extension") in VIDEOS for _, metadata in available)
    # A homogeneous post needs no manual photo/video switch. An explicit
    # photo filter still applies to mixed posts, where both choices exist.
    if has_videos and not has_photos and config["mode"] == "photos":
        config = dict(config, mode="mp4")
        emit("log", message="Publicação somente com vídeos: formato automático MP4.")
    elif config["mode"] == "photos":
        available = [(url, metadata) for url, metadata in available if metadata.get("extension") in IMAGES]
    if not available:
        raise ValueError("Nenhuma foto disponível neste link." if config["mode"] == "photos" else "Nenhuma mídia disponível nesta publicação.")
    candidates = media_candidates(available)
    selected = set(choose(candidates)) if len(candidates) > 2 and choose else {item["id"] for item in candidates}
    if not selected or not selected.issubset({item["id"] for item in candidates}):
        raise ValueError("Selecione pelo menos uma mídia válida para baixar.")
    emit("media_detected", count=len(available), photos=sum(item["kind"] == "Foto" for item in candidates),
         videos=sum(item["kind"] == "Vídeo" for item in candidates), selected=len(selected), mode=config["mode"])
    saved = []
    for index, (media_url, metadata) in enumerate(available, 1):
        if str(index) not in selected:
            continue
        if metadata.get("extension") in VIDEOS and metadata.get("_video_info"):
            path = save_video(session, metadata, config, emit, ask_duplicate, metadata.get("num") or index)
        else:
            path = save_media(session, media_url, metadata, config, emit, ask_duplicate, metadata.get("num") or index)
        if path:
            saved.append(path)
    return saved


def save_video(session, metadata, config, emit, ask_duplicate, index):
    """Apply the selected video format to Instagram's already resolved streams."""
    from yt_dlp import YoutubeDL
    from yt_dlp.postprocessor.common import PostProcessor
    from engine import build_options, Logger
    from file_output import publish, component
    from size_estimate import estimate_size
    folder = Path(config["folder"]).expanduser().resolve()
    staging = folder / ".onda-work" / hashlib.sha256(config["url"].encode()).hexdigest()[:20]
    staging.mkdir(parents=True, exist_ok=True)
    options = build_options(dict(config, folder=str(staging)))
    info = dict(metadata["_video_info"])
    dimensions = [f for f in info.get("formats", []) if f.get("width") and f.get("height")]
    if dimensions and all(f["width"] < f["height"] for f in dimensions):
        options["format"] = options["format"].replace("[height<=?", "[width<=?")
    name = f"{component(metadata.get('user'))[:50]} - {component(metadata.get('title'))[:100]} - {index:02d}"
    options["outtmpl"] = {"default": name.replace("%", "%%") + ".%(ext)s"}
    info["http_headers"] = {**info.get("http_headers", {}), **metadata.get("_http_headers", {})}
    saved = []

    def progress(data):
        emit("progress", status=data["status"], title=str(metadata.get("title") or "Vídeo"),
             downloaded=data.get("downloaded_bytes", 0), total=data.get("total_bytes") or data.get("total_bytes_estimate"),
             speed=data.get("speed"), eta=data.get("eta"), index=index)

    class Capture(PostProcessor):
        def run(self, result):
            source = Path(result["filepath"])
            final, skipped = publish(source, folder, config.get("duplicate_policy", "keep"), ask_duplicate)
            if skipped:
                source.unlink(missing_ok=True)
            saved.append(final)
            emit("file", path=final, size=Path(final).stat().st_size, skipped=skipped, mode=Path(final).suffix.lstrip(".").upper())
            return [], result

    class Estimate(PostProcessor):
        def run(self, result):
            size, reason = estimate_size(result, config)
            emit("estimate", size=size, reason=reason, title=result.get("title"), playlist=True)
            return [], result

    options.update(logger=Logger(), progress_hooks=[progress])
    with YoutubeDL(options) as downloader:
        for cookie in session.cookies:
            downloader.cookiejar.set_cookie(cookie)
        downloader.add_post_processor(Estimate(downloader), when="before_dl")
        downloader.add_post_processor(Capture(downloader), when="after_move")
        downloader.process_ie_result(info, download=True)
    if not saved:
        raise ValueError("O vídeo não foi concluído.")
    try:
        staging.rmdir()
        staging.parent.rmdir()
    except OSError:
        pass
    return saved[0]


def download_post(config, emit, ask_duplicate, choose=None):
    """Return False when a mixed post should use the standard video engine."""
    from gallery_dl import config as gallery_config, extractor
    from gallery_dl.extractor.common import Message
    url = config["url"]
    photos = config["mode"] == "photos"
    saved = []
    with session_for(config.get("cookies_file", "")) as session:
        from instagram_media import is_instagram, instagram_items
        if is_instagram(url):
            from engine import Logger
            emit("stage", message="Reconhecendo fotos e vídeos do Instagram…")
            items = instagram_items(url, session, config.get("cookies_file", ""), Logger())
            saved = download_selected(items, session, config, emit, ask_duplicate, choose)
            emit("done", files=saved)
            return True
        from twitter_media import is_twitter, twitter_items
        if is_twitter(url):
            from engine import Logger
            emit("stage", message="Reconhecendo fotos e vídeos do Twitter/X…")
            items = twitter_items(url, session, config.get("cookies_file", ""), Logger())
            saved = download_selected(items, session, config, emit, ask_duplicate, choose)
            emit("done", files=saved)
            return True
        host = (urlsplit(url).hostname or "").lower()
        if host in ("vm.tiktok.com", "vt.tiktok.com", "s.kw.ai", "kwai-video.com") or "/share/" in url:
            with session.get(url, timeout=20) as response:
                response.raise_for_status()
                url = response.url
        resolved_host = (urlsplit(url).hostname or "").lower()
        if resolved_host == "tiktok.com" or resolved_host.endswith(".tiktok.com"):
            from engine import Logger
            from tiktok_media import tiktok_items
            emit("stage", message="Reconhecendo fotos e vídeos do TikTok…")
            items = tiktok_items(url, session, config.get("cookies_file", ""), Logger())
            saved = download_selected(items, session, config, emit, ask_duplicate, choose)
            emit("done", files=saved)
            return True
        if resolved_host == "kwai.com" or resolved_host.endswith(".kwai.com"):
            with session.get(url, timeout=20) as response:
                response.raise_for_status()
                items = list(kwai_images(response.text, response.url))
            if not items:
                video_fallback(config, emit)
                return False
            if len(items) > 100:
                raise ValueError("Limite de 100 arquivos por publicação atingido.")
            saved = download_selected(items, session, config, emit, ask_duplicate, choose)
        else:
            # A worker handles one post, so no global user configuration is loaded.
            gallery_config.set(("extractor",), "timeout", 20)
            gallery_config.set(("extractor",), "retries", 2)
            gallery_config.set(("extractor",), "audio", False)
            gallery_config.set(("extractor",), "videos", "merged")
            gallery_config.set(("extractor",), "covers", False)
            gallery_config.set(("extractor",), "previews", False)
            if config.get("cookies_file"):
                gallery_config.set(("extractor",), "cookies", config["cookies_file"])
            source = extractor.find(url)
            if source is None:
                if photos:
                    raise ValueError("Não há extrator de fotos para este link. Use o link direto da publicação.")
                return False
            if source.subcategory not in ("post", "reel", "image", "gallery"):
                raise ValueError("Cole o link de uma publicação ou carrossel, em vez do perfil completo.")
            source.log = gallery_logger = GalleryLogger(emit)
            emit("stage", message="Consultando fotos e vídeos da publicação…")
            try:
                items = []
                for message in source:
                    if message[0] != Message.Url:
                        continue
                    media_url, metadata = message[1], dict(message[2])
                    if not media_url.startswith(("http://", "https://")):
                        raise ValueError("Este formato da publicação não está disponível como arquivo direto. Use Vídeo (MKV).")
                    if len(items) >= 100:
                        raise ValueError("Limite de 100 arquivos por publicação atingido.")
                    items.append((media_url, metadata))
                if not items and gallery_logger.errors:
                    raise ValueError(gallery_logger.errors[-1])
                saved = download_selected(items, source.session, config, emit, ask_duplicate, choose)
            finally:
                if source.session:
                    source.session.close()
    if not saved:
        raise ValueError("Nenhuma foto disponível neste link." if photos else "Nenhuma mídia disponível nesta publicação.")
    emit("done", files=saved)
    return True


def video_fallback(config, emit):
    """Keep the standard video engine available when Photos was selected."""
    if config["mode"] == "photos":
        config["mode"] = "mp4"
        emit("log", message="Publicação somente com vídeo: formato automático MP4.")
    emit("media_detected", count=1, photos=0, videos=1, selected=1, mode=config["mode"])


def access_error(exc):
    detail = str(exc)
    if "ip address is blocked" in detail.lower():
        return ("O TikTok bloqueou o acesso desta conexão à publicação. "
                "Confira se o link abre no seu navegador. Se abrir, você pode tentar cookies.txt da própria sessão "
                "em Configurações → Redes sociais, mas isso não garante a liberação do download. "
                "Não é um erro de formato ou da fila.")
    if any(word in detail.lower() for word in ("login", "log in", "authorization", "authentication", "private", "403", "401")):
        return ("A plataforma recusou o acesso ou exige autenticação. Confira o link e, se você tiver acesso no navegador, "
                "tente cookies.txt da própria sessão em Configurações → Redes sociais. Detalhes: " + detail)
    return "Falha ao processar a publicação. Detalhes: " + detail
