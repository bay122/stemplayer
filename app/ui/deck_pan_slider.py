"""Minimalist horizontal pan slider for the deck view.

Subclasses ``PanSlider`` and adds:
- L / C / R tick marks with labels.
- Magnetic snap at the center (C) position.

The original ``PanSlider`` has no snap behavior; the snap here is
limited to the center point only, as the user requested.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtCore import QRect

from app.ui.pan_slider import PanSlider
from app.ui.theme import current as theme


_CENTER_SNAP_THRESHOLD = 0.04  # 4% of the track width


class DeckPanSlider(PanSlider):
    """Compact, minimalist pan slider with L/C/R markers and center snap."""

    def __init__(self, parent=None, icons_dir: str = "./icons/svgs"):
        super().__init__(parent=parent, icons_dir=icons_dir)
        self.setMinimumSize(80, 40)
        self.setMaximumHeight(46)

    def _x_to_value(self, x: int) -> float:
        """Override parent to add magnetic snap to the center."""
        ratio = (x - 10) / (self.width() - 20)
        ratio = max(0.0, min(1.0, ratio))
        if abs(ratio - 0.5) < _CENTER_SNAP_THRESHOLD:
            ratio = 0.5
        return self._minimum + ratio * (self._maximum - self._minimum)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.BG_TERTIARY))

        track_y = self.height() // 2 - 2
        track_rect = QRect(10, track_y, self.width() - 20, 4)
        painter.fillRect(track_rect, QColor(theme.SLIDER_GROOVE))

        center_x = self.width() // 2
        # Center indicator (slightly taller than the side ticks)
        painter.setPen(QPen(QColor(theme.SLIDER_CENTER), 2))
        painter.drawLine(
            center_x, track_rect.top() - 4,
            center_x, track_rect.bottom() + 2,
        )

        # L and R tick marks + labels
        painter.setPen(QPen(QColor(theme.SLIDER_TEXT), 1))
        painter.setFont(QFont("Arial", 7))
        left_x = int(10 + 0.0 * (self.width() - 20))
        right_x = int(10 + 1.0 * (self.width() - 20))
        painter.drawLine(left_x, track_rect.top() - 3, left_x, track_rect.top() - 1)
        painter.drawLine(right_x, track_rect.top() - 3, right_x, track_rect.top() - 1)
        painter.drawText(left_x - 3, track_rect.bottom() + 10, "L")
        painter.drawText(right_x - 5, track_rect.bottom() + 10, "R")
        c_label_rect = painter.fontMetrics().boundingRect("C")
        painter.drawText(
            center_x - c_label_rect.width() // 2,
            track_rect.bottom() + 14,
            "C",
        )

        # Circular thumb (12px), centered vertically on the track
        handle_x = self._value_to_x(self._value)
        painter.setPen(QPen(QColor(theme.TEXT_PRIMARY), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(
            QRect(handle_x - 6, track_y - 4, 12, 12),
        )
