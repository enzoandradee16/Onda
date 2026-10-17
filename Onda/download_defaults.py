"""Effective download options, independent from spacing and tab visibility."""
from urllib.parse import urlsplit
SOCIAL_BEST_HOSTS=('instagram.com','tiktok.com','kwai.com','kwai-video.com','kw.ai','kuaishou.com')

def supported_social(url):
    host=(urlsplit(url).hostname or '').lower().rstrip('.')
    return any(host==domain or host.endswith('.'+domain) for domain in SOCIAL_BEST_HOSTS)

def automatic_social(config):
    return config.get('social_best_quality') is True and supported_social(config.get('url',''))

def effective_download(config):
    result=dict(config)
    # Editors and local conversion keep their explicit output settings.
    if result.get('_operation'):return result
    if automatic_social(result):
        result.update(mode='social',height=None,fps=None,audio_quality=None,normalize_volume=False,review_metadata=False,playlist=False)
        result['image_options']={'format':'Original','width':0,'height':0,'keep_ratio':True}
    elif result.get('simple_download_ui') is True:
        from metadata import is_streaming_link
        if result.get('mode')=='photos' and not is_streaming_link(result.get('url','')):result['image_options']={'format':'Original','width':0,'height':0,'keep_ratio':True}
        else:result['mode']='mp3' if is_streaming_link(result.get('url','')) else 'video'
        result.update(height=None,fps=None,audio_quality='320 kbps' if result['mode']=='mp3' else None)
    return result
