"""Minimalist horizontal volume slider for the deck view.

Subclasses ``VolumeSlider`` to inherit all value, signal and magnetic
snap logic; only the paint is replaced. Used exclusively in
``stemdeck_layout`` — the classic view continues to use the full
``VolumeSlider`` with the custom SVG handle.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor, QFont
from PySide6.QtCore import QRect

from app.ui.volume_slider import VolumeSlider
from app.ui.theme import current as theme


class DeckVolumeSlider(VolumeSlider):
    """Compact, minimalist volume slider with dB markers and magnetic snap."""

    def __init__(self, parent=None, icons_dir: str = "./icons/svgs"):
        super().__init__(parent=parent, icons_dir=icons_dir)
        # The full ``VolumeSlider`` is 50px tall. We want a thinner
        # footprint in the deck: smaller handle area, dB labels inline
        # beside the scale marks instead of below.
        self.setMinimumSize(110, 40)
        self.setMaximumHeight(46)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(theme.BG_TERTIARY))

        # Compact geometry: track 4px tall, centered, with 10px side margins
        track_y = self.height() // 2 - 2
        track_rect = QRect(10, track_y, self.width() - 20, 4)
        painter.fillRect(track_rect, QColor(theme.SLIDER_GROOVE))

        # Fill from left up to the value position
        if self._value > 0.01:
            fill_x = self._value_to_x(self._value)
            fill_rect = QRect(
                track_rect.left(), track_rect.top(),
                max(0, fill_x - track_rect.left()), track_rect.height(),
            )
            painter.fillRect(fill_rect, QColor(theme.ACCENT_PRIMARY))

        # dB scale marks + labels (compact, no separate label row)
        painter.setPen(QPen(QColor(theme.SLIDER_TEXT), 1))
        painter.setFont(QFont("Arial", 7))
        for ratio, _value, label in self.scale_points:
            x = int(10 + ratio * (self.width() - 20))
            painter.drawLine(x, track_rect.top() - 3, x, track_rect.top() - 1)
            text_rect = painter.fontMetrics().boundingRect(label)
            painter.drawText(
                x - text_rect.width() // 2,
                track_rect.bottom() + 14,
                label,
            )

        # Circular thumb (12px), centered vertically on the track
        handle_x = self._value_to_x(self._value)
        painter.setPen(QPen(QColor(theme.TEXT_PRIMARY), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(
            QRect(handle_x - 6, track_y - 4, 12, 12),
        )
