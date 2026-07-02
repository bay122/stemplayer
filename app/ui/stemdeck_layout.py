"""Layout alternativo 'StemDeck' (Layout 2).

Estructura vertical:
- Header (logo + título canción + botones Layout/Close)
- ExtractPanel (chips dinámicos como filtro por categoría)
- InfoCardsPanel (cards KEY/BPM/Duration/Canción + medidores apilados)
- Stems scroll (DeckStemRow con waveform, VolumeSlider, PanSlider, move_up/down)
- ActionsRow (Save/Gen Sheet/Live Chords/⋮)
- PlayerSection (master/metronome/count-in/undo/redo/reset/transport + waveform global)
- StatusRow (status_label + progress_bar)
- LiveChordWidget (oculto, se muestra con Live Chords toggle)
- ChordProPreviewWidget (sección colapsable, aparece si hay .chopro)
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QSizePolicy, QPushButton, QMenu, QWidgetAction, QSpinBox, QGridLayout,
    QLineEdit, QButtonGroup, QDialog, QFormLayout, QDialogButtonBox,
    QProgressBar
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from app.ui.svg_icon import svg_icon
from app.ui.theme import current as theme
from app.ui.info_cards import InfoCardsPanel
from app.ui.deck_stem_row import DeckStemRow
from app.ui.extract_panel import ExtractPanel
from app.ui.collapsible_section import CollapsibleSection
from app.ui.global_waveform import GlobalWaveformView
from app.ui.chordpro_preview import ChordProPreviewWidget
from app.utils.constants import get_key_at_semitone_shift
from app.utils.stem_classifier import categories_present


KEY_MAP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class PitchKeyDialog(QDialog):
    """Diálogo modal para editar tonalidad y aplicar pitch shift."""

    def __init__(self, current_key, current_shift, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pitch & Key")
        self.setModal(True)
        self._current_key = current_key or "C"
        self._current_shift = current_shift or 0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        info = QLabel(f"Tonalidad detectada: {self._current_key}")
        info.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(info)

        key_layout = QVBoxLayout()
        key_layout.setSpacing(6)
        key_lbl = QLabel("Editar tonalidad:")
        key_lbl.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 11px; font-weight: bold;")
        key_layout.addWidget(key_lbl)
        self.key_edit = QLineEdit(self._current_key)
        self.key_edit.setPlaceholderText("C, C#, D, D#, E, F, F#, G, G#, A, A#, B, Dm, Am...")
        self.key_edit.setMinimumHeight(30)
        key_layout.addWidget(self.key_edit)
        layout.addLayout(key_layout)

        pitch_lbl = QLabel("Pitch Shift:")
        pitch_lbl.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 11px; font-weight: bold;")
        layout.addWidget(pitch_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.pitch_buttons = []
        for shift in [-3, -2, -1, 0, 1, 2, 3]:
            label = get_key_at_semitone_shift(self._current_key, shift)
            if shift == 0:
                label += " (Original)"
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.setMinimumWidth(64)
            if shift == self._current_shift:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, s=shift: self._select_pitch(s))
            self.pitch_buttons.append((shift, btn))
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Aplicar")
        buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _select_pitch(self, shift):
        for s, btn in self.pitch_buttons:
            btn.blockSignals(True)
            btn.setChecked(s == shift)
            btn.blockSignals(False)
        self._current_shift = shift

    def get_new_key(self) -> str:
        return self.key_edit.text().strip()

    def get_new_shift(self) -> int:
        return self._current_shift


class TempoDialog(QDialog):
    """Diálogo modal para cambiar el tempo (BPM)."""

    def __init__(self, current_bpm, current_ratio, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tempo")
        self.setModal(True)
        self._current_bpm = int(current_bpm) if current_bpm and current_bpm > 0 else 120
        self._current_ratio = current_ratio or 1.0
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        info = QLabel(f"BPM original: {self._current_bpm}    Ratio actual: {self._current_ratio*100:.0f}%")
        info.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(info)

        form = QFormLayout()
        form.setSpacing(8)
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(20, 300)
        self.bpm_spin.setSuffix(" BPM")
        self.bpm_spin.setValue(int(self._current_bpm * self._current_ratio))
        self.bpm_spin.setMinimumHeight(30)
        form.addRow("BPM objetivo:", self.bpm_spin)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Aplicar")
        buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_new_bpm(self) -> int:
        return self.bpm_spin.value()


class ArtistEditDialog(QDialog):
    """Diálogo modal para editar el artista de la canción."""

    def __init__(self, current_artist, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar artista")
        self.setModal(True)
        self._build_ui(current_artist)

    def _build_ui(self, artist):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        info = QLabel("Editar el nombre del artista de la canción actual.")
        info.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.artist_edit = QLineEdit(artist or "")
        self.artist_edit.setPlaceholderText("Nombre del artista")
        self.artist_edit.setMinimumHeight(30)
        layout.addWidget(self.artist_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Guardar")
        buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_artist(self) -> str:
        return self.artist_edit.text().strip()


class StemDeckLayout(QWidget):
    """Layout alternativo StemDeck."""

    layout_change_requested = Signal()

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main = main_window
        self.icons_dir = main_window.icons_dir
        self._deck_rows = {}
        self._global_waveform = None
        self._global_peaks = None
        self._build_ui()
        self._wire_signals()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        self.extract_panel = ExtractPanel(config_mgr=self.main.config_mgr)
        self.extract_panel.set_icons_dir(self.icons_dir)
        root.addWidget(self.extract_panel)

        self.info_section = CollapsibleSection(
            "Información", "deck_info", config_mgr=self.main.config_mgr
        )
        self.info_section.updateContentMinimunHeight(160)
        self.info_cards = InfoCardsPanel(config_mgr=self.main.config_mgr)
        self.info_section.set_content(self.info_cards)
        root.addWidget(self.info_section)

        stems_header = QLabel("STEMS")
        stems_header.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 10px; font-weight: bold; "
            f"letter-spacing: 1px; padding: 4px 12px; background: transparent;"
        )
        root.addWidget(stems_header)

        self.stems_scroll = QScrollArea()
        self.stems_scroll.setWidgetResizable(True)
        self.stems_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.stems_scroll.setFrameShape(QFrame.NoFrame)
        self.stems_container = QWidget()
        self.stems_layout = QVBoxLayout(self.stems_container)
        self.stems_layout.setAlignment(Qt.AlignTop)
        self.stems_layout.setSpacing(4)
        self.stems_layout.setContentsMargins(8, 2, 8, 2)
        self.stems_scroll.setWidget(self.stems_container)
        root.addWidget(self.stems_scroll, 1)

        self.actions_row = self._build_actions_row()
        root.addWidget(self.actions_row)

        self.chordpro_section = CollapsibleSection(
            "Acordes", "deck_chordpro", config_mgr=self.main.config_mgr
        )
        self._chordpro_preview = ChordProPreviewWidget(
            parent=self, icons_dir=self.icons_dir
        )
        self._chordpro_preview.setMaximumHeight(180)
        self.chordpro_section.set_content(self._chordpro_preview)
        self.chordpro_section.setVisible(False)
        root.addWidget(self.chordpro_section)

        self.status_row = self._build_status_row()
        root.addWidget(self.status_row)

        self.player_section = self._build_player_section()
        root.addWidget(self.player_section)

        self._karaoke_widget = None

        self.setStyleSheet(f"""
            StemDeckLayout {{
                background-color: {theme.BG_PRIMARY};
            }}
        """)

    def _build_header(self):
        header = QFrame()
        header.setObjectName("deckHeaderRoot")
        header.setFixedHeight(40)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(10)

        self.hdr_logo = QLabel("StemPlayer")
        self.hdr_logo.setStyleSheet(
            f"color: {theme.ACCENT_PRIMARY}; font-size: 16px; font-weight: bold; background: transparent; margin-left: 15px"
        )
        self.hdr_logo.setFixedWidth(110)
        layout.addWidget(self.hdr_logo)

        self.hdr_song_title = QLabel("Sin canción cargada")
        self.hdr_song_title.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 13px; font-weight: bold; background: transparent;"
        )
        self.hdr_song_title.setMinimumWidth(150)
        layout.addWidget(self.hdr_song_title, 1)

        self.hdr_close_btn = QPushButton()
        self.hdr_close_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-close-x.svg"), theme.SVG_ICON_DANGER))
        self.hdr_close_btn.setFixedSize(32, 28)
        self.hdr_close_btn.setToolTip("Cerrar canción")
        self.hdr_close_btn.setVisible(False)
        layout.addWidget(self.hdr_close_btn)

        header.setStyleSheet(f"""
            QFrame#deckHeaderRoot {{
                background-color: {theme.BG_DARK};
                border-bottom: 1px solid {theme.BORDER_DARK};
            }}
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_MD};
                color: {theme.TEXT_PRIMARY};
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_BRIGHTEN};
            }}
        """)
        return header

    def _build_actions_row(self):
        row = QFrame()
        row.setObjectName("actionsRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        self.save_lib_btn = QPushButton("Guardar en librería")
        self.save_lib_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-save.svg")))
        self.save_lib_btn.setFixedHeight(28)
        self.save_lib_btn.setVisible(False)
        layout.addWidget(self.save_lib_btn)

        self.save_changes_btn = QPushButton("Guardar Cambios")
        self.save_changes_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-save.svg")))
        self.save_changes_btn.setFixedHeight(28)
        self.save_changes_btn.setVisible(False)
        layout.addWidget(self.save_changes_btn)

        self.generate_chordpro_btn = QPushButton("Generar Sheet")
        self.generate_chordpro_btn.setFixedHeight(28)
        self.generate_chordpro_btn.setVisible(False)
        layout.addWidget(self.generate_chordpro_btn)

        self.toggle_live_btn = QPushButton("Live Chords")
        self.toggle_live_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-microphone.svg")))
        self.toggle_live_btn.setFixedHeight(28)
        self.toggle_live_btn.setCheckable(True)
        self.toggle_live_btn.setVisible(False)
        layout.addWidget(self.toggle_live_btn)

        layout.addStretch()

        self.more_btn = QPushButton()
        self.more_btn.setFixedSize(28, 28)
        self.more_btn.setToolTip("Más opciones")
        self.more_btn.setStyleSheet("""
			QPushButton::menu-indicator {
				image: none;
				width: 0px;
				height: 0px;
				margin: 0px;
				padding: 0px;
			}
			QPushButton {
				padding: 0px;
			}
		""")
        self.more_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-levels.svg")))
        self.more_btn.setVisible(False)
        layout.addWidget(self.more_btn)

        row.setStyleSheet(f"""
            QFrame#actionsRow {{
                background-color: {theme.BG_DARK};
                border-top: 1px solid {theme.BORDER_DARK};
                border-bottom: 1px solid {theme.BORDER_DARK};
            }}
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_MD};
                color: {theme.TEXT_PRIMARY};
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_BRIGHTEN};
            }}
            QPushButton:checked {{
                background-color: {theme.ACCENT_PRIMARY};
                border: 1px solid {theme.ACCENT_PRIMARY};
            }}
        """)
        return row

    def _build_status_row(self):
        """Fila con status_label y progress_bar."""
        row = QFrame()
        row.setObjectName("statusRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(8)

        self.deck_status_label = QLabel("")
        self.deck_status_label.setStyleSheet(
            f"color: {theme.TEXT_SECONDARY}; font-size: 11px; background: transparent;"
        )
        self.deck_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.deck_status_label, 1)

        self.deck_progress_bar = QProgressBar()
        self.deck_progress_bar.setRange(0, 100)
        self.deck_progress_bar.setValue(0)
        self.deck_progress_bar.setMaximumWidth(220)
        self.deck_progress_bar.setFixedHeight(14)
        self.deck_progress_bar.setVisible(False)
        layout.addWidget(self.deck_progress_bar, 0)

        self.deck_bg_status_label = QLabel("")
        self.deck_bg_status_label.setStyleSheet(
            f"color: {theme.ACCENT_PURPLE}; font-size: 10px; font-style: italic; background: transparent;"
        )
        self.deck_bg_status_label.setVisible(False)
        layout.addWidget(self.deck_bg_status_label, 0)

        row.setStyleSheet(f"""
            QFrame#statusRow {{
                background-color: {theme.BG_DARK};
                border-bottom: 1px solid {theme.BORDER_DARK};
            }}
            QProgressBar {{
                background-color: {theme.BG_TERTIARY};
                border: 1px solid {theme.BORDER_DARK};
                border-radius: {theme.BORDER_RADIUS_SM};
                text-align: center;
                color: {theme.TEXT_PRIMARY};
                font-size: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {theme.ACCENT_PRIMARY};
                border-radius: {theme.BORDER_RADIUS_SM};
            }}
        """)
        return row

    def _build_player_section(self):
        """El reproductor del deck: crea widgets propios que llaman a los handlers del main."""
        main = self.main
        section = QFrame()
        section.setObjectName("playerSection")

        outer = QVBoxLayout(section)
        outer.setContentsMargins(10, 6, 10, 6)
        outer.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)
        outer.addLayout(top)

        left = QVBoxLayout()
        left.setSpacing(6)

        master_row = QHBoxLayout()
        master_row.setSpacing(6)
        master_lbl = QLabel("Master:")
        master_lbl.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 11px; font-weight: bold; background: transparent;")
        master_lbl.setFixedWidth(48)
        master_row.addWidget(master_lbl)

        from app.ui.volume_slider import VolumeSlider
        from app.ui.pan_slider import PanSlider
        self.deck_master_slider = VolumeSlider(parent=section, icons_dir=self.icons_dir)
        self.deck_master_slider.setValue(self.main.state.master_volume)
        self.deck_master_slider.valueChanged.connect(self.main._on_master_volume_changed)
        self.deck_master_slider.sliderReleased.connect(self.main._on_master_volume_released)
        self.deck_master_slider.setMinimumHeight(40)
        self.deck_master_slider.setMaximumHeight(50)
        master_row.addWidget(self.deck_master_slider, 1)
        left.addLayout(master_row)

        metro_row1 = QHBoxLayout()
        metro_row1.setSpacing(6)
        from PySide6.QtWidgets import QCheckBox
        self.deck_metro_icon_btn = QPushButton()
        self.deck_metro_icon_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-metronome.svg"), theme.SVG_ICON_MUTED))
        self.deck_metro_icon_btn.setFixedSize(24, 24)
        self.deck_metro_icon_btn.setToolTip("Volumen del metrónomo")
        self.deck_metro_icon_btn.setEnabled(self.main.state.click_during_playback)
        metro_row1.addWidget(self.deck_metro_icon_btn)

        self.deck_click_check = QCheckBox("Activar Metrónomo")
        self.deck_click_check.setToolTip("Metrónomo persistente durante la canción")
        self.deck_click_check.setChecked(self.main.state.click_during_playback)
        self.deck_click_check.stateChanged.connect(self.main._on_click_during_changed)
        metro_row1.addWidget(self.deck_click_check)
        metro_row1.addStretch()
        left.addLayout(metro_row1)

        metro_row2 = QHBoxLayout()
        metro_row2.setSpacing(6)
        self.deck_metro_vol_slider = VolumeSlider(parent=section, icons_dir=self.icons_dir)
        self.deck_metro_vol_slider.setValue(self.main.state.metronome_volume)
        self.deck_metro_vol_slider.valueChanged.connect(self.main._on_metronome_volume_changed)
        self.deck_metro_vol_slider.sliderReleased.connect(self.main._on_metronome_volume_released)
        self.deck_metro_vol_slider.setMinimumHeight(40)
        self.deck_metro_vol_slider.setVisible(self.main.state.click_during_playback)
        metro_row2.addWidget(self.deck_metro_vol_slider, 1)

        self.deck_metro_pan_slider = PanSlider(parent=section, icons_dir=self.icons_dir)
        self.deck_metro_pan_slider.setValue(self.main.state.metronome_pan)
        self.deck_metro_pan_slider.valueChanged.connect(self.main._on_metronome_pan_changed)
        self.deck_metro_pan_slider.sliderReleased.connect(self.main._on_metronome_pan_released)
        self.deck_metro_pan_slider.setMaximumHeight(50)
        self.deck_metro_pan_slider.setVisible(self.main.state.click_during_playback)
        metro_row2.addWidget(self.deck_metro_pan_slider, 0)
        left.addLayout(metro_row2)

        cin_row = QHBoxLayout()
        cin_row.setSpacing(6)
        cin_lbl = QLabel("Count-in:")
        cin_lbl.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 11px; font-weight: bold; background: transparent;")
        cin_lbl.setFixedWidth(58)
        cin_row.addWidget(cin_lbl)

        from PySide6.QtWidgets import QComboBox
        self.deck_count_in_combo = QComboBox()
        self.deck_count_in_combo.addItems(["Sin count-in", "1 compás", "2 compases"])
        self.deck_count_in_combo.setCurrentIndex(self.main.state.count_in_bars)
        self.deck_count_in_combo.currentIndexChanged.connect(self.main._on_count_in_changed)
        self.deck_count_in_combo.setMinimumHeight(28)
        cin_row.addWidget(self.deck_count_in_combo)
        cin_row.addStretch()

        self.deck_undo_btn = QPushButton()
        self.deck_undo_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-undo.svg")))
        self.deck_undo_btn.setFixedSize(32, 32)
        self.deck_undo_btn.setToolTip("Deshacer")
        self.deck_undo_btn.clicked.connect(self.main._undo)
        self.deck_undo_btn.setEnabled(self.main.state.history_idx > 0)
        cin_row.addWidget(self.deck_undo_btn)

        self.deck_redo_btn = QPushButton()
        self.deck_redo_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-redo.svg")))
        self.deck_redo_btn.setFixedSize(32, 32)
        self.deck_redo_btn.setToolTip("Rehacer")
        self.deck_redo_btn.clicked.connect(self.main._redo)
        self.deck_redo_btn.setEnabled(
            self.main.state.history_idx < len(self.main.state.history) - 1
        )
        cin_row.addWidget(self.deck_redo_btn)

        self.deck_reset_btn = QPushButton()
        self.deck_reset_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-history.svg")))
        self.deck_reset_btn.setFixedSize(32, 32)
        self.deck_reset_btn.setToolTip("Restablecer todos los cambios de pitch y volumen")
        self.deck_reset_btn.clicked.connect(self.main._reset_all)
        cin_row.addWidget(self.deck_reset_btn)
        left.addLayout(cin_row)

        top.addLayout(left, 1)

        right = QVBoxLayout()
        right.setSpacing(6)

        trans_row = QHBoxLayout()
        trans_row.setSpacing(8)
        trans_row.addStretch()
        self.deck_prev_btn = QPushButton()
        self.deck_prev_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-prev.svg")))
        self.deck_prev_btn.setFixedSize(40, 40)
        self.deck_prev_btn.setToolTip("Canción anterior")
        self.deck_prev_btn.clicked.connect(self.main.setlist_widget.play_previous)
        trans_row.addWidget(self.deck_prev_btn)

        self.deck_play_btn = QPushButton()
        self.deck_play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-play.svg")))
        self.deck_play_btn.setFixedSize(48, 48)
        self.deck_play_btn.setToolTip("Play / Pause")
        self.deck_play_btn.clicked.connect(self.main._toggle_play)
        trans_row.addWidget(self.deck_play_btn)

        self.deck_stop_btn = QPushButton()
        self.deck_stop_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-stop.svg")))
        self.deck_stop_btn.setFixedSize(40, 40)
        self.deck_stop_btn.setToolTip("Stop")
        self.deck_stop_btn.clicked.connect(self.main._stop_playback)
        trans_row.addWidget(self.deck_stop_btn)

        self.deck_next_btn = QPushButton()
        self.deck_next_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-next.svg")))
        self.deck_next_btn.setFixedSize(40, 40)
        self.deck_next_btn.setToolTip("Canción siguiente")
        self.deck_next_btn.clicked.connect(self.main.setlist_widget.play_next)
        trans_row.addWidget(self.deck_next_btn)

        self.deck_auto_play_btn = QPushButton()
        self.deck_auto_play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-preset-ab.svg"), theme.SVG_ICON_ACTIVE))
        self.deck_auto_play_btn.setFixedSize(40, 40)
        self.deck_auto_play_btn.setCheckable(True)
        self.deck_auto_play_btn.setToolTip("Auto-avanzar y reproducir en setlist")
        self.deck_auto_play_btn.toggled.connect(self.main._on_auto_play_toggled)
        trans_row.addWidget(self.deck_auto_play_btn)
        trans_row.addStretch()
        right.addLayout(trans_row)

        from PySide6.QtWidgets import QSlider
        # Fila con waveform global y textos de tiempo
        wf_row = QHBoxLayout()
        wf_row.setSpacing(6)
        self.deck_current_time = QLabel("00:00")
        self.deck_current_time.setStyleSheet(f"color: {theme.TEXT_PRIMARY}; font-size: 11px; font-family: {theme.FONT_MONO}; background: transparent;")
        self.deck_current_time.setFixedWidth(48)
        wf_row.addWidget(self.deck_current_time)
        # Slider oculto (lo mantenemos para los signals pero el visual es el waveform)
        self.deck_progress = QSlider(Qt.Horizontal)
        self.deck_progress.setRange(0, 1000)
        self.deck_progress.setValue(0)
        self.deck_progress.setStyleSheet(theme.playback_slider_qss())
        self.deck_progress.setTracking(True)
        self.deck_progress.sliderReleased.connect(self.main._on_playback_seek)
        self.deck_progress.sliderMoved.connect(self.main._on_playback_preview)
        self.deck_progress.setMaximumWidth(0)
        self.deck_progress.setVisible(False)
        wf_row.addWidget(self.deck_progress)
        # Waveform global con seek por click
        self._global_waveform = GlobalWaveformView(section)
        self._global_waveform.setMinimumHeight(56)
        self._global_waveform.setMaximumHeight(80)
        self._global_waveform.seek_requested.connect(self.main._on_waveform_seek)
        wf_row.addWidget(self._global_waveform, 1)
        self.deck_total_time = QLabel("00:00")
        self.deck_total_time.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px; font-family: {theme.FONT_MONO}; background: transparent;")
        self.deck_total_time.setFixedWidth(48)
        self.deck_total_time.setAlignment(Qt.AlignRight)
        wf_row.addWidget(self.deck_total_time)
        right.addLayout(wf_row)

        top.addLayout(right, 1)

        section.setStyleSheet(f"""
            QFrame#playerSection {{
                background-color: {theme.BG_SECONDARY};
                border-top: 1px solid {theme.BORDER_DARK};
            }}
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_MD};
                color: {theme.TEXT_PRIMARY};
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_BRIGHTEN};
            }}
            QPushButton:checked {{
                background-color: {theme.ACCENT_PRIMARY};
                border: 1px solid {theme.ACCENT_PRIMARY};
            }}
        """)
        return section

    def _wire_signals(self):
        m = self.main

        self.hdr_close_btn.clicked.connect(m._close_song)

        self.save_lib_btn.clicked.connect(m._save_to_library)
        self.save_changes_btn.clicked.connect(m._save_changes)
        self.generate_chordpro_btn.clicked.connect(m._on_generate_chordpro_clicked)
        self.toggle_live_btn.toggled.connect(self._on_toggle_live)
        m.live_display_widget.close_requested.connect(lambda: self.toggle_live_btn.setChecked(False))
        self.more_btn.setMenu(m.more_menu)

        self.info_cards.key_card_clicked.connect(self._open_pitch_popup)
        self.info_cards.bpm_card_clicked.connect(self._open_tempo_popup)
        self.info_cards.song_card_clicked.connect(self._open_song_edit_popup)

        self.extract_panel.chip_selected.connect(self._on_chip_selected)

    def _on_chip_selected(self, category):
        m = self.main
        for name, data in m.state.stems.items():
            cat = data.get("category", "Other")
            if category is None:
                new_solo = False
            else:
                new_solo = (cat == category)
            if data.get("solo", False) != new_solo:
                data["solo"] = new_solo
                if name in self._deck_rows:
                    self._deck_rows[name].set_solo(new_solo)
        m._push_state_if_needed()

    def _on_toggle_live(self, checked: bool):
        """Muestra/oculta el Live Chords. Reusa self.main.live_display_widget."""
        self.show_karaoke(checked)

    def _open_pitch_popup(self):
        m = self.main
        if not m.state.current_song_name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "Sin canción",
                "Carga una canción antes de cambiar el tono."
            )
            return

        dlg = PitchKeyDialog(
            m.state.detected_key, m.state.current_pitch_shift, self
        )
        if dlg.exec() == QDialog.Accepted:
            new_key = dlg.get_new_key()
            new_shift = dlg.get_new_shift()
            if new_key and new_key != m.state.detected_key:
                m.state.detected_key = new_key
                m.key_label.setText(f"Key: {new_key}")
                if (m.state.current_song_source == "library"
                        and m.state.current_song_name):
                    m.lib_mgr.library_path = m.config_mgr.get_library_path()
                    meta = m.lib_mgr.get_metadata(m.state.current_song_name)
                    if meta:
                        meta["detected_key"] = new_key
                        m.lib_mgr.save_metadata(m.state.current_song_name, meta)
            if new_shift != m.state.current_pitch_shift:
                m._on_pitch_clicked(new_shift)
            self.info_cards.update_info(m.state)

    def _open_tempo_popup(self):
        m = self.main
        if not m.state.current_song_name:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "Sin canción",
                "Carga una canción antes de cambiar el tempo."
            )
            return

        dlg = TempoDialog(
            m.state.detected_bpm, m.state.current_tempo_ratio, self
        )
        if dlg.exec() == QDialog.Accepted:
            new_bpm = dlg.get_new_bpm()
            m.bpm_spin.setValue(new_bpm)
            m._on_apply_tempo_clicked()
            self.info_cards.update_info(m.state)

    def _open_song_edit_popup(self):
        m = self.main
        dlg = ArtistEditDialog(m.state.current_song_artist, self)
        if dlg.exec() == QDialog.Accepted:
            new_artist = dlg.get_artist()
            if new_artist != m.state.current_song_artist:
                m._on_artist_changed(new_artist)
            self.update_song_header(m.state.current_song_name, m.state.current_song_artist)
            self.info_cards.update_info(m.state)

    def update_chip_visibility(self):
        cats = categories_present(self.main.state)
        self.extract_panel.update_visibility(cats)

    def refresh_info_cards(self):
        self.info_cards.update_info(self.main.state)
        self.update_chip_visibility()

    def _compute_global_peaks(self):
        """Calcula los peaks de la mezcla de todos los stems."""
        if not self.main.state.stems:
            return None
        return GlobalWaveformView.mix_stems_to_peaks(self.main.state.stems, target_bins=400)

    def rebuild_stems(self):
        while self.stems_layout.count():
            item = self.stems_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._deck_rows.clear()

        m = self.main
        category_colors = (
            m.config_mgr.get_category_colors() if m.config_mgr else None
        )
        for name, data in m.state.stems.items():
            audio = data.get("audio")
            row = DeckStemRow(
                name, data.get("category", "Other"),
                volume=data.get("volume", 1.0),
                pan=data.get("pan", 0.0),
                audio=audio, sr=m.state.mix_sr,
                icons_dir=self.icons_dir,
                category_colors=category_colors
            )
            row.set_mute(data.get("muted", False))
            row.set_solo(data.get("solo", False))
            row.set_fx(data.get("fx_enabled", True))

            row.volume_changed.connect(m._on_stem_volume_changed)
            row.pan_changed.connect(m._on_stem_pan_changed)
            row.mute_toggled.connect(self._on_stem_mute_toggled)
            row.solo_toggled.connect(self._on_stem_solo_toggled)
            row.fx_toggled.connect(m._on_stem_fx_toggled)
            row.name_changed.connect(m._on_stem_name_changed)
            row.category_changed.connect(m._on_stem_category_changed)
            row.delete_requested.connect(m._on_stem_delete)
            row.move_up_requested.connect(m._on_stem_move_up)
            row.move_down_requested.connect(m._on_stem_move_down)

            self.stems_layout.addWidget(row)
            self._deck_rows[name] = row

        # Calcular y asignar peaks del waveform global
        self._global_peaks = self._compute_global_peaks()
        if self._global_waveform is not None:
            self._global_waveform.set_peaks(self._global_peaks)

        self.refresh_info_cards()
        self._update_chordpro_section()

    def _update_chordpro_section(self):
        """Muestra/oculta la sección ChordPro según exista .chopro."""
        m = self.main
        if self._chordpro_preview is None:
            return
        has_chopro = False
        if (m.state.current_song_source == "library"
                and m.state.current_song_name):
            try:
                lib_path = m.config_mgr.get_library_path()
                chopro_path = os.path.join(
                    lib_path, m.state.current_song_name,
                    f"{m.state.current_song_name}.chopro"
                )
            except Exception:
                chopro_path = None
            if chopro_path and os.path.exists(chopro_path):
                has_chopro = True
                try:
                    self._chordpro_preview.load_chopro_content(chopro_path)
                except Exception:
                    pass

        if has_chopro:
            try:
                self._chordpro_preview.setVisible(True)
            except Exception:
                pass
            self.chordpro_section.setVisible(True)
        else:
            self.chordpro_section.setVisible(False)

    def _on_stem_mute_toggled(self, name, muted):
        m = self.main
        if name in m.state.stems:
            m.state.stems[name]["muted"] = muted
        m._on_stem_mute_toggled(name, muted)

    def _on_stem_solo_toggled(self, name, solo):
        m = self.main
        if name in m.state.stems:
            m.state.stems[name]["solo"] = solo
        m._on_stem_solo_toggled(name, solo)

    def update_playhead(self, ratio: float):
        for row in self._deck_rows.values():
            row.set_playhead(ratio)
        if self._global_waveform is not None:
            self._global_waveform.set_progress(ratio)

    def update_song_header(self, song_name: str, artist: str = ""):
        if song_name:
            text = song_name
            if artist:
                text = f"{song_name} — {artist}"
        else:
            text = "Sin canción cargada"
        self.hdr_song_title.setText(text)

    def update_visibility(self, song_source: str, has_song: bool):
        in_library = song_source == "library"
        is_folder = song_source == "folder"
        self.hdr_close_btn.setVisible(has_song)
        self._update_actions_row(in_library, is_folder)
        self._update_chordpro_section()

    def _update_actions_row(self, in_library, is_folder):
        m = self.main
        self.save_lib_btn.setVisible(is_folder)
        self.save_changes_btn.setVisible(
            in_library and m.state.has_unsaved_changes
        )
        self.generate_chordpro_btn.setVisible(in_library)
        self.toggle_live_btn.setVisible(in_library)
        self.more_btn.setVisible(in_library)

        if in_library and m.state.current_song_name:
            chopro_path = os.path.join(
                m.lib_mgr.library_path, m.state.current_song_name,
                f"{m.state.current_song_name}.chopro"
            )
            if os.path.exists(chopro_path):
                self.generate_chordpro_btn.setText("Regenerar Sheet")
            else:
                self.generate_chordpro_btn.setText("Generar Sheet")

    def update_save_buttons(self):
        in_library = self.main.state.current_song_source == "library"
        is_folder = self.main.state.current_song_source == "folder"
        self._update_actions_row(in_library, is_folder)

    def show_karaoke(self, visible: bool):
        """Muestra/oculta el Live Chords en lugar del reproductor y otros elementos."""
        if visible:
            if self._karaoke_widget is None:
                self._karaoke_widget = self.main.live_display_widget
            if self._karaoke_widget.parent() is not self:
                self._karaoke_widget.setParent(self)
            layout = self.layout()
            if layout is not None:
                if self._karaoke_widget not in [layout.itemAt(i).widget() for i in range(layout.count())]:
                    layout.addWidget(self._karaoke_widget, 1)
            self.player_section.setVisible(False)
            self.status_row.setVisible(False)
            self.stems_scroll.setVisible(False)
            self.actions_row.setVisible(False)
            self.info_section.setVisible(False)
            self.chordpro_section.setVisible(False)
            self.extract_panel.setVisible(False)
            self._karaoke_widget.setVisible(True)
        else:
            if self._karaoke_widget is not None:
                self._karaoke_widget.setVisible(False)
                self._karaoke_widget.setParent(None)
                self.main.center_stack.addWidget(self._karaoke_widget)
            self.player_section.setVisible(True)
            self.status_row.setVisible(True)
            self.stems_scroll.setVisible(True)
            self.actions_row.setVisible(True)
            self.info_section.setVisible(True)
            self.extract_panel.setVisible(self.main.state.stems != {})
            self._update_chordpro_section()

    def update_peak(self, peak_val):
        self.info_cards.update_peak(peak_val)

    def set_deck_status_text(self, text: str):
        try:
            self.deck_status_label.setText(text)
        except Exception:
            pass

    def set_deck_status_visible(self, visible: bool):
        try:
            self.deck_status_label.setVisible(visible)
        except Exception:
            pass

    def set_deck_progress_value(self, value: int, visible: bool = True):
        try:
            self.deck_progress_bar.setValue(value)
            self.deck_progress_bar.setVisible(visible)
        except Exception:
            pass

    def set_deck_bg_status(self, text: str, visible: bool = True):
        try:
            self.deck_bg_status_label.setText(text)
            self.deck_bg_status_label.setVisible(visible)
        except Exception:
            pass
