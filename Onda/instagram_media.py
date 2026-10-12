"""Use yt-dlp's current Instagram session/API support without dropping photos."""
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from yt_dlp import YoutubeDL
from yt_dlp.extractor.instagram import InstagramIE


def is_instagram(url):
    host = (urlsplit(url).hostname or "").lower()
    return host == "instagram.com" or host.endswith(".instagram.com")


class InstagramMediaIE(InstagramIE):
    def _extract_product(self, product_info, video_id=None, get_comments=True):
        self.product = product_info[0] if isinstance(product_info, list) else product_info
        # The parent extractor otherwise rejects photos or silently filters them.
        return {"id": video_id or str(self.product.get("pk")), "_type": "playlist", "entries": []}


def product_items(source, product):
    media = product.get("carousel_media") or [product]
    user = (product.get("user") or {}).get("username") or "Instagram"
    title = (product.get("caption") or {}).get("text") or product.get("code") or "Publicação Instagram"
    if len(media) > 100:
        raise ValueError("Limite de 100 mídias por publicação atingido.")
    for index, item in enumerate(media, 1):
        images = (item.get("image_versions2") or {}).get("candidates") or []
        best = max(images, key=lambda image: (image.get("width") or 0) * (image.get("height") or 0), default={})
        metadata = {"user": user, "title": title, "num": index, "count": len(media),
                    "width": best.get("width"), "height": best.get("height"), "thumbnail": best.get("url"),
                    "_http_headers": {"Referer": "https://www.instagram.com/"}}
        if item.get("media_type") == 2 or item.get("video_versions") or item.get("video_dash_manifest"):
            info = source._extract_product_media(item)
            info.update(title=f"{title[:100]} - {index:02d}", uploader=user)
            formats = info.get("formats") or []
            if not formats:
                raise ValueError(f"O Instagram não forneceu o vídeo {index} da publicação.")
            metadata.update(extension="mp4", _video_info=info)
            yield formats[0]["url"], metadata
        elif best.get("url"):
            extension = PurePosixPath(urlsplit(best["url"]).path).suffix.lstrip(".").lower()
            metadata["extension"] = extension if extension in ("jpg", "jpeg", "png", "webp", "avif") else "jpg"
            yield best["url"], metadata
        else:
            raise ValueError(f"O Instagram não forneceu a imagem {index} da publicação.")


def instagram_items(url, session, cookies="", logger=None):
    options = {"quiet": True, "socket_timeout": 20, "extractor_retries": 1, "logger": logger}
    if cookies:
        options["cookiefile"] = cookies
    with YoutubeDL(options) as downloader:
        source = InstagramMediaIE(downloader)
        source.extract(url)
        session.cookies.update(downloader.cookiejar)
        return list(product_items(source, source.product))
