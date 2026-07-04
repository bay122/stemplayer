"""Unified stem area for the deck layout.

Contains:
- A time ruler that spans all tracks
- A vertical stack of DeckTrackRow widgets
- A single red playhead that crosses ALL tracks at the same x position
"""
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
)

from app.ui.deck_track_row import DeckTrackRow, WaveformCanvas
from app.ui.theme import current as theme


class StemsTimelineWidget(QWidget):
    """Container that lays out the ruler, a stack of tracks, and a playhead."""

    HEADER_WIDTH = DeckTrackRow.HEADER_WIDTH

    volume_changed = Signal(str, float)
    pan_changed = Signal(str, float)
    mute_toggled = Signal(str, bool)
    solo_toggled = Signal(str, bool)
    fx_toggled = Signal(str, bool)
    name_changed = Signal(str, str)
    category_changed = Signal(str, str)
    delete_requested = Signal(str)
    move_up_requested = Signal(str)
    move_down_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration_seconds = 0.0
        self._playhead_ratio = -1.0
        self._rows: dict[str, DeckTrackRow] = {}
        self._build_ui()

    def _build_ui(self):
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

        # Time ruler
        self._ruler = TimeRuler(self.HEADER_WIDTH)
        self._outer.addWidget(self._ruler)

        # Tracks stack with overlay playhead
        self._tracks_container = QWidget()
        self._tracks_container.setStyleSheet(
            f"background-color: {theme.BG_PRIMARY};"
        )
        self._tracks_layout = QVBoxLayout(self._tracks_container)
        self._tracks_layout.setContentsMargins(0, 0, 0, 0)
        self._tracks_layout.setSpacing(0)
        self._tracks_layout.setAlignment(Qt.AlignTop)
        self._outer.addWidget(self._tracks_container, 1)

        # Overlay playhead
        self._playhead = QWidget(self._tracks_container)
        self._playhead.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._playhead.setStyleSheet("background: transparent;")
        self._playhead.lower()  # below track headers
        self._playhead.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._layout_playhead()

    def _layout_playhead(self):
        """Position the overlay playhead inside the tracks container."""
        if not self._rows:
            return
        if self._duration_seconds <= 0 or self._playhead_ratio < 0:
            self._playhead.hide()
            return
        # Playhead lives in tracks_container coordinates; skip the header
        # column so the red line only crosses the waveform zones.
        x = self.HEADER_WIDTH + int(
            self._playhead_ratio * max(0, self._tracks_container.width() - self.HEADER_WIDTH)
        )
        self._playhead.setGeometry(x, 0, 2, self._tracks_container.height())
        self._playhead.show()

    def set_duration(self, seconds: float):
        self._duration_seconds = max(0.0, seconds)
        self._ruler.set_duration(self._duration_seconds)
        self._layout_playhead()

    def set_playhead(self, ratio: float):
        self._playhead_ratio = max(-1.0, min(1.0, ratio))
        # Per-row playheads are not drawn (parent draws the shared one).
        for row in self._rows.values():
            row.set_playhead(-1.0)
        self._layout_playhead()
        # Force a repaint of the overlay so it follows the new ratio.
        if self._playhead.isVisible():
            self._playhead.update()

    def clear_tracks(self):
        while self._tracks_layout.count():
            item = self._tracks_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._rows.clear()

    def add_track(self, name, category, audio, sr, volume, pan,
                  muted, solo, fx_enabled, category_colors, icons_dir):
        row = DeckTrackRow(
            name=name, category=category, audio=audio, sr=sr,
            volume=volume, pan=pan, icons_dir=icons_dir,
            category_colors=category_colors,
        )
        row.set_mute(muted)
        row.set_solo(solo)
        row.set_fx(fx_enabled)

        row.volume_changed.connect(self._on_volume)
        row.pan_changed.connect(self._on_pan)
        row.mute_toggled.connect(self.mute_toggled)
        row.solo_toggled.connect(self.solo_toggled)
        row.fx_toggled.connect(self.fx_toggled)
        row.delete_requested.connect(self.delete_requested)
        row.move_up_requested.connect(self.move_up_requested)
        row.move_down_requested.connect(self.move_down_requested)

        self._tracks_layout.addWidget(row)
        self._rows[name] = row

    def get_row(self, name):
        return self._rows.get(name)

    def _on_volume(self, name, v):
        self.volume_changed.emit(name, v)

    def _on_pan(self, name, p):
        self.pan_changed.emit(name, p)


class TimeRuler(QWidget):
    """A simple time ruler that spans the waveform area."""

    def __init__(self, header_width: int, parent=None):
        super().__init__(parent)
        self._header_width = header_width
        self._duration_seconds = 0.0
        self.setFixedHeight(28)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet(
            f"background-color: {theme.BG_DARK}; border-bottom: 1px solid {theme.BORDER_DARK};"
        )

    def set_duration(self, seconds: float):
        self._duration_seconds = max(0.0, seconds)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w = self.width()
        h = self.height()
        # Header spacer
        painter.fillRect(0, 0, self._header_width, h, QColor(theme.BG_DARK))
        # Vertical separator
        painter.setPen(QPen(QColor(theme.BORDER_DARK), 1))
        painter.drawLine(self._header_width, 0, self._header_width, h)

        if self._duration_seconds <= 0:
            return
        span_w = w - self._header_width
        if span_w <= 0:
            return
        # Decide a step (in seconds) that gives ~8 ticks.
        candidates = [5, 10, 15, 30, 60, 120, 300, 600]
        step = next((c for c in candidates if self._duration_seconds / c <= 10),
                    max(1, self._duration_seconds / 10))
        # Draw ticks
        painter.setPen(QPen(QColor(theme.TEXT_MUTED), 1))
        painter.setFont(QFont("Courier New", 9))
        t = 0.0
        while t <= self._duration_seconds:
            x = self._header_width + int((t / self._duration_seconds) * span_w)
            painter.drawLine(x, h - 8, x, h)
            text = _format_time(t)
            text_rect = painter.fontMetrics().boundingRect(text)
            painter.drawText(
                x - text_rect.width() // 2,
                h - 12,
                text,
            )
            t += step


def _format_time(seconds: float) -> str:
    seconds = int(round(seconds))
    mins = seconds // 60
    secs = seconds % 60
    return f"{mins}:{secs:02d}"
