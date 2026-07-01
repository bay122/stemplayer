"""Mixin helper para sincronizar widgets del layout deck."""

from PySide6.QtWidgets import QLabel, QProgressBar


class DeckStatusMixin:
    """Provee métodos _sync_deck_* para mantener sincronizado el status/progress
    del layout deck con el estado de la app."""

    def _sync_deck_status(self, text: str):
        if getattr(self, 'deck_layout', None) is None:
            return
        try:
            self.deck_layout.set_deck_status_text(text)
        except Exception:
            pass

    def _sync_deck_status_visible(self, visible: bool):
        if getattr(self, 'deck_layout', None) is None:
            return
        try:
            self.deck_layout.set_deck_status_visible(visible)
        except Exception:
            pass

    def _sync_deck_progress(self, value: int, visible: bool = True):
        if getattr(self, 'deck_layout', None) is None:
            return
        try:
            self.deck_layout.set_deck_progress_value(value, visible)
        except Exception:
            pass

    def _sync_deck_bg_status(self, text: str, visible: bool = True):
        if getattr(self, 'deck_layout', None) is None:
            return
        try:
            self.deck_layout.set_deck_bg_status(text, visible)
        except Exception:
            pass
