import json
import os
import re
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QLineEdit, QFileDialog, QMessageBox, QInputDialog,
    QGroupBox, QMenu, QListWidgetItem, QDialog, QDialogButtonBox,
    QCheckBox
)
from PySide6.QtCore import Signal, Qt
from app.data.config_manager import get_library_path, set_library_path
from app.ui.svg_icon import svg_icon
from app.ui.theme import DARK_THEME as theme
from app.data.library_manager import get_library_songs, get_song_metadata, rename_song_folder, delete_song_folder


class LibraryPanel(QWidget):
    song_load_requested = Signal(str, str, dict)
    song_renamed = Signal(str, str)
    song_deleted = Signal(str)
    song_export_requested = Signal(str, str)

    def __init__(self, config, icons_dir, parent=None):
        super().__init__(parent)
        self.config = config
        self.icons_dir = icons_dir
        self.all_songs = []
        self._build_ui()
        self.refresh_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        lib_path_layout = QHBoxLayout()
        self.lib_path_label = QLabel("Librería: No configurada")
        self.lib_path_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px; padding-left: 20px;")
        self.lib_path_label.setWordWrap(True)
        lib_path_layout.addWidget(self.lib_path_label, 1)

        self.set_lib_btn = QPushButton("...")
        self.set_lib_btn.setToolTip("Cambiar carpeta de librería")
        self.set_lib_btn.setFixedSize(28, 28)
        self.set_lib_btn.clicked.connect(self._select_library_path)
        lib_path_layout.addWidget(self.set_lib_btn)
        layout.addLayout(lib_path_layout)

        lib_box = QGroupBox("Canciones en librería")
        lib_box_layout = QVBoxLayout(lib_box)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar canción o artista...")
        self.search_input.textChanged.connect(self._on_search_changed)
        lib_box_layout.addWidget(self.search_input)

        self.library_list = QListWidget()
        self.library_list.itemDoubleClicked.connect(self._load_selected)
        self.library_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.library_list.customContextMenuRequested.connect(self._on_context_menu)
        lib_box_layout.addWidget(self.library_list)

        lib_load_btn = QPushButton("Cargar desde librería")
        lib_load_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-open.svg")))
        lib_load_btn.clicked.connect(self._load_selected)
        lib_box_layout.addWidget(lib_load_btn)

        layout.addWidget(lib_box)

    def _select_library_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de librería")
        if folder:
            set_library_path(self.config, folder)
            self.refresh_ui()

    def refresh_ui(self):
        path = get_library_path(self.config)
        if path:
            self.lib_path_label.setText(f"Librería: {path}")
        else:
            self.lib_path_label.setText("Librería: No configurada")

        self.all_songs = []
        if path:
            songs = get_library_songs(path)
            for s in songs:
                meta = get_song_metadata(path, s)
                artist = meta.get("artist", "") if meta else ""
                duration = meta.get("duration", "") if meta else ""
                self.all_songs.append({"name": s, "artist": artist, "duration": duration})

        self._filter_list()

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
                    f"Tamaño total: {self._format_size(self._get_song_total_size(os.path.join(get_library_path(self.config), s['name'])))}"
                )
                self.library_list.addItem(item)

    def _on_search_changed(self, text):
        self._filter_list()

    def _load_selected(self):
        item = self.library_list.currentItem()
        if not item:
            return
        song_name = item.data(Qt.UserRole)
        path = get_library_path(self.config)
        metadata = get_song_metadata(path, song_name)
        song_folder = os.path.join(path, song_name)
        if os.path.exists(song_folder):
            self.song_load_requested.emit(song_folder, song_name, metadata if metadata else {})

    def _on_context_menu(self, pos):
        item = self.library_list.itemAt(pos)
        if not item:
            return
        menu = QMenu()
        menu.setStyleSheet(theme.menu_qss())

        load_action = menu.addAction("Cargar")
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
        song_name = item.data(Qt.UserRole)

        if action == load_action:
            self.library_list.setCurrentItem(item)
            self._load_selected()
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

    def _rename_song(self, old_name):
        new_name, ok = QInputDialog.getText(self, "Renombrar Canción", "Nuevo nombre:", text=old_name)
        if ok and new_name.strip() and new_name != old_name:
            path = get_library_path(self.config)
            if rename_song_folder(path, old_name, new_name):
                self.refresh_ui()
                self.song_renamed.emit(old_name, new_name)
            else:
                QMessageBox.warning(self, "Error", "No se pudo renombrar la canción. ¿Ya existe una con ese nombre o está en uso?")

    def _delete_song(self, name):
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            f"¿Estás seguro de eliminar '{name}' de la librería?\n\n¡ADVERTENCIA: Se eliminarán de tu disco de forma permanente todos los archivos de audio (.wav) y metadatos asociados a esta canción!",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            path = get_library_path(self.config)
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
        path = get_library_path(self.config)
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

        reply = QMessageBox.question(
            self, "Confirmar",
            f"¿Eliminar {len(to_delete)} carpetas de cache?\nSe borrarán del disco permanentemente.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        for folder in to_delete:
            shutil.rmtree(folder, ignore_errors=True)
        self.refresh_ui()
        QMessageBox.information(self, "Hecho", f"Se eliminaron {len(to_delete)} carpetas de cache.")

    def _show_song_details_dialog(self, song_name: str):
        path = get_library_path(self.config)
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
