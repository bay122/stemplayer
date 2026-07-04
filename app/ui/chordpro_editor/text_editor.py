import re

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QPlainTextEdit

from app.ui.chordpro_editor.chord_chart import render_chord_svg
from app.ui.chordpro_editor.constants import chord_in_scale
from app.ui.chordpro_editor.highlight import ChordProHighlighter
from app.ui.theme import current as theme

_CHORD_RE = re.compile(r"\[([^\]]+)\]")

# Use theme accent warning as the indicator that a chord is "off-scale".
ACCENT_WARNING_FALLBACK = "#FFA500"


def _warn_color():
    return getattr(theme, "ACCENT_WARNING", ACCENT_WARNING_FALLBACK)


class ChordProTextEditor(QPlainTextEdit):
    chordHovered = Signal(str)
    chordLeft = Signal()

    def __init__(self, scale_provider=None, parent=None):
        super().__init__(parent)
        self._scale_provider = scale_provider or (lambda: [])
        self.setFont(QFont("Consolas", 18))
        self.setStyleSheet("QPlainTextEdit { font-family: Consolas; font-size: 18px; }")
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setTabChangesFocus(False)
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self._highlighter = ChordProHighlighter(self.document(), self._scale_provider)
        self._hover_chord = None
        self.cursorPositionChanged.connect(self._on_cursor_moved)

    def set_scale_provider(self, scale_provider):
        self._scale_provider = scale_provider
        self._highlighter._scale_provider = scale_provider
        self._highlighter.rehighlight()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Tab:
            cursor = self.textCursor()
            cursor.insertText("    ")
            return
        super().keyPressEvent(event)

    def _on_cursor_moved(self):
        chord = self.get_chord_at_cursor()
        if chord == self._hover_chord:
            return
        self._hover_chord = chord
        if chord:
            off = not chord_in_scale(chord, "C")  # scale is re-evaluated by highlight; tooltip just renders the diagram
            svg = render_chord_svg(chord)
            html = (
                f'<div style="background:#1e1e1e; padding:6px;">{svg}'
                f'</div>'
            )
            QTimer.singleShot(0, lambda c=chord, h=html: self._show_tooltip(c, h))
            self.chordHovered.emit(chord)
        else:
            self.chordLeft.emit()
            QTimer.singleShot(0, self._hide_tooltip)

    def _show_tooltip(self, chord, html):
        cursor = self.cursorRect()
        if cursor.isNull():
            return
        pos = self.mapToGlobal(cursor.bottomRight())
        self.setToolTip(html)
        # Qt shows tooltip on hover; force-show at cursor
        from PySide6.QtWidgets import QToolTip
        QToolTip.showText(pos, html, self)

    def _hide_tooltip(self):
        from PySide6.QtWidgets import QToolTip
        QToolTip.hideText()

    def get_chord_at_cursor(self) -> str | None:
        cursor = self.textCursor()
        block_text = cursor.block().text()
        pos = cursor.positionInBlock()
        # Find the last chord whose end is <= pos
        last = None
        for m in _CHORD_RE.finditer(block_text):
            if m.end() <= pos + 1:
                last = m.group(1)
            else:
                break
        return last
