import os

from PySide6.QtCore import Qt, Signal, QMarginsF
from PySide6.QtGui import QAction, QKeySequence, QTextDocument, QPageLayout, QFont
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
)

from app.ui.chordpro_editor.model import ValidationIssue
from app.ui.chordpro_editor.parser import parse, serialize, validate
from app.ui.chordpro_editor.view import ChordProEditorView
from app.ui.chordpro_editor.sync_bridge import SyncBridge
from app.ui.theme import current as theme


class ChordProEditorWindow(QMainWindow):
    saved = Signal()
    play_requested = Signal(str)

    def __init__(self, chopro_path: str, sync_path: str | None = None,
                 main_window=None, parent=None):
        super().__init__(parent)
        self._chopro_path = chopro_path
        self._main_window = main_window
        self.setWindowTitle(f"ChordPro Editor - {os.path.basename(chopro_path)}")
        self.resize(1100, 720)

        self._view = ChordProEditorView(self)
        self.setCentralWidget(self._view)
        self._view.play_requested = self.play_requested  # forward signal

        doc = parse(chopro_path)
        self._view.set_document(doc)
        self._issues = validate(doc)
        self._update_status()

        # Sync bridge
        self._sync = SyncBridge(self._view.section_panel(), main_window, sync_path)
        self._sync.start()

        # Menus
        self._build_menu()
        self._view.dirtyChanged.connect(self._update_title)
        self._view.undo_stack().canUndoChanged.connect(self._update_actions)
        self._view.undo_stack().canRedoChanged.connect(self._update_actions)
        self._update_actions()
        self._update_title()

    def _build_menu(self):
        m_file = self.menuBar().addMenu("&Archivo")
        save_action = QAction("&Guardar", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save)
        m_file.addAction(save_action)
        export_action = QAction("&Exportar PDF...", self)
        export_action.triggered.connect(self.export_pdf)
        m_file.addAction(export_action)
        m_file.addSeparator()
        m_file.addAction("&Cerrar", self.close)

        m_edit = self.menuBar().addMenu("&Edición")
        self._undo_action = QAction("&Deshacer", self)
        self._undo_action.setShortcut(QKeySequence.Undo)
        self._undo_action.triggered.connect(self._view.undo_stack().undo)
        m_edit.addAction(self._undo_action)
        self._redo_action = QAction("&Rehacer", self)
        self._redo_action.setShortcut(QKeySequence.Redo)
        self._redo_action.triggered.connect(self._view.undo_stack().redo)
        m_edit.addAction(self._redo_action)

    def _update_actions(self):
        s = self._view.undo_stack()
        self._undo_action.setEnabled(s.canUndo())
        self._redo_action.setEnabled(s.canRedo())

    def _update_title(self):
        base = f"ChordPro Editor - {os.path.basename(self._chopro_path)}"
        if self._view.is_dirty():
            base += " *"
        self.setWindowTitle(base)

    def _update_status(self):
        n_warn = sum(1 for i in self._issues if i.level == "warning")
        n_sections = len(self._view.document().sections) if self._view.document() else 0
        msg = f"{n_sections} secciones"
        if n_warn:
            msg += f" · {n_warn} issues"
        self.statusBar().showMessage(msg)

    def closeEvent(self, event):
        if self._view.is_dirty():
            reply = QMessageBox.question(
                self,
                "Cambios sin guardar",
                "Hay cambios sin guardar. ¿Cerrar de todos modos?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        self._sync.stop()
        super().closeEvent(event)

    def save(self):
        if self._view.document() is None:
            return
        text = serialize(self._view.document())
        try:
            with open(self._chopro_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")
            return
        self._view._set_dirty(False)
        self._update_title()
        self.saved.emit()

    def export_pdf(self):
        from app.ui.chordpro_editor.render import render_section_html
        if self._view.document() is None:
            return
        default_path = self._chopro_path.replace(".chopro", ".pdf")
        dest_path, _ = QFileDialog.getSaveFileName(self, "Exportar a PDF", default_path, "PDF Files (*.pdf)")
        if not dest_path:
            return

        # Use "pt" for font sizes so QPrinter interprets them correctly
        # at print resolution. Using "px" makes the body text microscopic
        # because QTextDocument's CSS-pixel-to-device-pixel conversion
        # treats the high-resolution printer DPI as a multiplier.
        body_chunks = []
        for sec in self._view.document().sections:
            sec_html = render_section_html(sec.name, sec.lines, font_size=14, font_unit="pt")
            sec_html = sec_html.replace(
                f"color: {theme.ACCENT_SUCCESS}", "color: #000000; font-weight: bold;"
            )
            body_chunks.append(sec_html)

        meta = self._view.document().metadata
        html = [
            "<html><head><meta charset='utf-8'></head><body style='font-family: sans-serif; font-size: 14pt;'>",
            f"<h1 style='text-align: center; margin-bottom: 0; font-size: 18pt;'>{meta.title or 'Sin Título'}</h1>",
        ]
        if meta.artist:
            html.append(f"<h2 style='text-align: center; margin-top: 6px; color: #555; font-size: 14pt;'>{meta.artist}</h2>")
        if meta.key:
            html.append(f"<p style='text-align: center; font-size: 16pt;'>Tonalidad: <strong>{meta.key}</strong></p><hr>")
        html.extend(body_chunks)
        html.append("</body></html>")

        doc = QTextDocument()
        # Set a sane default font on the document. Without this, the
        # document may fall back to a tiny default that even the
        # <body> font-size can't override in some Qt versions.
        doc.setDefaultFont(QFont("sans-serif", 14))
        doc.setHtml("".join(html))
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(dest_path)
        printer.setPageMargins(QMarginsF(5, 5, 5, 5), QPageLayout.Millimeter)
        try:
            doc.print_(printer)
            QMessageBox.information(self, "Éxito", "PDF exportado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar el PDF:\n{e}")
