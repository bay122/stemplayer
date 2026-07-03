import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont

from app.ui.theme import current as theme

_CHORD_RE = re.compile(r"\[([^\]]+)\]")
_DIRECTIVE_RE = re.compile(r"\{[a-zA-Z][^}]*\}")


class ChordProHighlighter(QSyntaxHighlighter):
    def __init__(self, document, scale_provider):
        super().__init__(document)
        self._scale_provider = scale_provider

        self._directive_fmt = QTextCharFormat()
        self._directive_fmt.setForeground(QColor(theme.TEXT_MUTED))
        self._directive_fmt.setFontItalic(True)

        self._chord_fmt = QTextCharFormat()
        self._chord_fmt.setForeground(QColor(theme.ACCENT_SUCCESS))
        chord_font = QFont()
        chord_font.setBold(True)
        self._chord_fmt.setFont(chord_font)

        self._chord_off_fmt = QTextCharFormat()
        self._chord_off_fmt.setForeground(QColor(theme.TEXT_PRIMARY))
        self._chord_off_fmt.setBackground(QColor(theme.ACCENT_WARNING))
        from PySide6.QtGui import QFont as _QF
        self._chord_off_fmt.setFontWeight(_QF.Bold)

    def highlightBlock(self, text):
        for m in _DIRECTIVE_RE.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._directive_fmt)
        for m in _CHORD_RE.finditer(text):
            chord = m.group(1)
            diatonic = self._scale_provider()
            if diatonic and chord not in diatonic:
                fmt = self._chord_off_fmt
            else:
                fmt = self._chord_fmt
            self.setFormat(m.start(), m.end() - m.start(), fmt)
