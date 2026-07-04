"""Widget que renderiza la waveform global de la canción mezclada.

Permite hacer click para hacer seek y muestra un playhead en la posición
actual de reproducción. La zona reproducida se muestra en color dorado,
la no reproducida en gris translúcido.
"""

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient
from app.ui.theme import current as theme


PLAYED_COLOR = "#f4b740"  # Gold
UNPLAYED_COLOR = Qt.transparent  # gris translúcido
GRID_COLOR = "rgba(255,255,255,0.07)"


class GlobalWaveformView(QWidget):
    """Waveform global con seek por click."""

    seek_requested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._peaks = None
        self._progress = 0.0
        self.setMinimumHeight(40)
        self.setMinimumWidth(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent;")

    def set_peaks(self, peaks):
        """Recibe un array numpy de peaks normalizados [0, 1]."""
        if peaks is not None:
            self._peaks = np.asarray(peaks, dtype=np.float32)
        else:
            self._peaks = None
        self.update()

    def set_progress(self, ratio: float):
        """Actualiza la posición del playhead (0.0 a 1.0)."""
        self._progress = max(0.0, min(1.0, ratio))
        self.update()

    def clear(self):
        self._peaks = None
        self.update()

    @staticmethod
    def compute_peaks(audio, target_bins: int = 400):
        """Reduce un audio a peaks normalizados para dibujar."""
        if audio is None:
            return None
        if isinstance(audio, list):
            try:
                audio = np.array(audio, dtype=np.float32)
            except Exception:
                return None
        if not isinstance(audio, np.ndarray):
            try:
                audio = np.asarray(audio, dtype=np.float32)
            except Exception:
                return None
        if audio.size == 0:
            return None
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        n = audio.size
        if n == 0:
            return None
        if n <= target_bins:
            return audio.astype(np.float32)
        bin_size = n // target_bins
        usable = bin_size * target_bins
        audio = audio[:usable].reshape(target_bins, bin_size)
        peaks = np.max(np.abs(audio), axis=1).astype(np.float32)
        max_val = peaks.max()
        if max_val > 0:
            peaks = peaks / max_val
        return peaks

    @staticmethod
    def mix_stems_to_peaks(stems_dict, target_bins: int = 400):
        """Mezcla todos los stems (ponderados por volumen) y devuelve peaks."""
        if not stems_dict:
            return None
        max_len = 0
        for s in stems_dict.values():
            audio = s.get("audio")
            if audio is not None and isinstance(audio, np.ndarray):
                if audio.ndim > 1:
                    audio = audio.mean(axis=1)
                max_len = max(max_len, audio.size)
        if max_len == 0:
            return None

        mix = np.zeros(max_len, dtype=np.float32)
        total_weight = 0.0
        for s in stems_dict.values():
            audio = s.get("audio")
            if audio is None or s.get("muted", False):
                continue
            if not isinstance(audio, np.ndarray):
                continue
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
            vol = s.get("volume", 1.0) or 0.0
            pan = s.get("pan", 0.0) or 0.0
            lr = max(0.0, min(1.0, 0.5 - 0.5 * pan))
            weight = vol * lr
            if weight <= 0:
                continue
            n = min(audio.size, max_len)
            mix[:n] += audio[:n] * weight
            total_weight += weight

        if total_weight > 0:
            mix /= total_weight

        return GlobalWaveformView.compute_peaks(mix, target_bins)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.width() > 0:
            ratio = max(0.0, min(1.0, event.position().x() / self.width()))
            self.seek_requested.emit(ratio)
            self._progress = ratio
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        painter.fillRect(self.rect(), QColor(theme.BG_TERTIARY))

        if self._peaks is None or len(self._peaks) == 0:
            mid = self.height() // 2
            painter.setPen(QPen(QColor(theme.BORDER_DARK), 1, Qt.DashLine))
            painter.drawLine(0, mid, self.width(), mid)
            return

        w = self.width()
        h = self.height()
        mid = h // 2
        n = len(self._peaks)
        bar_width = max(1.0, w / n)
        play_x = int(self._progress * w)

        gold = QColor(PLAYED_COLOR)
        gray = QColor(255, 255, 255, 30)

        painter.setPen(Qt.NoPen)

        for i, p in enumerate(self._peaks):
            x = int(i * bar_width)
            bar_h = max(1, int(p * (h * 0.85)))
            y_top = mid - bar_h // 2
            color = gold if x < play_x else gray
            painter.setBrush(color)
            painter.drawRect(
                QRect(x, y_top, max(1, int(bar_width * 0.8)), bar_h)
            )

        if 0 < self._progress < 1.0:
            painter.setPen(QPen(QColor(PLAYED_COLOR), 2))
            painter.drawLine(play_x, 0, play_x, h)
            painter.setBrush(gold)
            painter.setPen(Qt.NoPen)
            r = 4
            painter.drawEllipse(play_x - r, mid - r, 2 * r, 2 * r)
