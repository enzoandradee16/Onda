"""Platform silhouettes tinted for the current desktop theme."""

from pathlib import Path
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtGui import QImage, QColor, QPainter


class PlatformIcons(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)

    def requestImage(self, identity, size, requestedSize):
        provider, _, color = identity.partition('/')
        from platform_info import platforms

        if provider not in {row['key'] for row in platforms()}:
            return QImage()
        image = QImage(
            str(
                Path(__file__).resolve().parent
                / 'assets/platforms'
                / (provider + '.png')
            )
        ).convertToFormat(QImage.Format_ARGB32_Premultiplied)
        if not image.isNull():
            painter = QPainter(image)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(image.rect(), QColor('#' + color))
            painter.end()
        return image
