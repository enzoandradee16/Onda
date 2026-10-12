"""Resolve photos and videos together using yt-dlp's Twitter session support."""
import json
from urllib.parse import urlsplit

from yt_dlp import YoutubeDL
from yt_dlp.extractor.twitter import TwitterIE
from yt_dlp.utils import ExtractorError, update_url_query


def is_twitter(url):
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return any(host == name or host.endswith("." + name) for name in ("twitter.com", "x.com"))


def tweet_items(source, status, tweet_id):
    # Syndication retains mediaDetails; use only the requested post, never its quote.
    media = list((status.get("mediaDetails") if "mediaDetails" in status else
                  (status.get("extended_entities") or {}).get("media")) or [])
    bindings = (status.get("card") or {}).get("binding_values") or {}
    if isinstance(bindings, list):
        bindings = {item["key"]: item["value"] for item in bindings if "key" in item and "value" in item}
    raw_card = (bindings.get("unified_card") or {}).get("string_value")
    if raw_card:
        try:
            card = json.loads(raw_card)
        except (TypeError, ValueError) as exc:
            raise ValueError("O Twitter/X forneceu um cartão de mídia inválido.") from exc
        existing = {str(item.get("id_str") or item.get("id")) for item in media}
        for key, item in (card.get("media_entities") or {}).items():
            if str(item.get("id_str") or item.get("id") or key) not in existing:
                media.append(item)
    if len(media) > 100:
        raise ValueError("Limite de 100 mídias por publicação atingido.")
    user = status.get("user") or {}
    author = user.get("screen_name") or user.get("name") or "Twitter"
    title = status.get("full_text") or status.get("text") or tweet_id
    for index, item in enumerate(media, 1):
        thumbnail = item.get("media_url_https") or item.get("media_url")
        dimensions = (item.get("original_info") or item.get("sizes", {}).get("large") or {})
        metadata = {"user": author, "title": title, "id": tweet_id, "num": index,
                    "thumbnail": thumbnail, "width": dimensions.get("width", dimensions.get("w")),
                    "height": dimensions.get("height", dimensions.get("h")),
                    "_http_headers": {"Referer": "https://x.com/"}}
        if item.get("type") == "photo" and thumbnail:
            extension = urlsplit(thumbnail).path.rsplit(".", 1)[-1].lower()
            if extension not in ("jpg", "jpeg", "png", "webp"):
                extension = "jpg"
            media_url = update_url_query(thumbnail, {"name": "orig"})
            metadata.update(extension=extension, thumbnail=media_url)
            yield media_url, metadata
        elif item.get("type") in ("video", "animated_gif"):
            video = item.get("video_info") or {}
            formats = []
            subtitles = {}
            for variant in video.get("variants") or []:
                found, subs = source._extract_variant_formats(variant, str(item.get("id_str") or tweet_id))
                formats.extend(found)
                source._merge_subtitles(subs, target=subtitles)
            if not formats:
                raise ValueError(f"O Twitter/X não forneceu o vídeo {index} da publicação.")
            metadata.update(extension="mp4", _video_info={
                "id": f"{tweet_id}-{index}", "title": f"{title[:100]} - {index:02d}",
                "uploader": author, "formats": formats, "subtitles": subtitles,
                "duration": (video.get("duration_millis") or 0) / 1000 or None,
                "thumbnail": thumbnail})
            yield formats[0]["url"], metadata


def twitter_items(url, session, cookies="", logger=None):
    if not TwitterIE.suitable(url):
        raise ValueError("Cole o link de uma publicação do Twitter/X, em vez do perfil.")
    options = {"quiet": True, "socket_timeout": 20, "extractor_retries": 1, "logger": logger}
    if cookies:
        options["cookiefile"] = cookies
    with YoutubeDL(options) as downloader:
        source = TwitterIE(downloader)
        source.initialize()
        tweet_id = source._match_id(url)
        try:
            status = source._extract_status(tweet_id)
        except ExtractorError:
            if source.is_logged_in:
                raise
            source.report_warning("Consultando a versão pública da publicação; algumas mídias podem exigir login.")
            status = source._call_syndication_api(tweet_id)
        session.cookies.update(downloader.cookiejar)
        return list(tweet_items(source, status, tweet_id))
