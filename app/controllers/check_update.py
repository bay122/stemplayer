import os
import sys
import subprocess
from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QMessageBox

from app.services.update_checker import UpdateCheckThread
from app.ui.update_dialog import UpdateDialog
from app.version import APP_VERSION


class CheckUpdateMixin:
    def _init_updater(self):
        self._update_check_thread = None
        QTimer.singleShot(3000, self._deferred_check)

    def _deferred_check(self):
        settings = QSettings("StemPlayer", "StemPlayer")
        if settings.value("updates/check_on_startup", "true") == "true":
            self._check_for_updates(silent=True)

    def _check_for_updates(self, silent: bool = False):
        self._update_silent = silent
        self._update_check_thread = UpdateCheckThread(self)
        self._update_check_thread.finished.connect(self._on_update_check_done)
        self._update_check_thread.error.connect(self._on_update_check_error)
        self._update_check_thread.start()

    def _on_update_check_done(self, result):
        if result is None:
            if not self._update_silent:
                QMessageBox.information(
                    self, "Buscar actualizaciones",
                    "No se pudo verificar si hay actualizaciones.\n"
                    "Verifica tu conexión a internet."
                )
            return

        if not result["is_newer"]:
            if not self._update_silent:
                QMessageBox.information(
                    self, "Sin actualizaciones",
                    f"Tienes la última versión ({APP_VERSION})."
                )
            return

        dialog = UpdateDialog(result, self)
        if dialog.exec() == UpdateDialog.Accepted:
            self._install_update(dialog.get_download_path())

    def _on_update_check_error(self, error_msg):
        if not self._update_silent:
            QMessageBox.warning(
                self, "Error de actualización",
                f"Ocurrió un error al buscar actualizaciones:\n{error_msg}"
            )

    def _install_update(self, path: str):
        if not path or not os.path.exists(path):
            return
        if sys.platform == "win32":
            subprocess.Popen(
                [path, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                shell=True,
            )
        else:
            try:
                subprocess.Popen(["pkexec", "dpkg", "-i", path])
            except FileNotFoundError:
                QMessageBox.information(
                    self, "Actualización descargada",
                    f"El instalador se ha descargado en:\n{path}\n\n"
                    "Para instalarlo, ejecuta en una terminal:\n"
                    f"  sudo dpkg -i {path}"
                )
                return
        sys.exit(0)
