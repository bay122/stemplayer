import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QTextEdit
)
from PySide6.QtCore import Qt
from app.ui.svg_icon import svg_icon
from app.ui.theme import current as theme


class ChordProPreviewWidget(QWidget):
    def __init__(self, parent=None, icons_dir=""):
        super().__init__(parent)
        self.icons_dir = icons_dir
        self.parent_window = parent
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        chord_preview_box = QGroupBox("ChordPro Preview")
        chord_preview_box.setObjectName("chordPreviewBox")

        box_layout = QVBoxLayout(chord_preview_box)
        box_layout.setContentsMargins(4, 4, 4, 4)
        box_layout.setSpacing(4)

        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.BG_EDITOR};
                color: {theme.TEXT_EDITOR};
                border: 1px solid {theme.BORDER_ALT};
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 11px;
                padding: 8px;
                line-height: 1.4;
            }}
        """)
        box_layout.addWidget(self.text_display)

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

        main_layout.addWidget(chord_preview_box)

    def load_chopro_content(self, chopro_path: str):
        if not os.path.exists(chopro_path):
            self.text_display.setText("No se encontró archivo de acordes.")
            return

        try:
            from chordpro import Song
            from chordpro.renderers.html import render as render_html

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
        if self.parent_window:
            self.parent_window._show_chordpro_fullscreen()

    def _on_live_clicked(self):
        if self.parent_window:
            self.parent_window.toggle_live_btn.setChecked(True)
            self.parent_window._toggle_live_mode(True)

    def _on_edit_clicked(self):
        if self.parent_window:
            self.parent_window._on_edit_chordpro_clicked()
