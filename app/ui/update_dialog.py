import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextBrowser, QProgressBar, QFrame,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont

from app.ui.theme import current as theme
from app.version import APP_VERSION


class UpdateDialog(QDialog):
    """Dialog that shows release info and manages download flow."""

    def __init__(self, release_info: dict, parent=None):
        super().__init__(parent)
        self._release = release_info
        self._downloading = False
        self._download_thread = None

        self.setWindowTitle("Actualización disponible")
        self.setMinimumWidth(520)
        self.setMinimumHeight(420)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme.BG_PRIMARY};
                color: {theme.TEXT_PRIMARY};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QHBoxLayout()
        icon_label = QLabel("⬆")
        icon_font = QFont(icon_label.font().family(), 32)
        icon_label.setFont(icon_font)
        header.addWidget(icon_label)
        header.addSpacing(12)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel("Nueva versión disponible")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {theme.TEXT_PRIMARY};")
        text_col.addWidget(title)

        subtitle = QLabel(
            f"{APP_VERSION} → {release_info['version']}"
        )
        subtitle.setStyleSheet(f"font-size: 14px; color: {theme.ACCENT_INFO};")
        text_col.addWidget(subtitle)
        header.addLayout(text_col, 1)
        layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {theme.BORDER}; max-height: 1px;")
        layout.addWidget(sep)

        notes_label = QLabel("Notas de la versión:")
        notes_label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {theme.TEXT_SECONDARY};")
        layout.addWidget(notes_label)

        self._notes_browser = QTextBrowser()
        self._notes_browser.setOpenExternalLinks(True)
        self._notes_browser.setHtml(self._format_release_notes(release_info))
        self._notes_browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {theme.BG_SECONDARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BG_TERTIARY};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 8px;
                font-size: 12px;
            }}
        """)
        layout.addWidget(self._notes_browser, 1)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme.BG_TERTIARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                text-align: center;
                color: {theme.TEXT_PRIMARY};
                font-size: 11px;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {theme.ACCENT_PRIMARY};
                border-radius: {theme.BORDER_RADIUS_SM - 1};
            }}
        """)
        layout.addWidget(self._progress_bar)

        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignCenter)
        self._status_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px;")
        self._status_label.setVisible(False)
        layout.addWidget(self._status_label)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._download_btn = QPushButton("Descargar e instalar")
        self._download_btn.setMinimumHeight(34)
        self._download_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_PRIMARY};
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 6px 20px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {theme.ACCENT_PRIMARY_HOVER}; }}
            QPushButton:disabled {{ background-color: {theme.BG_TERTIARY}; color: {theme.TEXT_MUTED}; }}
        """)
        self._download_btn.clicked.connect(self._on_download_clicked)
        btn_row.addWidget(self._download_btn)

        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.setMinimumHeight(34)
        self._cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 6px 16px;
                font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {theme.HOVER_BRIGHTEN}; }}
        """)
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._cancel_btn)

        layout.addLayout(btn_row)

    def _format_release_notes(self, info: dict) -> str:
        body = info.get("release_notes", "") or ""
        body = body.replace("\n", "<br>")
        url = info.get("release_url", "")
        html = f"<p>{body}</p>"
        if url:
            html += f'<p><a href="{url}" style="color: {theme.ACCENT_INFO};">Ver en GitHub →</a></p>'
        return html

    def _on_download_clicked(self):
        self._downloading = True
        self._download_btn.setEnabled(False)
        self._cancel_btn.setText("Cancelar")
        self._progress_bar.setVisible(True)
        self._status_label.setVisible(True)
        self._status_label.setText("Iniciando descarga...")

        from app.services.update_checker import UpdateDownloadThread
        self._download_thread = UpdateDownloadThread(self._release["download_url"])
        self._download_thread.progress.connect(self._on_progress)
        self._download_thread.finished.connect(self._on_download_done)
        self._download_thread.error.connect(self._on_download_error)
        self._download_thread.start()

    def _on_progress(self, current: int, total: int):
        pct = int(current * 100 / total) if total > 0 else 0
        self._progress_bar.setValue(pct)
        mb_current = current / (1024 * 1024)
        mb_total = total / (1024 * 1024)
        self._status_label.setText(f"Descargando... {mb_current:.1f} / {mb_total:.1f} MB")

    def _on_download_done(self, path: str):
        self._status_label.setText("Descarga completada")
        self.accept()

    def _on_download_error(self, error_msg: str):
        self._status_label.setVisible(False)
        self._progress_bar.setVisible(False)
        self._download_btn.setEnabled(True)
        self._download_btn.setText("Reintentar")
        self._cancel_btn.setText("Cerrar")
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.warning(
            self, "Error de descarga",
            f"No se pudo descargar la actualización:\n{error_msg}"
        )

    def get_download_path(self) -> str:
        if self._download_thread:
            return self._download_thread.dest_path()
        return ""

    def reject(self):
        if self._downloading and self._download_thread and self._download_thread.isRunning():
            self._download_thread.quit()
            self._download_thread.wait()
        super().reject()
