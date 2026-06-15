"""Interfaz gráfica principal de Stem Player."""

import os
import sys
import shutil
import json
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QProgressBar, QFileDialog,
    QGroupBox, QCheckBox, QSpinBox, QScrollArea, QFrame, QSizePolicy,
    QListWidget, QListWidgetItem, QComboBox, QInputDialog, QMessageBox,
    QLineEdit, QMenu, QTextEdit, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer, QSettings
from PySide6.QtGui import QFont, QIcon

from utils_paths import get_icons_dir
from utils import get_key_at_semitone_shift
from audio_engine import StemLoaderThread, PitchTempoThread, PlaybackThread
from stem_widgets import StemItemWidget, VolumeSlider, PanSlider, svg_icon
from config_manager import (
    load_config, save_config, get_library_path, set_library_path,
    get_setlists, add_setlist, update_setlist, remove_setlist
)
from library_manager import (
    get_library_songs, get_song_metadata, save_song_metadata, create_default_metadata
)
from gui_library import LibraryPanel
from gui_setlist import SetlistPanel
from gui_meters import SystemMetersPanel
from theme import apply_dark_theme
from chordpro import Song
from chordpro.renderers.html import render as render_html

class ChordProPreviewWidget(QWidget):
    """Widget para previsualizar el contenido del archivo .chopro"""
    
    def __init__(self, parent=None, icons_dir=""):
        super().__init__(parent)
        self.icons_dir = icons_dir
        self.parent_window = parent
        self._init_ui()
    
    def _init_ui(self):
        # Layout principal del widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        chord_preview_box = QGroupBox("ChordPro Preview")
        chord_preview_box.setObjectName("chordPreviewBox")
        
        box_layout = QVBoxLayout(chord_preview_box)
        box_layout.setContentsMargins(4, 4, 4, 4)
        box_layout.setSpacing(4)

        # Área de texto
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e42;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
                padding: 8px;
                line-height: 1.4;
            }
        """)
        box_layout.addWidget(self.text_display)

        # Botones
        button_row = QHBoxLayout()
        button_row.setSpacing(4)

        self.maximize_btn = QPushButton()
        self.maximize_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-v-expand.svg")))
        self.maximize_btn.setFixedSize(24, 24)
        self.maximize_btn.setToolTip("Maximizar preview de acordes")
        self.maximize_btn.clicked.connect(self._on_maximize)
        button_row.addWidget(self.maximize_btn)

        self.live_btn = QPushButton()
        self.live_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-microphone.svg")))
        self.live_btn.setFixedSize(24, 24)
        self.live_btn.setToolTip("Activar modo Karaoke/Live")
        self.live_btn.clicked.connect(self._on_live_clicked)
        button_row.addWidget(self.live_btn)

        self.edit_btn = QPushButton("Editar")
        self.edit_btn.setFixedHeight(24)
        self.edit_btn.setToolTip("Abrir editor de acordes")
        self.edit_btn.clicked.connect(self._on_edit_clicked)
        button_row.addWidget(self.edit_btn)

        button_row.addStretch()
        box_layout.addLayout(button_row)

        # ← Importante: agregar el groupbox al widget principal
        main_layout.addWidget(chord_preview_box)
    
    def load_chopro_content(self, chopro_path: str):
        if not os.path.exists(chopro_path):
            self.text_display.setText("No se encontró archivo de acordes.")
            return

        try:
            song = Song(chopro_path)
            html_content = render_html(song)

            try:
                html_content = html_content.encode('cp1252').decode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                html_content = html_content.encode('latin-1').decode('utf-8')

            if '<head>' not in html_content:
                html_content = '<meta charset="UTF-8">\n' + html_content
            else:
                html_content = html_content.replace('<head>', '<head>\n<meta charset="UTF-8">', 1)

            self.text_display.setHtml(html_content)

        except Exception as e:
            try:
                with open(chopro_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.text_display.setText(content)
                self.text_display.append(f"\n\n--- Error al renderizar: {str(e)} ---")
            except Exception as e2:
                self.text_display.setText(f"Error al cargar acordes: {str(e2)}")
    
    def _on_maximize(self):
        """Maximizar el preview en el panel central"""
        if self.parent_window:
            self.parent_window._show_chordpro_fullscreen()
    
    def _on_live_clicked(self):
        """Activar el modo live/karaoke"""
        if self.parent_window:
            self.parent_window.toggle_live_btn.setChecked(True)
            self.parent_window._toggle_live_mode(True)
    
    def _on_edit_clicked(self):
        """Abrir el editor de acordes"""
        if self.parent_window:
            self.parent_window._on_edit_chordpro_clicked()


class StemPlayer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stem Player")
        self.setMinimumSize(1400, 800)
        self.resize(1550, 800) # Tamaño inicial sugerido (el sistema puede ajustarlo si no cabe en pantalla)
        #self.showMaximized()
        self.mix_sr = 44100
        self.stems = {}
        self.originals = {}
        self.detected_key = "C"
        self.detected_bpm = 120
        self.current_pitch_shift = 0
        self.current_tempo_ratio = 1.0
        self.count_in_bars = 0
        self.click_during_playback = False
        self.metronome_volume = 0.5
        self.metronome_pan = 0.0
        self.master_volume = 1.0
        self.current_song_name = ""
        self.current_song_artist = ""
        self.has_unsaved_changes = False
        self.history = []
        self.history_idx = -1
        self.current_song_source = ""  # "folder" o "library"
        self.playback_thread = None
        self.loader_thread = None
        self.pitch_tempo_thread = None
        self.export_thread = None
        self.chord_analysis_thread = None
        self.openrouter_thread = None
        self._pending_seek = None 
        
        # Preloading cache
        self.preloaded_song_cache = None
        self.preloader_thread = None
        self._zombie_threads = set()
        
        # UI Blink Timer for playback
        self.blink_timer = QTimer(self)
        self.blink_timer.timeout.connect(self._toggle_blink)
        self.blink_timer.start(500)
        self.blink_state = False
        
        # ChordPro preview
        self.chordpro_preview_widget = None
        self.chordpro_fullscreen_view = None
        self.chordpro_path = None

        self.icons_dir = get_icons_dir()
        self.config = load_config()
        self.current_setlist_index = -1
        self.current_setlist_song_index = -1
        self._build_ui()
        apply_dark_theme(self)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        # Layout principal
        main = QHBoxLayout(central)
        main.setContentsMargins(0, 4, 8, 8)    # Izquierda completamente pegada
        main.setSpacing(6)

        # ==================== CONTENEDOR IZQUIERDO + CENTRAL ====================
        left_center_container = QWidget()
        left_center_layout = QHBoxLayout(left_center_container)
        left_center_layout.setContentsMargins(0, 0, 0, 0)
        left_center_layout.setSpacing(0)

        # ---- Panel Izquierdo (Librería) ----
        self.lib_panel = QWidget()
        self.lib_panel.setFixedWidth(340)
        lib_layout = QVBoxLayout(self.lib_panel)
        lib_layout.setContentsMargins(8, 8, 8, 8)
        lib_layout.setSpacing(8)

        self.library_widget = LibraryPanel(self.config, self.icons_dir, self)
        self.library_widget.song_load_requested.connect(self._on_song_load_requested)
        self.library_widget.song_renamed.connect(self._on_library_song_renamed)
        self.library_widget.song_deleted.connect(self._on_library_song_deleted)
        self.library_widget.song_export_requested.connect(self._on_song_export_requested)
        self.library_widget.library_list.itemClicked.connect(self._on_library_item_clicked)
        lib_layout.addWidget(self.library_widget)

        self.setlist_widget = SetlistPanel(self.config, self.icons_dir, self)
        self.setlist_widget.song_load_requested.connect(self._on_song_load_requested)
        self.setlist_widget.setlist_songs_list.itemClicked.connect(self._on_setlist_item_clicked)
        lib_layout.addWidget(self.setlist_widget)

        left_center_layout.addWidget(self.lib_panel)

        # ---- Panel Central (Stems) ----
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setContentsMargins(40, 0, 10, 0)
        center_layout.setSpacing(8)

        load_btn = QPushButton("Cargar Carpeta de Stems")
        load_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-open.svg")))
        load_btn.setMinimumHeight(36)
        load_btn.clicked.connect(self._load_stems)
        center_layout.addWidget(load_btn)

        # Current Song Info
        self.song_info_layout = QVBoxLayout()
        self.song_info_layout.setSpacing(2)
        
        self.song_name_label = QLabel("Canción: --")
        self.song_name_label.setStyleSheet("color: #FFFFFF; font-size: 14px; font-weight: bold;")
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

        self.status_label = QLabel("Listo")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #888888; font-size: 12px;")
        center_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        center_layout.addWidget(self.progress_bar)
        
        self.bg_status_label = QLabel("")
        self.bg_status_label.setAlignment(Qt.AlignCenter)
        self.bg_status_label.setStyleSheet("color: #5555AA; font-size: 11px; font-style: italic;")
        self.bg_status_label.setVisible(False)
        center_layout.addWidget(self.bg_status_label)

        # Master row
        master_row = QHBoxLayout()
        master_row.setSpacing(8)
        
        master_label = QLabel("Master:")
        master_label.setStyleSheet("color: #FFFFFF; font-size: 12px; font-weight: bold;")
        master_label.setFixedWidth(50)
        master_row.addWidget(master_label)
        
        self.master_volume_slider = VolumeSlider(parent=self, icons_dir=self.icons_dir)
        self.master_volume_slider.setValue(self.master_volume)
        self.master_volume_slider.valueChanged.connect(self._on_master_volume_changed)
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
        self.click_check.setChecked(self.click_during_playback)
        self.click_check.stateChanged.connect(self._on_click_during_changed)
        metro_row.addWidget(self.click_check)
        
        metro_row_2 = QHBoxLayout()
        metro_row_2.setSpacing(8)

        self.metronome_volume_slider = VolumeSlider(parent=self, icons_dir=self.icons_dir)
        self.metronome_volume_slider.setValue(self.metronome_volume)
        self.metronome_volume_slider.valueChanged.connect(self._on_metronome_volume_changed)
        self.metronome_volume_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.metronome_volume_slider.setVisible(False)
        metro_row_2.addWidget(self.metronome_volume_slider)
        
        self.metronome_pan_slider = PanSlider(parent=self, icons_dir=self.icons_dir)
        self.metronome_pan_slider.setValue(self.metronome_pan)
        self.metronome_pan_slider.setMaximumSize(200, 80)
        self.metronome_pan_slider.valueChanged.connect(self._on_metronome_pan_changed)
        self.metronome_pan_slider.setVisible(False)
        metro_row_2.addWidget(self.metronome_pan_slider)
        master_row.setStretch(master_row.indexOf(self.master_volume_slider), 1)

        center_layout.addLayout(master_row)
        center_layout.addLayout(metro_row)
        center_layout.addLayout(metro_row_2)

        # Stems scroll
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
        from PySide6.QtWidgets import QStackedWidget
        self.center_stack = QStackedWidget()
        self.center_stack.addWidget(scroll)
        
        from live_display import LiveChordWidget
        self.live_display_widget = LiveChordWidget()
        self.live_display_widget.close_requested.connect(lambda: self.toggle_live_btn.setChecked(False))
        self.center_stack.addWidget(self.live_display_widget)
        
        # ChordPro fullscreen widget
        self.chordpro_fullscreen_view = QWidget()
        chordpro_fullscreen_layout = QVBoxLayout(self.chordpro_fullscreen_view)
        chordpro_fullscreen_layout.setContentsMargins(10, 10, 10, 10)
        chordpro_fullscreen_layout.setSpacing(6)
        
        # Botones en el fullscreen
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
        
        # Área de texto para fullscreen
        self.chordpro_fullscreen_text = QTextEdit()
        self.chordpro_fullscreen_text.setReadOnly(True)
        self.chordpro_fullscreen_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e42;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                padding: 8px;
                line-height: 1.4;
            }
        """)
        chordpro_fullscreen_layout.addWidget(self.chordpro_fullscreen_text)
        
        self.center_stack.addWidget(self.chordpro_fullscreen_view)
        
        center_layout.addWidget(self.center_stack, 1)

        # Save buttons
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

        # Close song
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

        left_center_layout.addWidget(center_panel, 1)

        # Agregar contenedor izquierdo+central
        main.addWidget(left_center_container, 1)

        # ==================== PANEL DERECHO ====================
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        right_layout.setAlignment(Qt.AlignTop)

        # Análisis
        analysis_box = QGroupBox("Análisis")
        analysis_box.setObjectName("analysisBox")
        av = QVBoxLayout(analysis_box)
        av.setSpacing(8)

        self.key_label = QLabel("Key: --")
        self.key_label.setFont(QFont("Arial", 28, QFont.Bold))
        self.key_label.setAlignment(Qt.AlignCenter)
        self.key_label.setStyleSheet("color: #00BFFF;")
        av.addWidget(self.key_label)

        self.bpm_label = QLabel("BPM: --")
        self.bpm_label.setFont(QFont("Arial", 18, QFont.Bold))
        self.bpm_label.setAlignment(Qt.AlignCenter)
        self.bpm_label.setStyleSheet("color: #888888;")
        av.addWidget(self.bpm_label)

        right_layout.addWidget(analysis_box)

        # Pitch Shift
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

        # Tempo
        tempo_box = QGroupBox("Tempo")
        tempo_box.setObjectName("tempoBox")
        th = QHBoxLayout(tempo_box)
        th.setSpacing(10)

        th.addWidget(QLabel("Original:"))
        self.orig_bpm_label = QLabel("--")
        self.orig_bpm_label.setStyleSheet("color: #888888;")
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
        self.tempo_ratio_label.setStyleSheet("color: #888888; min-width: 50px;")
        th.addWidget(self.tempo_ratio_label)

        right_layout.addWidget(tempo_box)

        # Reset row
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

        # Playback
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
        self.playback_progress.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #3E3E42;
                height: 6px;
                background: #2D2D30;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #0078D7;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #FFFFFF;
                width: 12px;
                height: 12px;
                margin: -3px 0;
                border-radius: 6px;
            }
        """)
        self.playback_progress.setTracking(True)
        self.playback_progress.sliderReleased.connect(self._on_playback_seek)
        self.playback_progress.sliderMoved.connect(self._on_playback_preview)
        pv.addWidget(self.playback_progress)
        
        time_row = QHBoxLayout()
        time_row.setSpacing(4)
        
        self.current_time_label = QLabel("00:00")
        self.current_time_label.setStyleSheet("color: #FFFFFF; font-size: 11px; font-family: monospace;")
        self.current_time_label.setAlignment(Qt.AlignLeft)
        time_row.addWidget(self.current_time_label)
        
        time_row.addStretch()
        
        self.total_time_label = QLabel("00:00")
        self.total_time_label.setStyleSheet("color: #888888; font-size: 11px; font-family: monospace;")
        self.total_time_label.setAlignment(Qt.AlignRight)
        time_row.addWidget(self.total_time_label)
        
        pv.addLayout(time_row)

        right_layout.addWidget(play_box)
        
        # ChordPro Preview (si existe archivo .chopro)
        self.chordpro_preview_widget = ChordProPreviewWidget(parent=self, icons_dir=self.icons_dir)
        self.chordpro_preview_widget.setMaximumHeight(360)
        self.chordpro_preview_widget.setVisible(False)
        right_layout.addWidget(self.chordpro_preview_widget)
        
        # System Meters (dentro de un grupo)
        meters_group = QGroupBox("Medidores del Sistema")
        meters_layout = QVBoxLayout(meters_group)
        meters_layout.setContentsMargins(4, 8, 4, 4)
        meters_layout.setSpacing(4)
        self.meters_panel = SystemMetersPanel(self.icons_dir, self)
        meters_layout.addWidget(self.meters_panel)
        right_layout.addWidget(meters_group)
        
        right_layout.addStretch()

        main.addWidget(right_panel, 0)

        # ==================== BOTÓN COLLAPSE ====================
        self.collapse_btn = QPushButton(self)
        self.collapse_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-h-expand.svg"), "#888888"))
        self.collapse_btn.setFixedSize(24, 24)
        self.collapse_btn.setToolTip("Expandir/Contraer panel izquierdo")
        self.collapse_btn.clicked.connect(self._toggle_left_panel)
        self.collapse_btn.move(6, 8)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background: rgba(60, 60, 60, 100);
            }
        """)
        self.collapse_btn.raise_()
        self.left_panel_collapsed = False

    # ------------------------------------------------------------------
    # Library/Setlist Handlers
    # ------------------------------------------------------------------
    def _on_song_load_requested(self, song_folder: str, song_name: str, metadata: dict):
        self._load_folder_internal(song_folder, song_name, "library", metadata)
        
    def _on_library_song_renamed(self, old_name: str, new_name: str):
        if self.current_song_name == old_name:
            self.current_song_name = new_name
            self.song_name_label.setText(f"Canción: {new_name}")

    def _on_library_song_deleted(self, name: str):
        if self.current_song_name == name:
            self._close_song()

    # ------------------------------------------------------------------
    # Library management
    # ------------------------------------------------------------------
    def _save_to_library(self):
        if not self.stems:
            self.status_label.setText("No hay stems para guardar")
            return False
        path = get_library_path(self.config)
        if not path:
            self.status_label.setText("Primero configura la carpeta de librería")
            return False

        name, ok = QInputDialog.getText(self, "Guardar en librería", "Nombre de la canción:")
        if not ok or not name.strip():
            return False
        name = name.strip()

        # Si vino de carpeta manual, copiar
        if self.current_song_source == "folder" and self.current_song_name:
            source = self.current_song_name  # guardamos la ruta original aquí
            if os.path.isdir(source):
                dest = copy_folder_to_library(source, path, name)
                song_folder = dest
            else:
                song_folder = os.path.join(path, name)
                os.makedirs(song_folder, exist_ok=True)
        else:
            song_folder = os.path.join(path, name)
            os.makedirs(song_folder, exist_ok=True)

        # Guardar stems actuales en la carpeta (sobrescribir si ya existen)
        for stem_name, data in self.stems.items():
            stem_path = os.path.join(song_folder, f"{stem_name}.wav")
            import soundfile as sf
            sf.write(stem_path, data["audio"], self.mix_sr)

        # Guardar metadata
        metadata = create_default_metadata(
            name=name,
            artist=self.current_song_artist,
            detected_key=self.detected_key,
            detected_bpm=self.detected_bpm,
            pitch_shift=self.current_pitch_shift,
            tempo_ratio=self.current_tempo_ratio,
            count_in_bars=self.count_in_bars,
            click_during_playback=self.click_during_playback,
            metronome_volume=self.metronome_volume,
            metronome_pan=self.metronome_pan,
            master_volume=self.master_volume,
            duration=self.total_time_label.text(),
            click_offset_samples=getattr(self, 'click_offset_samples', 0),
            stems=[
                {
                    "name": n,
                    "category": d.get("category", "Other"),
                    "volume": d["volume"],
                    "pan": d.get("pan", 0.0),
                    "muted": d["muted"],
                    "solo": d["solo"],
                    "fx_enabled": d.get("fx_enabled", True),
                }
                for n, d in self.stems.items()
            ]
        )
        
        # Preservar cached_audio_path si existe (usualmente no si es nuevo, pero por si acaso)
        old_meta = get_song_metadata(path, name)
        if old_meta and "cached_audio_path" in old_meta:
            metadata["cached_audio_path"] = old_meta["cached_audio_path"]
            
        save_song_metadata(path, name, metadata)
        self.current_song_name = name
        self.current_song_source = "library"
        self.has_unsaved_changes = False
        self._update_save_buttons()
        self.library_widget.refresh_ui()
        self.status_label.setText(f"Guardado: {name}")
        
        if self.setlist_widget.current_setlist_index >= 0:
            self.setlist_widget.add_song_to_current(name)
            
        return True

    def _save_changes(self):
        if not self.stems or self.current_song_source != "library" or not self.current_song_name:
            return False
        path = get_library_path(self.config)
        name = self.current_song_name
        
        # Guardar metadata
        metadata = create_default_metadata(
            name=name,
            artist=self.current_song_artist,
            detected_key=self.detected_key,
            detected_bpm=self.detected_bpm,
            pitch_shift=self.current_pitch_shift,
            tempo_ratio=self.current_tempo_ratio,
            count_in_bars=self.count_in_bars,
            click_during_playback=self.click_during_playback,
            metronome_volume=self.metronome_volume,
            metronome_pan=self.metronome_pan,
            master_volume=self.master_volume,
            duration=self.total_time_label.text(),
            click_offset_samples=getattr(self, 'click_offset_samples', 0),
            stems=[
                {
                    "name": n,
                    "category": d.get("category", "Other"),
                    "volume": d["volume"],
                    "pan": d.get("pan", 0.0),
                    "muted": d["muted"],
                    "solo": d["solo"],
                    "fx_enabled": d.get("fx_enabled", True),
                }
                for n, d in self.stems.items()
            ]
        )
        
        # Preservar cached_audio_path
        old_meta = get_song_metadata(path, name)
        if old_meta and "cached_audio_path" in old_meta:
            metadata["cached_audio_path"] = old_meta["cached_audio_path"]
            
        save_song_metadata(path, name, metadata)
        self.has_unsaved_changes = False
        self._update_save_buttons()
        self.status_label.setText(f"Cambios guardados: {name}")
        return True

    def _save_as(self):
        if not self.stems or self.current_song_source != "library":
            return
        path = get_library_path(self.config)
        name, ok = QInputDialog.getText(self, "Guardar Como", "Nuevo nombre de la canción:")
        if not ok or not name.strip():
            return
        name = name.strip()
        
        source_folder = os.path.join(path, self.current_song_name)
        copy_folder_to_library(source_folder, path, name)
        
        self.current_song_name = name
        self.current_song_source = "library"
        self._save_changes()
        self.library_widget.refresh_ui()
        
        if self.setlist_widget.current_setlist_index >= 0:
            self.setlist_widget.add_song_to_current(name)

    def _ensure_openrouter_api_key(self) -> str:
        settings = QSettings("StemsPlayer", "StemsPlayer")
        api_key = str(settings.value("openrouter_api_key", "") or "").strip()
        if api_key:
            return api_key

        key, ok = QInputDialog.getText(
            self,
            "OpenRouter API Key",
            "Introduce tu API Key de OpenRouter:",
        )
        if not ok or not key.strip():
            return ""

        api_key = key.strip()
        settings.setValue("openrouter_api_key", api_key)
        return api_key

    def _prompt_lyrics_generation_mode(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Generar Sheet de acordes")
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setText("¿Cómo quieres proporcionar la letra de la canción?")
        msg_box.setInformativeText("Puedes pedir a la IA que la busque o pegarla manualmente.")

        search_btn = msg_box.addButton("Buscar letra con IA", QMessageBox.AcceptRole)
        manual_btn = msg_box.addButton("Pegar letra manualmente", QMessageBox.ActionRole)
        cancel_btn = msg_box.addButton(QMessageBox.Cancel)
        msg_box.setDefaultButton(search_btn)
        msg_box.exec()

        clicked = msg_box.clickedButton()
        if clicked == search_btn:
            return {"lyrics_text": "", "use_web_search": True}
        if clicked == manual_btn:
            lyrics_text, ok = QInputDialog.getMultiLineText(
                self,
                "Letra manual",
                "Pega o escribe la letra de la canción:",
            )
            if not ok:
                return None
            lyrics_text = lyrics_text.strip()
            if not lyrics_text:
                QMessageBox.warning(
                    self,
                    "Letra vacía",
                    "Debes pegar una letra antes de continuar con la opción manual.",
                )
                return None
            return {"lyrics_text": lyrics_text, "use_web_search": False}
        if clicked == cancel_btn:
            return None
        return None

    def _set_generation_feedback(self, busy: bool, message: str = "", tone: str = "info", determinate: bool = False):
        tone_colors = {
            "info": "#5555AA",
            "error": "#D96C6C",
            "success": "#5FAF5F",
        }
        color = tone_colors.get(tone, tone_colors["info"])
        self.bg_status_label.setStyleSheet(
            f"color: {color}; font-size: 11px; font-style: italic;"
        )

        if message:
            self.bg_status_label.setText(message)
            self.bg_status_label.setVisible(True)
        elif not busy:
            self.bg_status_label.setText("")
            self.bg_status_label.setVisible(False)

        self.generate_chordpro_btn.setEnabled(not busy)

        if busy:
            self.progress_bar.setVisible(True)
            if determinate:
                self.progress_bar.setRange(0, 100)
            else:
                self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(False)

    def _on_chord_analysis_progress(self, msg: str):
        self._set_generation_feedback(True, msg, tone="info", determinate=True)

    def _on_chord_analysis_progress_pct(self, value: int):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)

    def _on_openrouter_progress(self, msg: str):
        self._set_generation_feedback(True, msg, tone="info", determinate=False)

    def _on_generate_chordpro_clicked(self):
        if self.current_song_source != "library" or not self.current_song_name:
            QMessageBox.information(
                self,
                "Canción no disponible",
                "Primero carga una canción guardada en la librería para generar su sheet de acordes.",
            )
            return

        api_key = self._ensure_openrouter_api_key()
        if not api_key:
            return

        lyrics_request = self._prompt_lyrics_generation_mode()
        if not lyrics_request:
            return

        library_path = get_library_path(self.config)
        metadata = get_song_metadata(library_path, self.current_song_name) or {}
        sections = metadata.get("sections")
        chords_by_section = metadata.get("chords_by_section")

        # Validar que contienen datos reales, no solo que existan
        has_valid_sections = isinstance(sections, list) and len(sections) > 0
        has_valid_chords = isinstance(chords_by_section, dict) and len(chords_by_section) > 0
        print(f"[ChordPro] Validación de datos previos - Secciones válidas: {has_valid_sections}, Acordes válidos: {has_valid_chords}")

        if has_valid_sections and has_valid_chords:
            self._start_openrouter_thread(
                api_key,
                sections,
                chords_by_section,
                lyrics_request["lyrics_text"],
                lyrics_request["use_web_search"],
            )
        else:
            self.status_label.setText("Analizando estructura y acordes para generar el sheet...")
            self._set_generation_feedback(
                True,
                "Iniciando analisis musical para generar el sheet...",
                tone="info",
                determinate=True,
            )
            self.progress_bar.setValue(0)

            from lyrics_engine import ChordAnalysisThread
            self.chord_analysis_thread = ChordAnalysisThread(
                os.path.join(library_path, self.current_song_name),
                self.stems,
                self.mix_sr
            )
            self.chord_analysis_thread.progress.connect(self._on_chord_analysis_progress)
            self.chord_analysis_thread.progress_pct.connect(self._on_chord_analysis_progress_pct)
            self.chord_analysis_thread.finished_analysis.connect(
                lambda res, k=api_key, lt=lyrics_request["lyrics_text"], ws=lyrics_request["use_web_search"]:
                self._on_chord_analysis_finished(res, k, lt, ws)
            )
            self.chord_analysis_thread.error.connect(self._on_chord_generation_error)
            self.chord_analysis_thread.start()

    def _on_chord_analysis_finished(self, result: dict, api_key: str, lyrics_text: str, use_web_search: bool):
        sections = result.get("sections", [])
        chords_by_section = result.get("chords_by_section", {})
        self.chord_analysis_thread = None

        library_path = get_library_path(self.config)
        metadata = get_song_metadata(library_path, self.current_song_name)
        if metadata:
            metadata["sections"] = sections
            metadata["chords_by_section"] = chords_by_section
            save_song_metadata(library_path, self.current_song_name, metadata)

        self._start_openrouter_thread(api_key, sections, chords_by_section, lyrics_text, use_web_search)

    def _on_chord_generation_error(self, msg: str):
        self.chord_analysis_thread = None
        self.openrouter_thread = None
        self._set_generation_feedback(False, msg, tone="error")
        self.status_label.setText("No se pudo generar el sheet de acordes")
        QMessageBox.warning(self, "Generación fallida", msg)

    def _start_openrouter_thread(
        self,
        api_key: str,
        sections: list,
        chords_by_section: dict,
        lyrics_text: str = "",
        use_web_search: bool = True,
    ):
        self.status_label.setText("Generando sheet de acordes...")
        self._set_generation_feedback(
            True,
            "Conectando con OpenRouter...",
            tone="info",
            determinate=False,
        )

        from lyrics_engine import OpenRouterLLMThread
        self.openrouter_thread = OpenRouterLLMThread(
            self.current_song_name,
            self.current_song_artist,
            sections,
            chords_by_section,
            self.detected_key,
            self.detected_bpm,
            api_key,
            lyrics_text=lyrics_text,
            use_web_search=use_web_search,
        )
        self.openrouter_thread.progress.connect(self._on_openrouter_progress)
        self.openrouter_thread.finished_chordpro_and_sync.connect(self._on_openrouter_finished)
        self.openrouter_thread.error.connect(self._on_chord_generation_error)
        self.openrouter_thread.start()
        
    def _on_openrouter_finished(self, content: str, sync_data: dict):
        library_path = get_library_path(self.config)
        song_folder = os.path.join(library_path, self.current_song_name)
        chopro_path = os.path.join(song_folder, f"{self.current_song_name}.chopro")
        sync_path = os.path.join(song_folder, f"{self.current_song_name}.sync.json")
        self.openrouter_thread = None

        try:
            with open(chopro_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as exc:
            print(f"[ChordPro] No se pudo guardar el archivo: {exc}")
            self._on_chord_generation_error(
                "OpenRouter respondio correctamente, pero no se pudo guardar el archivo .chopro."
            )
            return

        # Guardar archivo de sincronización generado por OpenRouter
        try:
            with open(sync_path, "w", encoding="utf-8") as f:
                json.dump(sync_data, f, indent=2, ensure_ascii=False)
            print(f"[Sync] Archivo de sincronización guardado: {sync_path}")
        except OSError as exc:
            print(f"[Sync] No se pudo guardar el archivo de sincronización: {exc}")
            # No es crítico si falla el sync, continuamos

        self._set_generation_feedback(
            False,
            "Sheet de acordes generado correctamente.",
            tone="success",
        )
        self.status_label.setText("Sheet de acordes generado")
        self._update_save_buttons()
        # Actualizar preview del ChordPro
        self._load_chordpro_preview()

    def _on_edit_chordpro_clicked(self):
        library_path = get_library_path(self.config)
        chopro_path = os.path.join(library_path, self.current_song_name, f"{self.current_song_name}.chopro")
        if not os.path.exists(chopro_path):
            return
            
        from chordpro_editor import ChordProEditor
        self.chordpro_window = ChordProEditor(chopro_path)
        self.chordpro_window.setWindowTitle(f"Editando Acordes - {self.current_song_name}")
        self.chordpro_window.resize(900, 700)
        
        # Centrar ventana
        screen = self.screen().geometry()
        x = (screen.width() - self.chordpro_window.width()) // 2
        y = (screen.height() - self.chordpro_window.height()) // 2
        self.chordpro_window.move(x, y)
        
        def _on_chordpro_saved():
            self.status_label.setText("ChordPro guardado.")
            self._load_chordpro_preview()
        
        self.chordpro_window.saved.connect(_on_chordpro_saved)
        self.chordpro_window.show()

    def _on_library_song_deleted(self, name: str):
        if self.current_song_name == name and self.current_song_source == "library":
            self._close_song()
            
    def _on_song_export_requested(self, song_name: str, export_type: str):
        if self.export_thread and self.export_thread.isRunning():
            QMessageBox.warning(self, "Exportación en curso", "Ya hay una exportación en curso. Por favor espera.")
            return
            
        path = get_library_path(self.config)
        song_folder = os.path.join(path, song_name)
        metadata = get_song_metadata(path, song_name) or {}
        
        # Build default filename
        ext = ".zip" if export_type.startswith("zip") else ".wav"
        default_name = song_name
        if export_type.endswith("_cfg"):
            pitch = metadata.get("pitch_shift", 0)
            tempo = metadata.get("tempo_ratio", 1.0)
            if pitch != 0 or tempo != 1.0:
                default_name += f"_P{pitch}_T{int(tempo*100)}"
                
        default_path = os.path.join(os.path.expanduser("~"), "Desktop", default_name + ext)
        
        dest_path, _ = QFileDialog.getSaveFileName(self, "Guardar exportación", default_path, f"Files (*{ext})")
        if not dest_path:
            return
            
        from export_engine import ExportThread
        self.export_thread = ExportThread(export_type, dest_path, song_folder, metadata, self.mix_sr)
        self.export_thread.progress.connect(self._on_export_progress)
        self.export_thread.progress_pct.connect(self.progress_bar.setValue)
        self.export_thread.finished_export.connect(self._on_export_finished)
        self.export_thread.error.connect(self._on_export_error)
        
        self.status_label.setText("Iniciando exportación...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.export_thread.start()
        
    def _on_export_progress(self, msg: str):
        self.status_label.setText(msg)
        
    def _on_export_finished(self, dest_path: str):
        self.status_label.setText("Exportación finalizada")
        self.progress_bar.setVisible(False)
        self.export_thread = None
        QMessageBox.information(self, "Exportación exitosa", f"Archivo exportado en:\n{dest_path}")
        
    def _on_export_error(self, msg: str):
        self.status_label.setText(f"Error de exportación: {msg}")
        self.progress_bar.setVisible(False)
        self.export_thread = None

    # ------------------------------------------------------------------
    # Stem loading
    # ------------------------------------------------------------------
    def _load_stems(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de stems")
        if not folder:
            return
        self._load_folder_internal(folder, folder, "folder")

    def _load_folder_internal(self, folder: str, song_name: str, source: str, metadata: dict = None):
        if not self._close_song():
            return
            
        # Check cache
        if self.preloaded_song_cache and self.preloaded_song_cache["name"] == song_name:
            self.status_label.setText("Cargando desde caché...")
            self._on_loader_finished(
                self.preloaded_song_cache["stems"],
                self.preloaded_song_cache["key"],
                self.preloaded_song_cache["bpm"],
                metadata,
                self.preloaded_song_cache["click_offset_samples"],
                self.preloaded_song_cache["order"]
            )
            self.preloaded_song_cache = None
            return
            
        self.status_label.setText("Cargando stems...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.current_song_name = song_name
        self.current_song_source = source
        self.save_lib_btn.setVisible(True if source == "folder" else False)

        self.loader_thread = StemLoaderThread(
            folder, 
            self.mix_sr,
            pre_key=metadata.get("detected_key") if metadata else None,
            pre_bpm=metadata.get("detected_bpm") if metadata else None,
            cache_folder=folder if source == "library" else None
        )
        self.loader_thread.progress.connect(self._on_loader_progress)
        self.loader_thread.progress_pct.connect(self.progress_bar.setValue)
        self.loader_thread.finished_loading.connect(
            lambda stems, key, bpm, offset, order: self._on_loader_finished(stems, key, bpm, metadata, offset, order)
        )
        self.loader_thread.error.connect(self._on_loader_error)
        self.loader_thread.start()

    def _on_loader_progress(self, msg: str):
        self.status_label.setText(msg)

    def _on_loader_finished(self, stems, key, bpm, metadata=None, offset=0, order=None):
        if metadata is None:
            metadata = {}
        self.click_offset_samples = offset
        if order:
            self.stems = {k: stems[k] for k in order}
        else:
            self.stems = stems
        self.originals = {k: v["audio"].copy() for k, v in stems.items()}
        self.detected_key = key
        self.detected_bpm = bpm
        self.current_pitch_shift = 0
        self.current_tempo_ratio = 1.0
        self.count_in_bars = metadata.get("count_in_bars", 0)
        self.click_during_playback = metadata.get("click_during_playback", False)
        self.metronome_volume = metadata.get("metronome_volume", 0.5)
        self.metronome_pan = metadata.get("metronome_pan", 0.0)
        self.master_volume = metadata.get("master_volume", 1.0)
        self.detected_key = metadata.get("detected_key", key)
        self.detected_bpm = metadata.get("detected_bpm", bpm)
        self.current_song_artist = metadata.get("artist", "")
        
        # Apply stem configuration from metadata
        for stem_meta in metadata.get("stems", []):
            name = stem_meta.get("name")
            if name in self.stems:
                self.stems[name]["category"] = stem_meta.get("category", "Other")
                self.stems[name]["volume"] = stem_meta.get("volume", 1.0)
                self.stems[name]["pan"] = stem_meta.get("pan", 0.0)
                self.stems[name]["muted"] = stem_meta.get("muted", False)
                self.stems[name]["solo"] = stem_meta.get("solo", False)
                self.stems[name]["fx_enabled"] = stem_meta.get("fx_enabled", True)

        self.song_name_label.setText(f"Canción: {self.current_song_name}")
        self.artist_input.blockSignals(True)
        self.artist_input.setText(self.current_song_artist)
        self.artist_input.blockSignals(False)

        self.key_label.setText(f"Key: {self.detected_key}")
        self.bpm_label.setText(f"BPM: {self.detected_bpm}")
        self.orig_bpm_label.setText(str(self.detected_bpm))
        self.bpm_spin.blockSignals(True)
        self.bpm_spin.setValue(int(self.detected_bpm * self.current_tempo_ratio))
        self.bpm_spin.blockSignals(False)
        self.tempo_ratio_label.setText(f"{self.current_tempo_ratio*100:.1f}%")
        self.count_in_combo.blockSignals(True)
        self.count_in_combo.setCurrentIndex(self.count_in_bars)
        self.count_in_combo.blockSignals(False)
        self.click_check.blockSignals(True)
        self.click_check.setChecked(self.click_during_playback)
        self.click_check.blockSignals(False)
        self.master_volume_slider.blockSignals(True)
        self.master_volume_slider.setValue(self.master_volume)
        self.master_volume_slider.blockSignals(False)
        self.metronome_volume_slider.blockSignals(True)
        self.metronome_volume_slider.setValue(self.metronome_volume)
        self.metronome_volume_slider.blockSignals(False)
        self.metronome_pan_slider.blockSignals(True)
        self.metronome_pan_slider.setValue(self.metronome_pan)
        self.metronome_pan_slider.blockSignals(False)
        
        # Show/hide metronome controls based on click state
        show_controls = self.click_during_playback
        self.metronome_volume_slider.setVisible(show_controls)
        self.metronome_pan_slider.setVisible(show_controls)
        self.metro_icon_btn.setEnabled(show_controls)

        # Actualizar pitch buttons
        for s, btn in self.pitch_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(s == self.current_pitch_shift)
            btn.blockSignals(False)
        self._update_pitch_button_labels()

        self._rebuild_stems_ui()
        self.status_label.setText("Listo")
        self.progress_bar.setVisible(False)
        self.close_song_btn.setVisible(True)
        self.add_to_setlist_btn.setVisible(True)
        self.loader_thread = None

        self.history.clear()
        self.history_idx = -1
        self._push_state_if_needed()
        self._update_undo_redo_btns()
        self._update_list_icons()
        
        # Reset unsaved changes flag
        self.has_unsaved_changes = False
        self._update_save_buttons()

        # Actualizar metadatos si vinimos de librería (para guardar la key/bpm/offset reales)
        if self.current_song_source == "library":
            path = get_library_path(self.config)
            meta = get_song_metadata(path, self.current_song_name)
            if meta:
                meta["detected_key"] = key
                meta["detected_bpm"] = bpm
                meta["click_offset_samples"] = offset
                save_song_metadata(path, self.current_song_name, meta)

        # Aplicar pitch/tempo desde metadata (la función usará caché si existe)
        if metadata and (self.current_pitch_shift != 0 or self.current_tempo_ratio != 1.0):
            self._apply_pitch_tempo()
        
        # Cargar datos para el modo vivo si existe ChordPro
        if self.current_song_source == "library":
            path = get_library_path(self.config)
            folder = os.path.join(path, self.current_song_name)
            chopro_path = os.path.join(folder, f"{self.current_song_name}.chopro")
            sync_path = os.path.join(folder, f"{self.current_song_name}.sync.json")
            if os.path.exists(chopro_path):
                self.live_display_widget.load_sync_data(chopro_path, sync_path)
                self.toggle_live_btn.setEnabled(True)
            else:
                self.live_display_widget.reset()
                self.toggle_live_btn.setEnabled(False)
                self.toggle_live_btn.setChecked(False)
                self.center_stack.setCurrentIndex(0)
            
            # Cargar preview del ChordPro
            self._load_chordpro_preview()
        else:
            self.live_display_widget.reset()
            self.toggle_live_btn.setEnabled(False)
            self.toggle_live_btn.setChecked(False)
            self.center_stack.setCurrentIndex(0)
            self.chordpro_preview_widget.setVisible(False)
            
        self._preload_next_setlist_song()
        
        if getattr(self, '_auto_play_pending', False):
            self._auto_play_pending = False
            QTimer.singleShot(100, self._start_playback)

    def _preload_next_setlist_song(self):
        # Cancel any existing preloader
        if hasattr(self, 'preloader_thread') and self.preloader_thread and self.preloader_thread.isRunning():
            self.preloader_thread.cancel()
            self._zombie_threads.add(self.preloader_thread)
            self.preloader_thread.finished.connect(lambda t=self.preloader_thread: self._cleanup_zombie(t))
            self.preloader_thread = None
            if hasattr(self, 'bg_status_label'):
                self.bg_status_label.setVisible(False)
            
        if self.setlist_widget.current_setlist_index < 0:
            return
            
        setlists = get_setlists(self.config)
        sl = setlists[self.setlist_widget.current_setlist_index]
        songs = sl["song_ids"]
        
        next_idx = self.setlist_widget.current_setlist_song_index + 1
        if next_idx >= len(songs):
            return # No more songs to preload
            
        next_song_name = songs[next_idx]
        path = get_library_path(self.config)
        song_folder = os.path.join(path, next_song_name)
        
        if not os.path.exists(song_folder):
            return
            
        self.preloader_thread = StemLoaderThread(song_folder, self.mix_sr)
        self.preloader_thread.progress.connect(self._on_preload_progress)
        self.preloader_thread.finished_loading.connect(
            lambda stems, key, bpm, offset, order: self._on_preload_finished(next_song_name, stems, key, bpm, offset, order)
        )
        self.bg_status_label.setVisible(True)
        self.preloader_thread.start()
        
    def _on_preload_progress(self, msg: str):
        self.bg_status_label.setText(f"[Segundo Plano] {msg}")
        
    def _on_preload_finished(self, name, stems, key, bpm, offset, order):
        self.preloaded_song_cache = {
            "name": name,
            "stems": stems,
            "key": key,
            "bpm": bpm,
            "click_offset_samples": offset,
            "order": order
        }
        self.bg_status_label.setVisible(False)
        self.preloader_thread = None

    def _on_loader_error(self, msg: str):
        self.status_label.setText(f"Error: {msg}")
        self.progress_bar.setVisible(False)
        self.loader_thread = None

    # ------------------------------------------------------------------
    # Stem UI management
    # ------------------------------------------------------------------
    def _clear_stems_ui(self):
        while self.stems_layout.count():
            item = self.stems_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_library_item_clicked(self, item):
        if hasattr(self, 'setlist_widget'):
            self.setlist_widget.clear_selection()
            
    def _on_setlist_item_clicked(self, item):
        if hasattr(self, 'library_widget'):
            self.library_widget.clear_selection()

    def _toggle_blink(self):
        self.blink_state = not self.blink_state
        self._update_list_icons()
        
    def _update_list_icons(self):
        is_playing = self.playback_thread is not None and self.playback_thread.is_playing
        
        if hasattr(self, 'library_widget'):
            self.library_widget.update_icons(self.current_song_name, is_playing, self.blink_state, self.icons_dir)
            
        if hasattr(self, 'setlist_widget'):
            self.setlist_widget.update_icons(self.current_song_name, is_playing, self.blink_state, self.icons_dir)

    def _on_auto_play_toggled(self, checked):
        if checked:
            self.auto_play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-preset-ab.svg"), "#00FF00"))
        else:
            self.auto_play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-preset-ab.svg"), "#FFFFFF"))

    def _rebuild_stems_ui(self):
        self._clear_stems_ui()
        for name, data in self.stems.items():
            widget = StemItemWidget(
                name=name,
                category=data.get("category", "Other"),
                volume=data["volume"],
                icons_dir=self.icons_dir,
            )
            widget.set_mute(data.get("muted", False))
            widget.set_solo(data.get("solo", False))
            widget.set_fx(data.get("fx_enabled", True))
            widget.set_pan(data.get("pan", 0.0))
            widget.volume_changed.connect(self._on_stem_volume_changed)
            widget.pan_changed.connect(self._on_stem_pan_changed)
            widget.mute_toggled.connect(self._on_stem_mute_toggled)
            widget.solo_toggled.connect(self._on_stem_solo_toggled)
            widget.fx_toggled.connect(self._on_stem_fx_toggled)
            widget.name_changed.connect(self._on_stem_name_changed)
            widget.category_changed.connect(self._on_stem_category_changed)
            widget.delete_requested.connect(self._on_stem_delete)
            widget.move_up_requested.connect(self._on_stem_move_up)
            widget.move_down_requested.connect(self._on_stem_move_down)
            self.stems_layout.addWidget(widget)

    def _on_stem_volume_changed(self, name: str, volume: float):
        if name in self.stems:
            self.stems[name]["volume"] = volume
            self._push_state_if_needed()

    def _on_stem_pan_changed(self, name: str, pan: float):
        if name in self.stems:
            self.stems[name]["pan"] = pan
            self._push_state_if_needed()

    def _on_master_volume_changed(self, volume: float):
        self.master_volume = volume
        if self.playback_thread:
            self.playback_thread.set_master_volume(volume)
        self._push_state_if_needed()

    def _on_metronome_volume_changed(self, volume: float):
        self.metronome_volume = volume
        if self.playback_thread:
            self.playback_thread.set_metronome_volume(volume)
        self._push_state_if_needed()

    def _on_metronome_pan_changed(self, pan: float):
        self.metronome_pan = pan
        if self.playback_thread:
            self.playback_thread.set_metronome_pan(pan)
        self._push_state_if_needed()

    def _on_artist_changed(self, text: str):
        self.current_song_artist = text
        self._push_state_if_needed()

    def _on_click_during_changed(self, state: int):
        self.click_during_playback = (state == Qt.Checked)
        # Show/hide metronome volume controls
        show_controls = self.click_during_playback
        self.metronome_volume_slider.setVisible(show_controls)
        self.metronome_pan_slider.setVisible(show_controls)
        self.metro_icon_btn.setEnabled(show_controls)
        self._push_state_if_needed()

    def _on_stem_mute_toggled(self, name: str, muted: bool):
        if name in self.stems:
            self.stems[name]["muted"] = muted
            self._push_state_if_needed()

    def _on_stem_solo_toggled(self, name: str, solo: bool):
        if name in self.stems:
            self.stems[name]["solo"] = solo
            self._push_state_if_needed()

    def _on_stem_fx_toggled(self, name: str, fx: bool):
        if name in self.stems:
            self.stems[name]["fx_enabled"] = fx
            self._push_state_if_needed()

    def _get_current_state(self):
        return {
            "artist": self.current_song_artist,
            "master_volume": self.master_volume,
            "metronome_volume": self.metronome_volume,
            "metronome_pan": self.metronome_pan,
            "pitch_shift": self.current_pitch_shift,
            "tempo_ratio": self.current_tempo_ratio,
            "click_during": self.click_during_playback,
            "count_in_bars": self.count_in_bars,
            "stems": {
                name: {
                    "volume": data["volume"],
                    "pan": data.get("pan", 0.0),
                    "muted": data.get("muted", False),
                    "solo": data.get("solo", False),
                    "fx": data.get("fx_enabled", True),
                    "category": data.get("category", "Other")
                }
                for name, data in self.stems.items()
            }
        }

    def _apply_state(self, state: dict):
        self.current_song_artist = state["artist"]
        self.artist_input.blockSignals(True)
        self.artist_input.setText(self.current_song_artist)
        self.artist_input.blockSignals(False)
        
        self.master_volume = state["master_volume"]
        self.master_volume_slider.blockSignals(True)
        self.master_volume_slider.setValue(self.master_volume)
        self.master_volume_slider.blockSignals(False)
        if self.playback_thread: self.playback_thread.set_master_volume(self.master_volume)
        
        self.metronome_volume = state["metronome_volume"]
        self.metronome_volume_slider.blockSignals(True)
        self.metronome_volume_slider.setValue(self.metronome_volume)
        self.metronome_volume_slider.blockSignals(False)
        if self.playback_thread: self.playback_thread.set_metronome_volume(self.metronome_volume)
        
        self.metronome_pan = state["metronome_pan"]
        self.metronome_pan_slider.blockSignals(True)
        self.metronome_pan_slider.setValue(self.metronome_pan)
        self.metronome_pan_slider.blockSignals(False)
        if self.playback_thread: self.playback_thread.set_metronome_pan(self.metronome_pan)
        
        self.click_during_playback = state["click_during"]
        self.click_check.blockSignals(True)
        self.click_check.setChecked(self.click_during_playback)
        self.click_check.blockSignals(False)
        show_controls = self.click_during_playback
        self.metronome_volume_slider.setVisible(show_controls)
        self.metronome_pan_slider.setVisible(show_controls)
        self.metro_icon_btn.setEnabled(show_controls)
        
        self.count_in_bars = state["count_in_bars"]
        self.count_in_combo.blockSignals(True)
        self.count_in_combo.setCurrentIndex(self.count_in_bars)
        self.count_in_combo.blockSignals(False)
        
        # Apply pitch and tempo if changed
        pitch_changed = self.current_pitch_shift != state["pitch_shift"]
        tempo_changed = self.current_tempo_ratio != state["tempo_ratio"]
        self.current_pitch_shift = state["pitch_shift"]
        self.current_tempo_ratio = state["tempo_ratio"]
        self.bpm_spin.blockSignals(True)
        self.bpm_spin.setValue(int(self.detected_bpm * self.current_tempo_ratio))
        self.bpm_spin.blockSignals(False)
        self.tempo_ratio_label.setText(f"{self.current_tempo_ratio*100:.1f}%")
        for s, btn in self.pitch_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(s == self.current_pitch_shift)
            btn.blockSignals(False)
        
        for name, data in state["stems"].items():
            if name in self.stems:
                self.stems[name]["volume"] = data["volume"]
                self.stems[name]["pan"] = data["pan"]
                self.stems[name]["muted"] = data["muted"]
                self.stems[name]["solo"] = data["solo"]
                self.stems[name]["fx_enabled"] = data["fx"]
                self.stems[name]["category"] = data["category"]
        
        self._rebuild_stems_ui()
        
        if pitch_changed or tempo_changed:
            self._apply_pitch_tempo()
            
        self._mark_changes()

    def _push_state_if_needed(self):
        if not self.stems:
            return
        state = self._get_current_state()
        # Don't push if it's identical to current
        if self.history_idx >= 0 and self.history_idx < len(self.history):
            if self.history[self.history_idx] == state:
                return
        
        self.history = self.history[:self.history_idx + 1]
        self.history.append(state)
        self.history_idx += 1
        self._update_undo_redo_btns()
        self._mark_changes()
        
    def _toggle_live_mode(self, checked):
        if checked:
            self.center_stack.setCurrentIndex(1)
            self.toggle_live_btn.setText("Mezclador")
        else:
            self.center_stack.setCurrentIndex(0)
            self.toggle_live_btn.setText("Karaoke")

    def _undo(self):
        if self.history_idx > 0:
            self.history_idx -= 1
            self._apply_state(self.history[self.history_idx])
            self._update_undo_redo_btns()

    def _redo(self):
        if self.history_idx < len(self.history) - 1:
            self.history_idx += 1
            self._apply_state(self.history[self.history_idx])
            self._update_undo_redo_btns()

    def _update_undo_redo_btns(self):
        self.undo_btn.setEnabled(self.history_idx > 0)
        self.redo_btn.setEnabled(self.history_idx < len(self.history) - 1)

    def _mark_changes(self):
        """Mark that changes have been made and update save buttons."""
        self.has_unsaved_changes = True
        self._update_save_buttons()

    def _update_save_buttons(self):
        # Hide all save buttons first
        self.save_lib_btn.setVisible(False)
        self.save_changes_btn.setVisible(False)
        self.save_as_btn.setVisible(False)
        self.generate_chordpro_btn.setVisible(False)
        self.edit_chordpro_btn.setVisible(False)
        
        btn_style = """
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: 1px solid #0078D7;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """
        
        if self.current_song_source == "library":
            self.save_changes_btn.setVisible(self.has_unsaved_changes)
            self.save_lib_btn.setVisible(False)
            if self.has_unsaved_changes:
                self.save_changes_btn.setStyleSheet(btn_style)
            
            self.save_as_btn.setVisible(True)
            
            library_path = get_library_path(self.config)
            chopro_path = os.path.join(library_path, self.current_song_name, f"{self.current_song_name}.chopro")
            
            if os.path.exists(chopro_path):
                self.generate_chordpro_btn.setText("Regenerar Sheet de acordes")
                self.edit_chordpro_btn.setVisible(True)
            else:
                self.generate_chordpro_btn.setText("Generar Sheet de acordes")
                self.edit_chordpro_btn.setVisible(False)
                
            self.generate_chordpro_btn.setVisible(True)
        elif self.current_song_source == "folder":
            self.save_lib_btn.setVisible(True)
            self.save_lib_btn.setStyleSheet(btn_style)
            self.save_changes_btn.setVisible(False)
            self.generate_chordpro_btn.setVisible(False)
            self.edit_chordpro_btn.setVisible(False)
        else:
            self.save_lib_btn.setVisible(False)
            self.save_changes_btn.setVisible(False)
            self.generate_chordpro_btn.setVisible(False)
            self.edit_chordpro_btn.setVisible(False)

    def _toggle_left_panel(self):
        """Toggle the visibility and width of the left panel."""
        self.left_panel_collapsed = not self.left_panel_collapsed
        
        if self.left_panel_collapsed:
            # Collapse panel
            self.lib_panel.setMaximumWidth(0)
            self.lib_panel.setMinimumWidth(0)
            self.collapse_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-h-expand.svg"), "#888888"))
            self.collapse_btn.setToolTip("Expandir panel izquierdo")
        else:
            # Expand panel
            self.lib_panel.setMaximumWidth(280)
            self.lib_panel.setMinimumWidth(280)
            self.collapse_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-v-expand.svg"), "#888888"))
            self.collapse_btn.setToolTip("Contraer panel izquierdo")

    def closeEvent(self, event):
        self.status_label.setText("Cerrando aplicacion...")
        threads_to_wait = [
            self.playback_thread,
            self.pitch_tempo_thread,
            self.loader_thread,
            self.preloader_thread,
            self.chord_analysis_thread,
            self.openrouter_thread,
            *list(self._zombie_threads),
        ]
        self._stop_all_threads()

        for thread in threads_to_wait:
            if thread and thread.isRunning():
                thread.wait(3000)

        event.accept()

    def _close_song(self):
        """Close current song with confirmation for unsaved changes."""
        if not self.stems:
            self.status_label.setText("No hay canción cargada")
            return True
            
        if self.has_unsaved_changes:
            if hasattr(self, 'setlist_widget') and self.setlist_widget.current_setlist_index >= 0 and self.current_song_source == "library":
                self._save_changes()
            else:
                reply = QMessageBox.question(
                    self,
                    "Confirmar cierre",
                    "Hay cambios sin guardar. ¿Quieres guardar los cambios antes de cerrar?",
                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                    QMessageBox.Save
                )
                
                if reply == QMessageBox.Save:
                    if self.current_song_source == "library":
                        if not self._save_changes():
                            return False
                    else:
                        if not self._save_to_library():
                            return False
                elif reply == QMessageBox.Cancel:
                    return False
        
        # Close the song
        self._stop_all_threads()
        self._clear_stems_ui()
        self.stems.clear()
        self.originals.clear()
        self.current_song_name = ""
        self.current_song_source = ""
        self.has_unsaved_changes = False
        self.save_lib_btn.setVisible(False)
        self.save_changes_btn.setVisible(False)
        self.save_as_btn.setVisible(False)
        self.close_song_btn.setVisible(False)
        self.add_to_setlist_btn.setVisible(False)
        self.song_name_label.setText("Canción: --")
        self.artist_input.setText("")
        self.status_label.setText("Canción cerrada")
        
        # Reset UI state
        self.key_label.setText("Key: -")
        self.bpm_label.setText("BPM: -")
        self.orig_bpm_label.setText("-")
        self.bpm_spin.setValue(120)
        self.tempo_ratio_label.setText("100%")
        self.count_in_combo.setCurrentIndex(0)
        self.click_check.setChecked(False)
        self.master_volume_slider.setValue(1.0)
        self.metronome_volume_slider.setValue(0.5)
        self.metronome_pan_slider.setValue(0.0)
        self.current_time_label.setText("00:00")
        self.total_time_label.setText("00:00")
        self.playback_progress.setValue(0)
        self.history.clear()
        self.history_idx = -1
        self._update_undo_redo_btns()
        self._update_list_icons()
        
        # Ocultar preview del ChordPro
        self.chordpro_preview_widget.setVisible(False)
        self.chordpro_path = None
        self.chordpro_fullscreen_text.setText("")
        self.center_stack.setCurrentIndex(0)  # Asegurar que mostramos stems
        
        return True

    def _on_add_to_setlist_clicked(self):
        if self.current_song_source != "library" or not self.current_song_name:
            QMessageBox.warning(self, "Aviso", "La canción debe estar guardada en la librería primero para añadirla a un setlist.\nUsa el botón 'Guardar en librería'.")
            return
            
        if self.setlist_widget.current_setlist_index >= 0:
            if self.setlist_widget.add_song_to_current(self.current_song_name):
                QMessageBox.information(self, "Info", f"Canción '{self.current_song_name}' añadida al setlist actual.")
        else:
            if self.setlist_widget.create_and_add(self.current_song_name):
                QMessageBox.information(self, "Info", f"Nuevo setlist creado y canción '{self.current_song_name}' añadida.")

    def _on_stem_name_changed(self, old_name: str, new_name: str):
        if old_name in self.stems and new_name not in self.stems:
            self.stems[new_name] = self.stems.pop(old_name)
            self.originals[new_name] = self.originals.pop(old_name)
            self._rebuild_stems_ui()
            self._push_state_if_needed()

    def _on_stem_category_changed(self, name: str, category: str):
        if name in self.stems:
            self.stems[name]["category"] = category
            self._push_state_if_needed()

    def _on_stem_delete(self, name: str):
        if name in self.stems:
            reply = QMessageBox.question(
                self, 
                "Confirmar eliminación",
                f"¿Estás seguro de que quieres eliminar el stem '{name}'?\n\nEsta acción no se puede deshacer.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                del self.stems[name]
                del self.originals[name]
                self._rebuild_stems_ui()
                self._push_state_if_needed()
                self.status_label.setText(f"Stem '{name}' eliminado")

    def _on_stem_move_up(self, name: str):
        keys = list(self.stems.keys())
        idx = keys.index(name)
        if idx > 0:
            keys[idx], keys[idx-1] = keys[idx-1], keys[idx]
            new_stems = {k: self.stems[k] for k in keys}
            self.stems = new_stems
            self._rebuild_stems_ui()
            self._push_state_if_needed()

    def _on_stem_move_down(self, name: str):
        keys = list(self.stems.keys())
        idx = keys.index(name)
        if idx < len(keys) - 1:
            keys[idx], keys[idx+1] = keys[idx+1], keys[idx]
            new_stems = {k: self.stems[k] for k in keys}
            self.stems = new_stems
            self._rebuild_stems_ui()
            self._push_state_if_needed()

    # ------------------------------------------------------------------
    # Count-in
    # ------------------------------------------------------------------
    def _on_count_in_changed(self, index: int):
        self.count_in_bars = index  # 0, 1, 2
        self._push_state_if_needed()

    def _on_click_during_changed(self, state: int):
        self.click_during_playback = bool(state)
        # Show/hide metronome volume controls
        show_controls = self.click_during_playback
        self.metronome_volume_slider.setVisible(show_controls)
        self.metronome_pan_slider.setVisible(show_controls)
        self.metro_icon_btn.setEnabled(show_controls)
        self._push_state_if_needed()

    def _on_apply_tempo_clicked(self):
        value = self.bpm_spin.value()
        if self.detected_bpm > 0:
            self.current_tempo_ratio = value / self.detected_bpm
            self.tempo_ratio_label.setText(f"{self.current_tempo_ratio*100:.1f}%")
        self._apply_pitch_tempo()
        self._push_state_if_needed()

    # ------------------------------------------------------------------
    # Pitch / Tempo controls
    # ------------------------------------------------------------------
    def _on_pitch_clicked(self, shift: int):
        if self.current_pitch_shift == shift:
            return
        self.current_pitch_shift = shift
        for s, btn in self.pitch_buttons.items():
            btn.setChecked(s == shift)
        self._update_pitch_button_labels()
        self._apply_pitch_tempo()
        self._push_state_if_needed()

    def _update_pitch_button_labels(self):
        for shift, btn in self.pitch_buttons.items():
            if shift == 0:
                btn.setText(f"{self.detected_key}")
            else:
                key = get_key_at_semitone_shift(self.detected_key, shift)
                btn.setText(f"{key}")

    def _apply_pitch_tempo(self):
        self._stop_pitch_tempo_thread()
        if not self.originals:
            return
            
        target_key = get_key_at_semitone_shift(self.detected_key, self.current_pitch_shift)
        target_bpm = round(self.detected_bpm * self.current_tempo_ratio)
        
        if self.current_song_source == "library" and self.current_song_name:
            library_path = get_library_path(self.config)
            song_folder = os.path.join(library_path, self.current_song_name)
            
            relative_cache_path = f"cache/{target_key}-{target_bpm}bpm"
            cache_folder = os.path.join(song_folder, "cache", f"{target_key}-{target_bpm}bpm")
            
            if os.path.exists(cache_folder) and any(f.endswith(".npy") for f in os.listdir(cache_folder)):
                self.status_label.setText("Cargando desde caché...")
                for name, data in self.stems.items():
                    cached_file = os.path.join(cache_folder, f"{name}.npy")
                    if os.path.exists(cached_file):
                        self.stems[name]["audio"] = np.load(cached_file)
                
                metadata = get_song_metadata(library_path, self.current_song_name)
                if metadata:
                    if self.current_pitch_shift != 0 or self.current_tempo_ratio != 1.0:
                        metadata["cached_audio_path"] = relative_cache_path
                    else:
                        metadata.pop("cached_audio_path", None)
                    metadata["pitch_shift"] = self.current_pitch_shift
                    metadata["tempo_ratio"] = self.current_tempo_ratio
                    save_song_metadata(library_path, self.current_song_name, metadata)
                    
                self.status_label.setText("Listo")
                return
                
        self.status_label.setText("Aplicando pitch/tempo ...")
        self.progress_bar.setVisible(True)
        fx_map = {name: data.get("fx_enabled", True) for name, data in self.stems.items()}
        self.pitch_tempo_thread = PitchTempoThread(
            self.originals, self.current_pitch_shift, self.current_tempo_ratio, fx_map, self.mix_sr
        )
        self.pitch_tempo_thread.progress.connect(self._on_pt_progress)
        self.pitch_tempo_thread.progress_pct.connect(self.progress_bar.setValue)
        self.pitch_tempo_thread.finished_processing.connect(self._on_pt_finished)
        self.pitch_tempo_thread.error.connect(self._on_pt_error)
        self.pitch_tempo_thread.start()

    def _on_pt_progress(self, msg: str):
        self.status_label.setText(msg)

    def _on_pt_finished(self, updated: dict):
        for name, audio in updated.items():
            if name in self.stems:
                self.stems[name]["audio"] = audio
                
        if self.current_song_source == "library" and self.current_song_name:
            if self.current_pitch_shift != 0 or self.current_tempo_ratio != 1.0:
                target_key = get_key_at_semitone_shift(self.detected_key, self.current_pitch_shift)
                target_bpm = round(self.detected_bpm * self.current_tempo_ratio)
                library_path = get_library_path(self.config)
                song_folder = os.path.join(library_path, self.current_song_name)
                
                relative_cache_path = f"cache/{target_key}-{target_bpm}bpm"
                cache_folder = os.path.join(song_folder, "cache", f"{target_key}-{target_bpm}bpm")
                os.makedirs(cache_folder, exist_ok=True)
                
                for name, audio in updated.items():
                    np.save(os.path.join(cache_folder, f"{name}.npy"), audio)
                
                metadata = get_song_metadata(library_path, self.current_song_name)
                if metadata:
                    metadata["cached_audio_path"] = relative_cache_path
                    metadata["pitch_shift"] = self.current_pitch_shift
                    metadata["tempo_ratio"] = self.current_tempo_ratio
                    save_song_metadata(library_path, self.current_song_name, metadata)
                    
        self.status_label.setText("Listo")
        self.progress_bar.setVisible(False)
        self.pitch_tempo_thread = None

    def _on_pt_error(self, msg: str):
        self.status_label.setText(f"Error: {msg}")
        self.progress_bar.setVisible(False)
        self.pitch_tempo_thread = None

    def _reset_all(self):
        self._stop_pitch_tempo_thread()
        self.current_pitch_shift = 0
        self.current_tempo_ratio = 1.0
        self.bpm_spin.setValue(self.detected_bpm)
        self.tempo_ratio_label.setText("100%")
        self.count_in_combo.setCurrentIndex(0)
        self.click_check.setChecked(False)
        for s, btn in self.pitch_buttons.items():
            btn.setChecked(s == 0)
        self._update_pitch_button_labels()
        if self.originals:
            for name, audio in self.originals.items():
                if name in self.stems:
                    self.stems[name]["audio"] = audio.copy()
                    
            if self.current_song_source == "library" and self.current_song_name:
                library_path = get_library_path(self.config)
                metadata = get_song_metadata(library_path, self.current_song_name)
                if metadata:
                    metadata.pop("cached_audio_path", None)
                    metadata["pitch_shift"] = 0
                    metadata["tempo_ratio"] = 1.0
                    save_song_metadata(library_path, self.current_song_name, metadata)
                    
            self.status_label.setText("Efectos restablecidos")
            self._push_state_if_needed()

    # ------------------------------------------------------------------
    # Thread safety
    # ------------------------------------------------------------------
    def _cleanup_zombie(self, thread):
        thread.deleteLater()
        from PySide6.QtCore import QTimer
        # Wait 2 seconds AFTER finished is emitted to let deleteLater process
        QTimer.singleShot(2000, lambda t=thread: self._zombie_threads.discard(t))

    def _stop_all_threads(self):
        if self.playback_thread:
            self.playback_thread.stop()
            if not self.playback_thread.wait(500):
                self._zombie_threads.add(self.playback_thread)
                self.playback_thread.finished.connect(lambda t=self.playback_thread: self._cleanup_zombie(t))
            self.playback_thread = None
            
        self._stop_pitch_tempo_thread()
        if hasattr(self, 'loader_thread') and self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.cancel()
            self._zombie_threads.add(self.loader_thread)
            self.loader_thread.finished.connect(lambda t=self.loader_thread: self._cleanup_zombie(t))
            self.loader_thread = None
            
        if hasattr(self, 'preloader_thread') and self.preloader_thread and self.preloader_thread.isRunning():
            self.preloader_thread.cancel()
            self._zombie_threads.add(self.preloader_thread)
            self.preloader_thread.finished.connect(lambda t=self.preloader_thread: self._cleanup_zombie(t))
            self.preloader_thread = None

        if self.chord_analysis_thread and self.chord_analysis_thread.isRunning():
            self.chord_analysis_thread.cancel()
            self._zombie_threads.add(self.chord_analysis_thread)
            self.chord_analysis_thread.finished.connect(
                lambda t=self.chord_analysis_thread: self._cleanup_zombie(t)
            )
            self.chord_analysis_thread = None

        if self.openrouter_thread and self.openrouter_thread.isRunning():
            self.openrouter_thread.cancel()
            self._zombie_threads.add(self.openrouter_thread)
            self.openrouter_thread.finished.connect(
                lambda t=self.openrouter_thread: self._cleanup_zombie(t)
            )
            self.openrouter_thread = None

    def _stop_pitch_tempo_thread(self):
        if hasattr(self, 'pitch_tempo_thread') and self.pitch_tempo_thread and self.pitch_tempo_thread.isRunning():
            self.pitch_tempo_thread.cancel()
            self._zombie_threads.add(self.pitch_tempo_thread)
            self.pitch_tempo_thread.finished.connect(lambda t=self.pitch_tempo_thread: self._cleanup_zombie(t))
            self.pitch_tempo_thread = None

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------
    def _toggle_play(self):
        if self.playback_thread and self.playback_thread.is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        if not self.stems:
            self.status_label.setText("No hay stems cargados")
            return
        if self.playback_thread and self.playback_thread.isRunning():
            return

        self.playback_thread = PlaybackThread(
            self.stems, self.detected_bpm, self.mix_sr,
            count_in_bars=self.count_in_bars,
            click_during_playback=self.click_during_playback,
            master_volume=self.master_volume,
            metronome_volume=self.metronome_volume,
            metronome_pan=self.metronome_pan,
            click_offset_samples=getattr(self, 'click_offset_samples', 0)
        )
        if hasattr(self, '_pending_seek') and self._pending_seek is not None:
            self.playback_thread.seek(self._pending_seek)
            self._pending_seek = None
        self.playback_thread.update_progress.connect(self._on_playback_progress)
        self.playback_thread.peak_level.connect(self.meters_panel.update_peak)
        self.playback_thread.finished.connect(self._on_playback_finished)
        self.playback_thread.start()
        self.play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-pause.svg")))
        self._update_list_icons()

    def _pause_playback(self):
        self._is_manual_stop = True
        if self.playback_thread:
            if hasattr(self.playback_thread, 'current_pos'):
                self._pending_seek = self.playback_thread.current_pos
            self.playback_thread.stop()
            if not self.playback_thread.wait(500):
                self._zombie_threads.add(self.playback_thread)
                self.playback_thread.finished.connect(lambda t=self.playback_thread: self._cleanup_zombie(t))
            self.playback_thread = None
        self.play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-play.svg")))
        self._update_list_icons()

    def _stop_playback(self):
        self._is_manual_stop = True
        self._pending_seek = None
        if self.playback_thread:
            self.playback_thread.stop()
            if not self.playback_thread.wait(500):
                self._zombie_threads.add(self.playback_thread)
                self.playback_thread.finished.connect(lambda t=self.playback_thread: self._cleanup_zombie(t))
            self.playback_thread = None
        self.play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-play.svg")))
        self.playback_progress.blockSignals(True)
        self.playback_progress.setValue(0)
        self.playback_progress.blockSignals(False)
        self.current_time_label.setText("00:00")
        self._update_list_icons()

    def _on_playback_progress(self, value: float):
        if not self.playback_progress.isSliderDown():
            self.playback_progress.blockSignals(True)
            self.playback_progress.setValue(int(value * 1000))
            self.playback_progress.blockSignals(False)
            
            # Calculate and update time display
            if self.stems:
                max_len = max(len(s["audio"]) for s in self.stems.values())
                beats_per_bar = 4
                count_in_beats = self.count_in_bars * beats_per_bar
                count_in_samples = int(count_in_beats * self.mix_sr * 60 / self.detected_bpm) if count_in_beats > 0 else 0
                total_samples = max_len + count_in_samples
                
                current_samples = int(value * total_samples)
                
                if current_samples < count_in_samples:
                    current_seconds = 0
                else:
                    current_seconds = int((current_samples - count_in_samples) / self.mix_sr)
                    
                total_seconds = int(max_len / self.mix_sr)
                
                current_min, current_sec = divmod(current_seconds, 60)
                total_min, total_sec = divmod(total_seconds, 60)
                
                self.current_time_label.setText(f"{current_min:02d}:{current_sec:02d}")
                self.total_time_label.setText(f"{total_min:02d}:{total_sec:02d}")
                
                # Auto-advance checking
                if current_seconds >= total_seconds and total_seconds > 0:
                    self._pause_playback()
                    self._move_to_next_song_in_setlist()
                    return
                    
                # Update live display
                if self.center_stack.currentIndex() == 1:
                    self.live_display_widget.update_position(current_seconds)

    def _on_playback_preview(self, value: int):
        """Actualiza la etiqueta de tiempo mientras se arrastra el slider."""
        if not self.stems:
            return
        max_len = max(len(s["audio"]) for s in self.stems.values())
        beats_per_bar = 4
        count_in_beats = self.count_in_bars * beats_per_bar
        count_in_samples = int(count_in_beats * self.mix_sr * 60 / self.detected_bpm) if count_in_beats > 0 else 0
        total_samples = max_len + count_in_samples
        
        desired_sample = int((value / 1000.0) * total_samples)
        
        if desired_sample < count_in_samples:
            current_seconds = 0
        else:
            current_seconds = (desired_sample - count_in_samples) // self.mix_sr
            
        current_min, current_sec = divmod(current_seconds, 60)
        self.current_time_label.setText(f"{current_min:02d}:{current_sec:02d}")

    def _on_playback_seek(self):
        """Salta a la posición indicada por el slider (al soltar el ratón)."""
        if not self.stems:
            return
        value = self.playback_progress.value()
        max_len = max(len(s["audio"]) for s in self.stems.values())
        beats_per_bar = 4
        count_in_beats = self.count_in_bars * beats_per_bar
        count_in_samples = int(count_in_beats * self.mix_sr * 60 / self.detected_bpm) if count_in_beats > 0 else 0
        total_samples = max_len + count_in_samples
        
        absolute_pos = int((value / 1000.0) * total_samples)

        if self.playback_thread and self.playback_thread.isRunning():
            self.playback_thread.seek(absolute_pos)
        else:
            # Si no está reproduciendo, solo actualizamos la interfaz
            self.playback_progress.blockSignals(True)
            self.playback_progress.setValue(value)
            self.playback_progress.blockSignals(False)
            self._on_playback_preview(value)
            self._pending_seek = absolute_pos

    # ------------------------------------------------------------------
    # ChordPro preview methods
    # ------------------------------------------------------------------
    def _load_chordpro_preview(self):
        """Carga el contenido del .chopro en el widget de preview"""
        if self.current_song_source != "library" or not self.current_song_name:
            self.chordpro_preview_widget.setVisible(False)
            return
        
        library_path = get_library_path(self.config)
        chopro_path = os.path.join(library_path, self.current_song_name, f"{self.current_song_name}.chopro")
        sync_path = os.path.join(library_path, self.current_song_name, f"{self.current_song_name}.sync.json")
        
        if os.path.exists(chopro_path):
            self.chordpro_path = chopro_path
            
            # Cargar con formato bonito en el preview
            self.chordpro_preview_widget.load_chopro_content(chopro_path)
            self.chordpro_preview_widget.setVisible(True)
            
            # Cargar datos de sincronización para el live display
            if os.path.exists(sync_path):
                self.live_display_widget.load_sync_data(chopro_path, sync_path)
            
            # === Cargar también para el modo fullscreen ===
            try:            
                song = Song(chopro_path)
                html_content = render_html(song)
                
                try:
                    html_content = html_content.encode('cp1252').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    html_content = html_content.encode('latin-1').decode('utf-8')

                # Importante: Asegurar que el HTML declare UTF-8
                if '<head>' not in html_content:
                    html_content = '<meta charset="UTF-8">\n' + html_content
                else:
                    html_content = html_content.replace('<head>', '<head>\n<meta charset="UTF-8">', 1)
                
                self.chordpro_fullscreen_text.setHtml(html_content)
                
            except Exception as e:
                # Fallback a texto plano si falla el renderizado
                try:
                    with open(chopro_path, 'r', encoding='utf-8') as f:
                        raw_text = f.read()
                    self.chordpro_fullscreen_text.setPlainText(raw_text)
                    print(f"Warning: Usando texto plano en fullscreen: {e}")
                except Exception as e2:
                    self.chordpro_fullscreen_text.setPlainText(f"Error al cargar acordes:\n{e2}")
                    
        else:
            self.chordpro_preview_widget.setVisible(False)
    
    def _show_chordpro_fullscreen(self):
        """Muestra el preview del ChordPro en fullscreen"""
        if self.chordpro_path and os.path.exists(self.chordpro_path):
            self.center_stack.setCurrentIndex(2)  # 0=stems, 1=live, 2=chordpro
        else:
            QMessageBox.warning(self, "Error", "No hay archivo de acordes cargado")
    
    def _hide_chordpro_fullscreen(self):
        """Oculta el preview fullscreen y vuelve a la vista de stems"""
        self.center_stack.setCurrentIndex(0)  # Volver a stems

    def _on_playback_finished(self):
        is_natural = not getattr(self, '_is_manual_stop', False)
        self._is_manual_stop = False
        
        if is_natural:
            self._pending_seek = None
            
        self.play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-play.svg")))
        if is_natural:
            self.status_label.setText("Reproducción finalizada")
            self.current_time_label.setText("00:00")
            self.playback_progress.blockSignals(True)
            self.playback_progress.setValue(0)
            self.playback_progress.blockSignals(False)
        self.playback_thread = None
        self._update_list_icons()
        
        # Advance for setlist only if natural stop
        if is_natural and hasattr(self, 'setlist_widget') and self.setlist_widget.current_setlist_index >= 0:
            if self.setlist_widget.current_setlist_song_index < self.setlist_widget.setlist_songs_list.count() - 1:
                if hasattr(self, 'auto_play_btn') and self.auto_play_btn.isChecked():
                    self._auto_play_pending = True
                self.setlist_widget.play_next()
