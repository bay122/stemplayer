"""Gestión del ciclo de vida de hilos Qt - Previene errores QThread destroyed while running."""

from PySide6.QtCore import QThread

from app.audio.stem_loader import StemLoaderThread
from app.audio.pitch_tempo import PitchTempoThread
from app.audio.playback import PlaybackThread
from app.audio.exporter import ExportThread
from app.services.chord_analysis import ChordAnalysisThread
from app.services.openrouter_service import OpenRouterLLMThread


class ThreadManager:
    """Centraliza la creación, seguimiento y limpieza de hilos."""

    def __init__(self):
        self.playback_thread: PlaybackThread | None = None
        self.loader_thread: StemLoaderThread | None = None
        self.pitch_tempo_thread: PitchTempoThread | None = None
        self.export_thread: ExportThread | None = None
        self.chord_analysis_thread: ChordAnalysisThread | None = None
        self.openrouter_thread: OpenRouterLLMThread | None = None
        self.preloader_thread: StemLoaderThread | None = None

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------
    @staticmethod
    def _request_stop(thread):
        """Pide al hilo que termine (si tiene método cancel/stop)."""
        if thread is None:
            return
        if hasattr(thread, 'cancel'):
            thread.cancel()
        if hasattr(thread, 'stop'):
            thread.stop()

    @staticmethod
    def _wait_forced(thread, timeout_ms: int = 3000) -> bool:
        """Espera a que un hilo termine. Si timeout, fuerza terminate()."""
        if thread is None:
            return True
        if not thread.isRunning():
            return True
        thread.quit()
        if thread.wait(timeout_ms):
            return True
        thread.terminate()
        thread.wait(1000)
        return thread.isRunning()

    def _safe_stop(self, attr_name: str):
        """Detiene un hilo y pone su atributo en None de forma segura."""
        thread = getattr(self, attr_name, None)
        if thread is None:
            return
        try:
            self._request_stop(thread)
            self._wait_forced(thread)
        except RuntimeError:
            pass
        setattr(self, attr_name, None)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def safe_replace(self, attr_name: str, new_thread):
        """Reemplaza un hilo de forma segura: detiene el anterior, asigna el nuevo."""
        self._safe_stop(attr_name)
        setattr(self, attr_name, new_thread)

    def safe_start(self, thread) -> bool:
        if thread is None:
            return False
        if thread.isRunning():
            return False
        thread.start()
        return True

    def stop_playback(self):
        self._safe_stop('playback_thread')

    def cancel_all(self):
        for attr in ['preloader_thread', 'loader_thread', 'pitch_tempo_thread',
                      'export_thread', 'chord_analysis_thread', 'openrouter_thread']:
            self._safe_stop(attr)

    def cleanup_all(self):
        """Detiene TODOS los hilos (incluyendo playback). Úselo en closeEvent."""
        for attr in ['playback_thread', 'preloader_thread', 'loader_thread',
                      'pitch_tempo_thread', 'export_thread',
                      'chord_analysis_thread', 'openrouter_thread']:
            self._safe_stop(attr)
