import re

from PySide6.QtWidgets import QTextBrowser

from app.ui.chordpro_editor.render import render_lines_html
from app.ui.theme import current as theme


def _render_chordpro_html(chordpro_text: str) -> str:
    """Render chordpro text using the same layout as the live display.

    Kept as a thin wrapper for backwards compatibility with code that
    imports _render_chordpro_html directly.
    """
    lines = chordpro_text.split('\n')
    return render_lines_html(lines, font_size=16)


class ChordProPreview(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {theme.BG_SECONDARY}; "
            f"color: {theme.TEXT_PRIMARY}; padding: 10px;"
        )
        self._last_key = None
        self._last_text = None

    def set_chordpro_text(self, text: str, key: str = "") -> None:
        if text == self._last_text and key == self._last_key:
            return
        self._last_text = text
        self._last_key = key
        html = render_lines_html(text.split('\n'), font_size=16)
        self.setHtml(html)

    def clear_cache(self) -> None:
        self._last_key = None
        self._last_text = None
