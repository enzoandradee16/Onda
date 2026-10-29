"""Soft, full resolution artwork for the software-rendered floating player."""
import base64,io
from functools import lru_cache
from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider

@lru_cache(maxsize=8)
def blurred_artwork(source):
    from PIL import Image,ImageFilter,ImageOps
    if source.startswith('data:'):
        data=base64.b64decode(source.partition(',')[2])
    elif source.startswith(('http://','https://')):
        from tagging import fetch_cover
        cover=fetch_cover(source)
        if not cover:raise OSError()
        data=cover[0]
    else:
        path=QUrl(source).toLocalFile() if source.startswith('file:') else source
        data=Path(path).read_bytes()
    with Image.open(io.BytesIO(data)) as original:
        image=ImageOps.fit(original.convert('RGB'),(768,768),method=Image.Resampling.LANCZOS)
        image=image.filter(ImageFilter.GaussianBlur(22))
        result=io.BytesIO();image.save(result,'PNG');return result.getvalue()

class PlaybackBackdrop(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image,QQuickImageProvider.ForceAsynchronousImageLoading)
    def requestImage(self,identity,size,requestedSize):
        try:
            source=base64.urlsafe_b64decode(identity.split('?')[0]+'===').decode('utf-8')
            return QImage.fromData(blurred_artwork(source))
        except (OSError,ValueError,UnicodeError):return QImage()
