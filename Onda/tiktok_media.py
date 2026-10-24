"""Resolve TikTok photos with the same webpage/session support as videos."""
from pathlib import PurePosixPath
from urllib.parse import urlsplit, urlunsplit

from yt_dlp import YoutubeDL
from yt_dlp.extractor.tiktok import TikTokIE
from yt_dlp.utils import ExtractorError


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


MOBILE_USER_AGENT = 'Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36'


def embedded_post(state,post_id):
    data=(state.get('source') or {}).get('data') or {}
    video_data=(data.get('/embed/v2/'+post_id) or {}).get('videoData') or {}
    item=video_data.get('itemInfos') or {}
    if str(item.get('id') or '')!=post_id or item.get('secret') or item.get('forFriend'):
        raise ExtractorError('O TikTok não disponibilizou esta publicação no player público.',expected=True)
    video=item.get('video') or {};meta=video.get('videoMeta') or {}
    urls=[u for u in video.get('urls',[]) if isinstance(u,str) and urlsplit(u).scheme in ('https','http')]
    music=video_data.get('musicInfos') or {};audio=music.get('playUrl') or []
    post={'id':post_id,'desc':item.get('text') or '', 'createTime':item.get('createTime'),
            'author':video_data.get('authorInfos') or {},
            'video':{'playAddr':[{'src':u} for u in urls],'width':meta.get('width'),'height':meta.get('height'),
                     'duration':meta.get('duration'),'cover':next(iter(item.get('covers') or []),None)},
            'music':{'title':music.get('musicName'),'authorName':music.get('authorName'),
                     'playUrl':audio[0] if isinstance(audio,list) and audio else audio}}
    images=(video_data.get('imagePostInfo') or {}).get('displayImages')
    if images is not None:
        post['imagePost']={'images':[{'imageURL':{'urlList':row.get('urlList') or []},'imageWidth':row.get('width'),'imageHeight':row.get('height')} for row in images]}
    elif not urls:raise ExtractorError('O player público não forneceu o vídeo desta publicação.',expected=True)
    return post


def mobile_post(source, session, url):
    """Read this public post's mobile/player HTML when desktop HTML is unusable."""
    import re,json
    post_id=source._match_id(url)
    def page(target):
        import time
        for attempt in range(2):
            with session.get(target,headers={'User-Agent':MOBILE_USER_AGENT,'Accept-Encoding':'gzip, deflate'},stream=True,timeout=(15,20)) as response:
                if response.status_code in (429,502,503,504) and attempt==0:
                    try:wait=float(response.headers.get('Retry-After','1'))
                    except (TypeError,ValueError):wait=6
                    if 0<=wait<=5:
                        response.close();time.sleep(max(.5,wait));continue
                response.raise_for_status();data=bytearray()
                for chunk in response.iter_content(65536):
                    data.extend(chunk)
                    if len(data)>8*1024*1024:raise ValueError('Página TikTok acima do limite.')
            return data.decode('utf-8',errors='replace')
    state=source._get_universal_data(page(url),post_id) or {}
    detail=state.get('webapp.video-detail') or {}
    post=(detail.get('itemInfo') or {}).get('itemStruct') or {}
    if detail.get('statusCode') not in (None,0) or (post and str(post.get('id') or '')!=post_id):
        raise ExtractorError('O TikTok não disponibilizou esta publicação na página móvel.',expected=True)
    if post:return post
    html=page('https://www.tiktok.com/embed/v2/'+post_id)
    match=re.search(r"<script[^>]+id=[\"']__FRONTITY_CONNECT_STATE__[\"'][^>]*>(.*?)</script>",html,re.S)
    if not match:raise ExtractorError('O TikTok não disponibilizou dados no player público.',expected=True)
    return embedded_post(json.loads(match[1]),post_id)


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
        try:
            source.extract(canonical)
        except ExtractorError as error:
            message=str(error).lower()
            if not any(marker in message for marker in ('unexpected response from webpage request','unable to extract challenge data','unable to extract universal data for rehydration')):raise
            source.report_warning('A página desktop não forneceu os dados. Consultando a página móvel pública da mesma publicação.')
            source.post=mobile_post(source,session,canonical)
            for cookie in session.cookies:downloader.cookiejar.set_cookie(cookie)
        session.cookies.update(downloader.cookiejar)
        return list(post_items(source, source.post, canonical))
