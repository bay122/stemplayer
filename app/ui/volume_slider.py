import os
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QFont, QColor
from PySide6.QtCore import QRect
from PySide6.QtSvg import QSvgRenderer

from app.ui.theme import current as theme


class VolumeSlider(QWidget):
    """Custom horizontal volume slider with dB scale and enhanced design."""

    valueChanged = Signal(float)
    sliderReleased = Signal()

    def __init__(self, parent=None, icons_dir: str = "./icons/svgs"):
        super().__init__(parent)
        self.icons_dir = icons_dir
        self.setMinimumSize(120, 50)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._value = 1.0
        self._minimum = 0.0
        self._maximum = 1.2

        self.handle_icon = None
        handle_path = os.path.join(icons_dir, "fad-sliderhandle-1-white.svg")
        if os.path.exists(handle_path):
            self.handle_icon = QSvgRenderer(handle_path)

        self.setMouseTracking(True)
        self._dragging = False

        self.scale_points = [
            (0.0, 0.0, "-∞"),
            (0.25, 0.1, "-20dB"),
            (0.5, 0.5, "-6dB"),
            (0.75, 1.0, "0dB"),
            (1.0, 1.2, "+6dB")
        ]

    def value(self) -> float:
        return self._value

    def setValue(self, value: float):
        value = max(self._minimum, min(self._maximum, value))
        if value != self._value:
            self._value = value
            self.update()
            self.valueChanged.emit(value)

    def _value_to_ratio(self, value: float) -> float:
        for i in range(len(self.scale_points) - 1):
            r1, v1, _ = self.scale_points[i]
            r2, v2, _ = self.scale_points[i+1]
            if v1 <= value <= v2:
                if v2 == v1:
                    return r1
                return r1 + (r2 - r1) * (value - v1) / (v2 - v1)
        if value < self.scale_points[0][1]:
            return self.scale_points[0][0]
        return self.scale_points[-1][0]

    def _ratio_to_value(self, ratio: float) -> float:
        for i in range(len(self.scale_points) - 1):
            r1, v1, _ = self.scale_points[i]
            r2, v2, _ = self.scale_points[i+1]
            if r1 <= ratio <= r2:
                if r2 == r1:
                    return v1
                return v1 + (v2 - v1) * (ratio - r1) / (r2 - r1)
        if ratio < self.scale_points[0][0]:
            return self.scale_points[0][1]
        return self.scale_points[-1][1]

    def _value_to_x(self, value: float) -> int:
        ratio = self._value_to_ratio(value)
        return int(10 + ratio * (self.width() - 20))

    def _x_to_value(self, x: int) -> float:
        ratio = (x - 10) / (self.width() - 20)
        ratio = max(0.0, min(1.0, ratio))
        snap_threshold = 0.02
        for r, v, _ in self.scale_points:
            if abs(ratio - r) < snap_threshold:
                return v
        return self._ratio_to_value(ratio)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.BG_TERTIARY))
        y_offset = -8

        groove_rect = QRect(10, self.height() // 2 - 4 + y_offset, self.width() - 20, 8)
        painter.fillRect(groove_rect, QColor(theme.SLIDER_GROOVE))

        painter.setPen(QPen(QColor(theme.SLIDER_TEXT), 1))
        painter.setFont(QFont("Arial", 7))

        for ratio, value, label in self.scale_points:
            x = int(10 + ratio * (self.width() - 20))
            painter.drawLine(x, self.height() // 2 + 10 + y_offset, x, self.height() // 2 + 18 + y_offset)
            text_rect = painter.fontMetrics().boundingRect(label)
            painter.drawText(x - text_rect.width() // 2, self.height() // 2 + 30 + y_offset, label)

        if self._value > 0.01:
            fill_x = self._value_to_x(self._value)
            fill_rect = QRect(groove_rect.left(), groove_rect.top(),
                             fill_x - groove_rect.left(), groove_rect.height())
            painter.fillRect(fill_rect, QColor(theme.ACCENT_PRIMARY))

        handle_x = self._value_to_x(self._value)
        handle_rect = QRect(handle_x - 14, self.height() // 2 - 16 + y_offset, 28, 32)

        if self.handle_icon:
            self.handle_icon.render(painter, handle_rect)
        else:
            painter.fillRect(handle_rect, QColor(theme.ACCENT_PRIMARY))
            painter.setPen(QPen(QColor(theme.TEXT_PRIMARY), 1))
            painter.drawRect(handle_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._update_value(event.position().x())

    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_value(event.position().x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
            self.sliderReleased.emit()

    def _update_value(self, x: float):
        new_value = self._x_to_value(int(x))
        self.setValue(new_value)
