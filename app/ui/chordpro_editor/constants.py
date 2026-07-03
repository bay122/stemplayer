NOTE_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
CHORD_TYPES = ["", "m", "7", "maj7", "m7", "sus2", "sus4", "dim", "aug", "6", "m6", "9", "add9"]
SCALE_INTERVALS = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
}
SECTION_TYPES = ["verse", "chorus", "bridge", "intro", "outro", "pre-chorus", "comment", "other"]
SECTION_LABELS = {
    "verse": "Verse",
    "chorus": "Chorus",
    "bridge": "Bridge",
    "intro": "Intro",
    "outro": "Outro",
    "pre-chorus": "Pre-Chorus",
    "comment": "Comment",
    "other": "Other",
}

# Flat-preferring roots (relative to NOTE_NAMES_SHARP indices)
_FLAT_ROOTS = {5, 10, 1, 8, 3}  # F, Bb, Db, Ab, Eb

CHORD_POSITIONS = {
    "C":  [(0, 0), (2, 1), (1, 2), (0, 3)],
    "G":  [(2, 0), (3, 1), (0, 2), (0, 3), (0, 4), (3, 5)],
    "D":  [(3, 0), (2, 1), (0, 2), (0, 3), (0, 4)],
    "A":  [(0, 0), (1, 1), (2, 2), (2, 3)],
    "E":  [(0, 0), (0, 1), (1, 2), (2, 3), (2, 4), (0, 5)],
    "F":  [(1, 0), (1, 1), (2, 2), (3, 3), (3, 4), (1, 5)],
    "Am": [(0, 0), (1, 1), (2, 2), (2, 3)],
    "Em": [(0, 0), (0, 1), (0, 2), (2, 3), (2, 4), (0, 5)],
    "Dm": [(3, 0), (2, 1), (0, 2), (0, 3), (0, 4)],
    "Bm": [(0, 0), (1, 1), (2, 2), (3, 3), (3, 4), (1, 5)],
    "Bm7": [(0, 0), (1, 1), (2, 2), (0, 3)],
    "C7":  [(0, 0), (2, 1), (1, 2), (3, 3)],
    "G7":  [(2, 0), (3, 1), (0, 2), (0, 3), (0, 4), (1, 5)],
    "D7":  [(3, 0), (2, 1), (0, 2), (0, 3), (0, 4), (3, 5)],
    "A7":  [(0, 0), (1, 1), (2, 2), (0, 3)],
    "E7":  [(0, 0), (0, 1), (1, 2), (0, 3), (2, 4), (0, 5)],
    "Am7": [(0, 0), (1, 1), (2, 2), (0, 3)],
    "Em7": [(0, 0), (0, 1), (0, 2), (0, 3), (2, 4), (0, 5)],
    "Dm7": [(3, 0), (2, 1), (0, 2), (0, 3), (0, 4), (1, 5)],
    "Fmaj7": [(1, 0), (1, 1), (2, 2), (3, 3), (3, 4), (1, 5)],
    "Cmaj7": [(0, 0), (2, 1), (1, 2), (0, 3), (0, 4), (0, 5)],
    "Gmaj7": [(2, 0), (3, 1), (0, 2), (0, 3), (0, 4), (2, 5)],
    "Dmaj7": [(3, 0), (2, 1), (0, 2), (0, 3), (0, 4), (2, 5)],
    "Csus2": [(0, 0), (2, 1), (3, 2), (0, 3)],
    "Csus4": [(0, 0), (2, 1), (3, 2), (1, 3)],
    "Dsus2": [(3, 0), (2, 1), (0, 2), (0, 3), (0, 4), (0, 5)],
    "Dsus4": [(3, 0), (2, 1), (0, 2), (0, 3), (0, 4), (3, 5)],
    "Asus2": [(0, 0), (1, 1), (2, 2), (2, 3)],
    "Asus4": [(0, 0), (1, 1), (2, 2), (3, 3)],
    "Esus4": [(0, 0), (0, 1), (1, 2), (2, 3), (2, 4), (0, 5)],
}

_TYPE_ORDER = ["", "maj7", "m7", "add9", "sus2", "sus4", "m6", "dim", "aug", "m", "7", "6", "9"]


def _parse_root(name: str):
    """Returns (root, rest) or (0, name) on failure."""
    if not name:
        return 0, name
    head = name[0].upper()
    if head not in "ABCDEFG":
        return 0, name
    root = NOTE_NAMES_SHARP.index(head) if head in NOTE_NAMES_SHARP else 0
    rest = name[1:]
    if rest and rest[0] in ("#", "b"):
        if rest[0] == "#":
            root = (root + 1) % 12
        else:
            root = (root - 1) % 12
        rest = rest[1:]
    return root, rest


def parse_chord_name(name: str):
    """Parse a chord name like 'F#m7/A' into (root_pc, type, bass_pc).

    Returns (0, '', None) on parse failure.
    """
    if not name:
        return 0, "", None
    name = name.strip()
    bass = None
    if "/" in name:
        name, bass_part = name.split("/", 1)
        bass_root, _ = _parse_root(bass_part)
        bass = bass_root
    root, rest = _parse_root(name)
    ctype = ""
    for t in _TYPE_ORDER:
        if t and rest.startswith(t):
            ctype = t
            rest = rest[len(t):]
            break
    if rest.strip():
        return 0, "", None
    return root, ctype, bass


def format_chord(root: int, ctype: str = "", bass: int | None = None, use_flats: bool = False) -> str:
    names = NOTE_NAMES_FLAT if use_flats else NOTE_NAMES_SHARP
    result = names[root % 12]
    if ctype:
        result += ctype
    if bass is not None:
        result += "/" + names[bass % 12]
    return result


def detect_key_preference(root: int) -> bool:
    """Return True if this root prefers flat notation, False for sharps."""
    return root % 12 in _FLAT_ROOTS


def transpose_chord_name(name: str, semitones: int, use_flats: bool | None = None) -> str:
    root, ctype, bass = parse_chord_name(name)
    if ctype == "" and bass is None and root == 0 and name not in ("C", "C#", "Db"):
        return name
    if use_flats is None:
        head = name.strip()
        if len(head) >= 2 and head[1] == "b":
            use_flats = True
        elif len(head) >= 2 and head[1] == "#":
            use_flats = False
        else:
            new_root_preview = (root + semitones) % 12
            use_flats = detect_key_preference(new_root_preview)
    new_root = (root + semitones) % 12
    new_bass = ((bass + semitones) % 12) if bass is not None else None
    return format_chord(new_root, ctype, new_bass, use_flats)


_SCALE_QUALITIES_MAJOR = ["", "m", "m", "", "", "m", "dim"]
_SCALE_QUALITIES_MINOR = ["m", "m", "", "m", "m", "", ""]


def _key_to_pc(key: str) -> int:
    if not key:
        return -1
    root, _ = _parse_root(key)
    if not key[0].upper() in "ABCDEFG":
        return -1
    return root


def chord_root_pc(name: str) -> int:
    if not name:
        return -1
    root, _, _ = parse_chord_name(name)
    if name.strip() and not name[0].upper() in "ABCDEFG":
        return -1
    return root if name else -1


def scale_chords(key: str, mode: str = "major", use_flats: bool | None = None) -> list:
    pc = _key_to_pc(key)
    if pc < 0:
        return []
    if mode not in SCALE_INTERVALS:
        return []
    intervals = SCALE_INTERVALS[mode]
    qualities = _SCALE_QUALITIES_MAJOR if mode == "major" else _SCALE_QUALITIES_MINOR
    if use_flats is None:
        use_flats = detect_key_preference(pc)
    names = NOTE_NAMES_FLAT if use_flats else NOTE_NAMES_SHARP
    out = []
    for interval, quality in zip(intervals, qualities):
        root = names[(pc + interval) % 12]
        symbol = "°" if quality == "dim" else ""
        if quality == "m":
            symbol = "m"
        out.append(f"{root}{symbol}")
    return out


def chord_in_scale(name: str, key: str, mode: str = "major") -> bool:
    name_root, name_type, name_bass = parse_chord_name(name)
    if not name.strip() or not name[0].upper() in "ABCDEFG":
        return False
    diatonic = scale_chords(key, mode=mode)
    if not diatonic:
        return False
    for d in diatonic:
        d_root, d_type, d_bass = parse_chord_name(d)
        if d_root == name_root and d_type == name_type and d_bass == name_bass:
            return True
    return False
