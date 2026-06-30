import os
import re
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget,
    QPlainTextEdit, QTextBrowser, QPushButton, QLabel, QInputDialog
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from app.ui.theme import current as theme


class ChordProParser:
    @staticmethod
    def parse(file_path):
        if not os.path.exists(file_path):
            return {"metadata": {"title": "", "artist": "", "key": ""}, "sections": []}

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        metadata = {"title": "", "artist": "", "key": ""}
        sections = []
        current_section = {"name": "Global", "lines": [], "tag": "c"}

        for line in lines:
            line = line.strip()
            if not line:
                if current_section["lines"]:
                    current_section["lines"].append("")
                continue

            if line.startswith("{title:") or line.startswith("{t:"):
                metadata["title"] = line.split(":", 1)[1].replace("}", "").strip()
                continue
            if line.startswith("{artist:") or line.startswith("{a:"):
                metadata["artist"] = line.split(":", 1)[1].replace("}", "").strip()
                continue
            if line.startswith("{key:") or line.startswith("{k:"):
                metadata["key"] = line.split(":", 1)[1].replace("}", "").strip()
                continue

            sec_match = re.match(r'^\{(start_of_[a-zA-Z0-9_]+|soc|sov|sob)(?::\s*([^}]+))?\}$', line)
            comment_match = re.match(r'^\{c(?:omment)?:\s*([^}]+)\}$', line)

            if sec_match:
                tag = sec_match.group(1)
                name = sec_match.group(2) if sec_match.group(2) else tag.replace("start_of_", "").capitalize()

                if current_section["lines"] and any(current_section["lines"]):
                    sections.append(current_section)

                current_section = {"name": name, "lines": [], "tag": tag}
                continue

            if line.startswith("{end_of_") or line == "{eoc}" or line == "{eov}" or line == "{eob}":
                sections.append(current_section)
                current_section = {"name": "Siguiente", "lines": [], "tag": "c"}
                continue

            if comment_match:
                name = comment_match.group(1)
                if current_section["lines"] and any(current_section["lines"]):
                    sections.append(current_section)
                current_section = {"name": name, "lines": [], "tag": "comment"}
                continue

            current_section["lines"].append(line)

        if current_section["lines"] and any(current_section["lines"]):
            sections.append(current_section)

        for sec in sections:
            while sec["lines"] and not sec["lines"][0].strip():
                sec["lines"].pop(0)
            while sec["lines"] and not sec["lines"][-1].strip():
                sec["lines"].pop()

        return {"metadata": metadata, "sections": sections}

    @staticmethod
    def render_html(chordpro_text):
        """Converts raw chordpro lines to HTML showing chords above lyrics."""
        lines = chordpro_text.split('\n')
        html = ["<div style='font-family: monospace; font-size: 16px; line-height: 1.4; white-space: pre;'>"]

        for line in lines:
            if not line.strip():
                html.append("<br>")
                continue

            if line.startswith("{"):
                html.append(f"<span style='color: #888;'>{line}</span><br>")
                continue

            parts = re.split(r'(\[[^\]]+\])', line)

            chord_line = ""
            lyric_line = ""

            for i, part in enumerate(parts):
                if part.startswith("[") and part.endswith("]"):
                    chord = part[1:-1]
                    chord_line += f"<span style='color: #4CAF50; font-weight: bold;'>{chord}</span>"
                    prev_part = parts[i-1] if i > 0 else ""
                    next_part = parts[i+1] if i+1 < len(parts) else ""
                    prev_cont = bool(prev_part) and not prev_part[-1].isspace()
                    next_cont = bool(next_part) and not next_part[0].isspace()
                    if prev_cont and next_cont:
                        lyric_line += f"<span style='color: rgba(128,128,128,0.35);'>-</span>"
                        lyric_line += f"<span style='visibility: hidden;'>{' ' * max(0, len(chord)-1)}</span>"
                    else:
                        lyric_line += "<span style='visibility: hidden;'>" + ("_" * len(chord)) + "</span>"
                else:
                    safe_part = part.replace('<', '&lt;').replace('>', '&gt;')
                    chord_line += "<span style='visibility: hidden;'>" + safe_part + "</span>"
                    lyric_line += safe_part

            if "<span style='color: #4CAF50" in chord_line:
                html.append(f"<div style='margin-bottom: -5px;'>{chord_line}</div>")
            html.append(f"<div>{lyric_line}</div>")

        html.append("</div>")
        return "".join(html)


class ChordProEditor(QWidget):
    saved = Signal()

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.parsed_data = {"metadata": {}, "sections": []}
        self.current_section_idx = -1

        self._setup_ui()
        self.load_file()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)

        toolbar = QHBoxLayout()
        self.title_lbl = QLabel("ChordPro Editor")
        self.title_lbl.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {theme.TEXT_PRIMARY};")
        toolbar.addWidget(self.title_lbl)

        toolbar.addStretch()

        common_chords = ["C", "G", "D", "A", "E", "Am", "Em", "Dm", "F", "B"]
        for chord in common_chords:
            btn = QPushButton(chord)
            btn.setFixedSize(30, 30)
            btn.setToolTip(f"Insertar acorde {chord}")
            btn.setStyleSheet(f"background-color: {theme.BG_TERTIARY}; color: {theme.TEXT_PRIMARY};")
            btn.clicked.connect(lambda c=False, ch=chord: self.insert_chord(ch))
            toolbar.addWidget(btn)

        toolbar.addStretch()

        self.export_pdf_btn = QPushButton("Exportar PDF")
        self.export_pdf_btn.setToolTip("Exportar la hoja de acordes a PDF")
        self.export_pdf_btn.setStyleSheet(f"background-color: {theme.ACCENT_INFO}; color: {theme.TEXT_PRIMARY}; padding: 5px 15px; font-weight: bold;")
        self.export_pdf_btn.clicked.connect(self.export_pdf)
        toolbar.addWidget(self.export_pdf_btn)

        save_btn = QPushButton("Guardar Archivo")
        save_btn.setToolTip("Guardar el archivo ChordPro en disco")
        save_btn.setStyleSheet(f"background-color: {theme.ACCENT_SUCCESS}; color: {theme.TEXT_PRIMARY}; padding: 5px 15px; font-weight: bold;")
        save_btn.clicked.connect(self.save_file)
        toolbar.addWidget(save_btn)

        main_layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Horizontal)

        self.section_list = QListWidget()
        self.section_list.setMaximumWidth(200)
        self.section_list.currentRowChanged.connect(self._on_section_selected)
        splitter.addWidget(self.section_list)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        editor_splitter = QSplitter(Qt.Vertical)

        self.text_editor = QPlainTextEdit()
        font = QFont("Consolas", 12)
        self.text_editor.setFont(font)
        self.text_editor.textChanged.connect(self._on_text_changed)
        editor_splitter.addWidget(self.text_editor)

        self.preview = QTextBrowser()
        self.preview.setStyleSheet(f"background-color: {theme.BG_SECONDARY}; color: {theme.TEXT_PRIMARY}; padding: 10px;")
        editor_splitter.addWidget(self.preview)

        right_layout.addWidget(editor_splitter)
        splitter.addWidget(right_panel)

        splitter.setSizes([200, 600])
        main_layout.addWidget(splitter)

    def load_file(self):
        self.parsed_data = ChordProParser.parse(self.file_path)
        self.title_lbl.setText(f"Editando: {self.parsed_data['metadata'].get('title', 'Sin título')}")

        self.section_list.clear()
        for i, sec in enumerate(self.parsed_data["sections"]):
            name = sec.get("name", f"Sección {i+1}")
            self.section_list.addItem(name)

        if self.parsed_data["sections"]:
            self.section_list.setCurrentRow(0)

    def _on_section_selected(self, idx):
        if idx < 0 or idx >= len(self.parsed_data["sections"]):
            return

        if self.current_section_idx >= 0 and self.current_section_idx != idx:
            self.parsed_data["sections"][self.current_section_idx]["lines"] = self.text_editor.toPlainText().split('\n')

        self.current_section_idx = idx
        sec = self.parsed_data["sections"][idx]
        content = "\n".join(sec["lines"])

        self.text_editor.blockSignals(True)
        self.text_editor.setPlainText(content)
        self.text_editor.blockSignals(False)
        self._update_preview()

    def _on_text_changed(self):
        self._update_preview()

    def _update_preview(self):
        text = self.text_editor.toPlainText()
        html = ChordProParser.render_html(text)
        self.preview.setHtml(html)

    def insert_chord(self, chord_name):
        cursor = self.text_editor.textCursor()
        cursor.insertText(f"[{chord_name}]")
        self.text_editor.setFocus()

    def save_file(self):
        if self.current_section_idx >= 0:
            self.parsed_data["sections"][self.current_section_idx]["lines"] = self.text_editor.toPlainText().split('\n')

        with open(self.file_path, "w", encoding="utf-8") as f:
            meta = self.parsed_data["metadata"]
            if meta.get("title"):
                f.write(f"{{title: {meta['title']}}}\n")
            if meta.get("artist"):
                f.write(f"{{artist: {meta['artist']}}}\n")
            if meta.get("key"):
                f.write(f"{{key: {meta['key']}}}\n\n")

            for sec in self.parsed_data["sections"]:
                tag = sec.get("tag")
                if tag == "comment":
                    f.write(f"{{c: {sec['name']}}}\n")
                elif tag and tag.startswith("start_of_"):
                    f.write(f"{{{tag}: {sec['name']}}}\n")
                else:
                    f.write(f"{{c: {sec['name']}}}\n")

                for line in sec["lines"]:
                    f.write(line + "\n")

                if tag and tag.startswith("start_of_"):
                    end_tag = tag.replace("start_of_", "end_of_")
                    f.write(f"{{{end_tag}}}\n")

                f.write("\n")

        self.saved.emit()

    def export_pdf(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from PySide6.QtGui import QTextDocument, QPageLayout
        from PySide6.QtCore import QMarginsF
        from PySide6.QtPrintSupport import QPrinter

        if self.current_section_idx >= 0:
            self.parsed_data["sections"][self.current_section_idx]["lines"] = self.text_editor.toPlainText().split('\n')

        default_path = self.file_path.replace(".chopro", ".pdf")
        dest_path, _ = QFileDialog.getSaveFileName(self, "Exportar a PDF", default_path, "PDF Files (*.pdf)")
        if not dest_path:
            return

        html = ["<html><head><meta charset='utf-8'></head><body style='font-family: monospace; font-size: 14px;'>"]

        meta = self.parsed_data.get("metadata", {})
        title = meta.get("title", "Sin Título")
        artist = meta.get("artist", "")
        key = meta.get("key", "")

        html.append(f"<h1 style='text-align: center; margin-bottom: 0;'>{title}</h1>")
        if artist:
            html.append(f"<h2 style='text-align: center; margin-top: 5px; color: #555;'>{artist}</h2>")
        if key:
            html.append(f"<p style='text-align: center;'>Tonalidad: <strong>{key}</strong></p><hr>")

        for sec in self.parsed_data["sections"]:
            html.append(f"<h3 style='margin-top: 20px; color: #333;'>{sec.get('name', '')}</h3>")
            sec_text = "\n".join(sec["lines"])
            sec_html = ChordProParser.render_html(sec_text)

            sec_html = sec_html.replace("color: #4CAF50", "color: #000000; font-weight: bold;")
            sec_html = sec_html.replace("color: #FFFFFF", "color: #000000")
            html.append(sec_html)

        html.append("</body></html>")

        doc = QTextDocument()
        doc.setHtml("".join(html))

        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(dest_path)

        printer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Millimeter)

        try:
            doc.print_(printer)
            QMessageBox.information(self, "Éxito", "PDF exportado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar el PDF:\n{e}")
