"""Ventana principal que orquesta todos los módulos de la aplicación."""

import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QProgressBar,
    QGroupBox, QCheckBox, QSpinBox, QScrollArea, QFrame, QSizePolicy,
    QComboBox, QTextEdit, QStackedWidget, QLineEdit, QInputDialog
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont

from app.utils.paths import get_icons_dir
from app.state_manager import StateManager
from app.thread_manager import ThreadManager
from app.data.config_manager import ConfigManager
from app.data.library_manager import LibraryManager
from app.ui.theme import apply_theme, DARK_THEME
from app.ui.svg_icon import svg_icon
from app.ui.volume_slider import VolumeSlider
from app.ui.pan_slider import PanSlider
from app.ui.library_panel import LibraryPanel
from app.ui.setlist_panel import SetlistPanel
from app.ui.meters_panel import SystemMetersPanel
from app.ui.chordpro_preview import ChordProPreviewWidget
from app.ui.live_display import LiveChordWidget

from app.controllers.song_loading import SongLoadingMixin
from app.controllers.save_library import SaveLibraryMixin
from app.controllers.stem_ui import StemUIMixin
from app.controllers.master_metronome import MasterMetronomeMixin
from app.controllers.count_in_click import CountInClickMixin
from app.controllers.undo_redo import UndoRedoMixin
from app.controllers.layout import LayoutMixin
from app.controllers.pitch_tempo import PitchTempoMixin
from app.controllers.playback import PlaybackMixin
from app.controllers.chordpro_preview import ChordProPreviewMixin
from app.controllers.chordpro_generation import ChordProGenerationMixin


class StemPlayer(
    QMainWindow,
    SongLoadingMixin,
    SaveLibraryMixin,
    StemUIMixin,
    MasterMetronomeMixin,
    CountInClickMixin,
    UndoRedoMixin,
    LayoutMixin,
    PitchTempoMixin,
    PlaybackMixin,
    ChordProPreviewMixin,
    ChordProGenerationMixin,
):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stem Player")
        self.setMinimumSize(1400, 800)
        self.resize(1550, 800)

        self.state = StateManager()
        self.threads = ThreadManager()
        self.config_mgr = ConfigManager()
        self.lib_mgr = LibraryManager(self.config_mgr.get_library_path())
        self.icons_dir = get_icons_dir()

        self._pending_seek = None
        self._is_manual_stop = False
        self._auto_play_pending = False
        self.blink_state = False
        self.left_panel_collapsed = False

        self.chordpro_preview_widget = None
        self.chordpro_fullscreen_view = None
        self.chordpro_path = None

        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self._toggle_blink)
        self.blink_timer.start(500)

        self._build_ui()
        apply_theme(self, DARK_THEME)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QHBoxLayout(central)
        main.setContentsMargins(0, 4, 8, 8)
        main.setSpacing(6)

        left_center_container = QWidget()
        left_center_layout = QHBoxLayout(left_center_container)
        left_center_layout.setContentsMargins(0, 0, 0, 0)
        left_center_layout.setSpacing(0)

        # ---- Left Panel ----
        self._left_panel(left_center_layout)

        # ---- Center Panel ----
        self._center_panel(left_center_layout)

        main.addWidget(left_center_container, 1)

        # ---- Right Panel ----
        right_panel = QWidget()
        self._right_panel(right_panel)

        main.addWidget(right_panel, 0)

        self.collapse_btn = QPushButton(self)
        self.collapse_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-h-expand.svg"), "#888888"))
        self.collapse_btn.setFixedSize(24, 24)
        self.collapse_btn.setToolTip("Expandir/Contraer panel izquierdo")
        self.collapse_btn.clicked.connect(self._toggle_left_panel)
        self.collapse_btn.move(6, 8)
        self.collapse_btn.setStyleSheet("background: transparent; border: none; border-radius: 4px;")
        self.collapse_btn.raise_()

    def _on_edit_key_clicked(self):
        current_key = self.state.detected_key if self.state.detected_key else "C"
        new_key, ok = QInputDialog.getText(
            self, "Editar tonalidad",
            "Tonalidad de la canción (ej: C, C#, D, D#, E, F, F#, G, G#, A, A#, B, Dm, etc.):",
            text=current_key
        )
        if ok and new_key.strip():
            new_key = new_key.strip()
            self.state.detected_key = new_key
            self.key_label.setText(f"Key: {new_key}")
            if self.state.current_song_source == "library" and self.state.current_song_name:
                self.lib_mgr.library_path = self.config_mgr.get_library_path()
                meta = self.lib_mgr.get_metadata(self.state.current_song_name)
                if meta:
                    meta["detected_key"] = new_key
                    self.lib_mgr.save_metadata(self.state.current_song_name, meta)

    # -- ---------------------------------- --
    # -- ---------------------------------- --
    # Left Panel
    def _left_panel(self, left_center_layout):
        self.lib_panel = QWidget()
        self.lib_panel.setFixedWidth(340)
        lib_layout = QVBoxLayout(self.lib_panel)
        lib_layout.setContentsMargins(8, 8, 8, 8)
        lib_layout.setSpacing(8)

        self.library_widget = LibraryPanel(self.config_mgr.config, self.icons_dir, self)
        self.library_widget.song_load_requested.connect(self._on_song_load_requested)
        self.library_widget.song_renamed.connect(self._on_library_song_renamed)
        self.library_widget.song_deleted.connect(self._on_library_song_deleted)
        self.library_widget.song_export_requested.connect(self._on_song_export_requested)
        self.library_widget.library_list.itemClicked.connect(self._on_library_item_clicked)
        lib_layout.addWidget(self.library_widget)

        self.setlist_widget = SetlistPanel(self.config_mgr.config, self.icons_dir, self)
        self.setlist_widget.song_load_requested.connect(self._on_song_load_requested)
        self.setlist_widget.setlist_songs_list.itemClicked.connect(self._on_setlist_item_clicked)
        lib_layout.addWidget(self.setlist_widget)

        left_center_layout.addWidget(self.lib_panel)

    # -- ---------------------------------- --
    # -- ---------------------------------- --
    # Center Panel
    def _center_panel(self, left_center_layout):
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(40, 0, 10, 0)
        center_layout.setSpacing(8)

        self._build_load_button(center_layout)
        self._build_song_info(center_layout)
        self._build_status_area(center_layout)
        self._build_master_metronome_area(center_layout)
        self._build_stems_area(center_layout)
        self._build_action_buttons(center_layout)
        self._build_close_row(center_layout)

        left_center_layout.addWidget(center_panel, 1)

    def _build_load_button(self, center_layout):
        load_btn = QPushButton("Cargar Carpeta de Stems")
        load_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-open.svg")))
        load_btn.setMinimumHeight(36)
        load_btn.clicked.connect(self._load_stems)
        center_layout.addWidget(load_btn)

    def _build_song_info(self, center_layout):
        self.song_info_layout = QVBoxLayout()
        self.song_info_layout.setSpacing(2)

        self.song_name_label = QLabel("Canción: --")
        self.song_name_label.setStyleSheet(f"color: {DARK_THEME.TEXT_PRIMARY}; font-size: 14px; font-weight: bold;")
        self.song_name_label.setWordWrap(True)
        self.song_info_layout.addWidget(self.song_name_label)

        artist_row = QHBoxLayout()
        artist_row.addWidget(QLabel("Artista:"))
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Nombre del artista...")
        self.artist_input.textChanged.connect(self._on_artist_changed)
        artist_row.addWidget(self.artist_input)
        artist_row.addStretch()
        self.song_info_layout.addLayout(artist_row)

        center_layout.addLayout(self.song_info_layout)

    def _build_status_area(self, center_layout):
        self.status_label = QLabel("Listo")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {DARK_THEME.TEXT_SECONDARY}; font-size: 12px;")
        center_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        center_layout.addWidget(self.progress_bar)

        self.bg_status_label = QLabel("")
        self.bg_status_label.setAlignment(Qt.AlignCenter)
        self.bg_status_label.setStyleSheet(f"color: {DARK_THEME.ACCENT_PURPLE}; font-size: 11px; font-style: italic;")
        self.bg_status_label.setVisible(False)
        center_layout.addWidget(self.bg_status_label)

    def _build_master_metronome_area(self, center_layout):
        master_row = QHBoxLayout()
        master_row.setSpacing(8)

        master_label = QLabel("Master:")
        master_label.setStyleSheet(f"color: {DARK_THEME.TEXT_PRIMARY}; font-size: 12px; font-weight: bold;")
        master_label.setFixedWidth(50)
        master_row.addWidget(master_label)

        self.master_volume_slider = VolumeSlider(parent=self, icons_dir=self.icons_dir)
        self.master_volume_slider.setValue(self.state.master_volume)
        self.master_volume_slider.valueChanged.connect(self._on_master_volume_changed)
        self.master_volume_slider.sliderReleased.connect(self._on_master_volume_released)
        self.master_volume_slider.setMinimumSize(160, 50)
        self.master_volume_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        master_row.addWidget(self.master_volume_slider)

        metro_row = QHBoxLayout()
        metro_row.setSpacing(8)

        metro_icon_btn = QPushButton()
        metro_icon_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-metronome.svg"), "#888888"))
        metro_icon_btn.setFixedSize(24, 24)
        metro_icon_btn.setToolTip("Volumen del metrónomo")
        metro_icon_btn.setEnabled(False)
        self.metro_icon_btn = metro_icon_btn
        metro_row.addWidget(metro_icon_btn)

        self.click_check = QCheckBox("Activar Metrónomo")
        self.click_check.setToolTip("Metrónomo persistente durante la canción")
        self.click_check.setChecked(self.state.click_during_playback)
        self.click_check.stateChanged.connect(self._on_click_during_changed)
        metro_row.addWidget(self.click_check)

        metro_row_2 = QHBoxLayout()
        metro_row_2.setSpacing(8)

        self.metronome_volume_slider = VolumeSlider(parent=self, icons_dir=self.icons_dir)
        self.metronome_volume_slider.setValue(self.state.metronome_volume)
        self.metronome_volume_slider.valueChanged.connect(self._on_metronome_volume_changed)
        self.metronome_volume_slider.sliderReleased.connect(self._on_metronome_volume_released)
        self.metronome_volume_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.metronome_volume_slider.setVisible(False)
        metro_row_2.addWidget(self.metronome_volume_slider)

        self.metronome_pan_slider = PanSlider(parent=self, icons_dir=self.icons_dir)
        self.metronome_pan_slider.setValue(self.state.metronome_pan)
        self.metronome_pan_slider.setMaximumSize(200, 80)
        self.metronome_pan_slider.valueChanged.connect(self._on_metronome_pan_changed)
        self.metronome_pan_slider.sliderReleased.connect(self._on_metronome_pan_released)
        self.metronome_pan_slider.setVisible(False)
        metro_row_2.addWidget(self.metronome_pan_slider)
        master_row.setStretch(master_row.indexOf(self.master_volume_slider), 1)

        center_layout.addLayout(master_row)
        center_layout.addLayout(metro_row)
        center_layout.addLayout(metro_row_2)

    def _build_stems_area(self, center_layout):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.NoFrame)
        self.stems_container = QWidget()
        self.stems_layout = QVBoxLayout(self.stems_container)
        self.stems_layout.setAlignment(Qt.AlignTop)
        self.stems_layout.setSpacing(8)
        self.stems_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(self.stems_container)

        self.center_stack = QStackedWidget()
        self.center_stack.addWidget(scroll)

        self.live_display_widget = LiveChordWidget()
        self.live_display_widget.close_requested.connect(lambda: self.toggle_live_btn.setChecked(False))
        self.center_stack.addWidget(self.live_display_widget)

        self.chordpro_fullscreen_view = QWidget()
        chordpro_fullscreen_layout = QVBoxLayout(self.chordpro_fullscreen_view)
        chordpro_fullscreen_layout.setContentsMargins(10, 10, 10, 10)
        chordpro_fullscreen_layout.setSpacing(6)

        chordpro_button_row = QHBoxLayout()
        chordpro_button_row.setSpacing(6)

        self.chordpro_close_fullscreen_btn = QPushButton("Cerrar Preview")
        self.chordpro_close_fullscreen_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-close-x.svg"), "#FF5555"))
        self.chordpro_close_fullscreen_btn.setMinimumHeight(28)
        self.chordpro_close_fullscreen_btn.clicked.connect(self._hide_chordpro_fullscreen)
        chordpro_button_row.addWidget(self.chordpro_close_fullscreen_btn)

        self.chordpro_edit_fullscreen_btn = QPushButton("Editar Acordes")
        self.chordpro_edit_fullscreen_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-edit.svg")))
        self.chordpro_edit_fullscreen_btn.setMinimumHeight(28)
        self.chordpro_edit_fullscreen_btn.clicked.connect(self._on_edit_chordpro_clicked)
        chordpro_button_row.addWidget(self.chordpro_edit_fullscreen_btn)

        chordpro_button_row.addStretch()
        chordpro_fullscreen_layout.addLayout(chordpro_button_row)

        self.chordpro_fullscreen_text = QTextEdit()
        self.chordpro_fullscreen_text.setReadOnly(True)
        self.chordpro_fullscreen_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DARK_THEME.BG_EDITOR};
                color: {DARK_THEME.TEXT_EDITOR};
                border: 1px solid {DARK_THEME.BORDER_ALT};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                padding: 8px;
                line-height: 1.4;
            }}
        """)
        chordpro_fullscreen_layout.addWidget(self.chordpro_fullscreen_text)

        self.center_stack.addWidget(self.chordpro_fullscreen_view)

        center_layout.addWidget(self.center_stack, 1)

    def _build_action_buttons(self, center_layout):
        save_row = QHBoxLayout()
        self.save_lib_btn = QPushButton("Guardar en librería")
        self.save_lib_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-save.svg")))
        self.save_lib_btn.setFixedHeight(28)
        self.save_lib_btn.clicked.connect(self._save_to_library)
        self.save_lib_btn.setVisible(False)
        save_row.addWidget(self.save_lib_btn)

        self.save_changes_btn = QPushButton("Guardar Cambios")
        self.save_changes_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-save.svg")))
        self.save_changes_btn.setFixedHeight(28)
        self.save_changes_btn.clicked.connect(self._save_changes)
        self.save_changes_btn.setVisible(False)
        save_row.addWidget(self.save_changes_btn)

        self.generate_chordpro_btn = QPushButton("Generar Sheet de acordes")
        self.generate_chordpro_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-file-code.svg")))
        self.generate_chordpro_btn.setFixedHeight(28)
        self.generate_chordpro_btn.clicked.connect(self._on_generate_chordpro_clicked)
        self.generate_chordpro_btn.setVisible(False)
        save_row.addWidget(self.generate_chordpro_btn)

        self.edit_chordpro_btn = QPushButton("Editar Acordes")
        self.edit_chordpro_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-edit.svg")))
        self.edit_chordpro_btn.setFixedHeight(28)
        self.edit_chordpro_btn.clicked.connect(self._on_edit_chordpro_clicked)
        self.edit_chordpro_btn.setVisible(False)
        save_row.addWidget(self.edit_chordpro_btn)

        self.save_as_btn = QPushButton("Guardar Como...")
        self.save_as_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-saveas.svg")))
        self.save_as_btn.setFixedHeight(28)
        self.save_as_btn.clicked.connect(self._save_as)
        self.save_as_btn.setVisible(False)
        save_row.addWidget(self.save_as_btn)

        self.toggle_live_btn = QPushButton("Karaoke")
        self.toggle_live_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-microphone.svg")))
        self.toggle_live_btn.setFixedHeight(28)
        self.toggle_live_btn.setCheckable(True)
        self.toggle_live_btn.clicked.connect(self._toggle_live_mode)
        self.toggle_live_btn.setVisible(False)
        save_row.addWidget(self.toggle_live_btn)

        center_layout.addLayout(save_row)

    def _build_close_row(self, center_layout):
        close_row = QHBoxLayout()
        self.close_song_btn = QPushButton("Cerrar Canción")
        self.close_song_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-close-x.svg"), "#FF5555"))
        self.close_song_btn.setMinimumHeight(36)
        self.close_song_btn.clicked.connect(self._close_song)
        self.close_song_btn.setVisible(False)
        close_row.addWidget(self.close_song_btn)

        close_row.addStretch()

        self.add_to_setlist_btn = QPushButton("Añadir a Setlist")
        self.add_to_setlist_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-plus.svg")))
        self.add_to_setlist_btn.setMinimumHeight(36)
        self.add_to_setlist_btn.clicked.connect(self._on_add_to_setlist_clicked)
        self.add_to_setlist_btn.setVisible(False)
        close_row.addWidget(self.add_to_setlist_btn)

        center_layout.addLayout(close_row)

    # -- ---------------------------------- --
    # -- ---------------------------------- --
    # Right Panel
    def _right_panel(self, right_panel):
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        right_layout.setAlignment(Qt.AlignTop)

        analysis_box = QGroupBox("Análisis")
        analysis_box.setObjectName("analysisBox")
        av = QVBoxLayout(analysis_box)
        av.setSpacing(8)

        key_row = QHBoxLayout()
        self.key_label = QLabel("Key: --")
        self.key_label.setFont(QFont("Arial", 28, QFont.Bold))
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setStyleSheet(f"color: {DARK_THEME.ACCENT_CYAN};")
        key_row.addWidget(self.key_label, 1)
        self.edit_key_btn = QPushButton()
        self.edit_key_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-edit.svg"), "#888888"))
        self.edit_key_btn.setFixedSize(28, 28)
        self.edit_key_btn.setToolTip("Editar tonalidad detectada")
        self.edit_key_btn.clicked.connect(self._on_edit_key_clicked)
        key_row.addWidget(self.edit_key_btn)
        av.addLayout(key_row)

        self.bpm_label = QLabel("BPM: --")
        self.bpm_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.bpm_label.setAlignment(Qt.AlignCenter)
        self.bpm_label.setStyleSheet(f"color: {DARK_THEME.TEXT_SECONDARY};")
        av.addWidget(self.bpm_label)

        right_layout.addWidget(analysis_box)

        pitch_box = QGroupBox("Pitch Shift")
        pitch_box.setObjectName("pitchBox")
        ph = QHBoxLayout(pitch_box)
        ph.setSpacing(6)
        self.pitch_buttons = {}
        for shift in [-3, -2, -1, 0, 1, 2, 3]:
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setMinimumSize(50, 40)
            btn.setProperty("shift", shift)
            if shift == 0:
                btn.setText("Original")
                btn.setToolTip("Tono original")
            else:
                sign = "+" if shift > 0 else ""
                btn.setText(f"{sign}{shift}")
                btn.setToolTip(f"{sign}{shift} semitonos")
            btn.clicked.connect(lambda checked, s=shift: self._on_pitch_clicked(s))
            self.pitch_buttons[shift] = btn
            ph.addWidget(btn)
        self.pitch_buttons[0].setChecked(True)
        self._update_pitch_button_labels()
        right_layout.addWidget(pitch_box)

        tempo_box = QGroupBox("Tempo")
        tempo_box.setObjectName("tempoBox")
        th = QHBoxLayout(tempo_box)
        th.setSpacing(10)

        th.addWidget(QLabel("Original:"))
        self.orig_bpm_label = QLabel("--")
        self.orig_bpm_label.setStyleSheet(f"color: {DARK_THEME.TEXT_SECONDARY};")
        th.addWidget(self.orig_bpm_label)

        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(20, 300)
        self.bpm_spin.setValue(120)
        self.bpm_spin.setSuffix(" BPM")
        th.addWidget(self.bpm_spin)

        self.apply_tempo_btn = QPushButton("Aplicar")
        self.apply_tempo_btn.clicked.connect(self._on_apply_tempo_clicked)
        th.addWidget(self.apply_tempo_btn)

        self.tempo_ratio_label = QLabel("100%")
        self.tempo_ratio_label.setStyleSheet(f"color: {DARK_THEME.TEXT_SECONDARY}; min-width: 50px;")
        th.addWidget(self.tempo_ratio_label)

        right_layout.addWidget(tempo_box)

        reset_row = QHBoxLayout()
        self.undo_btn = QPushButton()
        self.undo_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-undo.svg")))
        self.undo_btn.setFixedSize(36, 36)
        self.undo_btn.setToolTip("Deshacer")
        self.undo_btn.clicked.connect(self._undo)
        self.undo_btn.setEnabled(False)
        reset_row.addWidget(self.undo_btn)

        self.redo_btn = QPushButton()
        self.redo_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-redo.svg")))
        self.redo_btn.setFixedSize(36, 36)
        self.redo_btn.setToolTip("Rehacer")
        self.redo_btn.clicked.connect(self._redo)
        self.redo_btn.setEnabled(False)
        reset_row.addWidget(self.redo_btn)

        self.reset_btn = QPushButton("Restablecer")
        self.reset_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-history.svg")))
        self.reset_btn.setMinimumHeight(36)
        self.reset_btn.clicked.connect(self._reset_all)
        reset_row.addWidget(self.reset_btn)

        right_layout.addLayout(reset_row)

        play_box = QGroupBox("Reproducción")
        play_box.setObjectName("playBox")
        pv = QVBoxLayout(play_box)
        pv.setSpacing(10)

        count_row = QHBoxLayout()
        count_row.addWidget(QLabel("Count-in:"))
        self.count_in_combo = QComboBox()
        self.count_in_combo.addItems(["Sin count-in", "1 compás", "2 compases"])
        self.count_in_combo.currentIndexChanged.connect(self._on_count_in_changed)
        count_row.addWidget(self.count_in_combo)
        count_row.addStretch()
        pv.addLayout(count_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-prev.svg")))
        self.prev_btn.setFixedSize(40, 40)
        self.prev_btn.setToolTip("Canción anterior")
        self.prev_btn.clicked.connect(self.setlist_widget.play_previous)
        btn_row.addWidget(self.prev_btn)

        self.play_btn = QPushButton()
        self.play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-play.svg")))
        self.play_btn.setFixedSize(48, 48)
        self.play_btn.setToolTip("Play / Pause")
        self.play_btn.clicked.connect(self._toggle_play)
        btn_row.addWidget(self.play_btn)

        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-stop.svg")))
        self.stop_btn.setFixedSize(40, 40)
        self.stop_btn.setToolTip("Stop")
        self.stop_btn.clicked.connect(self._stop_playback)
        btn_row.addWidget(self.stop_btn)

        self.next_btn = QPushButton()
        self.next_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-next.svg")))
        self.next_btn.setFixedSize(40, 40)
        self.next_btn.setToolTip("Canción siguiente")
        self.next_btn.clicked.connect(self.setlist_widget.play_next)
        btn_row.addWidget(self.next_btn)

        self.auto_play_btn = QPushButton()
        self.auto_play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-preset-ab.svg"), "#FFFFFF"))
        self.auto_play_btn.setFixedSize(40, 40)
        self.auto_play_btn.setCheckable(True)
        self.auto_play_btn.setToolTip("Auto-avanzar y reproducir en setlist")
        self.auto_play_btn.toggled.connect(self._on_auto_play_toggled)
        btn_row.addWidget(self.auto_play_btn)

        btn_row.addStretch()
        pv.addLayout(btn_row)

        self.playback_progress = QSlider(Qt.Horizontal)
        self.playback_progress.setRange(0, 1000)
        self.playback_progress.setValue(0)
        self.playback_progress.setStyleSheet(DARK_THEME.playback_slider_qss())
        self.playback_progress.setTracking(True)
        self.playback_progress.sliderReleased.connect(self._on_playback_seek)
        self.playback_progress.sliderMoved.connect(self._on_playback_preview)
        pv.addWidget(self.playback_progress)

        time_row = QHBoxLayout()
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet(f"color: {DARK_THEME.TEXT_PRIMARY}; font-size: 11px; font-family: {DARK_THEME.FONT_MONO};")
        time_row.addWidget(self.current_time_label)
        time_row.addStretch()
        self.total_time_label = QLabel("00:00")
        self.total_time_label.setStyleSheet(f"color: {DARK_THEME.TEXT_SECONDARY}; font-size: 11px; font-family: {DARK_THEME.FONT_MONO};")
        time_row.addWidget(self.total_time_label)
        pv.addLayout(time_row)

        right_layout.addWidget(play_box)

        self.chordpro_preview_widget = ChordProPreviewWidget(parent=self, icons_dir=self.icons_dir)
        self.chordpro_preview_widget.setMaximumHeight(360)
        self.chordpro_preview_widget.setVisible(False)
        right_layout.addWidget(self.chordpro_preview_widget)

        meters_group = QGroupBox("Medidores del Sistema")
        meters_layout = QVBoxLayout(meters_group)
        meters_layout.setContentsMargins(4, 8, 4, 4)
        meters_layout.setSpacing(4)
        self.meters_panel = SystemMetersPanel(self.icons_dir, self)
        meters_layout.addWidget(self.meters_panel)
        right_layout.addWidget(meters_group)

        right_layout.addStretch()
