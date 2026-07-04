"""Simplified per-stem row used in the unified stem deck timeline.

Designed to be placed side-by-side under a shared time ruler, with all
rows aligned so a single red playhead (drawn in the parent container)
crosses them at the same x position.

Each row exposes:
- name (colored)
- volume slider (CompactSlider with dB markers)
- pan slider
- M / S / FX toggle buttons
- up / down / delete buttons
- a waveform visual (drawn from the stem's audio peaks)
"""
import os
import numpy as np
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSizePolicy,
    QButtonGroup
)

from app.ui.compact_slider import CompactSlider
from app.ui.theme import current as theme
from app.ui.svg_icon import svg_icon


class DeckTrackRow(QWidget):
    """One stem row under the unified time ruler."""

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

    HEADER_WIDTH = 240

    def __init__(self, name: str, category: str, audio, sr: int,
                 volume: float = 1.0, pan: float = 0.0,
                 icons_dir: str = "./icons/svgs",
                 category_colors: dict | None = None, parent=None):
        super().__init__(parent)
        self.stem_name = name
        self.icons_dir = icons_dir
        self._audio = audio
        self._sr = sr
        self._peaks = None
        self._playhead_ratio = -1.0  # -1 means "not drawn here, parent draws it"

        self._build_ui(name, category, volume, pan, icons_dir, category_colors)
        self._compute_peaks()

    def _build_ui(self, name, category, volume, pan, icons_dir, category_colors):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left header (fixed width)
        header = QWidget()
        header.setFixedWidth(self.HEADER_WIDTH)
        header.setStyleSheet(
            f"background-color: {theme.BG_DARK}; border-right: 1px solid {theme.BORDER_DARK};"
        )
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(10, 6, 10, 6)
        h_layout.setSpacing(6)

        # Top: reorder buttons (right-aligned)
        reorder = QHBoxLayout()
        reorder.setSpacing(4)
        reorder.addStretch()
        self.up_btn = QPushButton("▲")
        self.up_btn.setFixedSize(22, 22)
        self.up_btn.setToolTip("Subir")
        self.up_btn.clicked.connect(lambda: self.move_up_requested.emit(self.stem_name))
        reorder.addWidget(self.up_btn)
        self.down_btn = QPushButton("▼")
        self.down_btn.setFixedSize(22, 22)
        self.down_btn.setToolTip("Bajar")
        self.down_btn.clicked.connect(lambda: self.move_down_requested.emit(self.stem_name))
        reorder.addWidget(self.down_btn)
        self.del_btn = QPushButton("✕")
        self.del_btn.setFixedSize(22, 22)
        self.del_btn.setToolTip("Eliminar")
        self.del_btn.setStyleSheet(
            f"color: {theme.ACCENT_DANGER}; border: 1px solid {theme.BORDER};"
        )
        self.del_btn.clicked.connect(lambda: self.delete_requested.emit(self.stem_name))
        reorder.addWidget(self.del_btn)
        h_layout.addLayout(reorder)

        # Name with color dot
        name_row = QHBoxLayout()
        name_row.setSpacing(6)
        self.color_dot = QLabel()
        self.color_dot.setFixedSize(10, 10)
        self.color_dot.setStyleSheet(self._color_dot_style(category, category_colors))
        name_row.addWidget(self.color_dot)
        self.name_lbl = QLabel(name)
        self.name_lbl.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 13px; font-weight: bold; background: transparent;"
        )
        name_row.addWidget(self.name_lbl, 1)
        h_layout.addLayout(name_row)

        # Sliders row
        sliders = QHBoxLayout()
        sliders.setSpacing(8)
        v_layout = QVBoxLayout()
        v_layout.setSpacing(2)
        v_lbl = QLabel("V")
        v_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px;")
        v_layout.addWidget(v_lbl, alignment=Qt.AlignCenter)
        self.volume_slider = CompactSlider(parent=self, icons_dir=icons_dir)
        self.volume_slider.setValue(volume)
        self.volume_slider.valueChanged.connect(
            lambda v: self.volume_changed.emit(self.stem_name, v)
        )
        v_layout.addWidget(self.volume_slider)
        sliders.addLayout(v_layout, 3)

        p_layout = QVBoxLayout()
        p_layout.setSpacing(2)
        p_lbl = QLabel("P")
        p_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 10px;")
        p_layout.addWidget(p_lbl, alignment=Qt.AlignCenter)
        self.pan_slider = CompactSlider(
            parent=self, icons_dir=icons_dir,
            scale_points=[
                (0.0, -1.0, "L50"),
                (0.5, 0.0, "C"),
                (1.0, 1.0, "R50"),
            ],
            snap_threshold=0.05,
            show_value=False,
        )
        self.pan_slider.setValue(pan)
        self.pan_slider.valueChanged.connect(
            lambda p: self.pan_changed.emit(self.stem_name, p)
        )
        p_layout.addWidget(self.pan_slider)
        sliders.addLayout(p_layout, 2)
        h_layout.addLayout(sliders)

        # M / S / FX buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)
        self.mute_btn = QPushButton("M")
        self.mute_btn.setCheckable(True)
        self.mute_btn.setFixedSize(28, 22)
        self.mute_btn.toggled.connect(
            lambda v: self.mute_toggled.emit(self.stem_name, v)
        )
        btn_row.addWidget(self.mute_btn)
        self.solo_btn = QPushButton("S")
        self.solo_btn.setCheckable(True)
        self.solo_btn.setFixedSize(28, 22)
        self.solo_btn.toggled.connect(
            lambda v: self.solo_toggled.emit(self.stem_name, v)
        )
        btn_row.addWidget(self.solo_btn)
        self.fx_btn = QPushButton("FX")
        self.fx_btn.setCheckable(True)
        self.fx_btn.setChecked(True)
        self.fx_btn.setFixedSize(34, 22)
        self.fx_btn.toggled.connect(
            lambda v: self.fx_toggled.emit(self.stem_name, v)
        )
        btn_row.addWidget(self.fx_btn)
        btn_row.addStretch()
        h_layout.addLayout(btn_row)

        layout.addWidget(header)

        # Right: waveform area
        self.waveform_area = QWidget()
        self.waveform_area.setStyleSheet(
            f"background-color: {theme.BG_PRIMARY}; border-bottom: 1px solid {theme.BORDER_DARK};"
        )
        self.waveform_area.setMinimumHeight(70)
        self.waveform_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        wf_layout = QVBoxLayout(self.waveform_area)
        wf_layout.setContentsMargins(2, 6, 2, 6)
        self.waveform_canvas = WaveformCanvas(self.waveform_area, audio=self._audio, sr=self._sr)
        self.waveform_canvas.setStyleSheet("background: transparent;")
        wf_layout.addWidget(self.waveform_canvas)
        layout.addWidget(self.waveform_area, 1)

    def _color_dot_style(self, category, category_colors):
        color = "#888"
        if category_colors and category in category_colors:
            color = category_colors[category]
        return f"background-color: {color}; border-radius: 5px;"

    def _compute_peaks(self):
        if self._audio is None:
            self._peaks = None
            return
        try:
            audio = np.asarray(self._audio, dtype=np.float32)
            if audio.ndim > 1:
                audio = audio.mean(axis=0)
            target_bins = 200
            n = len(audio)
            if n == 0:
                self._peaks = None
                return
            bin_size = max(1, n // target_bins)
            n_bins = n // bin_size
            if n_bins == 0:
                self._peaks = np.array([0.0])
                return
            audio = audio[: n_bins * bin_size]
            reshaped = audio.reshape(n_bins, bin_size)
            peaks = np.max(np.abs(reshaped), axis=1)
            if peaks.max() > 0:
                peaks = peaks / peaks.max()
            self._peaks = peaks.astype(np.float32)
        except Exception:
            self._peaks = None

    def set_mute(self, muted: bool):
        if self.mute_btn.isChecked() != muted:
            self.mute_btn.blockSignals(True)
            self.mute_btn.setChecked(muted)
            self.mute_btn.blockSignals(False)

    def set_solo(self, solo: bool):
        if self.solo_btn.isChecked() != solo:
            self.solo_btn.blockSignals(True)
            self.solo_btn.setChecked(solo)
            self.solo_btn.blockSignals(False)

    def set_fx(self, enabled: bool):
        if self.fx_btn.isChecked() != enabled:
            self.fx_btn.blockSignals(True)
            self.fx_btn.setChecked(enabled)
            self.fx_btn.blockSignals(False)

    def set_playhead(self, ratio: float):
        """Set the per-row playhead position. -1 hides it (parent draws instead)."""
        self._playhead_ratio = max(-1.0, min(1.0, ratio))
        self.waveform_canvas.set_playhead(self._playhead_ratio)


class WaveformCanvas(QWidget):
    """A simple peaks-renderer with an optional playhead line."""

    def __init__(self, parent=None, audio=None, sr: int = 44100):
        super().__init__(parent)
        self._peaks = None
        self._playhead_ratio = -1.0
        self.setMinimumHeight(50)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if audio is not None:
            self.set_audio(audio, sr)

    def set_audio(self, audio, sr: int):
        if audio is None:
            self._peaks = None
            return
        try:
            audio = np.asarray(audio, dtype=np.float32)
            if audio.ndim > 1:
                audio = audio.mean(axis=0)
            target_bins = 200
            n = len(audio)
            if n == 0:
                self._peaks = None
                return
            bin_size = max(1, n // target_bins)
            n_bins = n // bin_size
            audio = audio[: n_bins * bin_size]
            reshaped = audio.reshape(n_bins, bin_size)
            peaks = np.max(np.abs(reshaped), axis=1)
            if peaks.max() > 0:
                peaks = peaks / peaks.max()
            self._peaks = peaks.astype(np.float32)
        except Exception:
            self._peaks = None

    def set_playhead(self, ratio: float):
        self._playhead_ratio = max(-1.0, min(1.0, ratio))
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        w = self.width()
        h = self.height()
        if self._peaks is not None and len(self._peaks) > 0:
            n = len(self._peaks)
            mid = h // 2
            bar_w = max(1.0, w / n)
            for i, p in enumerate(self._peaks):
                x = int(i * bar_w)
                bar_h = int(p * (h * 0.85))
                painter.fillRect(
                    int(x), mid - bar_h // 2, max(1, int(bar_w)), bar_h,
                    QColor(theme.ACCENT_PRIMARY),
                )
        if 0.0 <= self._playhead_ratio <= 1.0:
            x = int(self._playhead_ratio * w)
            painter.setPen(QPen(QColor("#ff3333"), 2))
            painter.drawLine(x, 0, x, h)
