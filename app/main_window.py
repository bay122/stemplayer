"""Ventana principal que orquesta todos los módulos de la aplicación.

Estructura:
  QMainWindow
  └── QWidget (central)
      └── QHBoxLayout
          ├── [0] lib_panel (Panel izquierdo — SIEMPRE visible)
          └── [1] QStackedWidget (body_stack)
              ├── [0] page_classic: centro + derecho (layout original)
              └── [1] page_deck:    StemDeckLayout (layout alternativo)
"""

import os
from PySide6.QtWidgets import (
	QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
	QLabel, QPushButton, QSlider, QProgressBar, QMessageBox,
	QGroupBox, QCheckBox, QSpinBox, QScrollArea, QFrame, QSizePolicy,
	QComboBox, QTextEdit, QStackedWidget, QLineEdit, QInputDialog,
	QMenu, QSplitter
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QKeySequence, QShortcut

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
from app.ui.settings_dialog import SettingsDialog
from app.ui.stemdeck_layout import StemDeckLayout

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
from app.controllers.check_update import CheckUpdateMixin


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
	CheckUpdateMixin,
):
	def __init__(self, theme=None):
		super().__init__()
		self.setWindowTitle("Stem Player")
		self.setMinimumSize(1400, 800)
		self.resize(1550, 800)
		self.theme = theme if theme is not None else DARK_THEME

		self.state = StateManager()
		self.threads = ThreadManager()
		self.config_mgr = ConfigManager()
		self.lib_mgr = LibraryManager(self.config_mgr.get_library_path())
		self.icons_dir = self.theme.icons_dir if self.theme.icons_dir else get_icons_dir()

		self._pending_seek = None
		self._is_manual_stop = False
		self._auto_play_pending = False
		self.blink_state = False
		self.left_panel_collapsed = False

		self.chordpro_preview_widget = None
		self.chordpro_fullscreen_view = None
		self.chordpro_path = None

		self.current_layout = "classic"
		self.deck_layout = None

		self.blink_timer = QTimer(self)
		self.blink_timer.timeout.connect(self._toggle_blink)
		self.blink_timer.start(500)

		self._build_ui()
		apply_theme(self, self.theme)

		shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
		shortcut.activated.connect(self._toggle_layout)

		try:
			preferred = self.config_mgr.config.get("ui_layout", "classic")
		except Exception:
			preferred = "classic"
		if preferred == "deck":
			self.body_stack.setCurrentIndex(1)
			self.current_layout = "deck"

		self._init_updater()

	# ------------------------------------------------------------------
	# UI Construction
	# ------------------------------------------------------------------
	def _build_ui(self):
		central = QWidget()
		self.setCentralWidget(central)
		main = QHBoxLayout(central)
		main.setContentsMargins(0, 0, 0, 0)
		main.setSpacing(0)

		self._build_left_panel(main)

		self.body_stack = QStackedWidget()
		main.addWidget(self.body_stack, 1)

		page_classic = QWidget()
		classic_layout = QHBoxLayout(page_classic)
		classic_layout.setContentsMargins(0, 4, 8, 8)
		classic_layout.setSpacing(6)

		left_center_container = QWidget()
		left_center_layout = QHBoxLayout(left_center_container)
		left_center_layout.setContentsMargins(0, 0, 0, 0)
		left_center_layout.setSpacing(0)
		self._build_center_panel(left_center_layout)
		classic_layout.addWidget(left_center_container, 1)

		right_panel = QWidget()
		self._build_right_panel(right_panel)
		classic_layout.addWidget(right_panel, 0)

		self.body_stack.addWidget(page_classic)

		self.deck_layout = StemDeckLayout(self)
		self.deck_layout.layout_change_requested.connect(self._switch_to_classic)
		self.body_stack.addWidget(self.deck_layout)

		self.collapse_btn = QPushButton(self)
		self.collapse_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-h-expand.svg"), self.theme.SVG_ICON_MUTED))
		self.collapse_btn.setFixedSize(24, 24)
		self.collapse_btn.setToolTip("Expandir/Contraer panel izquierdo")
		self.collapse_btn.clicked.connect(self._toggle_left_panel)
		self.collapse_btn.move(6, 8)
		self.collapse_btn.setStyleSheet("background: transparent; border: none; border-radius: 4px;")
		self.collapse_btn.raise_()

	# ------------------------------------------------------------------
	# Layout switching
	# ------------------------------------------------------------------
	def _toggle_layout(self):
		if self.current_layout == "classic":
			self._switch_to_deck()
		else:
			self._switch_to_classic()

	def _switch_to_deck(self):
		if self.deck_layout is None:
			return
		self.body_stack.setCurrentIndex(1)
		self.current_layout = "deck"
		self.deck_layout.update_song_header(
			self.state.current_song_name or "",
			self.state.current_song_artist or ""
		)
		self.deck_layout.update_visibility(
			self.state.current_song_source,
			bool(self.state.current_song_name)
		)
		self.deck_layout.update_save_buttons()
		self.deck_layout.rebuild_stems()
		self._save_layout_choice("deck")

	def _switch_to_classic(self):
		if self.deck_layout is not None and self.deck_layout.toggle_live_btn.isChecked():
			self.deck_layout.toggle_live_btn.setChecked(False)
		self.body_stack.setCurrentIndex(0)
		self.current_layout = "classic"
		self._save_layout_choice("classic")

	def _save_layout_choice(self, name: str):
		try:
			self.config_mgr.config["ui_layout"] = name
			self.config_mgr.save()
		except Exception:
			pass

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
			if self.deck_layout is not None:
				self.deck_layout.info_cards.update_info(self.state)

	def _on_library_settings_changed(self):
		self.live_display_widget.set_stream_port(self.config_mgr.get_stream_port())

	def _on_stems_reclassified(self, song_name: str, changes: list):
		if self.state.current_song_name != song_name:
			return
		for change in changes:
			name = change["name"]
			if name in self.state.stems:
				self.state.stems[name]["category"] = change["category"]
				self.state.stems[name]["muted"] = change["muted"]
				self.state.stems[name]["fx_enabled"] = change["fx_enabled"]
		self._rebuild_stems_ui()
		self._push_state_if_needed()

	def _on_reclassify_stems_clicked(self):
		song_name = self.state.current_song_name
		if not song_name:
			QMessageBox.warning(self, "Recalcular stems", "No hay ninguna canción cargada.")
			return
		self.library_widget._reclassify_stems(song_name)

	def _open_settings(self):
		filters = self.config_mgr.get_stem_filters()
		port = self.config_mgr.get_stream_port()
		dialog = SettingsDialog(
			filters, port,
			config_mgr=self.config_mgr,
			icons_dir=self.icons_dir,
			check_updates_callback=lambda: self._check_for_updates(silent=False),
			parent=self,
		)
		if dialog.exec() == SettingsDialog.Accepted:
			self.config_mgr.set_stem_filters(dialog.get_stem_filters())
			self.config_mgr.set_stream_port(dialog.get_stream_port())
			self.config_mgr.set_category_colors(dialog.get_category_colors())
			self.live_display_widget.set_stream_port(self.config_mgr.get_stream_port())
			if self.deck_layout is not None:
				self.deck_layout.rebuild_stems()
				self.deck_layout.refresh_info_cards()
			if self.chordpro_preview_widget is not None:
				self.chordpro_preview_widget.set_icons_dir(self.icons_dir)

	# -- ---------------------------------- --
	# Left Panel
	def _build_left_panel(self, main_layout):
		self.lib_panel = QWidget()
		self.lib_panel.setFixedWidth(340)
		lib_layout = QVBoxLayout(self.lib_panel)
		lib_layout.setContentsMargins(8, 8, 8, 8)
		lib_layout.setSpacing(8)

		self.splitter = QSplitter(Qt.Vertical)
		self.splitter.setChildrenCollapsible(False)

		self.library_widget = LibraryPanel(self.config_mgr, self.icons_dir, self)
		self.library_widget.song_load_requested.connect(self._on_song_load_requested)
		self.library_widget.song_renamed.connect(self._on_library_song_renamed)
		self.library_widget.song_deleted.connect(self._on_library_song_deleted)
		self.library_widget.song_export_requested.connect(self._on_song_export_requested)
		self.library_widget.settings_changed.connect(self._on_library_settings_changed)
		self.library_widget.stems_reclassified.connect(self._on_stems_reclassified)
		self.library_widget.library_list.itemClicked.connect(self._on_library_item_clicked)
		self.splitter.addWidget(self.library_widget)

		self.setlist_widget = SetlistPanel(self.config_mgr, self.icons_dir, self)
		self.setlist_widget.song_load_requested.connect(self._on_song_load_requested)
		self.setlist_widget.setlist_songs_list.itemClicked.connect(self._on_setlist_item_clicked)
		self.splitter.addWidget(self.setlist_widget)

		lib_layout.addWidget(self.splitter, 1)

		self.left_spacer = QWidget()
		self.left_spacer.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
		lib_layout.addWidget(self.left_spacer)

		self.library_widget.section_toggled.connect(self._update_left_panel_layout)
		self.setlist_widget.section_toggled.connect(self._update_left_panel_layout)
		
		self.layout_toggle_btn = QPushButton("Layout", self)
		self.layout_toggle_btn.setFixedSize(68, 24)
		self.layout_toggle_btn.setToolTip("Cambiar layout (Ctrl+L) — clásico/Waveform")
		self.layout_toggle_btn.clicked.connect(self._toggle_layout)
		self.layout_toggle_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {self.theme.BUTTON_BG};
				border: 1px solid {self.theme.BORDER};
				border-radius: {self.theme.BORDER_RADIUS_SM};
				color: {self.theme.TEXT_PRIMARY};
				font-size: 11px;
			}}
			QPushButton:hover {{
				background-color: {self.theme.HOVER_BRIGHTEN};
			}}
            QPushButton:checked {{
                background-color: {self.theme.ACCENT_PRIMARY};
                border: 1px solid {self.theme.ACCENT_PRIMARY};
            }}
		""")
		self.layout_toggle_btn.raise_()
		lib_layout.addWidget(self.layout_toggle_btn)

		self._update_left_panel_layout()

		main_layout.addWidget(self.lib_panel)

	def _update_left_panel_layout(self):
		if not hasattr(self, 'splitter'):
			return

		lib_expanded = 0
		setlist_expanded = 0

		if hasattr(self, 'library_widget'):
			if not self.library_widget._songs_section._collapsed:
				lib_expanded += 1
			if not self.library_widget._fav_section._collapsed:
				lib_expanded += 1
			if not self.library_widget._recent_section._collapsed:
				lib_expanded += 1

		if hasattr(self, 'setlist_widget'):
			if not self.setlist_widget._section._collapsed:
				setlist_expanded += 1

		all_collapsed = (lib_expanded == 0 and setlist_expanded == 0)

		if all_collapsed:
			self.splitter.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
			self.left_spacer.setVisible(True)
			self.splitter.setStretchFactor(0, 0)
			self.splitter.setStretchFactor(1, 0)
			lib_min = self.library_widget.minimumSizeHint().height()
			set_min = self.setlist_widget.minimumSizeHint().height()
			self.splitter.setSizes([lib_min, set_min])
		else:
			self.splitter.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
			self.left_spacer.setVisible(False)

		total_h = self.splitter.height()

		if lib_expanded > 0 and setlist_expanded > 0:
			# Ambos expandidos → SetlistPanel ~20%
			self.splitter.setStretchFactor(0, 4)
			self.splitter.setStretchFactor(1, 1)
			if total_h > 0:
				self.splitter.setSizes([int(total_h * 0.8), int(total_h * 0.2)])
		elif lib_expanded == 0 and setlist_expanded > 0:
			# Library solo headers, SetlistPanel ocupa el resto
			self.splitter.setStretchFactor(0, 0)
			self.splitter.setStretchFactor(1, 1)
			lib_min = self.library_widget.minimumSizeHint().height()
			if total_h > lib_min:
				self.splitter.setSizes([lib_min, total_h - lib_min])
		elif lib_expanded > 0 and setlist_expanded == 0:
			self.splitter.setStretchFactor(0, 1)
			self.splitter.setStretchFactor(1, 0)

		self.splitter.updateGeometry()

	# -- ---------------------------------- --
	# Center Panel
	def _build_center_panel(self, left_center_layout):
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
		load_btn.setToolTip("Seleccionar una carpeta con pistas de audio (wav, mp3, flac, m4a)")
		load_btn.clicked.connect(self._load_stems)
		center_layout.addWidget(load_btn)

	def _build_song_info(self, center_layout):
		self.song_info_layout = QVBoxLayout()
		self.song_info_layout.setSpacing(2)

		self.song_name_label = QLabel("Canción: --")
		self.song_name_label.setStyleSheet(f"color: {self.theme.TEXT_PRIMARY}; font-size: 14px; font-weight: bold;")
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
		self.status_label.setStyleSheet(f"color: {self.theme.TEXT_SECONDARY}; font-size: 12px;")
		center_layout.addWidget(self.status_label)

		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 100)
		self.progress_bar.setValue(0)
		self.progress_bar.setTextVisible(True)
		self.progress_bar.setVisible(False)
		center_layout.addWidget(self.progress_bar)

		self.bg_status_label = QLabel("")
		self.bg_status_label.setAlignment(Qt.AlignCenter)
		self.bg_status_label.setStyleSheet(f"color: {self.theme.ACCENT_PURPLE}; font-size: 11px; font-style: italic;")
		self.bg_status_label.setVisible(False)
		center_layout.addWidget(self.bg_status_label)

	def _build_master_metronome_area(self, center_layout):
		master_row = QHBoxLayout()
		master_row.setSpacing(8)

		master_label = QLabel("Master:")
		master_label.setStyleSheet(f"color: {self.theme.TEXT_PRIMARY}; font-size: 12px; font-weight: bold;")
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
		metro_icon_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-metronome.svg"), self.theme.SVG_ICON_MUTED))
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
		self.metronome_volume_slider.setVisible(True)
		metro_row_2.addWidget(self.metronome_volume_slider)

		self.metronome_pan_slider = PanSlider(parent=self, icons_dir=self.icons_dir)
		self.metronome_pan_slider.setValue(self.state.metronome_pan)
		self.metronome_pan_slider.setMaximumSize(200, 80)
		self.metronome_pan_slider.valueChanged.connect(self._on_metronome_pan_changed)
		self.metronome_pan_slider.sliderReleased.connect(self._on_metronome_pan_released)
		self.metronome_pan_slider.setVisible(True)
		metro_row_2.addWidget(self.metronome_pan_slider)
		master_row.setStretch(master_row.indexOf(self.master_volume_slider), 1)

		center_layout.addLayout(master_row)
		center_layout.addLayout(metro_row)
		center_layout.addLayout(metro_row_2)

	def _build_stems_area(self, center_layout):
		self.stems_scroll = QScrollArea()
		self.stems_scroll.setWidgetResizable(True)
		self.stems_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
		self.stems_scroll.setFrameShape(QFrame.NoFrame)
		self.stems_container = QWidget()
		self.stems_layout = QVBoxLayout(self.stems_container)
		self.stems_layout.setAlignment(Qt.AlignTop)
		self.stems_layout.setSpacing(8)
		self.stems_layout.setContentsMargins(4, 4, 4, 4)
		self.stems_scroll.setWidget(self.stems_container)

		self.center_stack = QStackedWidget()
		self.center_stack.addWidget(self.stems_scroll)

		self.live_display_widget = LiveChordWidget()
		self.live_display_widget.set_stream_port(self.config_mgr.get_stream_port())
		self.live_display_widget.close_requested.connect(lambda: self.toggle_live_btn.setChecked(False))
		self.center_stack.addWidget(self.live_display_widget)

		self.chordpro_fullscreen_view = QWidget()
		chordpro_fullscreen_layout = QVBoxLayout(self.chordpro_fullscreen_view)
		chordpro_fullscreen_layout.setContentsMargins(10, 10, 10, 10)
		chordpro_fullscreen_layout.setSpacing(6)

		chordpro_button_row = QHBoxLayout()
		chordpro_button_row.setSpacing(6)

		self.chordpro_close_fullscreen_btn = QPushButton("Cerrar Preview")
		self.chordpro_close_fullscreen_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-close-x.svg"), self.theme.SVG_ICON_DANGER))
		self.chordpro_close_fullscreen_btn.setMinimumHeight(28)
		self.chordpro_close_fullscreen_btn.setToolTip("Cerrar la vista previa de ChordPro en pantalla completa")
		self.chordpro_close_fullscreen_btn.clicked.connect(self._hide_chordpro_fullscreen)
		chordpro_button_row.addWidget(self.chordpro_close_fullscreen_btn)

		self.chordpro_edit_fullscreen_btn = QPushButton("Editar Acordes")
		self.chordpro_edit_fullscreen_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-pen.svg")))
		self.chordpro_edit_fullscreen_btn.setMinimumHeight(28)
		self.chordpro_edit_fullscreen_btn.setToolTip("Abrir el editor de ChordPro para modificar los acordes")
		self.chordpro_edit_fullscreen_btn.clicked.connect(self._on_edit_chordpro_clicked)
		chordpro_button_row.addWidget(self.chordpro_edit_fullscreen_btn)

		chordpro_button_row.addStretch()
		chordpro_fullscreen_layout.addLayout(chordpro_button_row)

		self.chordpro_fullscreen_text = QTextEdit()
		self.chordpro_fullscreen_text.setReadOnly(True)
		self.chordpro_fullscreen_text.setStyleSheet(f"""
			QTextEdit {{
				background-color: {self.theme.BG_EDITOR};
				color: {self.theme.TEXT_EDITOR};
				border: 1px solid {self.theme.BORDER_ALT};
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
		save_row.setSpacing(4)

		self.save_lib_btn = QPushButton("Guardar en librería")
		self.save_lib_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-save.svg")))
		self.save_lib_btn.setFixedHeight(28)
		self.save_lib_btn.setToolTip("Guardar la canción actual en la librería")
		self.save_lib_btn.clicked.connect(self._save_to_library)
		self.save_lib_btn.setVisible(False)
		save_row.addWidget(self.save_lib_btn)

		self.save_changes_btn = QPushButton("Guardar Cambios")
		self.save_changes_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-save.svg")))
		self.save_changes_btn.setFixedHeight(28)
		self.save_changes_btn.setToolTip("Guardar los cambios realizados en la canción")
		self.save_changes_btn.clicked.connect(self._save_changes)
		self.save_changes_btn.setVisible(False)
		save_row.addWidget(self.save_changes_btn)

		self.generate_chordpro_btn = QPushButton("Generar Sheet")
		self.generate_chordpro_btn.setFixedHeight(28)
		self.generate_chordpro_btn.setToolTip("Generar hoja de acordes ChordPro automáticamente")
		self.generate_chordpro_btn.clicked.connect(self._on_generate_chordpro_clicked)
		self.generate_chordpro_btn.setVisible(False)
		save_row.addWidget(self.generate_chordpro_btn)

		self.toggle_live_btn = QPushButton("Live Chords")
		self.toggle_live_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-microphone.svg")))
		self.toggle_live_btn.setFixedHeight(28)
		self.toggle_live_btn.setToolTip("Activar/desactivar el modo Live Chords")
		self.toggle_live_btn.setCheckable(True)
		self.toggle_live_btn.toggled.connect(self._toggle_live_mode)
		self.toggle_live_btn.setVisible(False)
		save_row.addWidget(self.toggle_live_btn)

		save_row.addStretch()

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
		self.more_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-levels.svg")))
		self.more_btn.setVisible(False)
		self.more_menu = QMenu(self)
		self._save_as_action = self.more_menu.addAction(
			svg_icon(os.path.join(self.icons_dir, "fad-saveas.svg")), "Guardar Como...", self._save_as)
		self._edit_chordpro_action = self.more_menu.addAction("Editar Acordes", self._on_edit_chordpro_clicked)
		self.more_menu.addSeparator()
		self._regenerate_sync_action = self.more_menu.addAction(
			svg_icon(os.path.join(self.icons_dir, "fad-repeat.svg")), "Regenerar Sync (Whisper)", self._on_regenerate_sync_clicked)
		self._edit_sync_action = self.more_menu.addAction("Editar Sync...", self._on_edit_sync_clicked)
		self._reclassify_stems_action = self.more_menu.addAction(
			svg_icon(os.path.join(self.icons_dir, "fad-repeat.svg")), "Recalcular stems", self._on_reclassify_stems_clicked)
		self.more_menu.addSeparator()
		self._add_to_setlist_action = self.more_menu.addAction(
			svg_icon(os.path.join(self.icons_dir, "fad-plus.svg")), "Añadir a Setlist", self._on_add_to_setlist_clicked)
		self.more_menu.addSeparator()
		self._settings_action = self.more_menu.addAction("Configuración...", self._open_settings)
		self.more_btn.setMenu(self.more_menu)
		save_row.addWidget(self.more_btn)

		center_layout.addLayout(save_row)

	def _build_close_row(self, center_layout):
		close_row = QHBoxLayout()
		self.close_song_btn = QPushButton("Cerrar Canción")
		self.close_song_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-close-x.svg"), self.theme.SVG_ICON_DANGER))
		self.close_song_btn.setMinimumHeight(36)
		self.close_song_btn.setToolTip("Cerrar la canción actual y liberar recursos")
		self.close_song_btn.clicked.connect(self._close_song)
		self.close_song_btn.setVisible(False)
		close_row.addWidget(self.close_song_btn)

		close_row.addStretch()

		center_layout.addLayout(close_row)

	# -- ---------------------------------- --
	# Right Panel
	def _build_right_panel(self, right_panel):
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
		self.key_label.setStyleSheet(f"color: {self.theme.ACCENT_CYAN};")
		key_row.addWidget(self.key_label, 1)
		self.edit_key_btn = QPushButton()
		self.edit_key_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-pen.svg"), self.theme.SVG_ICON_MUTED))
		self.edit_key_btn.setFixedSize(28, 28)
		self.edit_key_btn.setToolTip("Editar tonalidad detectada")
		self.edit_key_btn.clicked.connect(self._on_edit_key_clicked)
		key_row.addWidget(self.edit_key_btn)
		av.addLayout(key_row)

		self.bpm_label = QLabel("BPM: --")
		self.bpm_label.setFont(QFont("Arial", 18, QFont.Bold))
		self.bpm_label.setAlignment(Qt.AlignCenter)
		self.bpm_label.setStyleSheet(f"color: {self.theme.TEXT_SECONDARY};")
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
		self.orig_bpm_label.setStyleSheet(f"color: {self.theme.TEXT_SECONDARY};")
		th.addWidget(self.orig_bpm_label)

		self.bpm_spin = QSpinBox()
		self.bpm_spin.setRange(20, 300)
		self.bpm_spin.setValue(120)
		self.bpm_spin.setSuffix(" BPM")
		th.addWidget(self.bpm_spin)

		self.apply_tempo_btn = QPushButton("Aplicar")
		self.apply_tempo_btn.setToolTip("Aplicar el nuevo tempo a la reproducción")
		self.apply_tempo_btn.clicked.connect(self._on_apply_tempo_clicked)
		th.addWidget(self.apply_tempo_btn)

		self.tempo_ratio_label = QLabel("100%")
		self.tempo_ratio_label.setStyleSheet(f"color: {self.theme.TEXT_SECONDARY}; min-width: 50px;")
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
		self.reset_btn.setToolTip("Restablecer todos los cambios de pitch y volumen")
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
		self.auto_play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-preset-ab.svg"), self.theme.SVG_ICON_ACTIVE))
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
		self.playback_progress.setStyleSheet(self.theme.playback_slider_qss())
		self.playback_progress.setTracking(True)
		self.playback_progress.sliderReleased.connect(self._on_playback_seek)
		self.playback_progress.sliderMoved.connect(self._on_playback_preview)
		pv.addWidget(self.playback_progress)

		time_row = QHBoxLayout()
		self.current_time_label = QLabel("00:00")
		self.current_time_label.setStyleSheet(f"color: {self.theme.TEXT_PRIMARY}; font-size: 11px; font-family: {self.theme.FONT_MONO};")
		time_row.addWidget(self.current_time_label)
		time_row.addStretch()
		self.total_time_label = QLabel("00:00")
		self.total_time_label.setStyleSheet(f"color: {self.theme.TEXT_SECONDARY}; font-size: 11px; font-family: {self.theme.FONT_MONO};")
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
