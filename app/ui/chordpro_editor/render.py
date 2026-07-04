"""Shared HTML rendering for chordpro sections.

The same renderer is used by:
- The editor's preview (app.ui.chordpro_editor.preview)
- The editor's PDF export (app.ui.chordpro_editor.editor_window)
- The live karaoke display (app.ui.live_display)

The function is intentionally a pure function that takes a list of
chordpro lines and returns an HTML fragment. The caller is responsible
for the outer wrapper (font size, alignment, etc.).
"""
import re

from app.ui.theme import current as theme


_DIRECTIVE_RE = re.compile(r"\{[a-zA-Z][^}]*\}")
_CHORD_RE = re.compile(r"\[([^\]]+)\]")
_CHORD_DIRECTIVE_RE = re.compile(r"\{chord:\s*([^}]+)\}")
# Non-capturing group: re.split keeps the full match (with brackets) in
# the result when using non-capturing groups. With a capturing group,
# Python's re.split returns only the captured group without brackets.
_CHORD_SPLIT_RE = re.compile(r"(\[[^\]]+\])")


def _split_chord_segments(normalized: str) -> list:
    """Split a normalized line into [text, chord, text, chord, ...] tokens.

    Returns a list of tuples (kind, value) where kind is 'chord' or 'lyric'.
    Empty segments are dropped.
    """
    out = []
    for seg in _CHORD_SPLIT_RE.split(normalized):
        if not seg:
            continue
        if seg.startswith("[") and seg.endswith("]"):
            out.append(("chord", seg[1:-1]))
        else:
            out.append(("lyric", seg))
    return out


def _align_chords(normalized: str) -> tuple:
    """Align chord tokens with their following lyrics in two parallel strings.

    For "{chord: Cm7}Uno, {chord: Cm}dos, ..." returns:
      chord_row = "Cm7   Cm  C  Cm  C   F "
      lyric_row = "  Uno dos uno dos tres cuatro"

    The convention: the first character of the word that follows a
    chord is placed UNDER the last character of that chord. So a chord
    of length N reserves N characters in the chord row and N-1
    characters of leading whitespace in the lyric row (so the lyric
    starts at the same column as the chord's last character).
    """
    segments = _split_chord_segments(normalized)
    chord_chars = []
    lyric_chars = []
    for kind, value in segments:
        if kind == "chord":
            chord_chars.append(value)
            lyric_chars.append(" " * max(0, len(value) - 1))
        else:
            chord_chars.append(" " * len(value))
            lyric_chars.append(value)
    return "".join(chord_chars), "".join(lyric_chars)


def _html_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_aligned_line(chord_row: str, lyric_row: str,
                         chord_color: str, chord_fs: int,
                         font_size: int) -> str:
    """Render one aligned chord-over-lyric pair as HTML.

    The chord row is wrapped in a <pre>-like block with a transparent
    baseline (because each chord is preceded by the same number of spaces
    as the lyric row beneath it). Trailing spaces are preserved so the
    alignment holds.
    """
    if chord_row.strip():
        # Build the chord row with bold spans for the actual chord text;
        # spaces stay as plain text but the line gets a "white-space: pre"
        # so they are not collapsed.
        chord_html = []
        i = 0
        n = len(chord_row)
        while i < n:
            ch = chord_row[i]
            if ch == " ":
                chord_html.append("&nbsp;")
                i += 1
                continue
            # find the run of non-space
            j = i
            while j < n and chord_row[j] != " ":
                j += 1
            token = chord_row[i:j]
            chord_html.append(
                f"<span style='color: {chord_color}; font-weight: bold; "
                f"font-size: {chord_fs}px;'>{_html_escape(token)}</span>"
            )
            i = j
        chord_line = "".join(chord_html)
        chord_block = (
            f"<div style='font-family: monospace; font-size: {chord_fs}px; "
            f"line-height: 1.15; white-space: pre; margin: 0;'>"
            f"{chord_line}</div>"
        )
    else:
        chord_block = ""
    lyric_block = (
        f"<div style='font-family: monospace; font-size: {font_size}px; "
        f"line-height: 1.5; white-space: pre-wrap; margin: 0 0 "
        f"{font_size * 0.4:.0f}px 0;'>{_html_escape(lyric_row)}</div>"
    )
    return chord_block + lyric_block


def render_lines_html(lines: list, font_size: int = 18,
                      align: str = "left",
                      chord_color: str | None = None,
                      opacity: float = 1.0) -> str:
    """Render a list of chordpro lines as HTML with chord-over-lyric layout.

    Supports two formats:
    - "[C]Hello [G]world" — chord brackets on a dedicated line (or
      inline at the start of a line), with lyrics on a separate line.
    - "{chord: Cm7}Uno, {chord: Cm}dos, ..." — inline chord directives
      embedded in the lyric line. The renderer extracts the chords and
      builds a parallel chord row aligned to the lyrics.

    Args:
        lines: list of chordpro lines.
        font_size: base font size in pixels for lyrics.
        align: "left" | "center" | "right" for the lyrics block.
        chord_color: override for the chord text color (defaults to theme accent).
        opacity: 0.0 to 1.0 opacity of the whole block.

    Returns:
        HTML fragment (no outer <html>/<body>).
    """
    chord_color = chord_color or theme.ACCENT_SUCCESS
    chord_fs = font_size + 2
    opacity_attr = f" opacity: {opacity};" if opacity < 1.0 else ""
    parts = [
        f"<div style='font-family: monospace; font-size: {font_size}px; "
        f"text-align: {align}; line-height: 1.4;{opacity_attr}'>"
    ]

    for line in lines:
        if line is None:
            continue
        stripped = line.strip()
        if not stripped:
            parts.append(f"<div style='height: {font_size * 0.6:.0f}px;'>&nbsp;</div>")
            continue

        if _DIRECTIVE_RE.match(stripped) and not _CHORD_DIRECTIVE_RE.match(stripped):
            # Non-chord directive ({title:}, {start_of_verse}, etc.) shown italic.
            parts.append(
                f"<div style='color: {theme.TEXT_SECONDARY}; "
                f"font-style: italic; margin: 6px 0 2px 0;'>"
                f"<em>{_html_escape(stripped)}</em></div>"
            )
            continue

        # Normalize {chord: X} -> [X] then build aligned parallel rows.
        normalized = _CHORD_DIRECTIVE_RE.sub(r"[\1]", line)
        chord_row, lyric_row = _align_chords(normalized)
        if not chord_row.strip() and not lyric_row.strip():
            continue
        parts.append(_render_aligned_line(
            chord_row, lyric_row, chord_color, chord_fs, font_size
        ))

    parts.append("</div>")
    return "".join(parts)


def render_section_html(name: str, lines: list, font_size: int = 18) -> str:
    """Render a section with its name as a heading, then the lines."""
    heading = (
        f"<h3 style='margin: 16px 0 4px 0; color: {theme.TEXT_PRIMARY}; "
        f"font-family: sans-serif; font-size: {font_size + 4}px;'>"
        f"{_html_escape(name)}</h3>"
    )
    body = render_lines_html(lines, font_size=font_size)
    return heading + body
