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


def render_lines_html(lines: list, font_size: int = 18,
                      align: str = "left",
                      chord_color: str | None = None,
                      opacity: float = 1.0) -> str:
    """Render a list of chordpro lines as HTML with chord-over-lyric layout.

    Args:
        lines: list of chordpro lines (without [chord] / {start_of_X} wrappers).
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

        if _DIRECTIVE_RE.match(stripped):
            parts.append(
                f"<div style='color: {theme.TEXT_SECONDARY}; "
                f"font-style: italic; margin: 6px 0 2px 0;'>"
                f"<em>{stripped}</em></div>"
            )
            continue

        normalized = _CHORD_DIRECTIVE_RE.sub(r"[\1]", line)
        segments = _CHORD_RE.split(normalized)
        chord_row = ""
        lyric_row = ""

        for i, seg in enumerate(segments):
            if not seg:
                continue
            if seg.startswith("[") and seg.endswith("]"):
                chord = seg[1:-1]
                chord_row += (
                    f"<span style='color: {chord_color}; font-weight: bold; "
                    f"font-size: {chord_fs}px;'>{chord}</span>"
                )
                prev_seg = segments[i-1] if i > 0 else ""
                next_seg = segments[i+1] if i+1 < len(segments) else ""
                prev_cont = bool(prev_seg) and not prev_seg[-1].isspace()
                next_cont = bool(next_seg) and not next_seg[0].isspace()
                if prev_cont and next_cont:
                    lyric_row += f"<span style='color: rgba(128,128,128,0.4);'>-</span>"
                    lyric_row += f"<span style='color: transparent;'>{' ' * max(0, len(chord)-1)}</span>"
                else:
                    lyric_row += f"<span style='color: transparent;'>{chord}</span>"
            else:
                safe = seg.replace('<', '&lt;').replace('>', '&gt;')
                chord_row += f"<span style='color: transparent;'>{safe}</span>"
                lyric_row += safe

        has_chords = chord_color in chord_row
        if has_chords:
            parts.append(
                f"<div style='line-height: 1.15; white-space: pre-wrap; "
                f"min-height: {chord_fs}px;'>{chord_row}</div>"
            )
        parts.append(
            f"<div style='line-height: 1.5; white-space: pre-wrap; "
            f"margin-bottom: {font_size * 0.4:.0f}px;'>{lyric_row}</div>"
        )

    parts.append("</div>")
    return "".join(parts)


def render_section_html(name: str, lines: list, font_size: int = 18) -> str:
    """Render a section with its name as a heading, then the lines."""
    heading = (
        f"<h3 style='margin: 16px 0 4px 0; color: {theme.TEXT_PRIMARY}; "
        f"font-family: sans-serif; font-size: {font_size + 2}px;'>"
        f"{name}</h3>"
    )
    body = render_lines_html(lines, font_size=font_size)
    return heading + body
