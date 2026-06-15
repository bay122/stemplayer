import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QLineEdit, QFileDialog, QMessageBox, QInputDialog,
    QGroupBox, QMenu
)
from PySide6.QtCore import Signal, Qt
from config_manager import get_library_path, set_library_path
from stem_widgets import svg_icon
from library_manager import get_library_songs, get_song_metadata, rename_song_folder, delete_song_folder

class LibraryPanel(QWidget):
    song_load_requested = Signal(str, str, dict)  # song_folder, song_name, metadata
    song_renamed = Signal(str, str) # old_name, new_name
    song_deleted = Signal(str) # name
    song_export_requested = Signal(str, str) # song_name, export_type

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

        # Library path
        lib_path_layout = QHBoxLayout()
        self.lib_path_label = QLabel("Librería: No configurada")
        self.lib_path_label.setStyleSheet("color: #888888; font-size: 11px; padding-left: 20px;")
        self.lib_path_label.setWordWrap(True)
        lib_path_layout.addWidget(self.lib_path_label, 1)
        
        self.set_lib_btn = QPushButton("...")
        self.set_lib_btn.setToolTip("Cambiar carpeta de librería")
        self.set_lib_btn.setFixedSize(28, 28)
        self.set_lib_btn.clicked.connect(self._select_library_path)
        lib_path_layout.addWidget(self.set_lib_btn)
        layout.addLayout(lib_path_layout)

        # Library songs list
        lib_box = QGroupBox("Canciones en librería")
        lib_box_layout = QVBoxLayout(lib_box)
        
        # Search bar
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
                
                from PySide6.QtWidgets import QListWidgetItem
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, s["name"])
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
        menu.setStyleSheet("QMenu { background-color: #2A2A2A; color: white; } QMenu::item:selected { background-color: #0078D7; }")
        
        rename_action = menu.addAction("Renombrar")
        delete_action = menu.addAction("Eliminar")
        
        export_menu = menu.addMenu("Exportar...")
        export_menu.setStyleSheet("QMenu { background-color: #2A2A2A; color: white; } QMenu::item:selected { background-color: #0078D7; }")
        
        exp_zip_orig = export_menu.addAction("Como Stems (.zip) - Originales")
        exp_zip_cfg = export_menu.addAction("Como Stems (.zip) - Con Configuración")
        export_menu.addSeparator()
        exp_wav_orig = export_menu.addAction("Como Mezcla (.wav) - Original")
        exp_wav_cfg = export_menu.addAction("Como Mezcla (.wav) - Con Configuración")
        
        action = menu.exec(self.library_list.mapToGlobal(pos))
        song_name = item.data(Qt.UserRole)
        
        if action == rename_action:
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

    def clear_selection(self):
        self.library_list.clearSelection()

    def update_icons(self, current_song: str, is_playing: bool, blink: bool, icons_dir: str):
        from stem_widgets import svg_icon
        import os
        
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
