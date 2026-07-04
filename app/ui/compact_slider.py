"""Compact horizontal slider for the deck player section.

Designed for tight spaces: short height (max ~30px), single-line dB/scale
markers, and the same "magnet" snap-to-marker behavior as VolumeSlider.

Use it for:
- Master volume (-20dB..+6dB with magnet on every 6dB step)
- Metronome volume (0..1 with magnet at common values)
- Metronome pan (-50..+50 with magnet at center)

The widget exposes the same `valueChanged` and `sliderReleased` signals
as VolumeSlider so existing handlers (e.g. _on_master_volume_changed)
can be reused.
"""
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPen, QFont, QColor
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtSvg import QSvgRenderer

from app.ui.theme import current as theme


class CompactSlider(QWidget):
    """A short horizontal slider with dB/scale markers and magnet snap."""

    valueChanged = Signal(float)
    sliderReleased = Signal()

    # Default scale points matching VolumeSlider:
    # (ratio 0..1, value, label)
    DEFAULT_SCALE = [
        (0.0, 0.0, "-∞"),
        (0.25, 0.1, "-20dB"),
        (0.5, 0.5, "-6dB"),
        (0.75, 1.0, "0dB"),
        (1.0, 1.2, "+6dB"),
    ]

    def __init__(self, parent=None, icons_dir: str = "./icons/svgs",
                 scale_points=None, snap_threshold: float = 0.03,
                 show_value: bool = True, value_suffix: str = "dB",
                 value_format=lambda v: f"{v*6 - 6:.0f}"):
        super().__init__(parent)
        self.icons_dir = icons_dir
        self.setMinimumHeight(28)
        self.setMaximumHeight(34)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMouseTracking(True)

        self._value = 0.75  # default ~0dB
        self._minimum = 0.0
        self._maximum = 1.2
        self._scale_points = scale_points if scale_points is not None else self.DEFAULT_SCALE
        self._snap_threshold = snap_threshold
        self._show_value = show_value
        self._value_suffix = value_suffix
        self._value_format = value_format

        self.handle_icon = None
        handle_path = os.path.join(icons_dir, "fad-sliderhandle-1-white.svg")
        if os.path.exists(handle_path):
            self.handle_icon = QSvgRenderer(handle_path)

        self._dragging = False

    def value(self) -> float:
        return self._value

    def setValue(self, value: float):
        value = max(self._minimum, min(self._maximum, value))
        if value != self._value:
            self._value = value
            self.update()
            self.valueChanged.emit(value)

    def _value_to_ratio(self, value: float) -> float:
        for i in range(len(self._scale_points) - 1):
            r1, v1, _ = self._scale_points[i]
            r2, v2, _ = self._scale_points[i+1]
            if v1 <= value <= v2:
                if v2 == v1:
                    return r1
                return r1 + (r2 - r1) * (value - v1) / (v2 - v1)
        if value < self._scale_points[0][1]:
            return self._scale_points[0][0]
        return self._scale_points[-1][0]

    def _ratio_to_value(self, ratio: float) -> float:
        for i in range(len(self._scale_points) - 1):
            r1, v1, _ = self._scale_points[i]
            r2, v2, _ = self._scale_points[i+1]
            if r1 <= ratio <= r2:
                if r2 == r1:
                    return v1
                return v1 + (v2 - v1) * (ratio - r1) / (r2 - r1)
        if ratio < self._scale_points[0][0]:
            return self._scale_points[0][1]
        return self._scale_points[-1][1]

    def _value_to_x(self, value: float) -> int:
        ratio = self._value_to_ratio(value)
        return int(6 + ratio * (self.width() - 12))

    def _x_to_value(self, x: int) -> float:
        ratio = (x - 6) / max(1, (self.width() - 12))
        ratio = max(0.0, min(1.0, ratio))
        for r, v, _ in self._scale_points:
            if abs(ratio - r) < self._snap_threshold:
                return v
        return self._ratio_to_value(ratio)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.BG_TERTIARY))

        # Centered groove
        groove_y = self.height() // 2 - 2
        groove_rect = self.rect().adjusted(6, groove_y, -6, groove_y + 4)
        painter.fillRect(groove_rect, QColor(theme.SLIDER_GROOVE))

        # Scale ticks + labels (above the groove)
        painter.setPen(QPen(QColor(theme.SLIDER_TEXT), 1))
        painter.setFont(QFont("Arial", 7))
        for ratio, _v, label in self._scale_points:
            x = int(6 + ratio * (self.width() - 12))
            painter.drawLine(x, groove_y - 4, x, groove_y)
            text_rect = painter.fontMetrics().boundingRect(label)
            painter.drawText(x - text_rect.width() // 2, groove_y - 6, label)

        # Fill up to the current value
        if self._value > 0.01:
            fill_x = self._value_to_x(self._value)
            fill_rect = groove_rect.adjusted(0, 0, -(groove_rect.right() - fill_x), 0)
            painter.fillRect(fill_rect, QColor(theme.ACCENT_PRIMARY))

        # Handle (small for compact)
        handle_x = self._value_to_x(self._value)
        handle_rect = self.rect().adjusted(
            handle_x - 10, groove_y - 10,
            handle_x - 10 + 20, groove_y - 10 + 20,
        )
        if self.handle_icon:
            self.handle_icon.render(painter, handle_rect)
        else:
            painter.fillRect(handle_rect, QColor(theme.ACCENT_PRIMARY))
            painter.setPen(QPen(QColor(theme.TEXT_PRIMARY), 1))
            painter.drawRect(handle_rect)

        # Value text (right of the slider, e.g. "+0dB")
        if self._show_value:
            text = self._value_format(self._value) + (self._value_suffix or "")
            painter.setPen(QPen(QColor(theme.ACCENT_PRIMARY), 1))
            painter.setFont(QFont("Arial", 8))
            text_rect = painter.fontMetrics().boundingRect(text)
            painter.drawText(
                self.width() - text_rect.width() - 4,
                self.height() - 4,
                text,
            )

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
