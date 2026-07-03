from app.ui.chordpro_editor.constants import CHORD_POSITIONS


def render_chord_svg(chord_name: str, size: int = 80) -> str:
    positions = CHORD_POSITIONS.get(chord_name)
    if not positions:
        return (
            f'<svg width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg">'
            f'<text x="50%" y="50%" text-anchor="middle" dy=".3em" '
            f'font-family="sans-serif" font-size="11" fill="#888">—</text>'
            f'</svg>'
        )
    # Find fret range
    frets = [f for _, f in positions]
    min_fret = min(frets)
    max_fret = max(frets)
    # Always show 4 frets
    fret_count = 4
    start_fret = min_fret
    # Strings shown 1..6 (low to high). We use string indices 0..5
    # drawn left-to-right as 0..5. Finger positions are (string, fret)
    # with string 0 = low E (leftmost in diagram).
    pad = 8
    usable_w = size - 2 * pad
    usable_h = size - 2 * pad - 12
    string_step = usable_w / 5
    fret_step = usable_h / fret_count
    dot_r = 4

    parts = [
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg" style="background:#1e1e1e">',
        f'<text x="{size/2}" y="11" text-anchor="middle" font-size="10" '
        f'font-family="sans-serif" fill="#fff">{chord_name}</text>',
    ]
    # Frets
    for i in range(fret_count + 1):
        y = pad + 12 + i * fret_step
        parts.append(
            f'<line x1="{pad}" y1="{y:.1f}" x2="{pad + 5 * string_step:.1f}" y2="{y:.1f}" '
            f'stroke="#888" stroke-width="1"/>'
        )
    # Strings
    for i in range(6):
        x = pad + i * string_step
        parts.append(
            f'<line x1="{x:.1f}" y1="{pad + 12}" x2="{x:.1f}" y2="{pad + 12 + fret_count * fret_step:.1f}" '
            f'stroke="#888" stroke-width="1"/>'
        )
    # Dots
    for string, fret in positions:
        if fret < start_fret or fret >= start_fret + fret_count:
            continue
        x = pad + string * string_step
        y = pad + 12 + (fret - start_fret + 0.5) * fret_step
        parts.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{dot_r}" fill="#7CFC00"/>'
        )
    # Top nut if min_fret == 0
    if start_fret == 0:
        parts.append(
            f'<rect x="{pad}" y="{pad + 12 - 3}" width="{5 * string_step:.1f}" height="3" fill="#fff"/>'
        )
    parts.append('</svg>')
    return "".join(parts)
