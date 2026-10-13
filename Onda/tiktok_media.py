"""Resolve TikTok photos with the same webpage/session support as videos."""
from pathlib import PurePosixPath
from urllib.parse import urlsplit, urlunsplit

from yt_dlp import YoutubeDL
from yt_dlp.extractor.tiktok import TikTokIE


class TikTokMediaIE(TikTokIE):
    def _parse_aweme_video_web(self, post, webpage_url, video_id, extract_flat=False):
        self.post = post
        return {"id": video_id, "_type": "playlist", "entries": []}


def post_items(source, post, url):
    post_id = str(post.get("id") or source._match_id(url))
    author = post.get("author") or post.get("authorInfo") or {}
    user = author.get("uniqueId") or author.get("nickname") or "TikTok"
    title = post.get("desc") or f"TikTok {post_id}"
    if "imagePost" in post:
        images = (post.get("imagePost") or {}).get("images") or []
        if not images:
            raise ValueError("O TikTok não forneceu as imagens desta publicação.")
        if len(images) > 100:
            raise ValueError("Limite de 100 mídias por publicação atingido.")
        from photo_music import direct_audio
        audio = direct_audio((post.get('music') or {}).get('playUrl'))
        for index, image in enumerate(images, 1):
            urls = (image.get("imageURL") or {}).get("urlList") or []
            media_url = next((value for value in urls if isinstance(value, str) and urlsplit(value).scheme in ("https", "http")), None)
            if not media_url:
                raise ValueError(f"O TikTok não forneceu a foto {index} da publicação.")
            extension = PurePosixPath(urlsplit(media_url).path).suffix.lstrip(".").lower()
            yield media_url, {"extension": extension if extension in ("jpg", "jpeg", "png", "webp", "avif", "heic") else "jpg",
                              "user": user, "title": title, "id": post_id, "num": index,
                              "width": image.get("imageWidth"), "height": image.get("imageHeight"),
                              "thumbnail": media_url, "_photo_audio": audio, "_http_headers": {"Referer": "https://www.tiktok.com/"}}
    else:
        info = TikTokIE._parse_aweme_video_web(source, post, url, post_id)
        formats = info.get("formats") or []
        if not formats or not any(fmt.get("vcodec") != "none" for fmt in formats):
            raise ValueError("O TikTok não forneceu um vídeo nesta publicação.")
        yield formats[0]["url"], {"extension": "mp4", "user": user, "title": title, "id": post_id,
                                 "num": 1, "thumbnail": (post.get("video") or {}).get("cover"),
                                 "_video_info": info, "_http_headers": {"Referer": "https://www.tiktok.com/"}}


def tiktok_items(url, session, cookies="", logger=None):
    parsed = urlsplit(url)
    # Photo posts expose their metadata at the canonical /video/ page too.
    canonical = urlunsplit(("https", "www.tiktok.com", parsed.path.replace("/photo/", "/video/", 1), "", ""))
    if not TikTokIE.suitable(canonical):
        raise ValueError("Cole o link de uma publicação do TikTok, em vez do perfil.")
    options = {"quiet": True, "socket_timeout": 20, "extractor_retries": 1, "logger": logger}
    if cookies:
        options["cookiefile"] = cookies
    with YoutubeDL(options) as downloader:
        source = TikTokMediaIE(downloader)
        source.extract(canonical)
        session.cookies.update(downloader.cookiejar)
        return list(post_items(source, source.post, canonical))
