"""Fila de stem para el layout Deck con waveform decorativa."""

import os
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QSlider,
    QSizePolicy, QLineEdit, QComboBox, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QFont
from app.ui.svg_icon import svg_icon
from app.ui.theme import current as theme
from app.ui.volume_slider import VolumeSlider
from app.ui.pan_slider import PanSlider
from app.ui.widgets import NoWheelComboBox
from app.utils.constants import STEM_CATEGORIES


CATEGORY_COLORS_DEFAULT = {
    "Vocals":     "#FF5555",
    "Drums":      "#FFAA00",
    "Bass":       "#FFCC00",
    "Guitars":    "#55CC55",
    "Keys":       theme.ACCENT_PURPLE,
    "Strings":    "#00BFFF",
    "Brass":      "#FF8800",
    "Winds":      "#88CCFF",
    "Percussion": "#FF6644",
    "Synths":     "#CC88FF",
    "FX":         "#888888",
    "Ref":        "#666666",
    "Other":      "#AAAAAA",
}


def get_category_color(category: str, custom_colors=None) -> str:
    if custom_colors:
        return custom_colors.get(category, CATEGORY_COLORS_DEFAULT.get(category, "#AAAAAA"))
    return CATEGORY_COLORS_DEFAULT.get(category, "#AAAAAA")


class WaveformView(QWidget):
    """Renderiza la forma de onda de un stem con amplitud según volumen."""

    def __init__(self, color: str = "#FF5555", parent=None):
        super().__init__(parent)
        self.color = color
        self._peaks = None
        self._volume = 1.0
        self.setMinimumHeight(36)
        self.setFixedHeight(36)
        self.setMinimumWidth(80)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("background: transparent;")
        self._playhead_pos = -1.0

    def set_color(self, color: str):
        self.color = color
        self.update()

    def set_peaks(self, peaks, volume: float = 1.0):
        self._peaks = peaks
        self._volume = max(0.0, min(2.0, volume))
        self.update()

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(2.0, volume))
        self.update()

    def set_playhead(self, ratio: float):
        self._playhead_pos = ratio
        self.update()

    def clear(self):
        self._peaks = None
        self.update()

    @staticmethod
    def compute_peaks(audio, target_bins: int = 600):
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

        painter.setPen(Qt.NoPen)
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0.0, QColor(self.color))
        gradient.setColorAt(0.5, QColor(self.color).darker(140))
        gradient.setColorAt(1.0, QColor(self.color))
        painter.setBrush(gradient)

        max_h = h * 0.85
        for i, p in enumerate(self._peaks):
            x = int(i * bar_width)
            amp = p * self._volume
            bar_h = max(1, int(amp * max_h))
            y_top = mid - bar_h // 2
            painter.drawRect(QRect(x, y_top, max(1, int(bar_width * 0.85)), bar_h))

        painter.setPen(QPen(QColor(theme.BORDER_DARK), 1, Qt.DashLine))
        painter.drawLine(0, mid, w, mid)

        if 0 <= self._playhead_pos <= 1:
            x = int(self._playhead_pos * w)
            painter.setPen(QPen(QColor(theme.ACCENT_PRIMARY), 2))
            painter.drawLine(x, 0, x, h)


class ZoomableWaveformView(QWidget):
    """Waveform con scroll horizontal, zoom y grid de referencias temporales."""

    zoom_changed = Signal(float)
    seek_requested = Signal(float)

    def __init__(self, color: str = "#FF5555", parent=None):
        super().__init__(parent)
        self.color = color
        self._peaks = None
        self._volume = 1.0
        self._zoom = 1.0
        self._offset = 0.0
        self._total_duration = 0.0
        self._playhead_pos = -1.0
        self.setMinimumHeight(36)
        self.setFixedHeight(36)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("background: transparent;")
        self.setMouseTracking(True)

    def set_color(self, color: str):
        self.color = color
        self.update()

    def set_peaks(self, peaks, volume: float = 1.0):
        self._peaks = peaks
        self._volume = max(0.0, min(2.0, volume))
        self.update()

    def set_total_duration(self, seconds: float):
        self._total_duration = max(0.0, seconds)

    def set_playhead(self, ratio: float):
        self._playhead_pos = ratio
        self.update()

    def set_zoom(self, zoom: float):
        self._zoom = max(1.0, min(20.0, zoom))
        self._offset = 0.0
        self.update()
        self.zoom_changed.emit(self._zoom)

    def get_zoom(self) -> float:
        return self._zoom

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self.set_zoom(self._zoom * 1.2)
            elif delta < 0:
                self.set_zoom(self._zoom / 1.2)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.width() > 0 and self._peaks is not None:
            ratio = max(0.0, min(1.0, event.position().x() / self.width()))
            self._playhead_pos = ratio
            self.seek_requested.emit(ratio)
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

        # Dibujar grid de referencias temporales
        painter.setPen(QPen(QColor(255, 255, 255, 15), 1, Qt.DotLine))
        n_grid = 8
        for i in range(1, n_grid):
            x = int(i * w / n_grid)
            painter.drawLine(x, 0, x, h)
        # Texto del grid (en mm:ss)
        if self._total_duration > 0:
            painter.setPen(QColor(150, 150, 150, 120))
            font = QFont(painter.font().family(), 7)
            painter.setFont(font)
            for i in range(n_grid + 1):
                x = int(i * w / n_grid)
                sec = (i / n_grid) * self._total_duration
                mins = int(sec // 60)
                secs = int(sec % 60)
                painter.drawText(x + 2, 10, f"{mins}:{secs:02d}")

        n = len(self._peaks)
        bar_width = max(1.0, w / n)
        play_x = int(self._playhead_pos * w) if 0 <= self._playhead_pos <= 1 else -1

        painter.setPen(Qt.NoPen)
        gradient = QLinearGradient(0, 0, 0, h)
        gradient.setColorAt(0.0, QColor(self.color))
        gradient.setColorAt(0.5, QColor(self.color).darker(140))
        gradient.setColorAt(1.0, QColor(self.color))
        painter.setBrush(gradient)

        max_h = h * 0.70
        for i, p in enumerate(self._peaks):
            x = int(i * bar_width)
            amp = p * self._volume
            bar_h = max(1, int(amp * max_h))
            y_top = mid - bar_h // 2
            painter.drawRect(QRect(x, y_top, max(1, int(bar_width * 0.85)), bar_h))

        if play_x >= 0:
            painter.setPen(QPen(QColor(theme.ACCENT_PRIMARY), 2))
            painter.drawLine(play_x, 0, play_x, h)


class DeckStemRow(QWidget):
    """Fila de stem estilo Deck: controles compactos + waveform con zoom."""

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

    def __init__(self, name: str, category: str, volume: float = 1.0,
                 pan: float = 0.0, audio=None, sr: int = 44100,
                 icons_dir: str = "./icons/svgs", parent=None,
                 category_colors=None):
        super().__init__(parent)
        self.stem_name = name
        self.icons_dir = icons_dir
        self._audio = audio
        self._sr = sr
        self._peaks = None
        self._category_colors = category_colors or {}
        self._build_ui(name, category, volume, pan)
        self._apply_style()
        if audio is not None:
            self._peaks = WaveformView.compute_peaks(audio, target_bins=600)
            self.waveform.set_peaks(self._peaks, volume)

    def _build_ui(self, name: str, category: str, volume: float, pan: float):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 1, 4, 1)
        layout.setSpacing(4)

        # Bloque izquierdo: nombre + categoría
        info = QVBoxLayout()
        info.setSpacing(1)
        info.setContentsMargins(0, 0, 0, 0)

        self.name_edit = QLineEdit(name)
        self.name_edit.setMaximumWidth(110)
        self.name_edit.setMinimumWidth(80)
        self.name_edit.editingFinished.connect(self._on_name_edited)
        info.addWidget(self.name_edit)

        self.category_combo = NoWheelComboBox()
        self.category_combo.addItems(STEM_CATEGORIES)
        self.category_combo.setCurrentText(category)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        self.category_combo.setMaximumWidth(110)
        self.category_combo.setMinimumWidth(80)
        info.addWidget(self.category_combo)

        info_w = QWidget()
        info_w.setLayout(info)
        info_w.setFixedWidth(100)
        layout.addWidget(info_w, 0)

        # Bloque central: Vol / Pan apilados
        sliders = QVBoxLayout()
        sliders.setSpacing(1)
        sliders.setContentsMargins(0, 0, 0, 0)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(2)
        vol_lbl = QLabel("V")
        vol_lbl.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 9px; min-width: 10px;")
        vol_row.addWidget(vol_lbl)
        self.volume_slider = VolumeSlider(parent=self, icons_dir=self.icons_dir)
        self.volume_slider.setValue(volume)
        self.volume_slider.setMinimumHeight(24)
        self.volume_slider.setMaximumHeight(30)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.volume_slider.sliderReleased.connect(self._on_volume_released)
        vol_row.addWidget(self.volume_slider, 1)
        sliders.addLayout(vol_row, 1)

        pan_row = QHBoxLayout()
        pan_row.setSpacing(2)
        pan_lbl = QLabel("P")
        pan_lbl.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 9px; min-width: 10px;")
        pan_row.addWidget(pan_lbl)
        self.pan_slider = PanSlider(parent=self, icons_dir=self.icons_dir)
        self.pan_slider.setValue(pan)
        self.pan_slider.setMinimumHeight(24)
        self.pan_slider.setMaximumHeight(30)
        self.pan_slider.valueChanged.connect(self._on_pan_changed)
        self.pan_slider.sliderReleased.connect(self._on_pan_released)
        pan_row.addWidget(self.pan_slider, 1)
        sliders.addLayout(pan_row, 1)

        sliders_w = QWidget()
        sliders_w.setLayout(sliders)
        sliders_w.setFixedWidth(110)
        layout.addWidget(sliders_w, 0)

        # Bloque de botones M / S / FX apilados
        msf = QVBoxLayout()
        msf.setSpacing(1)
        msf.setContentsMargins(0, 0, 0, 0)

        self.mute_btn = QPushButton("M")
        self.mute_btn.setCheckable(True)
        self.mute_btn.setFixedSize(22, 18)
        self.mute_btn.setToolTip("Mute")
        self.mute_btn.toggled.connect(self._on_mute_toggled)
        msf.addWidget(self.mute_btn)

        self.solo_btn = QPushButton("S")
        self.solo_btn.setCheckable(True)
        self.solo_btn.setFixedSize(22, 18)
        self.solo_btn.setToolTip("Solo")
        self.solo_btn.toggled.connect(self._on_solo_toggled)
        msf.addWidget(self.solo_btn)

        self.fx_btn = QPushButton("FX")
        self.fx_btn.setCheckable(True)
        self.fx_btn.setChecked(True)
        self.fx_btn.setFixedSize(22, 18)
        self.fx_btn.setToolTip("Activa pitch/tempo para este stem")
        self.fx_btn.toggled.connect(self._on_fx_toggled)
        msf.addWidget(self.fx_btn)

        msf_w = QWidget()
        msf_w.setLayout(msf)
        msf_w.setFixedWidth(28)
        layout.addWidget(msf_w, 0)

        # Waveform con zoom (en scroll area para horizontal)
        wf_container = QFrame()
        wf_container.setObjectName("stemWaveformContainer")
        wf_container.setFixedHeight(48)
        wf_layout = QVBoxLayout(wf_container)
        wf_layout.setContentsMargins(0, 0, 0, 0)
        wf_layout.setSpacing(0)

        wf_scroll = QScrollArea()
        wf_scroll.setWidgetResizable(False)
        wf_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        wf_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        wf_scroll.setFrameShape(QScrollArea.NoFrame)
        wf_scroll.setFixedHeight(48)
        wf_scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:horizontal {{
                background: {theme.BG_DARK};
                height: 8px;
            }}
            QScrollBar::handle:horizontal {{
                background: {theme.BORDER_LIGHT};
                border-radius: 4px;
                min-width: 30px;
            }}
        """)
        wf_layout.addWidget(wf_scroll)

        # El widget interno del scroll es más ancho que el contenedor
        wf_inner = QWidget()
        wf_inner.setFixedHeight(48)
        wf_inner_layout = QHBoxLayout(wf_inner)
        wf_inner_layout.setContentsMargins(0, 0, 0, 0)
        wf_inner_layout.setSpacing(0)

        self.waveform = ZoomableWaveformView(
            color=get_category_color(category, self._category_colors)
        )
        self.waveform.setFixedHeight(40)
        #self.waveform.setMinimumWidth(80)
        self.waveform.setMinimumWidth(wf_container.width()+1000)

        self.waveform.seek_requested.connect(self._on_waveform_seek)
        wf_inner_layout.addWidget(self.waveform)

        wf_scroll.setWidget(wf_inner)
        # Inicialmente el waveform ocupa el ancho del scroll
        self.waveform.resize(400, 36)

        layout.addWidget(wf_container, 1)

        # Botones de reordenar y eliminar (compactos, apilados)
        right = QVBoxLayout()
        right.setSpacing(1)
        right.setContentsMargins(0, 0, 0, 0)

        self.up_btn = QPushButton()
        self.up_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-caret-up.svg"), theme.SVG_ICON_ACTIVE))
        self.up_btn.setFixedSize(22, 12)
        self.up_btn.setToolTip("Mover este stem hacia arriba")
        self.up_btn.clicked.connect(lambda: self.move_up_requested.emit(self.stem_name))
        right.addWidget(self.up_btn)

        self.down_btn = QPushButton()
        self.down_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-caret-down.svg"), theme.SVG_ICON_ACTIVE))
        self.down_btn.setFixedSize(22, 12)
        self.down_btn.setToolTip("Mover este stem hacia abajo")
        self.down_btn.clicked.connect(lambda: self.move_down_requested.emit(self.stem_name))
        right.addWidget(self.down_btn)

        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-close-x.svg"), theme.SVG_ICON_DANGER))
        self.delete_btn.setFixedSize(22, 16)
        self.delete_btn.setToolTip("Eliminar stem")
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.stem_name))
        right.addWidget(self.delete_btn)

        right_w = QWidget()
        right_w.setLayout(right)
        right_w.setFixedWidth(28)
        layout.addWidget(right_w, 0)

    def set_total_duration(self, seconds: float):
        self.waveform.set_total_duration(seconds)

    def set_zoom(self, zoom: float):
        self.waveform.set_zoom(zoom)
        # Ajustar el ancho del waveform según el zoom
        base_width = max(self.waveform.parent().width() if self.waveform.parent() else 400, 100)
        new_width = int(base_width * zoom)
        self.waveform.resize(new_width, self.waveform.height())

    def _apply_style(self):
        self.setStyleSheet(f"""
            DeckStemRow {{
                background-color: {theme.BG_TERTIARY};
                border: 1px solid {theme.BORDER_WIDGET};
                border-radius: {theme.BORDER_RADIUS_MD};
            }}
            QLineEdit {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 1px 4px;
                font-size: 10px;
                max-height: 18px;
            }}
            QComboBox {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 1px 4px;
                font-size: 9px;
                max-height: 18px;
            }}
            QComboBox::drop-down {{ border: none; width: 14px; }}
            QComboBox QAbstractItemView {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                selection-background-color: {theme.ACCENT_PRIMARY};
            }}
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                border: 1px solid {theme.BORDER};
                border-radius: 2px;
                color: {theme.TEXT_PRIMARY};
                font-size: 9px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_BRIGHTEN};
            }}
            QPushButton:checked {{
                background-color: {theme.ACCENT_PRIMARY};
                border: 1px solid {theme.ACCENT_PRIMARY};
            }}
        """)

    def set_volume_visual(self, volume: float):
        self.waveform.set_volume(volume)

    def set_playhead(self, ratio: float):
        self.waveform.set_playhead(ratio)

    def set_name(self, new_name: str):
        """Actualiza el nombre interno del stem sin recrear el widget."""
        self.stem_name = new_name

    def set_volume(self, volume: float):
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(volume)
        self.volume_slider.blockSignals(False)

    def set_pan(self, pan: float):
        self.pan_slider.blockSignals(True)
        self.pan_slider.setValue(pan)
        self.pan_slider.blockSignals(False)

    def set_mute(self, muted: bool):
        self.mute_btn.blockSignals(True)
        self.mute_btn.setChecked(muted)
        self.mute_btn.blockSignals(False)

    def set_solo(self, solo: bool):
        self.solo_btn.blockSignals(True)
        self.solo_btn.setChecked(solo)
        self.solo_btn.blockSignals(False)

    def set_fx(self, fx: bool):
        self.fx_btn.blockSignals(True)
        self.fx_btn.setChecked(fx)
        self.fx_btn.blockSignals(False)

    def set_category_color(self, category: str):
        self.waveform.set_color(get_category_color(category, self._category_colors))

    def _on_volume_changed(self, value: float):
        self.waveform.set_volume(value)
        self.volume_changed.emit(self.stem_name, value)

    def _on_volume_released(self):
        main = self.window()
        if main and hasattr(main, '_on_stem_volume_released'):
            try:
                main._on_stem_volume_released(self.stem_name)
            except Exception:
                pass

    def _on_pan_changed(self, value: float):
        self.pan_changed.emit(self.stem_name, value)

    def _on_pan_released(self):
        main = self.window()
        if main and hasattr(main, '_on_stem_pan_released'):
            try:
                main._on_stem_pan_released(self.stem_name)
            except Exception:
                pass

    def _on_waveform_seek(self, ratio: float):
        # Seek local del stem (no implementado: solo cambia el playhead)
        pass

    def _on_mute_toggled(self, checked: bool):
        if checked:
            self.mute_btn.setStyleSheet(
                f"background-color: {theme.ACCENT_DANGER}; color: {theme.TEXT_PRIMARY}; "
                f"border: 1px solid {theme.ACCENT_DANGER}; font-weight: bold;"
            )
        else:
            self.mute_btn.setStyleSheet("")
        self.mute_toggled.emit(self.stem_name, checked)

    def _on_solo_toggled(self, checked: bool):
        if checked:
            self.solo_btn.setStyleSheet(
                f"background-color: {theme.ACCENT_SOLO}; color: {theme.TEXT_PRIMARY}; "
                f"border: 1px solid {theme.ACCENT_SOLO}; font-weight: bold;"
            )
        else:
            self.solo_btn.setStyleSheet("")
        self.solo_toggled.emit(self.stem_name, checked)

    def _on_fx_toggled(self, checked: bool):
        if checked:
            self.fx_btn.setStyleSheet(
                f"background-color: {theme.ACCENT_PRIMARY}; color: {theme.TEXT_PRIMARY}; "
                f"border: 1px solid {theme.ACCENT_PRIMARY}; font-weight: bold;"
            )
        else:
            self.fx_btn.setStyleSheet("")
        self.fx_toggled.emit(self.stem_name, checked)

    def _on_name_edited(self):
        new_name = self.name_edit.text().strip()
        if new_name and new_name != self.stem_name:
            old_name = self.stem_name
            self.stem_name = new_name
            self.name_changed.emit(old_name, new_name)

    def _on_category_changed(self, category: str):
        self.set_category_color(category)
        self.category_changed.emit(self.stem_name, category)
