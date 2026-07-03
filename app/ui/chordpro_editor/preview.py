import re

from PySide6.QtWidgets import QTextBrowser

from app.ui.theme import current as theme


def _render_chordpro_html(chordpro_text: str) -> str:
    lines = chordpro_text.split('\n')
    html = [
        "<div style='font-family: monospace; font-size: 16px; line-height: 1.4; white-space: pre;'>"
    ]
    for line in lines:
        if not line.strip():
            html.append("<br>")
            continue
        if line.startswith("{"):
            html.append(
                f"<span style='color: {theme.TEXT_SECONDARY};'>{line}</span><br>"
            )
            continue
        parts = re.split(r'(\[[^\]]+\])', line)
        chord_line = ""
        lyric_line = ""
        for i, part in enumerate(parts):
            if part.startswith("[") and part.endswith("]"):
                chord = part[1:-1]
                chord_line += (
                    f"<span style='color: {theme.ACCENT_SUCCESS}; font-weight: bold;'>{chord}</span>"
                )
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
        if f"<span style='color: {theme.ACCENT_SUCCESS}" in chord_line:
            html.append(f"<div style='margin-bottom: -5px;'>{chord_line}</div>")
        html.append(f"<div>{lyric_line}</div>")
    html.append("</div>")
    return "".join(html)


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
        html = _render_chordpro_html(text)
        self.setHtml(html)

    def clear_cache(self) -> None:
        self._last_key = None
        self._last_text = None
