"""Panel de tarjetas de información (Info Cards) para el layout Deck.

Muestra cards dinámicas según la canción:
- KEY (siempre, clickable para popup pitch) - muestra original y actual
- BPM (siempre, clickable para popup tempo) - muestra original y actual
- DURATION (si hay stems)
- CANCIÓN (si hay canción) - muestra nombre y artista, clickable
- ARTISTA (si hay artista) - clickable para editar
- Medidores del sistema: CPU, RAM, PEAK (siempre, apilados verticalmente a la derecha)
- Cards de presencia por categoría: VOCAL, DRUM, BASS, GUITAR, PIANO, OTHER, REF, PERC
  (solo si la canción tiene stems de esa categoría) - muestra volumen max
"""

import os
import numpy as np
import psutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QProgressBar, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer
from app.ui.theme import current as theme
from app.utils.stem_classifier import has_stems_of_category


CATEGORY_CARDS = [
    ("Vocals",     "VOCAL PRESENCE"),
    ("Drums",      "DRUM INTENSITY"),
    ("Bass",       "BASS DEPTH"),
    ("Guitars",    "GUITAR PRESENCE"),
    ("Keys",       "PIANO PRESENCE"),
    ("Percussion", "PERC LEVEL"),
    ("Other",      "OTHER"),
    ("Ref",        "REF LEVEL"),
]

DEFAULT_CARD_COLORS = {
    "Vocals":     "#FF5555",
    "Drums":      "#FFAA00",
    "Bass":       "#FFCC00",
    "Guitars":    "#55CC55",
    "Keys":       "#5555AA",
    "Percussion": "#FF8800",
    "Other":      "#AAAAAA",
    "Ref":        "#888888",
}


class InfoCard(QFrame):
    """Tarjeta individual con etiqueta, valor y subtexto. Clickable opcional."""

    clicked = Signal()

    def __init__(self, label: str, accent_color: str = None, clickable: bool = False, parent=None):
        super().__init__(parent)
        self.accent_color = accent_color or theme.TEXT_PRIMARY
        self._clickable = clickable
        self.setObjectName("infoCard")
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(76)
        self._build_ui(label)
        self._apply_style()

    def _build_ui(self, label: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        self.label = QLabel(label)
        self.label.setStyleSheet(
            f"color: {theme.TEXT_SECONDARY}; font-size: 9px; "
            f"font-weight: bold; letter-spacing: 1px; background: transparent;"
        )
        layout.addWidget(self.label)

        self.value_label = QLabel("--")
        self.value_label.setStyleSheet(
            f"color: {self.accent_color}; font-size: 18px; font-weight: bold; "
            f"background: transparent;"
        )
        self.value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.value_label.setWordWrap(False)
        self.value_label.setTextInteractionFlags(Qt.NoTextInteraction)
        layout.addWidget(self.value_label)

        self.sub_label = QLabel("")
        self.sub_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 10px; background: transparent;"
        )
        self.sub_label.setAlignment(Qt.AlignLeft)
        self.sub_label.setWordWrap(False)
        layout.addWidget(self.sub_label)

    def mousePressEvent(self, event):
        if self._clickable and event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _apply_style(self):
        cursor = Qt.PointingHandCursor if self._clickable else Qt.ArrowCursor
        self.setCursor(cursor)
        self.setStyleSheet(f"""
            QFrame#infoCard {{
                background-color: {theme.BG_SECONDARY};
                border: 1px solid {theme.BORDER_DARK};
                border-radius: {theme.BORDER_RADIUS_MD};
            }}
            QFrame#infoCard:hover {{
                border: 1px solid {theme.BORDER_LIGHT};
            }}
        """)

    def set_value(self, value: str, sub: str = ""):
        self.value_label.setText(value)
        self.sub_label.setText(sub)
        self.sub_label.setVisible(bool(sub))


class MeterMiniBar(QFrame):
    """Mini barra de medidor del sistema (CPU/RAM/PEAK)."""

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.setObjectName("meterCard")
        self.setFrameShape(QFrame.NoFrame)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(0)
        self._build_ui(label)
        self._apply_style()

    def _build_ui(self, label: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        self.label = QLabel(label)
        self.label.setStyleSheet(
            f"color: {theme.TEXT_SECONDARY}; font-size: 9px; font-weight: bold; "
            f"letter-spacing: 1px; background: transparent;"
        )
        layout.addWidget(self.label)

        bar_row = QHBoxLayout()
        bar_row.setSpacing(6)
        bar_row.setContentsMargins(0, 0, 0, 0)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(True)
        self.bar.setFixedHeight(14)
        self.bar.setFormat("%v%")
        bar_row.addWidget(self.bar, 1)

        layout.addLayout(bar_row)
        layout.addStretch(1)

    def _apply_bar_style(self, color: str, value: int):
        self.bar.setValue(value)
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme.BG_TERTIARY};
                border: 1px solid {theme.BORDER_DARK};
                border-radius: {theme.BORDER_RADIUS_SM};
                color: {theme.TEXT_PRIMARY};
                text-align: center;
                font-size: 9px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: {theme.BORDER_RADIUS_SM};
            }}
        """)

    def set_value(self, value: int):
        if value < 60:
            color = theme.ACCENT_SUCCESS
        elif value < 85:
            color = theme.ACCENT_WARNING
        else:
            color = theme.ACCENT_DANGER
        self._apply_bar_style(color, value)

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#meterCard {{
                background-color: {theme.BG_SECONDARY};
                border: 1px solid {theme.BORDER_DARK};
                border-radius: {theme.BORDER_RADIUS_MD};
            }}
        """)


class InfoCardsPanel(QWidget):
    """Conjunto de tarjetas de información para el layout Deck."""

    key_card_clicked = Signal()
    bpm_card_clicked = Signal()
    song_card_clicked = Signal()

    def __init__(self, parent=None, config_mgr=None):
        super().__init__(parent)
        self._peak_val = 0.0
        self._config_mgr = config_mgr
        self._card_colors = (
            config_mgr.get_category_colors() if config_mgr is not None
            else dict(DEFAULT_CARD_COLORS)
        )
        self._build_ui()
        self._start_timers()

    def _build_ui(self):
        self._outer = QHBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(6)

        # Columna izquierda: grid con las cards principales
        self._left_col = QVBoxLayout()
        self._left_col.setSpacing(6)
        self._outer.addLayout(self._left_col, 1)

        # Fila 1: KEY, BPM, DURATION, CANCIÓN
        self._row1 = QHBoxLayout()
        self._row1.setSpacing(6)
        self._left_col.addLayout(self._row1, 1)

        # Fila 2: cards de presencia
        self._presence_layout = QHBoxLayout()
        self._presence_layout.setSpacing(6)
        self._left_col.addLayout(self._presence_layout, 1)

        # Columna derecha: medidores apilados (CPU, RAM, PEAK)
        self._meters_col_widget = QWidget()
        self._meters_col_widget.setFixedWidth(130)
        self._meters_col = QVBoxLayout(self._meters_col_widget)
        self._meters_col.setSpacing(6)
        self._meters_col.setContentsMargins(0, 0, 0, 0)
        self._outer.addWidget(self._meters_col_widget, 0)

        self.card_key = InfoCard("KEY", theme.ACCENT_CYAN, clickable=True)
        self.card_key.clicked.connect(self.key_card_clicked.emit)
        self.card_bpm = InfoCard("BPM", theme.ACCENT_WARNING, clickable=True)
        self.card_bpm.clicked.connect(self.bpm_card_clicked.emit)
        self.card_duration = InfoCard("DURATION", theme.ACCENT_SUCCESS)
        self.card_song = InfoCard("CANCIÓN", theme.ACCENT_PRIMARY, clickable=True)
        self.card_song.clicked.connect(self.song_card_clicked.emit)

        self.card_key.set_value("--", "")
        self.card_bpm.set_value("--", "")
        self.card_duration.set_value("--", "")
        self.card_song.set_value("—", "Click para editar")

        self._row1.addWidget(self.card_key, 1)
        self._row1.addWidget(self.card_bpm, 1)
        self._row1.addWidget(self.card_duration, 1)
        self._row1.addWidget(self.card_song, 1)

        self.meter_cpu = MeterMiniBar("CPU")
        self.meter_ram = MeterMiniBar("RAM")
        self.meter_peak = MeterMiniBar("PEAK")

        self._meters_col.addWidget(self.meter_cpu, 1)
        self._meters_col.addWidget(self.meter_ram, 1)
        self._meters_col.addWidget(self.meter_peak, 1)

        self._presence_cards = {}
        for cat, label in CATEGORY_CARDS:
            color = self._card_colors.get(cat, DEFAULT_CARD_COLORS.get(cat, "#AAAAAA"))
            card = InfoCard(label, color)
            card.set_value("--", "Vol max")
            self._presence_cards[cat] = card

    def update_colors(self):
        if self._config_mgr is not None:
            self._card_colors = self._config_mgr.get_category_colors()
        for cat, card in self._presence_cards.items():
            color = self._card_colors.get(cat, DEFAULT_CARD_COLORS.get(cat, "#AAAAAA"))
            card.accent_color = color
            card._apply_style()
            card.value_label.setStyleSheet(
                f"color: {color}; font-size: 18px; font-weight: bold; background: transparent;"
            )

    def _start_timers(self):
        self._sys_timer = QTimer(self)
        self._sys_timer.timeout.connect(self._update_system)
        self._sys_timer.start(1000)

        self._peak_timer = QTimer(self)
        self._peak_timer.timeout.connect(self._decay_peak)
        self._peak_timer.start(80)

    def _update_system(self):
        try:
            cpu = int(psutil.cpu_percent())
            self.meter_cpu.set_value(cpu)
        except Exception:
            pass
        try:
            ram = int(psutil.virtual_memory().percent)
            self.meter_ram.set_value(ram)
        except Exception:
            pass

    def _decay_peak(self):
        self._peak_val = max(0.0, self._peak_val - 0.05)
        pct = min(100, int(self._peak_val * 100))
        self.meter_peak.set_value(pct)

    def update_peak(self, peak_val):
        if peak_val is not None and peak_val > self._peak_val:
            self._peak_val = peak_val
            pct = min(100, int(peak_val * 100))
            self.meter_peak.set_value(pct)

    def update_info(self, state):
        """Actualiza los valores de las cards principales."""
        from app.utils.constants import get_key_at_semitone_shift

        # KEY
        key = state.detected_key or "—"
        if (state.current_pitch_shift != 0
                and state.detected_key):
            original = get_key_at_semitone_shift(
                state.detected_key, -state.current_pitch_shift
            )
            if original != state.detected_key:
                sub_key = f"Original: {original} ({state.current_pitch_shift:+d})"
            else:
                sub_key = ""
        else:
            sub_key = ""
        self.card_key.set_value(key, sub_key)

        # BPM
        if state.detected_bpm and state.detected_bpm > 0:
            actual_bpm = int(state.detected_bpm * state.current_tempo_ratio)
            if state.current_tempo_ratio != 1.0:
                sub_bpm = f"Original: {int(state.detected_bpm)} ({state.current_tempo_ratio*100:.0f}%)"
            else:
                sub_bpm = ""
            self.card_bpm.set_value(str(actual_bpm), sub_bpm)
        else:
            self.card_bpm.set_value("—", "BPM")

        # DURATION
        if state.stems:
            try:
                max_len = 0
                for s in state.stems.values():
                    audio = s.get("audio")
                    if audio is not None and isinstance(audio, np.ndarray):
                        max_len = max(max_len, audio.size)
                if max_len > 0:
                    total_secs = max_len / state.mix_sr
                    mins = int(total_secs // 60)
                    secs = int(total_secs % 60)
                    self.card_duration.set_value(
                        f"{mins:02d}:{secs:02d}", "Track length"
                    )
                else:
                    self.card_duration.set_value("—", "")
            except Exception:
                self.card_duration.set_value("—", "")
        else:
            self.card_duration.set_value("—", "")

        # CANCIÓN
        song_name = state.current_song_name or "—"
        if song_name and song_name != "—":
            artist = state.current_song_artist or ""
            if artist:
                sub_song = f"{artist}"
            else:
                sub_song = "Click para editar"
            self.card_song.set_value(song_name, sub_song)
        else:
            self.card_song.set_value("—", "Click para editar")

        self._update_presence_cards(state)

    def _update_presence_cards(self, state):
        """Muestra el volumen máximo de los stems de cada categoría presente."""
        for cat, card in self._presence_cards.items():
            card.setParent(None)
            card.setVisible(False)
            try:
                self._presence_layout.removeWidget(card)
            except Exception:
                pass

        if not state.stems:
            return

        category_max_volume = {}
        for s in state.stems.values():
            cat = s.get("category", "Other")
            if cat not in category_max_volume:
                category_max_volume[cat] = 0.0
            if s.get("muted", False):
                continue
            vol = s.get("volume", 1.0)
            if vol > category_max_volume[cat]:
                category_max_volume[cat] = vol

        for cat, card in self._presence_cards.items():
            if cat in category_max_volume and category_max_volume[cat] > 0:
                pct = int(min(100, category_max_volume[cat] * 100))
                card.set_value(f"{pct}%", "Vol max")
                card.setVisible(True)
                self._presence_layout.addWidget(card, 1)
