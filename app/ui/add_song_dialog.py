import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QPushButton, QLabel, QListWidgetItem
)
from PySide6.QtCore import Qt
from app.ui.svg_icon import svg_icon


class AddSongToSetlistDialog(QDialog):
    def __init__(self, songs: list, existing_songs: list, icons_dir: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Añadir canción al setlist")
        self.setMinimumSize(400, 500)

        self.all_songs = []
        for s in songs:
            if s["name"] not in existing_songs:
                self.all_songs.append(s)

        self.selected_song = None
        self._build_ui(icons_dir)
        self._filter_list()

    def _build_ui(self, icons_dir: str):
        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        search_icon = QLabel()
        search_icon.setPixmap(svg_icon(os.path.join(icons_dir, "fad-search.svg")).pixmap(16, 16))
        search_layout.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Buscar por título o artista...")
        self.search_input.textChanged.connect(self._filter_list)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        self.song_list = QListWidget()
        self.song_list.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.song_list)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.add_btn = QPushButton("Añadir")
        self.add_btn.setDefault(True)
        self.add_btn.clicked.connect(self._on_add_clicked)
        btn_layout.addWidget(self.add_btn)

        layout.addLayout(btn_layout)

    def _filter_list(self):
        query = self.search_input.text().lower()
        self.song_list.clear()

        for s in self.all_songs:
            if query in s["name"].lower() or query in s["artist"].lower():
                display_text = s["name"]
                if s.get("duration"):
                    display_text = f"{display_text} [{s['duration']}]"

                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, s["name"])
                self.song_list.addItem(item)

    def _on_item_double_clicked(self, item):
        self.selected_song = item.data(Qt.UserRole)
        self.accept()

    def _on_add_clicked(self):
        item = self.song_list.currentItem()
        if item:
            self.selected_song = item.data(Qt.UserRole)
            self.accept()
        else:
            self.reject()
