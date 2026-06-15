import os
from PySide6.QtGui import QIcon, QColor, QPixmap, QPainter
from PySide6.QtCore import Qt
from PySide6.QtSvg import QSvgRenderer


def svg_icon(path: str, color: str = "#FFFFFF") -> QIcon:
    """Carga un icono SVG y le aplica un color."""
    renderer = QSvgRenderer(path)
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return QIcon(pixmap)
