import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QComboBox, QInputDialog, QMessageBox, QGroupBox, QListWidgetItem, QMenu
)
from PySide6.QtCore import Signal, Qt
from config_manager import get_setlists, add_setlist, update_setlist, remove_setlist, get_library_path
from stem_widgets import svg_icon
from library_manager import get_library_songs, get_song_metadata

class SetlistPanel(QWidget):
    song_load_requested = Signal(str, str, dict)  # song_folder, song_name, metadata

    def __init__(self, config, icons_dir, parent=None):
        super().__init__(parent)
        self.config = config
        self.icons_dir = icons_dir
        self.current_setlist_index = -1
        self.current_setlist_song_index = -1
        self._build_ui()
        self.refresh_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        setlist_box = QGroupBox("Setlists")
        setlist_layout = QVBoxLayout(setlist_box)

        self.setlist_combo = QComboBox()
        self.setlist_combo.currentIndexChanged.connect(self._on_setlist_selected)
        setlist_layout.addWidget(self.setlist_combo)

        sl_row = QHBoxLayout()
        self.setlist_songs_list = QListWidget()
        self.setlist_songs_list.itemDoubleClicked.connect(self._on_song_clicked)
        self.setlist_songs_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.setlist_songs_list.customContextMenuRequested.connect(self._on_context_menu)
        sl_row.addWidget(self.setlist_songs_list)
        
        reorder_btns = QVBoxLayout()
        self.btn_up = QPushButton()
        self.btn_up.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-caret-up.svg"), "#FFFFFF"))
        self.btn_up.setFixedSize(28, 28)
        self.btn_up.clicked.connect(self._move_up)
        reorder_btns.addWidget(self.btn_up)
        
        self.btn_down = QPushButton()
        self.btn_down.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-caret-down.svg"), "#FFFFFF"))
        self.btn_down.setFixedSize(28, 28)
        self.btn_down.clicked.connect(self._move_down)
        reorder_btns.addWidget(self.btn_down)
        
        self.btn_add_to_setlist = QPushButton()
        self.btn_add_to_setlist.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-plus.svg"), "#FFFFFF"))
        self.btn_add_to_setlist.setFixedSize(28, 28)
        self.btn_add_to_setlist.setToolTip("Añadir canción al setlist")
        self.btn_add_to_setlist.clicked.connect(self._add_song_to_setlist_dialog)
        reorder_btns.addWidget(self.btn_add_to_setlist)
        
        self.btn_close_setlist = QPushButton()
        self.btn_close_setlist.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-close-x.svg"), "#FF5555"))
        self.btn_close_setlist.setFixedSize(28, 28)
        self.btn_close_setlist.setToolTip("Deseleccionar setlist")
        self.btn_close_setlist.clicked.connect(self.deselect_setlist)
        reorder_btns.addWidget(self.btn_close_setlist)
        
        reorder_btns.addStretch()
        sl_row.addLayout(reorder_btns)
        
        setlist_layout.addLayout(sl_row)

        setlist_btns = QHBoxLayout()
        setlist_btns.setSpacing(4)
        
        self.new_btn = QPushButton()
        self.new_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-plus.svg"), "#FFFFFF"))
        self.new_btn.setFixedSize(28, 28)
        self.new_btn.setToolTip("Nuevo setlist")
        self.new_btn.clicked.connect(self._create_setlist)
        setlist_btns.addWidget(self.new_btn)
        
        self.edit_btn = QPushButton()
        self.edit_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-pen.svg"), "#FFFFFF"))
        self.edit_btn.setFixedSize(28, 28)
        self.edit_btn.setToolTip("Renombrar setlist")
        self.edit_btn.clicked.connect(self._edit_setlist)
        setlist_btns.addWidget(self.edit_btn)
        
        self.del_btn = QPushButton()
        self.del_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-eraser.svg"), "#FF5555"))
        self.del_btn.setFixedSize(28, 28)
        self.del_btn.setToolTip("Eliminar setlist")
        self.del_btn.clicked.connect(self._delete_setlist)
        setlist_btns.addWidget(self.del_btn)
        
        self.save_btn = QPushButton()
        self.save_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-save.svg"), "#FFFFFF"))
        self.save_btn.setFixedSize(28, 28)
        self.save_btn.setToolTip("Guardar setlist")
        self.save_btn.clicked.connect(self._save_changes)
        self.save_btn.setEnabled(False)
        setlist_btns.addWidget(self.save_btn)
        
        setlist_layout.addLayout(setlist_btns)
        layout.addWidget(setlist_box)

    def refresh_ui(self):
        self.setlist_combo.blockSignals(True)
        self.setlist_combo.clear()
        self.setlist_combo.addItem("-- Seleccionar setlist --")
        for sl in get_setlists(self.config):
            self.setlist_combo.addItem(sl["name"])
        self.setlist_combo.blockSignals(False)
        
        if self.current_setlist_index >= 0:
            self.setlist_combo.setCurrentIndex(self.current_setlist_index + 1)
        else:
            self.setlist_songs_list.clear()

    def _on_setlist_selected(self, index: int):
        self.setlist_songs_list.clear()
        if index <= 0:
            self.current_setlist_index = -1
            return
        self.current_setlist_index = index - 1
        setlists = get_setlists(self.config)
        path = get_library_path(self.config)
        if self.current_setlist_index < len(setlists):
            song_ids = setlists[self.current_setlist_index]["song_ids"]
            for sid in song_ids:
                meta = get_song_metadata(path, sid)
                display_text = sid
                if meta and meta.get("duration"):
                    display_text = f"{sid} [{meta['duration']}]"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, sid)
                self.setlist_songs_list.addItem(item)
                
            if self.setlist_songs_list.count() > 0:
                self.setlist_songs_list.setCurrentRow(0)
                self._on_song_clicked(self.setlist_songs_list.item(0))
                
        self.save_btn.setEnabled(False)

    def deselect_setlist(self):
        self.setlist_combo.setCurrentIndex(0)
        self.current_setlist_index = -1
        self.setlist_songs_list.clear()
        self.save_btn.setEnabled(False)

    def _on_song_clicked(self, item: QListWidgetItem):
        self.current_setlist_song_index = self.setlist_songs_list.row(item)
        self._load_current_song()

    def _load_current_song(self):
        if self.current_setlist_index < 0:
            return
        setlists = get_setlists(self.config)
        songs = setlists[self.current_setlist_index]["song_ids"]
        if 0 <= self.current_setlist_song_index < len(songs):
            song_name = songs[self.current_setlist_song_index]
            path = get_library_path(self.config)
            metadata = get_song_metadata(path, song_name)
            song_folder = os.path.join(path, song_name)
            if os.path.exists(song_folder):
                self.song_load_requested.emit(song_folder, song_name, metadata if metadata else {})

    def play_next(self):
        if self.current_setlist_index < 0:
            return
        setlists = get_setlists(self.config)
        songs = setlists[self.current_setlist_index]["song_ids"]
        if not songs:
            return
        self.current_setlist_song_index += 1
        if self.current_setlist_song_index >= len(songs):
            self.current_setlist_song_index = 0
        self._load_current_song()

    def play_previous(self):
        if self.current_setlist_index < 0:
            return
        setlists = get_setlists(self.config)
        songs = setlists[self.current_setlist_index]["song_ids"]
        if not songs:
            return
        self.current_setlist_song_index -= 1
        if self.current_setlist_song_index < 0:
            self.current_setlist_song_index = len(songs) - 1
        self._load_current_song()

    def _create_setlist(self):
        name, ok = QInputDialog.getText(self, "Nuevo setlist", "Nombre del setlist:")
        if not ok or not name.strip():
            return
        name = name.strip()
        path = get_library_path(self.config)
        songs = get_library_songs(path)
        if not songs:
            QMessageBox.information(self, "Info", "No hay canciones en la librería")
            return
        selected, ok = QInputDialog.getItem(self, "Añadir canción", "Selecciona una canción:", songs, 0, False)
        if ok and selected:
            add_setlist(self.config, name, [selected])
            self.current_setlist_index = len(get_setlists(self.config)) - 1
        self.refresh_ui()

    def _add_song_to_setlist_dialog(self):
        if self.current_setlist_index < 0:
            QMessageBox.warning(self, "Atención", "Primero selecciona un setlist.")
            return
        path = get_library_path(self.config)
        songs = get_library_songs(path)
        if not songs:
            QMessageBox.information(self, "Info", "No hay canciones en la librería")
            return
            
        all_songs_data = []
        for s in songs:
            meta = get_song_metadata(path, s)
            all_songs_data.append({
                "name": s,
                "artist": meta.get("artist", "") if meta else "",
                "duration": meta.get("duration", "") if meta else ""
            })
            
        setlists = get_setlists(self.config)
        sl = setlists[self.current_setlist_index]
        existing_songs = sl["song_ids"]
        
        from gui_custom_dialogs import AddSongToSetlistDialog
        dialog = AddSongToSetlistDialog(all_songs_data, existing_songs, self.icons_dir, self)
        if dialog.exec():
            self.add_song_to_current(dialog.selected_song)
            
    def add_song_to_current(self, song_name: str) -> bool:
        if self.current_setlist_index < 0:
            return False
        setlists = get_setlists(self.config)
        sl = setlists[self.current_setlist_index]
        sl["song_ids"].append(song_name)
        update_setlist(self.config, self.current_setlist_index, sl["name"], sl["song_ids"])
        self.refresh_ui()
        return True
        
    def create_and_add(self, song_name: str) -> bool:
        name, ok = QInputDialog.getText(self, "Nuevo setlist", "Nombre del setlist:")
        if not ok or not name.strip():
            return False
        add_setlist(self.config, name.strip(), [song_name])
        self.current_setlist_index = len(get_setlists(self.config)) - 1
        self.refresh_ui()
        return True

    def _edit_setlist(self):
        if self.current_setlist_index < 0:
            return
        setlists = get_setlists(self.config)
        sl = setlists[self.current_setlist_index]
        new_name, ok = QInputDialog.getText(self, "Renombrar Setlist", "Nuevo nombre:", text=sl["name"])
        if ok and new_name.strip() and new_name != sl["name"]:
            sl["name"] = new_name.strip()
            update_setlist(self.config, self.current_setlist_index, sl["name"], sl["song_ids"])
            self.refresh_ui()

    def _delete_setlist(self):
        if self.current_setlist_index < 0:
            return
        setlists = get_setlists(self.config)
        if self.current_setlist_index < len(setlists):
            setlist_name = setlists[self.current_setlist_index]["name"]
            reply = QMessageBox.question(
                self, "Confirmar eliminación",
                f"¿Eliminar el setlist '{setlist_name}'?\n\nEsta acción no se puede deshacer.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                remove_setlist(self.config, self.current_setlist_index)
                self.current_setlist_index = -1
                self.refresh_ui()

    def _move_up(self):
        row = self.setlist_songs_list.currentRow()
        if row > 0:
            item = self.setlist_songs_list.takeItem(row)
            self.setlist_songs_list.insertItem(row - 1, item)
            self.setlist_songs_list.setCurrentRow(row - 1)
            self.save_btn.setEnabled(True)

    def _move_down(self):
        row = self.setlist_songs_list.currentRow()
        if row < self.setlist_songs_list.count() - 1 and row >= 0:
            item = self.setlist_songs_list.takeItem(row)
            self.setlist_songs_list.insertItem(row + 1, item)
            self.setlist_songs_list.setCurrentRow(row + 1)
            self.save_btn.setEnabled(True)

    def _on_context_menu(self, pos):
        item = self.setlist_songs_list.itemAt(pos)
        if not item:
            return
        self.setlist_songs_list.setCurrentItem(item)
        menu = QMenu()
        menu.setStyleSheet("QMenu { background-color: #2A2A2A; color: white; } QMenu::item:selected { background-color: #0078D7; }")
        
        move_up_act = menu.addAction("Mover Arriba")
        move_down_act = menu.addAction("Mover Abajo")
        menu.addSeparator()
        delete_act = menu.addAction("Eliminar del setlist")
        
        action = menu.exec(self.setlist_songs_list.mapToGlobal(pos))
        if action == move_up_act:
            self._move_up()
        elif action == move_down_act:
            self._move_down()
        elif action == delete_act:
            self._delete_song_from_setlist()
            
    def _delete_song_from_setlist(self):
        row = self.setlist_songs_list.currentRow()
        if row >= 0:
            self.setlist_songs_list.takeItem(row)
            self.save_btn.setEnabled(True)

    def _save_changes(self):
        if self.current_setlist_index < 0:
            return
        setlists = get_setlists(self.config)
        sl = setlists[self.current_setlist_index]
        new_ids = [self.setlist_songs_list.item(i).data(Qt.UserRole) for i in range(self.setlist_songs_list.count())]
        update_setlist(self.config, self.current_setlist_index, sl["name"], new_ids)
        self.save_btn.setEnabled(False)
        
    def clear_selection(self):
        self.setlist_songs_list.clearSelection()

    def update_icons(self, current_song: str, is_playing: bool, blink: bool, icons_dir: str):
        from stem_widgets import svg_icon
        import os
        
        for i in range(self.setlist_songs_list.count()):
            item = self.setlist_songs_list.item(i)
            song_name = item.data(Qt.UserRole)
            
            if song_name == current_song:
                if is_playing and blink:
                    item.setIcon(svg_icon(os.path.join(icons_dir, "fad-speaker.svg"), "#00FF00"))
                else:
                    item.setIcon(svg_icon(os.path.join(icons_dir, "fad-speaker.svg"), "#0078D7"))
            else:
                item.setIcon(svg_icon(os.path.join(icons_dir, "fad-speaker.svg"), "#444444"))
