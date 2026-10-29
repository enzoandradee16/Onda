"""Read Kwai's public Nuxt post data as data, without executing page scripts."""

import json
import re
from urllib.parse import urlsplit, parse_qs

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    js_to_json,
    int_or_none,
    float_or_none,
    url_or_none,
    parse_duration,
)


def object_at(text, start):
    """Extract a balanced JS object, respecting quoted braces and escapes."""
    if start >= len(text) or text[start] != "{":
        raise ValueError("Objeto da publicação ausente")
    level, quote, escaped = 0, None, False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
        elif char in "\"'`":
            quote = char
        elif char == "{":
            level += 1
        elif char == "}":
            level -= 1
            if level == 0:
                return text[start : index + 1]
    raise ValueError("Dados incompletos da publicação")


def normalize_literal(value):
    # Keys can share names with the minifier's arguments. Keep strings intact.
    value = re.sub(
        r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|([,{]\s*)([$A-Za-z_][$\w]*)(\s*:)''',
        lambda m: m[1] + json.dumps(m[2]) + m[3] if m[1] else m[0],
        value,
    )
    return re.sub(
        r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`|(?<![\w.])(-?)\.(\d+)''',
        lambda m: m[1] + "0." + m[2] if m[1] is not None else m[0],
        value,
    )


def nuxt_objects(script):
    match = re.search(
        r"window\.__NUXT__\s*=\s*\(function\(([^)]*)\)\{(.*)\}\((.*)\)\)\s*;?\s*$",
        script,
        re.S,
    )
    if not match:
        return []
    try:
        values = json.loads(
            js_to_json(normalize_literal("[" + match[3] + "]"), strict=True)
        )
        aliases = {
            name.strip(): json.dumps(value)
            for name, value in zip(match[1].split(","), values)
        }
    except (ValueError, TypeError):
        return []
    objects = []
    for assignment in re.finditer(r"(?:^|;)\s*[$\w]+\[\d+\]\s*=\s*(?=\{)", match[2]):
        try:
            value = normalize_literal(object_at(match[2], assignment.end()))
            objects.append(json.loads(js_to_json(value, vars=aliases)))
        except (ValueError, TypeError):
            continue
    return objects


def walk(value):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)


def find_post(html, photo_id):
    from social_media import PageData

    page = PageData()
    page.feed(html)
    for script in page.scripts:
        roots = nuxt_objects(script)
        try:
            roots.append(json.loads(script))
        except ValueError:
            for match in re.finditer(
                r"(?:window\.)?__(?:INIT_STATE|INITIAL_STATE|NEXT_DATA)__\s*=\s*",
                script,
            ):
                try:
                    roots.append(
                        json.JSONDecoder().raw_decode(script[match.end() :])[0]
                    )
                except ValueError:
                    pass
        for root in roots:
            for node in walk(root):
                identity = (
                    node.get("photo_id_str")
                    or node.get("photoId")
                    or node.get("photo_id")
                    or node.get("id")
                )
                if str(identity) == str(photo_id):
                    return node
    return None


def find_schema_video(html, video_id):
    """Only accept media explicitly identified as the requested Kwai video."""
    from social_media import PageData

    page = PageData()
    page.feed(html)
    for script in page.scripts:
        try:
            root = json.loads(script)
        except ValueError:
            continue
        for node in walk(root):
            if node.get("@type") != "VideoObject":
                continue
            identity = urlsplit(str(node.get("url") or ""))
            if identity.hostname not in ("www.kwai.com", "kwai.com", "m.kwai.com"):
                continue
            if identity.path.rstrip("/").split("/")[-1] != str(video_id):
                continue
            media = url_or_none(node.get("contentUrl"))
            if media:
                creator = (node.get("creator") or {}).get("mainEntity") or {}
                return {
                    "id": str(video_id),
                    "title": node.get("name") or f"Vídeo Kwai {video_id}",
                    "url": media,
                    "ext": "mp4",
                    "webpage_url": node["url"],
                    "duration": parse_duration(node.get("duration")),
                    "width": int_or_none(node.get("width")),
                    "height": int_or_none(node.get("height")),
                    "uploader": creator.get("name"),
                    "uploader_id": creator.get("alternateName"),
                    "http_headers": {"Referer": "https://www.kwai.com/"},
                }
    return None


class OndaKwaiIE(InfoExtractor):
    IE_NAME = "onda:kwai"
    _VALID_URL = (
        r"https?://(?:[\w-]+\.)?(?:kwai\.com|kwai-video\.com|kw\.ai)/(?P<id>[^?#]+)"
    )

    def _real_extract(self, url):
        short_id = self._match_id(url).rstrip("/").split("/")[-1]
        webpage, response = self._download_webpage_handle(
            url, short_id, impersonate=True
        )
        canonical = (
            self._og_search_property("url", webpage, default=None) or response.url
        )
        video_id = (
            parse_qs(urlsplit(canonical).query).get("photoId")
            or [urlsplit(canonical).path.rstrip("/").split("/")[-1]]
        )[0]
        schema = find_schema_video(webpage, video_id)
        if schema:
            return schema
        post = find_post(webpage, video_id)
        if not post:
            mobile_page = self._download_webpage(
                url,
                short_id,
                fatal=False,
                note="Consultando a página móvel do Kwai",
                headers={
                    "User-Agent": "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
                },
            )
            if mobile_page:
                schema = find_schema_video(mobile_page, video_id)
                if schema:
                    return schema
                post = find_post(mobile_page, video_id)
        if not post and re.fullmatch(r"[0-9]+", video_id):
            data = (
                self._download_json(
                    "https://www.kwai.com/rest/o/w/pwa/feed/slides",
                    video_id,
                    note="Consultando os dados públicos do vídeo",
                    fatal=False,
                    data=json.dumps(
                        {
                            "photo_id_str": video_id,
                            "count": 3,
                            "request_source": 1105,
                            "mobile": True,
                        }
                    ).encode(),
                    headers={"Content-Type": "application/json", "Referer": canonical},
                )
                or {}
            )
            for node in walk(data.get("feeds") or []):
                identity = (
                    node.get("photo_id_str")
                    or node.get("photoId")
                    or node.get("photo_id")
                )
                if str(identity) == video_id:
                    post = node
                    break
            if not post and data.get("photoNotFound") is True:
                raise ExtractorError(
                    "O Kwai não encontrou este vídeo na consulta pública. Confira se o link ainda abre e reproduz no Kwai; ele pode ter sido removido, estar indisponível nesta região ou ter acesso restrito. Nenhum vídeo recomendado foi baixado.",
                    expected=True,
                )
        if not post:
            raise ExtractorError(
                "O Kwai não forneceu os dados públicos deste vídeo. Confira se o link abre e reproduz no aplicativo ou navegador. Não foi possível confirmar a disponibilidade desta publicação.",
                expected=True,
            )
        formats, seen = [], set()
        manifest = post.get("transcode_manifest_info") or {}
        for adaptation in manifest.get("adaptationSet") or []:
            for representation in adaptation.get("representation") or []:
                media_url = url_or_none(representation.get("url"))
                if not media_url or media_url in seen:
                    continue
                seen.add(media_url)
                formats.append(
                    {
                        "url": media_url,
                        "format_id": str(representation.get("id") or len(formats)),
                        "ext": "mp4",
                        "width": int_or_none(representation.get("width")),
                        "height": int_or_none(representation.get("height")),
                        "fps": float_or_none(representation.get("frameRate")),
                        "filesize": int_or_none(representation.get("fileSize")),
                        "vcodec": {"avc": "h264", "hevc": "hevc"}.get(
                            representation.get("videoCodec")
                        ),
                        "tbr": float_or_none(representation.get("avgBitrate")),
                    }
                )
        for index, item in enumerate(post.get("main_mv_urls") or []):
            media_url = url_or_none(item.get("url"))
            if media_url and media_url not in seen:
                seen.add(media_url)
                formats.append(
                    {
                        "url": media_url,
                        "ext": "mp4",
                        "format_id": f"original-{index}",
                        "width": int_or_none((post.get("ext_params") or {}).get("cw")),
                        "height": int_or_none((post.get("ext_params") or {}).get("ch")),
                        "fps": float_or_none(
                            (post.get("ext_params") or {}).get("interval")
                        ),
                        "quality": -1,
                    }
                )
        if not formats:
            raise ExtractorError(
                "Esta publicação não contém um vídeo disponível. Para fotos, selecione Fotos / carrossel.",
                expected=True,
            )
        return {
            "id": video_id,
            "title": post.get("caption") or f"Vídeo Kwai {video_id}",
            "uploader": post.get("user_name") or post.get("kwai_id"),
            "uploader_id": post.get("kwai_id"),
            "formats": formats,
            "webpage_url": canonical,
            "duration": float_or_none(
                (post.get("ext_params") or {}).get("video"), scale=1000
            ),
            "http_headers": {"Referer": "https://www.kwai.com/"},
        }
