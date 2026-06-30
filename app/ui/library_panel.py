import json
import os
import re
import shutil
from PySide6.QtWidgets import (
	QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
	QListWidget, QLineEdit, QFileDialog, QMessageBox, QInputDialog,
	QMenu, QListWidgetItem, QDialog, QDialogButtonBox,
	QCheckBox, QComboBox, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from app.ui.svg_icon import svg_icon
from app.ui.theme import current as theme
from app.data.library_manager import get_library_songs, get_song_metadata, rename_song_folder, delete_song_folder
from app.ui.settings_dialog import SettingsDialog
from app.ui.collapsible_section import CollapsibleSection


class LibraryPanel(QWidget):
	song_load_requested = Signal(str, str, dict)
	song_renamed = Signal(str, str)
	song_deleted = Signal(str)
	song_export_requested = Signal(str, str)
	settings_changed = Signal()
	section_toggled = Signal()

	def __init__(self, config_mgr, icons_dir, parent=None):
		super().__init__(parent)
		self.config_mgr = config_mgr
		self.config = config_mgr.config
		self.icons_dir = icons_dir
		self.all_songs = []
		self._build_ui()
		self.refresh_ui()

	def _build_ui(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(6)

		# ---- Library selector + actions row ----
		top_row = QHBoxLayout()
		top_row.setSpacing(4)

		self.lib_combo = QComboBox()
		self.lib_combo.setToolTip("Seleccionar librería activa")
		self.lib_combo.setStyleSheet(f"""
			QComboBox {{
				background-color: {theme.BG_INPUT};
				color: {theme.TEXT_PRIMARY};
				border: 1px solid {theme.BORDER};
				border-radius: {theme.BORDER_RADIUS_SM};
				padding: 2px 4px;
				margin-left: 25px;
				font-size: 11px;
			}}
			QComboBox::drop-down {{ border: none; width: 16px; }}
			QComboBox QAbstractItemView {{
				background-color: {theme.BG_INPUT};
				color: {theme.TEXT_PRIMARY};
				selection-background-color: {theme.ACCENT_INFO};
			}}
		""")
		self.lib_combo.currentIndexChanged.connect(self._on_library_changed)
		top_row.addWidget(self.lib_combo, 1)

		self.add_lib_btn = QPushButton("+")
		self.add_lib_btn.setFixedSize(24, 24)
		self.add_lib_btn.setToolTip("Añadir nueva librería")
		self.add_lib_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.ACCENT_SUCCESS};
				color: #FFF;
				border: none;
				border-radius: 3px;
				font-weight: bold;
				font-size: 13px;
			}}
			QPushButton:hover {{ background-color: #66BB6A; }}
		""")
		self.add_lib_btn.clicked.connect(self._add_library)
		top_row.addWidget(self.add_lib_btn)

		self.del_lib_btn = QPushButton("−")
		self.del_lib_btn.setFixedSize(24, 24)
		self.del_lib_btn.setToolTip("Eliminar librería seleccionada")
		self.del_lib_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.ACCENT_DANGER_ALT};
				color: #FFF;
				border: none;
				border-radius: 3px;
				font-weight: bold;
				font-size: 13px;
			}}
			QPushButton:hover {{ background-color: #FF3333; }}
		""")
		self.del_lib_btn.clicked.connect(self._delete_library)
		top_row.addWidget(self.del_lib_btn)

		layout.addLayout(top_row)

		# ---- Path + settings row ----
		path_row = QHBoxLayout()
		self.lib_path_label = QLabel("Librería: No configurada")
		self.lib_path_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 10px;")
		self.lib_path_label.setWordWrap(True)
		path_row.addWidget(self.lib_path_label, 1)

		self.settings_btn = QPushButton("⚙")
		self.settings_btn.setFixedSize(24, 24)
		self.settings_btn.setToolTip("Configuración")
		self.settings_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.BG_TERTIARY};
				color: {theme.TEXT_PRIMARY};
				border: 1px solid {theme.BORDER};
				border-radius: 3px;
				font-size: 13px;
			}}
			QPushButton:hover {{ background-color: {theme.HOVER_BRIGHTEN}; }}
		""")
		self.settings_btn.clicked.connect(self._open_settings)
		path_row.addWidget(self.settings_btn)

		self.set_lib_btn = QPushButton("...")
		self.set_lib_btn.setToolTip("Cambiar carpeta de librería")
		self.set_lib_btn.setFixedSize(24, 24)
		self.set_lib_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.BG_TERTIARY};
				color: {theme.TEXT_PRIMARY};
				border: 1px solid {theme.BORDER};
				border-radius: 3px;
				font-weight: bold;
			}}
			QPushButton:hover {{ background-color: {theme.HOVER_BRIGHTEN}; }}
		""")
		self.set_lib_btn.clicked.connect(self._select_library_path)
		path_row.addWidget(self.set_lib_btn)

		layout.addLayout(path_row)

		# ---- Song library box ----
		lib_content = QWidget()
		lib_cl = QVBoxLayout(lib_content)
		lib_cl.setContentsMargins(0, 0, 0, 0)
		lib_cl.setSpacing(4)

		self.search_input = QLineEdit()
		self.search_input.setPlaceholderText("Buscar canción o artista...")
		self.search_input.setStyleSheet(f"""
			QLineEdit {{
				background-color: {theme.BG_INPUT};
				color: {theme.TEXT_PRIMARY};
				border: 1px solid {theme.BORDER};
				border-radius: {theme.BORDER_RADIUS_SM};
				padding: 3px 6px;
				font-size: 11px;
			}}
			QLineEdit:focus {{ border: 1px solid {theme.ACCENT_INFO}; }}
		""")
		self.search_input.textChanged.connect(self._on_search_changed)
		lib_cl.addWidget(self.search_input)

		self.library_list = QListWidget()
		self.library_list.setStyleSheet(f"""
			QListWidget {{
				background-color: {theme.BG_SECONDARY};
				border: 1px solid {theme.BORDER_DARK};
				border-radius: {theme.BORDER_RADIUS_SM};
				color: {theme.TEXT_PRIMARY};
				font-size: 11px;
			}}
			QListWidget::item:selected {{ background-color: {theme.ACCENT_INFO}; }}
		""")
		self.library_list.itemDoubleClicked.connect(self._load_selected)
		self.library_list.setContextMenuPolicy(Qt.CustomContextMenu)
		self.library_list.customContextMenuRequested.connect(self._on_context_menu)
		lib_cl.addWidget(self.library_list, 1)

		lib_load_btn = QPushButton("Cargar")
		lib_load_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-open.svg")))
		lib_load_btn.setToolTip("Cargar la canción seleccionada desde la librería")
		lib_load_btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {theme.ACCENT_INFO};
				color: #FFF;
				border: none;
				border-radius: {theme.BORDER_RADIUS_SM};
				padding: 4px 10px;
				font-size: 11px;
				font-weight: bold;
			}}
			QPushButton:hover {{ background-color: #42A5F5; }}
		""")
		lib_load_btn.clicked.connect(self._load_selected)
		lib_cl.addWidget(lib_load_btn)

		self._songs_section = CollapsibleSection("Canciones", "songs", config_mgr=self.config_mgr)
		self._songs_section.set_content(lib_content)
		layout.addWidget(self._songs_section)

		# ---- Favorites section ----
		self._fav_section = self._build_collapsible(layout, "Favoritos", "favorites", "_fav_list")

		# ---- Recent section ----
		self._recent_section = self._build_collapsible(layout, "Recientes", "recent", "_recent_list")

		# Connect collapsible section toggled signals
		self._songs_section.toggled.connect(self._update_stretches)
		self._fav_section.toggled.connect(self._update_stretches)
		self._recent_section.toggled.connect(self._update_stretches)

		# Initial stretches update
		self._update_stretches()

	def _update_stretches(self):
		songs_expanded = not self._songs_section._collapsed
		fav_expanded = not self._fav_section._collapsed
		recent_expanded = not self._recent_section._collapsed

		# Update stretch factors in LibraryPanel's layout
		layout = self.layout()
		layout.setStretchFactor(self._songs_section, 1 if songs_expanded else 0)
		layout.setStretchFactor(self._fav_section, 1 if fav_expanded else 0)
		layout.setStretchFactor(self._recent_section, 1 if recent_expanded else 0)

		# Also update the size policy of LibraryPanel itself!
		any_expanded = songs_expanded or fav_expanded or recent_expanded
		if any_expanded:
			self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
		else:
			self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
		self.updateGeometry()
		self.section_toggled.emit()

	def _build_collapsible(self, parent_layout, title, section_id, list_attr):
		lst = QListWidget()
		lst.setStyleSheet(f"""
			QListWidget {{
				background-color: {theme.BG_INPUT};
				border: 1px solid {theme.BORDER_DARK};
				border-radius: 3px;
				color: {theme.TEXT_PRIMARY};
				font-size: 11px;
			}}
			QListWidget::item:selected {{ background-color: {theme.ACCENT_INFO}; }}
		""")
		lst.itemDoubleClicked.connect(self._load_selected_from_list)

		sec = CollapsibleSection(title, section_id, config_mgr=self.config_mgr)
		sec.set_content(lst)
		setattr(self, list_attr, lst)
		parent_layout.addWidget(sec)
		return sec

	# ---- Library management ----

	def _on_library_changed(self, index):
		libraries = self.config_mgr.get_libraries()
		if 0 <= index < len(libraries):
			self.config_mgr.set_active_library(index)
			self.config = self.config_mgr.config
			self.refresh_ui()

	def _add_library(self):
		name, ok = QInputDialog.getText(self, "Nueva librería", "Nombre de la librería:")
		if not ok or not name.strip():
			return
		folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta para la librería")
		if not folder:
			return
		self.config_mgr.add_library(name.strip(), folder)
		self.config = self.config_mgr.config
		self.refresh_ui()

	def _delete_library(self):
		idx = self.lib_combo.currentIndex()
		if idx < 0:
			return
		libraries = self.config_mgr.get_libraries()
		if idx < len(libraries):
			name = libraries[idx]["name"]
			reply = QMessageBox.question(self, "Confirmar",
				f"¿Eliminar la librería '{name}' de la configuración?\n(Las canciones en disco no se borrarán.)",
				QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
			if reply == QMessageBox.Yes:
				self.config_mgr.remove_library(idx)
				self.config = self.config_mgr.config
				self.refresh_ui()

	def _select_library_path(self):
		folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de librería")
		if folder:
			self.config_mgr.set_library_path(folder)
			self.config = self.config_mgr.config
			self.refresh_ui()

	def _open_settings(self):
		filters = self.config_mgr.get_stem_filters()
		port = self.config_mgr.get_stream_port()
		dialog = SettingsDialog(filters, port, config_mgr=self.config_mgr, parent=self)
		if dialog.exec() == SettingsDialog.Accepted:
			self.config_mgr.set_stem_filters(dialog.get_stem_filters())
			self.config_mgr.set_stream_port(dialog.get_stream_port())
			self.settings_changed.emit()

	# ---- Data refresh ----

	def refresh_ui(self):
		libs = self.config_mgr.get_libraries()
		active = self.config_mgr.get_active_library()

		self.lib_combo.blockSignals(True)
		self.lib_combo.clear()
		for i, lib in enumerate(libs):
			name = lib.get("name", f"Librería {i+1}")
			self.lib_combo.addItem(name)
			if lib.get("last_used"):
				self.lib_combo.setCurrentIndex(i)
		self.lib_combo.blockSignals(False)

		path = active["path"] if active else ""
		if path:
			self.lib_path_label.setText(f"{active['name']}: {path}")
		else:
			self.lib_path_label.setText("Librería: No configurada")

		self.all_songs = []
		if path and os.path.exists(path):
			songs = get_library_songs(path)
			for s in songs:
				meta = get_song_metadata(path, s)
				artist = meta.get("artist", "") if meta else ""
				duration = meta.get("duration", "") if meta else ""
				self.all_songs.append({"name": s, "artist": artist, "duration": duration})

		self._filter_list()
		self._refresh_favorites()
		self._refresh_recent()

	def _refresh_favorites(self):
		lst = self._fav_list
		lst.clear()
		favs = self.config_mgr.get_favorites()
		for name in favs:
			item = QListWidgetItem(f"★ {name}")
			item.setData(Qt.UserRole, name)
			lst.addItem(item)

	def _refresh_recent(self):
		lst = self._recent_list
		lst.clear()
		recent = self.config_mgr.get_recent_played()
		for name in recent:
			item = QListWidgetItem(name)
			item.setData(Qt.UserRole, name)
			lst.addItem(item)

	# ---- Song list ----

	def _filter_list(self):
		query = self.search_input.text().lower()
		self.library_list.clear()
		for s in self.all_songs:
			if query in s["name"].lower() or query in s["artist"].lower():
				display_text = s["name"]
				if s.get("duration"):
					display_text = f"{display_text} [{s['duration']}]"

				item = QListWidgetItem(display_text)
				item.setData(Qt.UserRole, s["name"])
				item.setToolTip(
					f"Nombre: {s['name']}\n"
					f"Artista: {s.get('artist', '(sin artista)')}\n"
					f"Tamaño total: {self._format_size(self._get_song_total_size(os.path.join(self.config_mgr.get_library_path(), s['name'])))}"
				)
				self.library_list.addItem(item)

	def _on_search_changed(self, text):
		self._filter_list()

	def _load_selected(self):
		item = self.library_list.currentItem()
		if not item:
			return
		song_name = item.data(Qt.UserRole)
		path = self.config_mgr.get_library_path()
		metadata = get_song_metadata(path, song_name)
		song_folder = os.path.join(path, song_name)
		if os.path.exists(song_folder):
			self.config_mgr.add_recent_played(song_name)
			self._refresh_recent()
			self.song_load_requested.emit(song_folder, song_name, metadata if metadata else {})

	def _load_selected_from_list(self, item):
		song_name = item.data(Qt.UserRole)
		if not song_name:
			return
		path = self.config_mgr.get_library_path()
		metadata = get_song_metadata(path, song_name)
		song_folder = os.path.join(path, song_name)
		if os.path.exists(song_folder):
			self.config_mgr.add_recent_played(song_name)
			self._refresh_recent()
			self.song_load_requested.emit(song_folder, song_name, metadata if metadata else {})

	# ---- Context menu ----

	def _on_context_menu(self, pos):
		item = self.library_list.itemAt(pos)
		if not item:
			return
		menu = QMenu()
		menu.setStyleSheet(theme.menu_qss())

		load_action = menu.addAction("Cargar")
		song_name = item.data(Qt.UserRole)
		is_fav = self.config_mgr.is_favorite(song_name)

		if is_fav:
			fav_action = menu.addAction("Quitar de favoritos")
		else:
			fav_action = menu.addAction("Añadir a favoritos")
		menu.addSeparator()
		rename_action = menu.addAction("Renombrar")
		delete_action = menu.addAction("Eliminar")
		menu.addSeparator()

		export_menu = menu.addMenu("Exportar...")
		export_menu.setStyleSheet(theme.menu_qss())
		exp_zip_orig = export_menu.addAction("Como Stems (.zip) - Originales")
		exp_zip_cfg = export_menu.addAction("Como Stems (.zip) - Con Configuración")
		export_menu.addSeparator()
		exp_wav_orig = export_menu.addAction("Como Mezcla (.wav) - Original")
		exp_wav_cfg = export_menu.addAction("Como Mezcla (.wav) - Con Configuración")
		menu.addSeparator()

		cache_action = menu.addAction("Borrar cache...")
		details_action = menu.addAction("Detalles")

		action = menu.exec(self.library_list.mapToGlobal(pos))

		if action == load_action:
			self.library_list.setCurrentItem(item)
			self._load_selected()
		elif action == fav_action:
			if is_fav:
				self.config_mgr.remove_favorite(song_name)
			else:
				self.config_mgr.add_favorite(song_name)
			self._refresh_favorites()
		elif action == rename_action:
			self._rename_song(song_name)
		elif action == delete_action:
			self._delete_song(song_name)
		elif action == exp_zip_orig:
			self.song_export_requested.emit(song_name, "zip_orig")
		elif action == exp_zip_cfg:
			self.song_export_requested.emit(song_name, "zip_cfg")
		elif action == exp_wav_orig:
			self.song_export_requested.emit(song_name, "wav_orig")
		elif action == exp_wav_cfg:
			self.song_export_requested.emit(song_name, "wav_cfg")
		elif action == cache_action:
			self._show_cache_cleanup_dialog(song_name)
		elif action == details_action:
			self._show_song_details_dialog(song_name)

	# ---- CRUD songs ----

	def _rename_song(self, old_name):
		new_name, ok = QInputDialog.getText(self, "Renombrar Canción", "Nuevo nombre:", text=old_name)
		if ok and new_name.strip() and new_name != old_name:
			path = self.config_mgr.get_library_path()
			if rename_song_folder(path, old_name, new_name):
				self.refresh_ui()
				self.song_renamed.emit(old_name, new_name)
			else:
				QMessageBox.warning(self, "Error", "No se pudo renombrar la canción. ¿Ya existe una con ese nombre o está en uso?")

	def _delete_song(self, name):
		reply = QMessageBox.question(self, "Confirmar eliminación",
			f"¿Estás seguro de eliminar '{name}' de la librería?\n\n"
			f"¡ADVERTENCIA: Se eliminarán de tu disco de forma permanente todos los archivos de audio (.wav) y metadatos asociados a esta canción!",
			QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
		if reply == QMessageBox.Yes:
			path = self.config_mgr.get_library_path()
			delete_song_folder(path, name)
			self.refresh_ui()
			self.song_deleted.emit(name)

	@staticmethod
	def _get_song_total_size(folder: str) -> int:
		total = 0
		for dirpath, _, filenames in os.walk(folder):
			for f in filenames:
				try:
					total += os.path.getsize(os.path.join(dirpath, f))
				except OSError:
					pass
		return total

	@staticmethod
	def _format_size(size: int) -> str:
		for unit in ("B", "KB", "MB", "GB"):
			if size < 1024:
				return f"{size:.1f} {unit}"
			size /= 1024
		return f"{size:.1f} TB"

	@staticmethod
	def _parse_cache_folder_name(folder_name: str):
		m = re.match(r"(.+)-(\d+)bpm", os.path.basename(folder_name))
		if m:
			return m.group(1), m.group(2)
		return "?", "?"

	def _show_cache_cleanup_dialog(self, song_name: str):
		path = self.config_mgr.get_library_path()
		song_folder = os.path.join(path, song_name)
		if not os.path.isdir(song_folder):
			QMessageBox.warning(self, "Error", "No se encontró la carpeta de la canción.")
			return

		cache_entries = []
		for entry in os.listdir(song_folder):
			entry_path = os.path.join(song_folder, entry)
			if os.path.isdir(entry_path) and entry.startswith("cache"):
				key, bpm = self._parse_cache_folder_name(entry)
				size = self._get_song_total_size(entry_path)
				cache_entries.append((entry, entry_path, key, bpm, size))

		if not cache_entries:
			QMessageBox.information(self, "Cache limpio", "No hay carpetas de cache para esta canción.")
			return

		dialog = QDialog(self)
		dialog.setWindowTitle(f"Borrar cache - {song_name}")
		dialog.setMinimumWidth(400)
		dlg_layout = QVBoxLayout(dialog)
		dlg_layout.setSpacing(8)
		dlg_layout.addWidget(QLabel("Selecciona las carpetas de cache a eliminar:"))

		checkboxes = []
		for entry, entry_path, key, bpm, size in cache_entries:
			cb = QCheckBox(f"{entry}  |  Key: {key}  BPM: {bpm}  ({self._format_size(size)})")
			cb.setProperty("path", entry_path)
			checkboxes.append(cb)
			dlg_layout.addWidget(cb)

		btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		btn_box.accepted.connect(dialog.accept)
		btn_box.rejected.connect(dialog.reject)
		dlg_layout.addWidget(btn_box)

		if dialog.exec() != QDialog.Accepted:
			return

		to_delete = [cb.property("path") for cb in checkboxes if cb.isChecked()]
		if not to_delete:
			return

		reply = QMessageBox.question(self, "Confirmar",
			f"¿Eliminar {len(to_delete)} carpetas de cache?\nSe borrarán del disco permanentemente.",
			QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
		if reply != QMessageBox.Yes:
			return

		for folder in to_delete:
			shutil.rmtree(folder, ignore_errors=True)
		self.refresh_ui()
		QMessageBox.information(self, "Hecho", f"Se eliminaron {len(to_delete)} carpetas de cache.")

	def _show_song_details_dialog(self, song_name: str):
		path = self.config_mgr.get_library_path()
		song_folder = os.path.join(path, song_name)
		if not os.path.isdir(song_folder):
			QMessageBox.warning(self, "Error", "No se encontró la carpeta de la canción.")
			return

		meta = get_song_metadata(path, song_name) or {}
		info_lines = [
			f"Nombre: {song_name}",
			f"Artista: {meta.get('artist', '(sin artista)')}",
			f"Duración: {meta.get('duration', '?')}",
			f"Tamaño original: {self._format_size(self._get_song_total_size(song_folder))}",
		]

		stems = meta.get("stems", [])
		if stems:
			info_lines.append(f"\nStems ({len(stems)}):")
			for s in stems:
				info_lines.append(f"  - {s.get('name', '?')} ({s.get('category', 'Other')})")
		else:
			info_lines.append("\nStems: (ninguno)")

		cache_entries = []
		for entry in os.listdir(song_folder):
			entry_path = os.path.join(song_folder, entry)
			if os.path.isdir(entry_path) and entry.startswith("cache"):
				key, bpm = self._parse_cache_folder_name(entry)
				size = self._get_song_total_size(entry_path)
				cache_entries.append((entry, key, bpm, size))

		if cache_entries:
			info_lines.append(f"\nCache ({len(cache_entries)}):")
			for entry, key, bpm, size in cache_entries:
				info_lines.append(f"  - {entry}: Key={key}, BPM={bpm}, {self._format_size(size)}")
		else:
			info_lines.append("\nCache: (ninguno)")

		text = "\n".join(info_lines)
		dialog = QDialog(self)
		dialog.setWindowTitle(f"Detalles - {song_name}")
		dialog.setMinimumWidth(400)
		dlg_layout = QVBoxLayout(dialog)
		info_label = QLabel(text)
		info_label.setWordWrap(True)
		dlg_layout.addWidget(info_label)
		close_btn = QPushButton("Cerrar")
		close_btn.setToolTip("Cerrar esta ventana")
		close_btn.clicked.connect(dialog.accept)
		dlg_layout.addWidget(close_btn)

		dialog.exec()

	def clear_selection(self):
		self.library_list.clearSelection()

	def update_icons(self, current_song: str, is_playing: bool, blink: bool, icons_dir: str):
		for i in range(self.library_list.count()):
			item = self.library_list.item(i)
			song_name = item.data(Qt.UserRole)

			if song_name == current_song:
				if is_playing and blink:
					item.setIcon(svg_icon(os.path.join(icons_dir, "fad-speaker.svg"), "#00FF00"))
				else:
					item.setIcon(svg_icon(os.path.join(icons_dir, "fad-speaker.svg"), "#0078D7"))
			else:
				item.setIcon(svg_icon(os.path.join(icons_dir, "fad-speaker.svg"), "#444444"))
