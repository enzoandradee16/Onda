"""Soft, full resolution artwork for the software-rendered floating player."""

import base64, io
from functools import lru_cache
from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider


def artwork_bytes(source):
    if source.startswith('data:'):
        return base64.b64decode(source.partition(',')[2])
    elif source.startswith(('http://', 'https://')):
        from tagging import fetch_cover

        cover = fetch_cover(source)
        if not cover:
            raise OSError()
        return cover[0]
    else:
        path = QUrl(source).toLocalFile() if source.startswith('file:') else source
        return Path(path).read_bytes()


@lru_cache(maxsize=8)
def album_rgb(source):
    from PIL import Image

    with Image.open(io.BytesIO(artwork_bytes(source))) as original:
        sample = original.convert('RGB').resize((48, 48)).quantize(colors=12)
    palette = sample.getpalette()
    bins = sample.getcolors()
    _, index = max(bins, key=lambda entry: entry[0])
    return tuple(palette[3 * index : 3 * index + 3])


def album_gradient(source, dark):
    return color_gradient(album_rgb(source), dark)


@lru_cache(maxsize=16)
def color_gradient(rgb, dark):
    from PIL import Image
    from custom_accent import backdrop_opacity

    if dark:
        rgb = [round(channel * .72 + 255 * .28) for channel in rgb]
    opacity = backdrop_opacity(rgb, dark)
    gradient = Image.new('RGBA', (1, 128))
    gradient.putdata(
        [(*rgb, round(255 * opacity * (1 - .42 * y / 127))) for y in range(128)]
    )
    result = io.BytesIO()
    gradient.save(result, 'PNG')
    return result.getvalue()


@lru_cache(maxsize=8)
def blurred_artwork(source):
    from PIL import Image, ImageFilter, ImageOps

    with Image.open(io.BytesIO(artwork_bytes(source))) as original:
        image = ImageOps.fit(
            original.convert('RGB'), (768, 768), method=Image.Resampling.LANCZOS
        )
        image = image.filter(ImageFilter.GaussianBlur(22))
        result = io.BytesIO()
        image.save(result, 'PNG')
        return result.getvalue()


class PlaybackBackdrop(QQuickImageProvider):
    def __init__(self, report_accent=None):
        super().__init__(
            QQuickImageProvider.Image, QQuickImageProvider.ForceAsynchronousImageLoading
        )

        self.report_accent = report_accent

    def requestImage(self, identity, size, requestedSize):
        try:
            mode, _, encoded = identity.partition('/')
            if mode in ('color-dark', 'color-light'):
                if len(encoded) != 6:
                    return QImage()
                rgb = tuple(int(encoded[i : i + 2], 16) for i in (0, 2, 4))
                return QImage.fromData(color_gradient(rgb, mode == 'color-dark'))
            if mode in ('album-dark', 'album-light'):
                source = base64.urlsafe_b64decode(encoded + '===').decode('utf-8')
                rgb = album_rgb(source)
                if self.report_accent:
                    self.report_accent('image://backdrop/' + identity, '#%02x%02x%02x' % rgb)
                return QImage.fromData(color_gradient(rgb, mode == 'album-dark'))
            source = base64.urlsafe_b64decode(identity.split('?')[0] + '===').decode(
                'utf-8'
            )
            return QImage.fromData(blurred_artwork(source))
        except (OSError, ValueError, UnicodeError):
            return QImage()
