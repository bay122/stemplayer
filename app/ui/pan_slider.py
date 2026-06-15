import os
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QFont, QColor
from PySide6.QtCore import QRect
from PySide6.QtSvg import QSvgRenderer


class PanSlider(QWidget):
    """Custom horizontal pan slider using fad-sliderhandle-2-white.svg."""

    valueChanged = Signal(float)
    sliderReleased = Signal()

    def __init__(self, parent=None, icons_dir: str = "./icons/svgs"):
        super().__init__(parent)
        self.icons_dir = icons_dir
        self.setMinimumSize(80, 50)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self._value = 0.0
        self._minimum = -1.0
        self._maximum = 1.0

        self.handle_icon = None
        handle_path = os.path.join(icons_dir, "fad-sliderhandle-2-white.svg")
        if os.path.exists(handle_path):
            self.handle_icon = QSvgRenderer(handle_path)

        self.setMouseTracking(True)
        self._dragging = False

    def value(self) -> float:
        return self._value

    def setValue(self, value: float):
        value = max(self._minimum, min(self._maximum, value))
        if value != self._value:
            self._value = value
            self.update()
            self.valueChanged.emit(value)

    def _value_to_x(self, value: float) -> int:
        ratio = (value - self._minimum) / (self._maximum - self._minimum)
        return int(10 + ratio * (self.width() - 20))

    def _x_to_value(self, x: int) -> float:
        ratio = (x - 10) / (self.width() - 20)
        ratio = max(0.0, min(1.0, ratio))
        return self._minimum + ratio * (self._maximum - self._minimum)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(42, 42, 42))

        groove_rect = QRect(10, self.height() // 2 - 2, self.width() - 20, 4)
        painter.fillRect(groove_rect, QColor(68, 68, 68))

        center_x = self.width() // 2
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawLine(center_x, groove_rect.top() - 2, center_x, groove_rect.bottom() + 2)

        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.setFont(QFont("Arial", 7))
        painter.drawText(2, self.height() // 2 + 5, "L")
        painter.drawText(self.width() - 8, self.height() // 2 + 5, "R")

        handle_x = self._value_to_x(self._value)
        handle_rect = QRect(handle_x - 12, self.height() // 2 - 10, 24, 20)

        if self.handle_icon:
            self.handle_icon.render(painter, handle_rect)
        else:
            painter.fillRect(handle_rect, QColor(0, 120, 215))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
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
