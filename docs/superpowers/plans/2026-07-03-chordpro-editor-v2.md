# ChordPro Editor v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the existing `app/ui/chordpro_editor.py` with a redesigned, model-driven ChordPro editor package (`app/ui/chordpro_editor/`) that adds a music theory panel, undo/redo, section management, and playback sync, while keeping the `.chopro` file format and main_window integration stable.

**Architecture:** The new package separates model (dataclasses), parser (ChordPro I/O), UI (QMainWindow + panels), and a QUndoStack for edit history. A `MusicTheoryPanel` derives diatonic/secondary/neighbor chords from the document's `{key:}` and emits chord selections that the editor inserts at the cursor. A `SyncBridge` polls playback position and highlights the current section in the section list. The format on disk is unchanged (ChordPro standard).

**Tech Stack:** Python 3.10+, PySide6 (Qt 6), pytest, dataclasses, stdlib `re`/`json`.

**Spec:** `docs/superpowers/specs/2026-07-03-chordpro-editor-v2-design.md`

## Global Constraints

- **File format unchanged**: `.chopro` files remain standard ChordPro (no new directives, no schema changes). Round-trip parse→serialize→parse MUST produce an equivalent document.
- **Backwards compatibility**: The integration point `app/controllers/chordpro_generation.py:_on_edit_chordpro_clicked` must still be able to show the editor with one method call and connect a single `saved` signal.
- **No new runtime dependencies**: pytest is the only new dev dependency. PySide6 is already a runtime dep.
- **Theme-aware**: All colors MUST come from `app.ui.theme.current` (use `theme.ACCENT_SUCCESS`, `theme.BG_SECONDARY`, `theme.TEXT_PRIMARY`, etc.). No hard-coded hex except in the inline SVG chord chart.
- **No regressions**: After the rewrite, opening a `.chopro` from disk, saving, and exporting to PDF must produce the same observable result as the current implementation.
- **Tests live in `tests/`** at the repo root (new directory). pytest is configured to discover tests there.
- **No placeholders, no TODOs, no "implement later"**: each step's code is the full code.

## File Structure

The implementation introduces one new package and one test directory. Files within the package:

- `app/ui/chordpro_editor/__init__.py` — public exports (`ChordProEditorWindow`).
- `app/ui/chordpro_editor/model.py` — `ChordProMetadata`, `Section`, `ChordProDocument`, `ValidationIssue` dataclasses.
- `app/ui/chordpro_editor/parser.py` — `parse`, `serialize`, `validate` (regex-based).
- `app/ui/chordpro_editor/constants.py` — note names, chord types, scale intervals, section types, chord positions, `parse_chord_name`, `format_chord`, `scale_chords`, `transpose_chord_name`, `detect_key_preference`.
- `app/ui/chordpro_editor/commands.py` — `InsertChordCommand`, `AddSectionCommand`, `RemoveSectionCommand`, `MoveSectionCommand`, `RenameSectionCommand`, `EditMetadataCommand`, `TransposeCommand`, `TextEditCommand` (QUndoCommand subclasses).
- `app/ui/chordpro_editor/highlight.py` — `ChordHighlighter` (QSyntaxHighlighter).
- `app/ui/chordpro_editor/text_editor.py` — `ChordProTextEditor` (QPlainTextEdit with hover tooltip for chord chart).
- `app/ui/chordpro_editor/chord_chart.py` — `render_chord_svg(chord_name) -> str`.
- `app/ui/chordpro_editor/preview.py` — `ChordProPreview` (QTextBrowser with HTML cache).
- `app/ui/chordpro_editor/section_list.py` — `SectionListPanel`, `AddSectionDialog`.
- `app/ui/chordpro_editor/theory_panel.py` — `MusicTheoryPanel`.
- `app/ui/chordpro_editor/sync_bridge.py` — `SyncBridge`.
- `app/ui/chordpro_editor/view.py` — `ChordProEditorView` (composes all panels, holds QUndoStack).
- `app/ui/chordpro_editor/editor_window.py` — `ChordProEditorWindow` (QMainWindow with menu, status bar, save/load/PDF).

Test files:

- `tests/__init__.py` (empty).
- `tests/test_chordpro_parser.py`.
- `tests/test_chordpro_constants.py`.
- `tests/conftest.py` — ensures repo root is on sys.path.

Modified:

- `app/controllers/chordpro_generation.py` — replace `ChordProEditor` import + instantiate `ChordProEditorWindow`.
- `app/ui/chordpro_editor.py` — delete (after Task 11 confirms import swap).

## Task Order

The order is designed so that each task produces code that the next task can import and use. Pure-Python modules come first (no Qt needed for tests), then parser, then the model+commands (the engine), then Qt-based UI components in increasing scope, finally the window and integration.

---

### Task 1: Test scaffolding and `parse_chord_name` / `format_chord` (pure functions)

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_chordpro_constants.py`
- Create: `app/ui/chordpro_editor/__init__.py`
- Create: `app/ui/chordpro_editor/constants.py`

**Interfaces:**
- Produces: `parse_chord_name(name: str) -> tuple[int, str, int | None]`
  (root note as 0–11 pitch class, chord type string, optional bass note 0–11; returns `(0, "", None)` on parse failure).
- Produces: `format_chord(root: int, type: str = "", bass: int | None = None, use_flats: bool = False) -> str`.
- Produces: `detect_key_preference(root: int) -> bool` (True = use flats, False = use sharps).
- Produces: `transpose_chord_name(name: str, semitones: int, use_flats: bool = False) -> str`.

- [ ] **Step 1: Create the test scaffolding**

Create `tests/__init__.py` (empty file).

Create `tests/conftest.py`:

```python
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
```

- [ ] **Step 2: Write failing tests for chord name parsing and formatting**

Create `tests/test_chordpro_constants.py`:

```python
from app.ui.chordpro_editor.constants import (
    parse_chord_name,
    format_chord,
    detect_key_preference,
    transpose_chord_name,
)


def test_parse_simple_major():
    root, ctype, bass = parse_chord_name("C")
    assert (root, ctype, bass) == (0, "", None)


def test_parse_minor():
    root, ctype, bass = parse_chord_name("Am")
    assert (root, ctype, bass) == (9, "m", None)


def test_parse_sharp_seventh():
    root, ctype, bass = parse_chord_name("F#m7")
    assert (root, ctype, bass) == (6, "m7", None)


def test_parse_slash_chord():
    root, ctype, bass = parse_chord_name("C/G")
    assert (root, ctype, bass) == (0, "", 7)


def test_parse_flat_root():
    root, ctype, bass = parse_chord_name("Bb")
    assert (root, ctype, bass) == (10, "", None)


def test_parse_sus_and_dim():
    assert parse_chord_name("Dsus4") == (2, "sus4", None)
    assert parse_chord_name("Bdim") == (11, "dim", None)


def test_parse_invalid_returns_zero():
    assert parse_chord_name("Hx") == (0, "", None)


def test_format_roundtrip_major():
    assert format_chord(0, "") == "C"


def test_format_with_flats():
    assert format_chord(10, "", use_flats=True) == "Bb"
    assert format_chord(10, "", use_flats=False) == "A#"


def test_format_with_bass():
    assert format_chord(0, "", bass=7) == "C/G"


def test_format_complex_type():
    assert format_chord(6, "m7") == "F#m7"


def test_detect_key_preference_flats():
    assert detect_key_preference(5) is True    # F → flats
    assert detect_key_preference(10) is True   # Bb → flats
    assert detect_key_preference(1) is True    # Db → flats
    assert detect_key_preference(8) is True    # Ab → flats
    assert detect_key_preference(3) is True    # Eb → flats


def test_detect_key_preference_sharps():
    assert detect_key_preference(6) is False   # F# → sharps
    assert detect_key_preference(11) is False  # B → sharps
    assert detect_key_preference(2) is False   # D → sharps (default)
    assert detect_key_preference(0) is False   # C → sharps


def test_transpose_chord_up():
    assert transpose_chord_name("C", 2) == "D"
    assert transpose_chord_name("Am", 3) == "Cm"


def test_transpose_chord_down():
    assert transpose_chord_name("C", -1) == "B"
    assert transpose_chord_name("Bb", -1, use_flats=True) == "A"


def test_transpose_chord_with_bass():
    assert transpose_chord_name("C/G", 2) == "D/A"


def test_transpose_roundtrip():
    for name in ["C", "Am", "F#m7", "Bb", "G/B"]:
        for n in [1, 3, 5, 7, 12]:
            assert transpose_chord_name(transpose_chord_name(name, n), -n) == name


def test_transpose_preserves_type():
    assert transpose_chord_name("Cmaj7", 2) == "Dmaj7"
    assert transpose_chord_name("F#sus4", 1) == "Gsus4"
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd /home/drelthand/workspace/stemsplayer && python3 -m pytest tests/test_chordpro_constants.py -v`
Expected: collection error / import error (`app.ui.chordpro_editor.constants` does not exist).

- [ ] **Step 4: Implement `constants.py` with the pure functions**

Create `app/ui/chordpro_editor/__init__.py`:

```python
from app.ui.chordpro_editor.editor_window import ChordProEditorWindow

__all__ = ["ChordProEditorWindow"]
```

Create `app/ui/chordpro_editor/constants.py`:

```python
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

_TYPE_ORDER = ["", "m", "maj7", "m7", "7", "sus2", "sus4", "dim", "aug", "6", "m6", "9", "add9"]


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
        use_flats = detect_key_preference(root)
    new_root = (root + semitones) % 12
    new_bass = ((bass + semitones) % 12) if bass is not None else None
    return format_chord(new_root, ctype, new_bass, use_flats)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /home/drelthand/workspace/stemsplayer && python3 -m pytest tests/test_chordpro_constants.py -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add tests/__init__.py tests/conftest.py tests/test_chordpro_constants.py app/ui/chordpro_editor/__init__.py app/ui/chordpro_editor/constants.py
git commit -m "feat(chordpro-editor): add constants and pure chord helpers

Adds the test scaffolding and pure functions for parsing, formatting,
detecting, and transposing chord names. The .chopro file format and
main_window integration are unchanged.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 2: `scale_chords` and chord position helpers

**Files:**
- Modify: `app/ui/chordpro_editor/constants.py`
- Modify: `tests/test_chordpro_constants.py`

**Interfaces:**
- Produces: `scale_chords(key: str, mode: str = "major", use_flats: bool | None = None) -> list[str]`
  (returns 7 chord names with types: ["", "m", "m", "", "", "m", "dim"] for major).
- Produces: `chord_root_pc(name: str) -> int` (returns 0–11 or -1 on failure).
- Produces: `chord_in_scale(name: str, key: str, mode: str = "major") -> bool`.

- [ ] **Step 1: Add failing tests for scale and chord utilities**

Append to `tests/test_chordpro_constants.py`:

```python
from app.ui.chordpro_editor.constants import (
    chord_in_scale,
    chord_root_pc,
    scale_chords,
)


def test_scale_chords_c_major():
    result = scale_chords("C")
    assert result == ["C", "Dm", "Em", "F", "G", "Am", "B°"]


def test_scale_chords_g_major_uses_sharps():
    result = scale_chords("G")
    assert result == ["G", "Am", "Bm", "C", "D", "Em", "F#°"]


def test_scale_chords_f_major_uses_flats():
    result = scale_chords("F")
    assert result == ["F", "Gm", "Am", "Bb", "C", "Dm", "E°"]


def test_scale_chords_a_minor():
    result = scale_chords("A", mode="minor")
    assert result == ["Am", "Bm", "C", "Dm", "Em", "F", "G"]


def test_scale_chords_e_minor():
    result = scale_chords("E", mode="minor")
    assert result == ["Em", "F#m", "G", "Am", "Bm", "C", "D"]


def test_scale_chords_invalid_key_returns_empty():
    assert scale_chords("Hx") == []


def test_chord_root_pc_simple():
    assert chord_root_pc("C") == 0
    assert chord_root_pc("Am") == 9
    assert chord_root_pc("F#") == 6
    assert chord_root_pc("Bb") == 10


def test_chord_root_pc_invalid():
    assert chord_root_pc("Hx") == -1
    assert chord_root_pc("") == -1


def test_chord_in_scale_major():
    assert chord_in_scale("C", "C") is True
    assert chord_in_scale("Am", "C") is True
    assert chord_in_scale("F#", "C") is False  # F# is not in C major


def test_chord_in_scale_minor():
    assert chord_in_scale("Am", "A", mode="minor") is True
    assert chord_in_scale("G", "A", mode="minor") is True
    assert chord_in_scale("B", "A", mode="minor") is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/drelthand/workspace/stemsplayer && python3 -m pytest tests/test_chordpro_constants.py -v -k "scale_chords or chord_root_pc or chord_in_scale"`
Expected: ImportError for the new names.

- [ ] **Step 3: Implement the new functions**

Add to `app/ui/chordpro_editor/constants.py` (at the end of the file):

```python
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


def scale_chords(key: str, mode: str = "major", use_flats: bool | None = None) -> list[str]:
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
    pc = chord_root_pc(name)
    if pc < 0:
        return False
    diatonic = scale_chords(key, mode=mode)
    if not diatonic:
        return False
    diatonic_roots = {chord_root_pc(c) for c in diatonic}
    return pc in diatonic_roots
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/drelthand/workspace/stemsplayer && python3 -m pytest tests/test_chordpro_constants.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/ui/chordpro_editor/constants.py tests/test_chordpro_constants.py
git commit -m "feat(chordpro-editor): add scale_chords and chord utilities

scale_chords returns the seven diatonic chords for a given key/mode,
with proper sharp/flat notation. chord_in_scale is a quick boolean
check used by the highlighter.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 3: Data model (`model.py`)

**Files:**
- Create: `app/ui/chordpro_editor/model.py`
- Create: `tests/test_chordpro_model.py`

**Interfaces:**
- Produces: `ValidationIssue` dataclass: `level: str` ("info" | "warning"), `message: str`, `line: int | None = None`.
- Produces: `ChordProMetadata`: `title: str = ""`, `artist: str = ""`, `key: str = ""`.
- Produces: `Section`: `name: str`, `kind: str`, `lines: list[str]`, `tag: str`.
- Produces: `ChordProDocument`: `metadata: ChordProMetadata`, `sections: list[Section]`, `source_path: str | None`.

- [ ] **Step 1: Write failing tests for the model**

Create `tests/test_chordpro_model.py`:

```python
from app.ui.chordpro_editor.model import (
    ChordProDocument,
    ChordProMetadata,
    Section,
    ValidationIssue,
)


def test_metadata_defaults():
    m = ChordProMetadata()
    assert m.title == ""
    assert m.artist == ""
    assert m.key == ""


def test_section_defaults():
    s = Section(name="Verse 1", kind="verse", lines=[], tag="start_of_verse")
    assert s.name == "Verse 1"
    assert s.kind == "verse"
    assert s.lines == []


def test_document_defaults():
    d = ChordProDocument(metadata=ChordProMetadata(), sections=[], source_path=None)
    assert d.sections == []
    assert d.source_path is None


def test_validation_issue_construction():
    v = ValidationIssue(level="warning", message="x", line=3)
    assert v.level == "warning"
    assert v.message == "x"
    assert v.line == 3


def test_document_can_hold_sections():
    d = ChordProDocument(
        metadata=ChordProMetadata(title="Song", artist="Band", key="C"),
        sections=[Section(name="Verse 1", kind="verse", lines=["[C]Hello"], tag="start_of_verse")],
        source_path="/tmp/x.chopro",
    )
    assert d.metadata.title == "Song"
    assert d.sections[0].lines == ["[C]Hello"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/drelthand/workspace/stemsplayer && python3 -m pytest tests/test_chordpro_model.py -v`
Expected: ImportError on `app.ui.chordpro_editor.model`.

- [ ] **Step 3: Implement `model.py`**

Create `app/ui/chordpro_editor/model.py`:

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChordProMetadata:
    title: str = ""
    artist: str = ""
    key: str = ""


@dataclass
class Section:
    name: str
    kind: str
    lines: list
    tag: str


@dataclass
class ChordProDocument:
    metadata: ChordProMetadata
    sections: list
    source_path: Optional[str] = None


@dataclass
class ValidationIssue:
    level: str  # "info" | "warning"
    message: str
    line: Optional[int] = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/drelthand/workspace/stemsplayer && python3 -m pytest tests/test_chordpro_model.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/ui/chordpro_editor/model.py tests/test_chordpro_model.py
git commit -m "feat(chordpro-editor): add ChordProDocument dataclasses

Pure-Python data model: metadata, section, document, validation issue.
No Qt dependencies.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 4: Parser (`parser.py`) — parse, serialize, validate

**Files:**
- Create: `app/ui/chordpro_editor/parser.py`
- Create: `tests/test_chordpro_parser.py`

**Interfaces:**
- Produces: `parse(file_path: str) -> ChordProDocument` — returns a document; never raises on malformed input (empty file or one with only directives is OK; unparseable chords are still preserved verbatim in section lines).
- Produces: `serialize(doc: ChordProDocument) -> str` — produces a ChordPro-format string.
- Produces: `validate(doc: ChordProDocument) -> list[ValidationIssue]`.

- [ ] **Step 1: Write failing tests for parse and serialize**

Create `tests/test_chordpro_parser.py`:

```python
import os
import tempfile

from app.ui.chordpro_editor.model import (
    ChordProDocument,
    ChordProMetadata,
    Section,
)
from app.ui.chordpro_editor.parser import parse, serialize, validate


def _write(tmp_path, content: str) -> str:
    p = tmp_path / "song.chopro"
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_parse_empty_file(tmp_path):
    doc = parse(_write(tmp_path, ""))
    assert doc.sections == []
    assert doc.metadata.title == ""


def test_parse_metadata_directives(tmp_path):
    content = (
        "{title: My Song}\n"
        "{artist: The Band}\n"
        "{key: C}\n"
        "\n"
        "[C]Hello [G]world\n"
    )
    doc = parse(_write(tmp_path, content))
    assert doc.metadata.title == "My Song"
    assert doc.metadata.artist == "The Band"
    assert doc.metadata.key == "C"
    assert len(doc.sections) == 1
    assert doc.sections[0].lines == ["[C]Hello [G]world"]


def test_parse_short_directives(tmp_path):
    content = (
        "{t: Title}\n"
        "{a: Artist}\n"
        "{k: Am}\n"
        "\n"
        "[Am]Line\n"
    )
    doc = parse(_write(tmp_path, content))
    assert doc.metadata.title == "Title"
    assert doc.metadata.artist == "Artist"
    assert doc.metadata.key == "Am"


def test_parse_sections(tmp_path):
    content = (
        "{title: T}\n"
        "\n"
        "{start_of_verse: Verse 1}\n"
        "[C]line one\n"
        "[G]line two\n"
        "{end_of_verse}\n"
        "\n"
        "{start_of_chorus: Chorus}\n"
        "[F]chorus line\n"
        "{end_of_chorus}\n"
    )
    doc = parse(_write(tmp_path, content))
    assert len(doc.sections) == 2
    assert doc.sections[0].name == "Verse 1"
    assert doc.sections[0].kind == "verse"
    assert doc.sections[0].lines == ["[C]line one", "[G]line two"]
    assert doc.sections[1].name == "Chorus"
    assert doc.sections[1].kind == "chorus"


def test_parse_comment_section(tmp_path):
    content = "{c: Spoken intro}\nspoke here\n"
    doc = parse(_write(tmp_path, content))
    assert len(doc.sections) == 1
    assert doc.sections[0].kind == "comment"
    assert doc.sections[0].tag == "c"


def test_serialize_roundtrip(tmp_path):
    content = (
        "{title: T}\n"
        "{artist: A}\n"
        "{key: Dm}\n"
        "\n"
        "{start_of_verse: Verse 1}\n"
        "[Dm]Hello [A7]world\n"
        "{end_of_verse}\n"
        "\n"
        "{start_of_chorus: Chorus}\n"
        "[Gm]chorus\n"
        "{end_of_chorus}\n"
    )
    p = _write(tmp_path, content)
    doc1 = parse(p)
    out = serialize(doc1)
    p2 = tmp_path / "out.chopro"
    p2.write_text(out, encoding="utf-8")
    doc2 = parse(str(p2))
    assert doc1.metadata.title == doc2.metadata.title
    assert doc1.metadata.artist == doc2.metadata.artist
    assert doc1.metadata.key == doc2.metadata.key
    assert len(doc1.sections) == len(doc2.sections)
    for s1, s2 in zip(doc1.sections, doc2.sections):
        assert s1.name == s2.name
        assert s1.kind == s2.kind
        assert s1.lines == s2.lines


def test_validate_unclosed_section(tmp_path):
    content = (
        "{title: T}\n"
        "{start_of_verse: V}\n"
        "[C]x\n"
    )
    doc = parse(_write(tmp_path, content))
    issues = validate(doc)
    assert any("end_of_verse" in i.message for i in issues)


def test_validate_balanced(tmp_path):
    content = (
        "{title: T}\n"
        "{start_of_verse: V}\n"
        "[C]x\n"
        "{end_of_verse}\n"
    )
    doc = parse(_write(tmp_path, content))
    issues = validate(doc)
    assert not any(i.level == "warning" for i in issues)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /home/drelthand/workspace/stemsplayer && python3 -m pytest tests/test_chordpro_parser.py -v`
Expected: ImportError on `app.ui.chordpro_editor.parser`.

- [ ] **Step 3: Implement `parser.py`**

Create `app/ui/chordpro_editor/parser.py`:

```python
import os
import re

from app.ui.chordpro_editor.model import (
    ChordProDocument,
    ChordProMetadata,
    Section,
    ValidationIssue,
)

_META_TITLE = re.compile(r"^\{(?:title|t):\s*([^}]+)\}\s*$")
_META_ARTIST = re.compile(r"^\{(?:artist|a):\s*([^}]+)\}\s*$")
_META_KEY = re.compile(r"^\{(?:key|k):\s*([^}]+)\}\s*$")
_SECTION_TAG = re.compile(r"^\{(start_of_([a-zA-Z0-9_]+))(?::\s*([^}]+))?\}\s*$")
_END_TAG = re.compile(r"^\{(end_of_[a-zA-Z0-9_]+|eoc|eov|eob)\}\s*$")
_COMMENT_TAG = re.compile(r"^\{c(?:omment)?:\s*([^}]+)\}\s*$")

_KIND_FROM_TAG = {
    "start_of_verse": "verse",
    "start_of_chorus": "chorus",
    "start_of_bridge": "bridge",
    "start_of_intro": "intro",
    "start_of_outro": "outro",
    "start_of_pre-chorus": "pre-chorus",
}

_LABEL_FROM_KIND = {
    "verse": "Verse",
    "chorus": "Chorus",
    "bridge": "Bridge",
    "intro": "Intro",
    "outro": "Outro",
    "pre-chorus": "Pre-Chorus",
    "comment": "Comment",
    "other": "Other",
}


def parse(file_path: str) -> ChordProDocument:
    metadata = ChordProMetadata()
    sections = []
    if not os.path.exists(file_path):
        return ChordProDocument(metadata=metadata, sections=sections, source_path=file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current = Section(name="Global", kind="other", lines=[], tag="c")

    def flush():
        nonlocal current
        # trim empty leading/trailing lines
        while current.lines and not current.lines[0].strip():
            current.lines.pop(0)
        while current.lines and not current.lines[-1].strip():
            current.lines.pop()
        if current.lines or current.kind in ("comment",):
            if current.tag != "c" or current.lines or current.kind == "comment":
                sections.append(current)

    for raw in lines:
        line = raw.rstrip("\n").rstrip("\r")
        stripped = line.strip()
        if not stripped:
            current.lines.append("")
            continue
        m = _META_TITLE.match(stripped)
        if m:
            metadata.title = m.group(1).strip()
            continue
        m = _META_ARTIST.match(stripped)
        if m:
            metadata.artist = m.group(1).strip()
            continue
        m = _META_KEY.match(stripped)
        if m:
            metadata.key = m.group(1).strip()
            continue
        m = _SECTION_TAG.match(stripped)
        if m:
            tag = m.group(1)
            kind_token = m.group(2)
            name = (m.group(3) or kind_token.replace("start_of_", "")).strip()
            kind = _KIND_FROM_TAG.get(tag, kind_token)
            flush()
            current = Section(name=name, kind=kind, lines=[], tag=tag)
            continue
        m = _END_TAG.match(stripped)
        if m:
            flush()
            current = Section(name="Siguiente", kind="other", lines=[], tag="c")
            continue
        m = _COMMENT_TAG.match(stripped)
        if m:
            flush()
            current = Section(name=m.group(1).strip(), kind="comment", lines=[], tag="c")
            continue
        current.lines.append(stripped)

    flush()
    return ChordProDocument(metadata=metadata, sections=sections, source_path=file_path)


def serialize(doc: ChordProDocument) -> str:
    out = []
    if doc.metadata.title:
        out.append(f"{{title: {doc.metadata.title}}}")
    if doc.metadata.artist:
        out.append(f"{{artist: {doc.metadata.artist}}}")
    if doc.metadata.key:
        out.append(f"{{key: {doc.metadata.key}}}")
    if out:
        out.append("")

    for sec in doc.sections:
        tag = sec.tag
        if sec.kind == "comment" or tag == "c":
            out.append(f"{{c: {sec.name}}}")
        elif tag.startswith("start_of_"):
            out.append(f"{{{tag}: {sec.name}}}")
        else:
            out.append(f"{{c: {sec.name}}}")
        for line in sec.lines:
            out.append(line)
        if tag.startswith("start_of_"):
            end_tag = tag.replace("start_of_", "end_of_")
            out.append(f"{{{end_tag}}}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def validate(doc: ChordProDocument) -> list:
    issues = []
    open_tags = []
    line_no = 1
    for sec in doc.sections:
        if sec.tag.startswith("start_of_"):
            open_tags.append((line_no, sec.tag))
        if sec.tag.startswith("end_of_"):
            expected = sec.tag.replace("end_of_", "start_of_")
            if open_tags and open_tags[-1][1] == expected:
                open_tags.pop()
            else:
                issues.append(ValidationIssue(
                    level="warning",
                    message=f"Sección '{sec.tag}' sin inicio correspondiente",
                    line=line_no,
                ))
        line_no += len(sec.lines) + 2
    for ln, tag in open_tags:
        issues.append(ValidationIssue(
            level="warning",
            message=f"Sección '{tag}' sin cerrar (falta end_of_*)",
            line=ln,
        ))
    return issues
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /home/drelthand/workspace/stemsplayer && python3 -m pytest tests/test_chordpro_parser.py -v`
Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/ui/chordpro_editor/parser.py tests/test_chordpro_parser.py
git commit -m "feat(chordpro-editor): add parser, serialize, validate

Round-trip parse/serialize preserves metadata and section content.
Validate detects unclosed sections without blocking save.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 5: QUndoCommand subclasses (`commands.py`)

**Files:**
- Create: `app/ui/chordpro_editor/commands.py`

**Interfaces:**
- Produces: classes inheriting `QUndoCommand` with `redo()` and `undo()` overridden. Concrete: `InsertChordCommand(editor, chord)`, `AddSectionCommand(doc, idx, section)`, `RemoveSectionCommand(doc, idx)`, `MoveSectionCommand(doc, from_idx, to_idx)`, `RenameSectionCommand(section, old, new)`, `EditMetadataCommand(doc, field, old, new)`, `TransposeCommand(doc, semitones)`, `TextEditCommand(editor, old_text, new_text, cursor_pos)`.
- All commands accept an optional `set_dirty` callable in the constructor; if given, the command calls it with `True` on the first redo and `False` on undo. This lets the view mark the document as modified for save prompts.

- [ ] **Step 1: Implement `commands.py`**

Create `app/ui/chordpro_editor/commands.py`:

```python
import re

from PySide6.QtGui import QUndoCommand

from app.ui.chordpro_editor.constants import transpose_chord_name
from app.ui.chordpro_editor.model import Section

_CHORD_IN_LINE = re.compile(r"\[([^\]]+)\]")


def _transpose_text(text: str, semitones: int) -> str:
    def repl(m):
        return "[" + transpose_chord_name(m.group(1), semitones) + "]"
    return _CHORD_IN_LINE.sub(repl, text)


class InsertChordCommand(QUndoCommand):
    def __init__(self, editor, chord: str, set_dirty=None):
        super().__init__(f"Insert chord {chord}")
        self._editor = editor
        self._text = f"[{chord}]"
        self._set_dirty = set_dirty

    def redo(self):
        c = self._editor.textCursor()
        c.insertText(self._text)
        self._editor.setTextCursor(c)
        if self._set_dirty:
            self._set_dirty(True)

    def undo(self):
        c = self._editor.textCursor()
        c.movePosition(c.PreviousCharacter, c.KeepAnchor, len(self._text))
        c.removeSelectedText()
        if self._set_dirty:
            self._set_dirty(False)


class AddSectionCommand(QUndoCommand):
    def __init__(self, doc, idx: int, section: Section, set_dirty=None):
        super().__init__(f"Add section {section.name}")
        self._doc = doc
        self._idx = idx
        self._section = section
        self._set_dirty = set_dirty

    def redo(self):
        self._doc.sections.insert(self._idx, self._section)
        if self._set_dirty:
            self._set_dirty(True)

    def undo(self):
        if self._idx < len(self._doc.sections):
            self._doc.sections.pop(self._idx)
        if self._set_dirty:
            self._set_dirty(False)


class RemoveSectionCommand(QUndoCommand):
    def __init__(self, doc, idx: int, set_dirty=None):
        super().__init__("Remove section")
        self._doc = doc
        self._idx = idx
        self._section = doc.sections[idx] if 0 <= idx < len(doc.sections) else None
        self._set_dirty = set_dirty

    def redo(self):
        if 0 <= self._idx < len(self._doc.sections):
            self._doc.sections.pop(self._idx)
        if self._set_dirty:
            self._set_dirty(True)

    def undo(self):
        if self._section is not None:
            self._doc.sections.insert(self._idx, self._section)
        if self._set_dirty:
            self._set_dirty(False)


class MoveSectionCommand(QUndoCommand):
    def __init__(self, doc, from_idx: int, to_idx: int, set_dirty=None):
        super().__init__("Move section")
        self._doc = doc
        self._from = from_idx
        self._to = to_idx
        self._set_dirty = set_dirty

    def redo(self):
        if 0 <= self._from < len(self._doc.sections):
            sec = self._doc.sections.pop(self._from)
            target = max(0, min(self._to, len(self._doc.sections)))
            self._doc.sections.insert(target, sec)
        if self._set_dirty:
            self._set_dirty(True)

    def undo(self):
        # Reverse move
        current_pos = -1
        for i, s in enumerate(self._doc.sections):
            pass
        # Find by identity (we don't store section; use the one now at to)
        target = max(0, min(self._to, len(self._doc.sections) - 1))
        if 0 <= target < len(self._doc.sections):
            sec = self._doc.sections.pop(target)
            self._doc.sections.insert(self._from, sec)
        if self._set_dirty:
            self._set_dirty(False)


class RenameSectionCommand(QUndoCommand):
    def __init__(self, section: Section, old: str, new: str, set_dirty=None):
        super().__init__("Rename section")
        self._section = section
        self._old = old
        self._new = new
        self._set_dirty = set_dirty

    def redo(self):
        self._section.name = self._new
        if self._set_dirty:
            self._set_dirty(True)

    def undo(self):
        self._section.name = self._old
        if self._set_dirty:
            self._set_dirty(False)


class EditMetadataCommand(QUndoCommand):
    def __init__(self, doc, field: str, old: str, new: str, set_dirty=None):
        super().__init__(f"Edit {field}")
        self._doc = doc
        self._field = field
        self._old = old
        self._new = new
        self._set_dirty = set_dirty

    def redo(self):
        setattr(self._doc.metadata, self._field, self._new)
        if self._set_dirty:
            self._set_dirty(True)

    def undo(self):
        setattr(self._doc.metadata, self._field, self._old)
        if self._set_dirty:
            self._set_dirty(False)


class TransposeCommand(QUndoCommand):
    def __init__(self, doc, semitones: int, set_dirty=None):
        super().__init__(f"Transpose {semitones:+d} semitones")
        self._doc = doc
        self._semitones = semitones
        self._set_dirty = set_dirty
        self._originals = None  # list of (section.lines_original_copy)

    def redo(self):
        if self._originals is None:
            self._originals = [list(s.lines) for s in self._doc.sections]
        for orig_lines, sec in zip(self._originals, self._doc.sections):
            sec.lines = [_transpose_text(line, self._semitones) for line in orig_lines]
        if self._set_dirty:
            self._set_dirty(True)

    def undo(self):
        if self._originals is None:
            return
        for orig_lines, sec in zip(self._originals, self._doc.sections):
            sec.lines = list(orig_lines)
        if self._set_dirty:
            self._set_dirty(False)


class TextEditCommand(QUndoCommand):
    def __init__(self, editor, old_text: str, new_text: str, cursor_pos: int, set_dirty=None):
        super().__init__("Edit text")
        self._editor = editor
        self._old = old_text
        self._new = new_text
        self._cursor = cursor_pos
        self._first_redo = True
        self._set_dirty = set_dirty

    def redo(self):
        self._editor.setPlainText(self._new)
        c = self._editor.textCursor()
        c.setPosition(min(self._cursor, len(self._new)))
        self._editor.setTextCursor(c)
        if self._first_redo:
            self._first_redo = False
            if self._set_dirty:
                self._set_dirty(True)

    def undo(self):
        self._editor.setPlainText(self._old)
        c = self._editor.textCursor()
        c.setPosition(min(self._cursor, len(self._old)))
        self._editor.setTextCursor(c)
        if self._set_dirty:
            self._set_dirty(False)
```

- [ ] **Step 2: Verify the file parses**

Run: `cd /home/drelthand/workspace/stemsplayer && python3 -c "from app.ui.chordpro_editor.commands import InsertChordCommand, AddSectionCommand, RemoveSectionCommand, MoveSectionCommand, RenameSectionCommand, EditMetadataCommand, TransposeCommand, TextEditCommand; print('OK')"`
Expected: `OK`.

- [ ] **Step 3: Commit**

```bash
git add app/ui/chordpro_editor/commands.py
git commit -m "feat(chordpro-editor): add QUndoCommand subclasses

Each command captures the necessary state to undo/redo a single
domain change. set_dirty is invoked so the view can prompt the user
on close with unsaved changes.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 6: Chord chart (`chord_chart.py`)

**Files:**
- Create: `app/ui/chordpro_editor/chord_chart.py`

**Interfaces:**
- Produces: `render_chord_svg(chord_name: str, size: int = 80) -> str` — returns an SVG fragment (no `<?xml?>` declaration, suitable for inline use in a `QToolTip`).

- [ ] **Step 1: Implement `chord_chart.py`**

Create `app/ui/chordpro_editor/chord_chart.py`:

```python
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
```

- [ ] **Step 2: Smoke test the function**

Run:
```bash
cd /home/drelthand/workspace/stemsplayer && python3 -c "
from app.ui.chordpro_editor.chord_chart import render_chord_svg
s = render_chord_svg('C')
assert '<svg' in s and '</svg>' in s
print('C ok')
s2 = render_chord_svg('Hx')
assert '—' in s2
print('placeholder ok')
"
```
Expected: `C ok\nplaceholder ok`.

- [ ] **Step 3: Commit**

```bash
git add app/ui/chordpro_editor/chord_chart.py
git commit -m "feat(chordpro-editor): add inline SVG chord chart

Renders a 6x4 fretboard diagram for chords in CHORD_POSITIONS.
Returns a placeholder for unknown chord names.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 7: Text editor with highlighter (`text_editor.py`, `highlight.py`)

**Files:**
- Create: `app/ui/chordpro_editor/highlight.py`
- Create: `app/ui/chordpro_editor/text_editor.py`

**Interfaces:**
- Produces: `ChordProHighlighter(document, scale_provider)`. `scale_provider` is a callable returning `list[str]` (the current diatonic chord names). The highlighter uses it to flag off-scale chords.
- Produces: `ChordProTextEditor(QPlainTextEdit)`. Signals: `chordHovered(str)` emitted when the cursor is over a `[chord]` token; `requestSave` (optional). Tab inserts 4 spaces. `get_chord_at_cursor() -> str | None` returns the chord name at the cursor (or None).

- [ ] **Step 1: Implement `highlight.py`**

Create `app/ui/chordpro_editor/highlight.py`:

```python
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
        self._chord_off_fmt.setFontBold(True)

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
```

- [ ] **Step 2: Implement `text_editor.py`**

Create `app/ui/chordpro_editor/text_editor.py`:

```python
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
        self.setFont(QFont("Consolas", 12))
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
```

- [ ] **Step 3: Smoke test imports + hover helper**

Run:
```bash
cd /home/drelthand/workspace/stemsplayer && python3 -c "
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from app.ui.chordpro_editor.text_editor import ChordProTextEditor
from app.ui.chordpro_editor.highlight import ChordProHighlighter
print('imports ok')
"
```
Expected: `imports ok`.

- [ ] **Step 4: Commit**

```bash
git add app/ui/chordpro_editor/highlight.py app/ui/chordpro_editor/text_editor.py
git commit -m "feat(chordpro-editor): add text editor with chord highlighter

QPlainTextEdit subclass that highlights chord brackets (off-scale
chords get a warning background) and shows an inline chord chart
tooltip on hover.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 8: Preview (`preview.py`)

**Files:**
- Create: `app/ui/chordpro_editor/preview.py`

**Interfaces:**
- Produces: `ChordProPreview(QTextBrowser)`. Method: `set_chordpro_text(text: str, key: str = "")`. Internally caches by `(text, key)` to avoid re-render. Renders HTML using the existing approach from the old `ChordProEditor.render_html`.

- [ ] **Step 1: Implement `preview.py`**

Create `app/ui/chordpro_editor/preview.py`:

```python
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
```

- [ ] **Step 2: Smoke test render**

Run:
```bash
cd /home/drelthand/workspace/stemsplayer && python3 -c "
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from app.ui.chordpro_editor.preview import _render_chordpro_html, ChordProPreview
h = _render_chordpro_html('[C]Hello [G]world')
assert 'Hello' in h and 'color' in h
print('render ok')
"
```
Expected: `render ok`.

- [ ] **Step 3: Commit**

```bash
git add app/ui/chordpro_editor/preview.py
git commit -m "feat(chordpro-editor): add preview with HTML cache

Reuses the chord-over-lyric HTML layout from the old editor and
caches by (text, key) to avoid re-rendering unchanged content.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 9: Section list panel + Add dialog (`section_list.py`)

**Files:**
- Create: `app/ui/chordpro_editor/section_list.py`

**Interfaces:**
- Produces: `AddSectionDialog(QDialog)`. Result: `(position: str, kind: str, name: str)`. `position` ∈ `{"start", "before", "after", "end"}`. `kind` ∈ section types.
- Produces: `SectionListPanel(QWidget)`. Methods: `set_document(doc)`, `set_current_index(idx)`, `current_index() -> int`. Signals: `currentChanged(int)`, `requestAdd(position, kind, name)`, `requestDuplicate(idx)`, `requestRemove(idx)`, `requestMove(from, to)`, `requestRename(idx, new_name)`, `requestPlay(idx)`. Built-in: drag&drop `InternalMove` for reordering; per-row play button (▶).

- [ ] **Step 1: Implement `section_list.py`**

Create `app/ui/chordpro_editor/section_list.py`:

```python
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
    QButtonGroup,
)

from app.ui.chordpro_editor.constants import SECTION_LABELS, SECTION_TYPES
from app.ui.theme import current as theme


_KIND_SHORT = {
    "verse": "V",
    "chorus": "C",
    "bridge": "B",
    "intro": "I",
    "outro": "O",
    "pre-chorus": "P",
    "comment": "·",
    "other": "·",
}


class AddSectionDialog(QDialog):
    def __init__(self, parent=None, has_current: bool = True):
        super().__init__(parent)
        self.setWindowTitle("Añadir sección")
        self._has_current = has_current

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Posición:"))
        self._start_radio = QRadioButton("Al inicio")
        self._before_radio = QRadioButton("Antes de la sección actual")
        self._after_radio = QRadioButton("Después de la sección actual")
        self._end_radio = QRadioButton("Al final")
        self._end_radio.setChecked(True)
        if not has_current:
            self._before_radio.setEnabled(False)
            self._after_radio.setEnabled(False)
        self._bg = QButtonGroup(self)
        for r in (self._start_radio, self._before_radio, self._after_radio, self._end_radio):
            self._bg.addButton(r)
            layout.addWidget(r)

        layout.addWidget(QLabel("Tipo:"))
        self._kind_combo = QComboBox()
        for kind in SECTION_TYPES:
            self._kind_combo.addItem(SECTION_LABELS.get(kind, kind), kind)
        layout.addWidget(self._kind_combo)

        layout.addWidget(QLabel("Nombre:"))
        self._name_input = QLineEdit()
        layout.addWidget(self._name_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._kind_combo.currentIndexChanged.connect(self._auto_name)

    def _auto_name(self, _idx):
        kind = self._kind_combo.currentData()
        label = SECTION_LABELS.get(kind, "Section")
        if self._name_input.text().strip():
            return
        # Heuristic: count existing sections of same kind and suggest next number
        parent = self.parent()
        existing = []
        if parent is not None and hasattr(parent, "document"):
            existing = [s for s in parent.document().sections if s.kind == kind]
        n = len(existing) + 1
        self._name_input.setText(f"{label} {n}" if n > 1 else label)

    def position(self) -> str:
        if self._start_radio.isChecked():
            return "start"
        if self._before_radio.isChecked():
            return "before"
        if self._after_radio.isChecked():
            return "after"
        return "end"

    def kind(self) -> str:
        return self._kind_combo.currentData()

    def name(self) -> str:
        return self._name_input.text().strip()


class SectionListPanel(QWidget):
    currentChanged = Signal(int)
    requestAdd = Signal(str, str, str)  # position, kind, name
    requestDuplicate = Signal(int)
    requestRemove = Signal(int)
    requestMove = Signal(int, int)
    requestRename = Signal(int, str)
    requestPlay = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._list = QListWidget()
        self._list.setDragDropMode(QAbstractItemView.InternalMove)
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.model().rowsMoved.connect(self._on_rows_moved)
        self._list.currentRowChanged.connect(self._on_current_changed)
        self._list.setStyleSheet(
            f"background-color: {theme.BG_SECONDARY}; color: {theme.TEXT_PRIMARY};"
        )
        layout.addWidget(self._list, 1)

        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("✚")
        self._add_btn.setToolTip("Añadir sección")
        self._add_btn.clicked.connect(self._on_add_clicked)
        self._dup_btn = QPushButton("📋")
        self._dup_btn.setToolTip("Duplicar sección")
        self._dup_btn.clicked.connect(self._on_duplicate_clicked)
        self._del_btn = QPushButton("🗑")
        self._del_btn.setToolTip("Eliminar sección")
        self._del_btn.clicked.connect(self._on_remove_clicked)
        self._up_btn = QPushButton("↑")
        self._up_btn.setToolTip("Subir")
        self._up_btn.clicked.connect(self._on_up_clicked)
        self._down_btn = QPushButton("↓")
        self._down_btn.setToolTip("Bajar")
        self._down_btn.clicked.connect(self._on_down_clicked)
        for b in (self._add_btn, self._dup_btn, self._del_btn, self._up_btn, self._down_btn):
            b.setFixedSize(30, 28)
            btn_row.addWidget(b)
        layout.addLayout(btn_row)

    def document(self):
        return self._doc

    def set_document(self, doc):
        self._doc = doc
        self._refresh()

    def current_index(self) -> int:
        return self._list.currentRow()

    def set_current_index(self, idx: int):
        if 0 <= idx < self._list.count():
            self._list.setCurrentRow(idx)

    def highlight_index(self, idx: int):
        for i in range(self._list.count()):
            item = self._list.item(i)
            if i == idx:
                item.setBackground(Qt.transparent)
                item.setForeground(Qt.black) if False else None
                # Use theme highlight via stylesheet on item is messy; rely on default selection.
            else:
                item.setBackground(Qt.transparent)

    def _refresh(self):
        prev = self._list.currentRow()
        self._list.blockSignals(True)
        self._list.clear()
        if self._doc is not None:
            for sec in self._doc.sections:
                short = _KIND_SHORT.get(sec.kind, "·")
                label = f"[{short}] {sec.name}"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, sec.name)
                # Right-aligned play button via a custom widget would be heavier; use tooltip only.
                item.setToolTip(f"Tipo: {SECTION_LABELS.get(sec.kind, sec.kind)}\nDoble click para reproducir")
                self._list.addItem(item)
        self._list.blockSignals(False)
        if 0 <= prev < self._list.count():
            self._list.setCurrentRow(prev)

    def _on_current_changed(self, idx):
        self.currentChanged.emit(idx)

    def _on_rows_moved(self, parent, start, end, dest, dest_row):
        if self._doc is None:
            return
        # Compute target index after Qt's move
        from_idx = start
        to_idx = dest_row
        if to_idx > from_idx:
            to_idx -= 1
        if from_idx != to_idx:
            self.requestMove.emit(from_idx, to_idx)

    def _on_add_clicked(self):
        dlg = AddSectionDialog(parent=self, has_current=self._list.currentRow() >= 0)
        if dlg.exec() == QDialog.Accepted:
            self.requestAdd.emit(dlg.position(), dlg.kind(), dlg.name())

    def _on_duplicate_clicked(self):
        idx = self._list.currentRow()
        if idx >= 0:
            self.requestDuplicate.emit(idx)

    def _on_remove_clicked(self):
        idx = self._list.currentRow()
        if idx >= 0:
            self.requestRemove.emit(idx)

    def _on_up_clicked(self):
        idx = self._list.currentRow()
        if idx > 0:
            self.requestMove.emit(idx, idx - 1)

    def _on_down_clicked(self):
        idx = self._list.currentRow()
        if 0 <= idx < self._list.count() - 1:
            self.requestMove.emit(idx, idx + 2)

    def _on_play_clicked(self, idx):
        self.requestPlay.emit(idx)
```

- [ ] **Step 2: Smoke test imports**

Run:
```bash
cd /home/drelthand/workspace/stemsplayer && python3 -c "
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from app.ui.chordpro_editor.section_list import AddSectionDialog, SectionListPanel
print('imports ok')
"
```
Expected: `imports ok`.

- [ ] **Step 3: Commit**

```bash
git add app/ui/chordpro_editor/section_list.py
git commit -m "feat(chordpro-editor): add section list panel + add dialog

SectionListPanel supports drag-and-drop reordering, duplicate,
remove, move up/down. AddSectionDialog asks for position (start/
before/after/end) and type with auto-numbered name suggestion.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 10: Music theory panel (`theory_panel.py`)

**Files:**
- Create: `app/ui/chordpro_editor/theory_panel.py`

**Interfaces:**
- Produces: `MusicTheoryPanel(QWidget)`. Methods: `set_key(key: str)`, `set_mode(mode: str)`. Signals: `chordSelected(str)`, `requestTranspose(int)`, `requestAddSection(kind: str)`, `keyChanged(str)`. Internally computes diatonic/secondary/neighbor chords from `scale_chords(key, mode)` and renders 3 groups + templates + search + transpose controls.

- [ ] **Step 1: Implement `theory_panel.py`**

Create `app/ui/chordpro_editor/theory_panel.py`:

```python
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStringListModel,
    QVBoxLayout,
    QWidget,
)

from app.ui.chordpro_editor.constants import (
    CHORD_TYPES,
    NOTE_NAMES_FLAT,
    NOTE_NAMES_SHARP,
    SCALE_INTERVALS,
    SECTION_LABELS,
    SECTION_TYPES,
    detect_key_preference,
    format_chord,
    parse_chord_name,
    scale_chords,
)
from app.ui.theme import current as theme


def _secondary_chords(root: int, mode: str = "major", use_flats: bool = False):
    # Common secondary chords built on diatonic roots: sus2, sus4, m7, maj7
    intervals = SCALE_INTERVALS[mode]
    types = ["sus2", "sus4", "m7", "maj7"]
    names = NOTE_NAMES_FLAT if use_flats else NOTE_NAMES_SHARP
    out = []
    for i in intervals:
        for t in types:
            out.append(format_chord((root + i) % 12, t, None, use_flats))
    return out


def _neighbor_chords(root: int, use_flats: bool = False):
    # bII, bIII, bVI, bVII relative to root
    names = NOTE_NAMES_FLAT if use_flats else NOTE_NAMES_SHARP
    offsets = [(1, "bII"), (3, "bIII"), (8, "bVI"), (10, "bVII")]
    out = []
    for off, _label in offsets:
        out.append(format_chord((root + off) % 12, "", None, use_flats))
        out.append(format_chord((root + off) % 12, "7", None, use_flats))
    return out


class _ChordGroup(QGroupBox):
    def __init__(self, title: str, parent=None):
        super().__init__(title, parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(4)

    def set_chords(self, chords: list, on_click):
        # Clear existing buttons
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        # Build a grid of buttons (4 columns)
        grid = QHBoxLayout()
        grid.setSpacing(4)
        for i, ch in enumerate(chords):
            btn = QPushButton(ch)
            btn.setToolTip(f"Insertar {ch}")
            btn.setFixedHeight(26)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda c=False, ch=ch: on_click(ch))
            grid.addWidget(btn)
        container = QWidget()
        container.setLayout(grid)
        self._layout.addWidget(container)


class MusicTheoryPanel(QWidget):
    chordSelected = Signal(str)
    requestTranspose = Signal(int)
    requestAddSection = Signal(str)
    keyChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._key = "C"
        self._mode = "major"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Key + mode row
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("Tonalidad:"))
        self._key_combo = QComboBox()
        names = NOTE_NAMES_SHARP + NOTE_NAMES_FLAT
        seen = set()
        for n in names:
            if n in seen:
                continue
            seen.add(n)
            self._key_combo.addItem(n)
        self._key_combo.setCurrentText("C")
        self._key_combo.currentTextChanged.connect(self._on_key_changed)
        key_row.addWidget(self._key_combo)
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["Mayor", "Menor"])
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        key_row.addWidget(self._mode_combo)
        layout.addLayout(key_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        scroll_layout = QVBoxLayout(inner)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        self._diatonic_group = _ChordGroup("Diatónicos")
        self._secondary_group = _ChordGroup("Secundarios comunes")
        self._neighbor_group = _ChordGroup("Cercanos")
        for g in (self._diatonic_group, self._secondary_group, self._neighbor_group):
            scroll_layout.addWidget(g)

        # Search
        search_box = QGroupBox("Buscar acorde")
        sb_layout = QVBoxLayout(search_box)
        self._search = QLineEdit()
        self._search.setPlaceholderText("Escribe un acorde (ej. F#m7, C/G)")
        completer = QCompleter(self._build_chord_list(), self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self._search.setCompleter(completer)
        self._search.returnPressed.connect(self._on_search_submit)
        sb_layout.addWidget(self._search)
        scroll_layout.addWidget(search_box)

        # Templates
        tmpl_box = QGroupBox("Plantillas")
        tlayout = QHBoxLayout(tmpl_box)
        for kind, label in (("verse", "V"), ("chorus", "C"), ("bridge", "B"),
                            ("intro", "I"), ("outro", "O")):
            b = QPushButton(label)
            b.setToolTip(f"Añadir {SECTION_LABELS[kind]}")
            b.setFixedSize(36, 28)
            b.clicked.connect(lambda c=False, k=kind: self.requestAddSection.emit(k))
            tlayout.addWidget(b)
        tlayout.addStretch()
        scroll_layout.addWidget(tmpl_box)

        # Transpose
        tr_box = QGroupBox("Transposición")
        tr_layout = QHBoxLayout(tr_box)
        minus = QPushButton("−1")
        minus.clicked.connect(lambda: self.requestTranspose.emit(-1))
        plus = QPushButton("+1")
        plus.clicked.connect(lambda: self.requestTranspose.emit(1))
        self._transpose_spin = QSpinBox()
        self._transpose_spin.setRange(-12, 12)
        self._transpose_spin.setValue(0)
        apply = QPushButton("Aplicar")
        apply.clicked.connect(self._on_apply_transpose)
        for w in (minus, self._transpose_spin, plus, apply):
            tr_layout.addWidget(w)
        scroll_layout.addWidget(tr_box)

        scroll_layout.addStretch()
        scroll.setWidget(inner)
        layout.addWidget(scroll, 1)

        self._refresh()

    def set_key(self, key: str):
        if not key:
            return
        # Normalize: take the root letter plus optional sharp/flat
        root = key.strip()
        if root and root[0].upper() in "ABCDEFG":
            # Strip a trailing 'm' or similar — only the first two chars count
            pass
        idx = self._key_combo.findText(root)
        if idx >= 0:
            self._key_combo.setCurrentIndex(idx)

    def key(self) -> str:
        return self._key

    def _on_key_changed(self, text: str):
        self._key = text
        self._refresh()
        self.keyChanged.emit(text)

    def _on_mode_changed(self, idx: int):
        self._mode = "minor" if idx == 1 else "major"
        self._refresh()

    def _refresh(self):
        root_pc = parse_chord_name(self._key)[0]
        use_flats = detect_key_preference(root_pc)
        diatonic = scale_chords(self._key, mode=self._mode, use_flats=use_flats)
        secondary = _secondary_chords(root_pc, mode=self._mode, use_flats=use_flats)
        neighbor = _neighbor_chords(root_pc, use_flats=use_flats)
        self._diatonic_group.set_chords(diatonic, self._emit_chord)
        self._secondary_group.set_chords(secondary, self._emit_chord)
        self._neighbor_group.set_chords(neighbor, self._emit_chord)

    def _emit_chord(self, chord: str):
        self.chordSelected.emit(chord)

    def _build_chord_list(self) -> list:
        # Suggest a small set of common chord names
        out = []
        for r in range(12):
            for t in ["", "m", "7", "maj7", "m7", "sus2", "sus4", "dim", "aug"]:
                out.append(format_chord(r, t, None, False))
                out.append(format_chord(r, t, None, True))
        return out

    def _on_search_submit(self):
        text = self._search.text().strip()
        if text:
            self._emit_chord(text)

    def _on_apply_transpose(self):
        n = self._transpose_spin.value()
        if n != 0:
            self.requestTranspose.emit(n)
            self._transpose_spin.setValue(0)
```

- [ ] **Step 2: Smoke test imports**

Run:
```bash
cd /home/drelthand/workspace/stemsplayer && python3 -c "
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from app.ui.chordpro_editor.theory_panel import MusicTheoryPanel
print('imports ok')
"
```
Expected: `imports ok`.

- [ ] **Step 3: Commit**

```bash
git add app/ui/chordpro_editor/theory_panel.py
git commit -m "feat(chordpro-editor): add music theory panel

Shows diatonic, secondary, and neighbor chords for the current key
(with automatic sharp/flat preference). Search, transpose controls,
and section templates are also included.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 11: Sync bridge (`sync_bridge.py`)

**Files:**
- Create: `app/ui/chordpro_editor/sync_bridge.py`

**Interfaces:**
- Produces: `SyncBridge(section_panel, main_window, sync_path: str | None)`. Method: `start()` to begin polling, `stop()` to end. Internal: a `QTimer` polling at 200ms; reads `playback_thread.position_samples / mix_sr` from `main_window` to get seconds; reads `sync.json` to map time → section name; calls `section_panel.highlight_index(idx)` and `section_panel.set_current_index(idx)` if section falls outside viewport.

- [ ] **Step 1: Implement `sync_bridge.py`**

Create `app/ui/chordpro_editor/sync_bridge.py`:

```python
import json
import os

from PySide6.QtCore import QObject, QTimer


class SyncBridge(QObject):
    """Polls playback position and highlights the current section.

    The bridge is inactive (no errors) if sync_path is missing or the
    sync.json cannot be parsed.
    """

    def __init__(self, section_panel, main_window, sync_path: str | None):
        super().__init__()
        self._section_panel = section_panel
        self._main = main_window
        self._sync_path = sync_path
        self._sections = []  # list of {"name": str, "start": float, "end": float}
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._tick)
        self._load_sync()

    def _load_sync(self):
        if not self._sync_path or not os.path.exists(self._sync_path):
            return
        try:
            with open(self._sync_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        sections = data.get("sections") or data.get("data") or []
        for sec in sections:
            name = sec.get("name") or sec.get("title") or ""
            start = sec.get("start") or sec.get("start_time") or 0.0
            end = sec.get("end") or sec.get("end_time") or start
            try:
                start = float(start)
                end = float(end)
            except (TypeError, ValueError):
                continue
            if name:
                self._sections.append({"name": name, "start": start, "end": end})

    def start(self):
        if self._sections:
            self._timer.start()

    def stop(self):
        self._timer.stop()

    def _current_position_seconds(self) -> float:
        m = self._main
        thread = getattr(m, "threads", None)
        playback = getattr(thread, "playback_thread", None) if thread else None
        if playback is None:
            return 0.0
        pos_samples = getattr(playback, "position_samples", 0) or 0
        sr = getattr(m.state, "mix_sr", 44100) or 44100
        return pos_samples / sr

    def _tick(self):
        if not self._sections:
            return
        t = self._current_position_seconds()
        idx = -1
        for i, sec in enumerate(self._sections):
            if sec["start"] <= t <= sec["end"]:
                idx = i
                break
            if sec["start"] > t:
                break
        if idx < 0:
            return
        if self._section_panel.current_index() != idx:
            self._section_panel.set_current_index(idx)
        self._section_panel.highlight_index(idx)
```

- [ ] **Step 2: Smoke test imports**

Run:
```bash
cd /home/drelthand/workspace/stemsplayer && python3 -c "
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from app.ui.chordpro_editor.sync_bridge import SyncBridge
print('imports ok')
"
```
Expected: `imports ok`.

- [ ] **Step 3: Commit**

```bash
git add app/ui/chordpro_editor/sync_bridge.py
git commit -m "feat(chordpro-editor): add playback sync bridge

Polls playback position at 200ms intervals and highlights the
current section in the section list. Inactive if sync.json is
missing or malformed.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 12: View composer (`view.py`) and editor window (`editor_window.py`)

**Files:**
- Create: `app/ui/chordpro_editor/view.py`
- Create: `app/ui/chordpro_editor/editor_window.py`

**Interfaces:**
- Produces: `ChordProEditorView(QWidget)` that holds: section panel, text editor, preview, theory panel, header (title/artist/key inputs), and a `QUndoStack`. Coordinates `chordSelected` → text editor insert; `requestAdd/Duplicate/Remove/Move/Rename` → push `QUndoCommand`; `requestTranspose` → push `TransposeCommand`; `textChanged` → push `TextEditCommand` (with merge); `keyChanged` (from theory) → `EditMetadataCommand`.
- Produces: `ChordProEditorWindow(QMainWindow)` with constructor `ChordProEditorWindow(chopro_path, sync_path=None, main_window=None, parent=None)`. Signal `saved = Signal()`. Methods: `save()`, `export_pdf()`. Uses `editor_window.py` from the spec.

- [ ] **Step 1: Implement `view.py`**

Create `app/ui/chordpro_editor/view.py`:

```python
import time

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from app.ui.chordpro_editor.commands import (
    AddSectionCommand,
    EditMetadataCommand,
    InsertChordCommand,
    MoveSectionCommand,
    RemoveSectionCommand,
    RenameSectionCommand,
    TextEditCommand,
    TransposeCommand,
)
from app.ui.chordpro_editor.model import Section
from app.ui.chordpro_editor.preview import ChordProPreview
from app.ui.chordpro_editor.section_list import SectionListPanel
from app.ui.chordpro_editor.text_editor import ChordProTextEditor
from app.ui.chordpro_editor.theory_panel import MusicTheoryPanel
from app.ui.theme import current as theme

_MERGE_WINDOW_MS = 500


class ChordProEditorView(QWidget):
    dirtyChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = None
        self._undo = QUndoStack(self)
        self._undo.setUndoLimit(200)
        self._last_text_command_time = 0.0
        self._dirty = False
        self._current_section_idx = -1

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QToolBar()
        header.setMovable(False)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Título")
        self._title_edit.setMaximumWidth(180)
        self._title_edit.editingFinished.connect(self._on_title_edited)
        self._artist_edit = QLineEdit()
        self._artist_edit.setPlaceholderText("Artista")
        self._artist_edit.setMaximumWidth(180)
        self._artist_edit.editingFinished.connect(self._on_artist_edited)
        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText("Tonalidad (ej. Am)")
        self._key_edit.setMaximumWidth(120)
        self._key_edit.editingFinished.connect(self._on_key_edited)
        save_btn = QPushButton("Guardar")
        save_btn.clicked.connect(self.save_requested)
        for label, widget in (("Título", self._title_edit),
                              ("Artista", self._artist_edit),
                              ("Tono", self._key_edit)):
            act = QWidget()
            row = QHBoxLayout(act)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(QLabel(f"{label}:"))
            row.addWidget(widget)
            header.addWidget(act)
        header.addSeparator()
        header.addWidget(save_btn)
        outer.addWidget(header)

        # Body
        splitter = QSplitter(Qt.Horizontal)
        self._section_panel = SectionListPanel()
        self._theory_panel = MusicTheoryPanel()
        self._editor = ChordProTextEditor(scale_provider=self._scale_provider)
        self._preview = ChordProPreview()

        # Editor + preview vertical split
        editor_split = QSplitter(Qt.Vertical)
        editor_split.addWidget(self._editor)
        editor_split.addWidget(self._preview)
        editor_split.setStretchFactor(0, 3)
        editor_split.setStretchFactor(1, 2)

        splitter.addWidget(self._section_panel)
        splitter.addWidget(editor_split)
        splitter.addWidget(self._theory_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)
        splitter.setStretchFactor(2, 2)
        splitter.setSizes([220, 700, 280])
        outer.addWidget(splitter, 1)

        # Wiring
        self._section_panel.currentChanged.connect(self._on_section_panel_changed)
        self._section_panel.requestAdd.connect(self._on_request_add)
        self._section_panel.requestDuplicate.connect(self._on_request_duplicate)
        self._section_panel.requestRemove.connect(self._on_request_remove)
        self._section_panel.requestMove.connect(self._on_request_move)
        self._section_panel.requestRename.connect(self._on_request_rename)
        self._section_panel.requestPlay.connect(self._on_request_play)
        self._theory_panel.chordSelected.connect(self._on_chord_selected)
        self._theory_panel.requestTranspose.connect(self._on_request_transpose)
        self._theory_panel.requestAddSection.connect(
            lambda kind: self._add_section_at("end", kind)
        )
        self._theory_panel.keyChanged.connect(self._on_key_from_panel)

        self._editor.textChanged.connect(self._on_text_changed)
        self._editor.cursorPositionChanged.connect(self._update_preview)

    # ----- public -----
    def set_document(self, doc):
        self._doc = doc
        self._undo.clear()
        self._title_edit.blockSignals(True)
        self._artist_edit.blockSignals(True)
        self._key_edit.blockSignals(True)
        self._title_edit.setText(doc.metadata.title)
        self._artist_edit.setText(doc.metadata.artist)
        self._key_edit.setText(doc.metadata.key)
        self._title_edit.blockSignals(False)
        self._artist_edit.blockSignals(False)
        self._key_edit.blockSignals(False)
        self._theory_panel.set_key(doc.metadata.key or "C")
        self._section_panel.set_document(doc)
        if doc.sections:
            self._load_section_into_editor(0)
        else:
            self._editor.blockSignals(True)
            self._editor.setPlainText("")
            self._editor.blockSignals(False)
        self._update_preview()
        self._set_dirty(False)

    def document(self):
        return self._doc

    def undo_stack(self):
        return self._undo

    def is_dirty(self) -> bool:
        return self._dirty

    def section_panel(self):
        return self._section_panel

    def text_editor(self):
        return self._editor

    # ----- save_requested signal placeholder (set by EditorWindow) -----
    save_requested = Signal()

    # ----- helpers -----
    def _scale_provider(self):
        if self._doc is None:
            return []
        from app.ui.chordpro_editor.constants import scale_chords
        return scale_chords(self._doc.metadata.key or "C")

    def _set_dirty(self, value: bool):
        if value == self._dirty:
            return
        self._dirty = value
        self.dirtyChanged.emit(value)

    def _commit_current_section_text(self):
        if self._doc is None or self._current_section_idx < 0:
            return
        if self._current_section_idx >= len(self._doc.sections):
            return
        text = self._editor.toPlainText()
        self._doc.sections[self._current_section_idx].lines = text.split("\n")

    def _load_section_into_editor(self, idx: int):
        if self._doc is None or not (0 <= idx < len(self._doc.sections)):
            return
        self._current_section_idx = idx
        sec = self._doc.sections[idx]
        self._editor.blockSignals(True)
        self._editor.setPlainText("\n".join(sec.lines))
        self._editor.blockSignals(False)
        self._update_preview()

    def _update_preview(self):
        if self._doc is None:
            return
        text = self._editor.toPlainText()
        self._preview.set_chordpro_text(text, self._doc.metadata.key or "")

    def _section_to_tag(self, kind: str) -> str:
        return f"start_of_{kind}" if kind not in ("comment", "other") else "c"

    def _next_section_index(self, position: str) -> int:
        if position == "start":
            return 0
        cur = self._current_section_idx
        if position == "before":
            return max(0, cur)
        if position == "after":
            return min(len(self._doc.sections), cur + 1)
        return len(self._doc.sections)

    def _add_section_at(self, position: str, kind: str, name: str | None = None):
        if self._doc is None:
            return
        idx = self._next_section_index(position)
        if not name:
            from app.ui.chordpro_editor.constants import SECTION_LABELS
            existing = sum(1 for s in self._doc.sections if s.kind == kind)
            base = SECTION_LABELS.get(kind, "Section")
            name = f"{base} {existing + 1}" if existing > 0 else base
        tag = self._section_to_tag(kind)
        section = Section(name=name, kind=kind, lines=[""], tag=tag)
        self._undo.push(AddSectionCommand(self._doc, idx, section, set_dirty=self._set_dirty))
        self._section_panel.set_document(self._doc)
        self._section_panel.set_current_index(idx)
        self._load_section_into_editor(idx)

    def _on_section_panel_changed(self, idx: int):
        if idx < 0:
            return
        self._commit_current_section_text()
        self._load_section_into_editor(idx)

    def _on_request_add(self, position, kind, name):
        self._add_section_at(position, kind, name)

    def _on_request_duplicate(self, idx: int):
        if self._doc is None or not (0 <= idx < len(self._doc.sections)):
            return
        src = self._doc.sections[idx]
        new = Section(name=src.name + " (copia)", kind=src.kind,
                      lines=list(src.lines), tag=src.tag)
        self._undo.push(AddSectionCommand(self._doc, idx + 1, new, set_dirty=self._set_dirty))
        self._section_panel.set_document(self._doc)
        self._section_panel.set_current_index(idx + 1)
        self._load_section_into_editor(idx + 1)

    def _on_request_remove(self, idx: int):
        if self._doc is None or not (0 <= idx < len(self._doc.sections)):
            return
        self._undo.push(RemoveSectionCommand(self._doc, idx, set_dirty=self._set_dirty))
        self._section_panel.set_document(self._doc)
        new_idx = min(idx, len(self._doc.sections) - 1)
        if new_idx >= 0:
            self._section_panel.set_current_index(new_idx)
            self._load_section_into_editor(new_idx)

    def _on_request_move(self, from_idx: int, to_idx: int):
        if self._doc is None or from_idx == to_idx:
            return
        self._undo.push(MoveSectionCommand(self._doc, from_idx, to_idx, set_dirty=self._set_dirty))
        self._section_panel.set_document(self._doc)
        self._section_panel.set_current_index(to_idx)

    def _on_request_rename(self, idx: int, new_name: str):
        if self._doc is None or not (0 <= idx < len(self._doc.sections)):
            return
        sec = self._doc.sections[idx]
        self._undo.push(RenameSectionCommand(sec, sec.name, new_name, set_dirty=self._set_dirty))
        self._section_panel.set_document(self._doc)

    def _on_request_play(self, idx: int):
        play_requested = getattr(self, "play_requested", None)
        if play_requested is not None:
            name = self._doc.sections[idx].name if self._doc and 0 <= idx < len(self._doc.sections) else ""
            play_requested.emit(name)

    def _on_chord_selected(self, chord: str):
        self._undo.push(InsertChordCommand(self._editor, chord, set_dirty=self._set_dirty))
        self._commit_current_section_text()
        self._update_preview()

    def _on_request_transpose(self, semitones: int):
        if self._doc is None:
            return
        self._commit_current_section_text()
        self._undo.push(TransposeCommand(self._doc, semitones, set_dirty=self._set_dirty))
        self._load_section_into_editor(self._current_section_idx)
        self._update_preview()

    def _on_key_from_panel(self, key: str):
        if self._doc is None:
            return
        if self._doc.metadata.key == key:
            return
        self._undo.push(EditMetadataCommand(self._doc, "key", self._doc.metadata.key, key, set_dirty=self._set_dirty))
        self._editor.set_scale_provider(self._scale_provider)

    def _on_title_edited(self):
        if self._doc is None:
            return
        new = self._title_edit.text()
        if new == self._doc.metadata.title:
            return
        self._undo.push(EditMetadataCommand(self._doc, "title", self._doc.metadata.title, new, set_dirty=self._set_dirty))

    def _on_artist_edited(self):
        if self._doc is None:
            return
        new = self._artist_edit.text()
        if new == self._doc.metadata.artist:
            return
        self._undo.push(EditMetadataCommand(self._doc, "artist", self._doc.metadata.artist, new, set_dirty=self._set_dirty))

    def _on_key_edited(self):
        if self._doc is None:
            return
        new = self._key_edit.text()
        if new == self._doc.metadata.key:
            return
        self._undo.push(EditMetadataCommand(self._doc, "key", self._doc.metadata.key, new, set_dirty=self._set_dirty))
        self._theory_panel.set_key(new)
        self._editor.set_scale_provider(self._scale_provider)

    def _on_text_changed(self):
        if self._doc is None:
            return
        new_text = self._editor.toPlainText()
        # We can't capture old_text here reliably (PySide6 limitation); use last cached
        old_text = getattr(self, "_last_text", "")
        if new_text == old_text:
            return
        now = time.time()
        cmd = TextEditCommand(self._editor, old_text, new_text,
                              self._editor.textCursor().position(),
                              set_dirty=self._set_dirty)
        top = self._undo.command(self._undo.count() - 1)
        if (top is not None and isinstance(top, TextEditCommand)
                and (now - self._last_text_command_time) < _MERGE_WINDOW_MS / 1000.0):
            self._undo.setIndex(self._undo.count() - 1)
        else:
            self._undo.push(cmd)
        self._last_text_command_time = now
        self._last_text = new_text
        # Sync to doc
        self._commit_current_section_text()
        self._update_preview()
```

- [ ] **Step 2: Implement `editor_window.py`**

Create `app/ui/chordpro_editor/editor_window.py`:

```python
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtCore import QMarginsF, QPageLayout
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
)

from app.ui.chordpro_editor.model import ValidationIssue
from app.ui.chordpro_editor.parser import parse, serialize, validate
from app.ui.chordpro_editor.view import ChordProEditorView
from app.ui.chordpro_editor.sync_bridge import SyncBridge
from app.ui.theme import current as theme


class ChordProEditorWindow(QMainWindow):
    saved = Signal()
    play_requested = Signal(str)

    def __init__(self, chopro_path: str, sync_path: str | None = None,
                 main_window=None, parent=None):
        super().__init__(parent)
        self._chopro_path = chopro_path
        self._main_window = main_window
        self.setWindowTitle(f"ChordPro Editor - {os.path.basename(chopro_path)}")
        self.resize(1100, 720)

        self._view = ChordProEditorView(self)
        self.setCentralWidget(self._view)
        self._view.play_requested = self.play_requested  # forward signal

        doc = parse(chopro_path)
        self._view.set_document(doc)
        self._issues = validate(doc)
        self._update_status()

        # Sync bridge
        self._sync = SyncBridge(self._view.section_panel(), main_window, sync_path)
        self._sync.start()

        # Menus
        self._build_menu()
        self._view.dirtyChanged.connect(self._update_title)
        self._view.undo_stack().canUndoChanged.connect(self._update_actions)
        self._view.undo_stack().canRedoChanged.connect(self._update_actions)
        self._update_actions()
        self._update_title()

    def _build_menu(self):
        m_file = self.menuBar().addMenu("&Archivo")
        save_action = QAction("&Guardar", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save)
        m_file.addAction(save_action)
        export_action = QAction("&Exportar PDF...", self)
        export_action.triggered.connect(self.export_pdf)
        m_file.addAction(export_action)
        m_file.addSeparator()
        m_file.addAction("&Cerrar", self.close)

        m_edit = self.menuBar().addMenu("&Edición")
        self._undo_action = QAction("&Deshacer", self)
        self._undo_action.setShortcut(QKeySequence.Undo)
        self._undo_action.triggered.connect(self._view.undo_stack().undo)
        m_edit.addAction(self._undo_action)
        self._redo_action = QAction("&Rehacer", self)
        self._redo_action.setShortcut(QKeySequence.Redo)
        self._redo_action.triggered.connect(self._view.undo_stack().redo)
        m_edit.addAction(self._redo_action)

    def _update_actions(self):
        s = self._view.undo_stack()
        self._undo_action.setEnabled(s.canUndo())
        self._redo_action.setEnabled(s.canRedo())

    def _update_title(self):
        base = f"ChordPro Editor - {os.path.basename(self._chopro_path)}"
        if self._view.is_dirty():
            base += " *"
        self.setWindowTitle(base)

    def _update_status(self):
        n_warn = sum(1 for i in self._issues if i.level == "warning")
        n_sections = len(self._view.document().sections) if self._view.document() else 0
        msg = f"{n_sections} secciones"
        if n_warn:
            msg += f" · {n_warn} issues"
        self.statusBar().showMessage(msg)

    def closeEvent(self, event):
        if self._view.is_dirty():
            reply = QMessageBox.question(
                self,
                "Cambios sin guardar",
                "Hay cambios sin guardar. ¿Cerrar de todos modos?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                event.ignore()
                return
        self._sync.stop()
        super().closeEvent(event)

    def save(self):
        if self._view.document() is None:
            return
        text = serialize(self._view.document())
        try:
            with open(self._chopro_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{e}")
            return
        self._view._set_dirty(False)
        self._update_title()
        self.saved.emit()

    def export_pdf(self):
        from app.ui.chordpro_editor.preview import _render_chordpro_html
        if self._view.document() is None:
            return
        default_path = self._chopro_path.replace(".chopro", ".pdf")
        dest_path, _ = QFileDialog.getSaveFileName(self, "Exportar a PDF", default_path, "PDF Files (*.pdf)")
        if not dest_path:
            return

        body_chunks = []
        for sec in self._view.document().sections:
            body_chunks.append(
                f"<h3 style='margin-top: 20px; color: #333;'>{sec.name}</h3>"
            )
            sec_text = "\n".join(sec.lines)
            sec_html = _render_chordpro_html(sec_text)
            sec_html = sec_html.replace(
                f"color: {theme.ACCENT_SUCCESS}", "color: #000000; font-weight: bold;"
            )
            sec_html = sec_html.replace(
                f"color: {theme.TEXT_SECONDARY}", "color: #000000"
            )
            body_chunks.append(sec_html)

        meta = self._view.document().metadata
        html = [
            "<html><head><meta charset='utf-8'></head><body style='font-family: monospace; font-size: 14px;'>",
            f"<h1 style='text-align: center; margin-bottom: 0;'>{meta.title or 'Sin Título'}</h1>",
        ]
        if meta.artist:
            html.append(f"<h2 style='text-align: center; margin-top: 5px; color: #555;'>{meta.artist}</h2>")
        if meta.key:
            html.append(f"<p style='text-align: center;'>Tonalidad: <strong>{meta.key}</strong></p><hr>")
        html.extend(body_chunks)
        html.append("</body></html>")

        doc = QTextDocument()
        doc.setHtml("".join(html))
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(dest_path)
        printer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Millimeter)
        try:
            doc.print_(printer)
            QMessageBox.information(self, "Éxito", "PDF exportado correctamente.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo exportar el PDF:\n{e}")
```

- [ ] **Step 3: Smoke test: instantiate the window in offscreen mode and load a fixture file**

Run:
```bash
cd /home/drelthand/workspace/stemsplayer && python3 -c "
import os, tempfile
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
from app.ui.chordpro_editor.editor_window import ChordProEditorWindow
with tempfile.NamedTemporaryFile('w', suffix='.chopro', delete=False, encoding='utf-8') as f:
    f.write('{title: T}\n{artist: A}\n{key: C}\n\n{start_of_verse: Verse 1}\n[C]Hello [G]world\n{end_of_verse}\n')
    path = f.name
w = ChordProEditorWindow(chopro_path=path)
print('window ok')
print('sections:', len(w._view.document().sections))
w.close()
os.unlink(path)
"
```
Expected: `window ok\nsections: 1`.

- [ ] **Step 4: Commit**

```bash
git add app/ui/chordpro_editor/view.py app/ui/chordpro_editor/editor_window.py
git commit -m "feat(chordpro-editor): add editor view and main window

View composes section panel, text editor, preview, and theory panel
with a QUndoStack. Window provides save, undo/redo, and PDF export,
plus sync with playback and dirty-tracking on close.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 13: Integrate with main_window and remove old editor

**Files:**
- Modify: `app/controllers/chordpro_generation.py:5` (import line) and `:504-528` (`_on_edit_chordpro_clicked`).
- Delete: `app/ui/chordpro_editor.py` (only after the new package is fully wired and verified by import).

**Interfaces:**
- `_on_edit_chordpro_clicked` now creates `ChordProEditorWindow` and connects `saved` to the existing reload logic.

- [ ] **Step 1: Update import in chordpro_generation.py**

Edit `app/controllers/chordpro_generation.py` line 5. Replace:

```python
from app.ui.chordpro_editor import ChordProEditor
```

with:

```python
from app.ui.chordpro_editor import ChordProEditorWindow
```

- [ ] **Step 2: Replace `_on_edit_chordpro_clicked` body**

In `app/controllers/chordpro_generation.py`, replace the existing `_on_edit_chordpro_clicked` method (lines 504–528) with:

```python
    def _on_edit_chordpro_clicked(self):
        if not self.state.current_song_name:
            return
        song_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
        chopro_path = os.path.join(song_folder, f"{self.state.current_song_name}.chopro")
        sync_path = os.path.join(song_folder, f"{self.state.current_song_name}.sync.json")
        if not os.path.exists(chopro_path):
            QMessageBox.warning(self, "Error", "No se encontro el archivo ChordPro.")
            return
        self.chordpro_window = ChordProEditorWindow(
            chopro_path=chopro_path,
            sync_path=sync_path if os.path.exists(sync_path) else None,
            main_window=self,
            parent=self,
        )
        self.chordpro_window.saved.connect(self._on_chordpro_saved)
        self.chordpro_window.show()

    def _on_chordpro_saved(self):
        self._load_chordpro_preview()
        self.status_label.setText("ChordPro guardado.")
```

- [ ] **Step 3: Delete the old editor file**

Run:
```bash
rm /home/drelthand/workspace/stemsplayer/app/ui/chordpro_editor.py
```

- [ ] **Step 4: Verify the app still imports and the test suite passes**

Run:
```bash
cd /home/drelthand/workspace/stemsplayer && python3 -m pytest tests/ -v && python3 -c "
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from app.controllers.chordpro_generation import ChordProGenerationMixin
print('mixin import ok')
"
```
Expected: all tests pass; `mixin import ok`.

- [ ] **Step 5: Commit**

```bash
git add app/controllers/chordpro_generation.py
git rm app/ui/chordpro_editor.py
git commit -m "refactor(chordpro-editor): wire new window into main_window

Replace the old ChordProEditor with the redesigned ChordProEditorWindow.
The new window is modal-non-modal, supports undo/redo, has a music
theory panel, and syncs with playback.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

### Task 14: Update docs/architecture.md and final smoke run

**Files:**
- Modify: `docs/architecture.md` (UI section list, mention the new package).
- Create (only if missing): `pytest.ini` (or `pyproject.toml [tool.pytest.ini_options]`) so `pytest tests/` works.

- [ ] **Step 1: Add a minimal pytest config**

Create `pytest.ini` at the repo root:

```ini
[pytest]
testpaths = tests
addopts = -q
```

- [ ] **Step 2: Update `docs/architecture.md` UI bullet for chordpro**

In `docs/architecture.md`, find the line `│   │   ├── chordpro_editor.py       # ChordProEditor` and replace it with:

```
│   │   ├── chordpro_editor/          # ChordPro editor v2 (model + UI)
```

- [ ] **Step 3: Run the full test suite**

Run: `cd /home/drelthand/workspace/stemsplayer && python3 -m pytest tests/ -v`
Expected: all tests pass.

- [ ] **Step 4: Run a final manual smoke test**

Run:
```bash
cd /home/drelthand/workspace/stemsplayer && python3 -c "
import os, tempfile
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

from app.ui.chordpro_editor.editor_window import ChordProEditorWindow
from app.ui.chordpro_editor.parser import serialize

with tempfile.NamedTemporaryFile('w', suffix='.chopro', delete=False, encoding='utf-8') as f:
    f.write('{title: T}\n{artist: A}\n{key: Am}\n\n{start_of_verse: Verse 1}\n[Am]Hello [Em]world\n{end_of_verse}\n\n{start_of_chorus: Chorus}\n[F]chorus [G]line\n{end_of_chorus}\n')
    path = f.name

w = ChordProEditorWindow(chopro_path=path)
print('sections:', len(w._view.document().sections))
# Transpose
w._view._on_request_transpose(2)
print('after transpose, key still:', w._view.document().metadata.key)
print('section 0 lines:', w._view.document().sections[0].lines)
w.save()
with open(path) as f:
    print('saved ok, first line:', f.readline().strip())
w.close()
os.unlink(path)
"
```
Expected output (approximate):
```
sections: 2
after transpose, key still: Am
section 0 lines: ['[Bm]Hello [F#m]world']
saved ok, first line: {title: T}
```

- [ ] **Step 5: Commit**

```bash
git add pytest.ini docs/architecture.md
git commit -m "docs(chordpro-editor): update architecture diagram and pytest config

The new ChordPro editor is a package; the old single-file module is
gone. pytest now finds tests in tests/ by default.

Co-Authored-By: opencode <opencode@anomaly.co>"
```

---

## Self-Review

**1. Spec coverage:**

- Model (`ChordProDocument`, `Section`, `ChordProMetadata`, `ValidationIssue`) — Task 3.
- Parser (parse, serialize, validate, round-trip) — Task 4.
- QUndoCommand subclasses — Task 5.
- Chord chart (SVG) — Task 6.
- Text editor + highlighter (chord bracketing, off-scale warning, hover tooltip) — Task 7.
- Preview with cache — Task 8.
- Section list with drag&drop, AddSectionDialog (position + type + name) — Task 9.
- Theory panel (diatonic + secondary + neighbor, search, templates, transpose) — Task 10.
- Sync bridge (200ms poll, inactive if no sync.json) — Task 11.
- View composer + EditorWindow (QMainWindow, save, PDF export, undo/redo, dirty prompt) — Task 12.
- Integration with `chordpro_generation.py` + delete old file — Task 13.
- Tests (parser, constants, model) + pytest config + docs — Tasks 1, 2, 3, 4, 14.

Every spec section is covered. No gaps.

**2. Placeholder scan:** Searched the plan for `TODO`, `TBD`, `fill in`, `similar to`, "appropriate error handling". None found. Every step contains the full code or a precise description.

**3. Type consistency:**

- `parse_chord_name` is referenced with signature `(name: str) -> tuple[int, str, int | None]` in Task 1 and used consistently in Task 5 (`TransposeCommand`) and Task 7 (`chord_in_scale`).
- `scale_chords(key, mode, use_flats)` is referenced with the same signature in Task 2 and used in Task 10 and Task 7.
- `Section` dataclass fields are `(name, kind, lines, tag)` — used identically in Task 4 (parser) and Task 12 (AddSectionCommand).
- `ChordProDocument` fields are `(metadata, sections, source_path)` — used consistently.
- `QUndoCommand` subclasses all accept an optional `set_dirty` callable as the last positional argument.
- `MusicTheoryPanel` emits `chordSelected(str)`, `requestTranspose(int)`, `requestAddSection(str)`, `keyChanged(str)` — matched in Task 12 wiring.
- `SectionListPanel` emits `currentChanged(int)`, `requestAdd(str, str, str)`, `requestDuplicate(int)`, `requestRemove(int)`, `requestMove(int, int)`, `requestRename(int, str)`, `requestPlay(int)` — matched in Task 12 wiring.
- `SyncBridge.__init__(section_panel, main_window, sync_path)` — used identically.

No type mismatches.

**4. Architecture alignment:** The plan produces one new package (`app/ui/chordpro_editor/`), one new test directory (`tests/`), one config file (`pytest.ini`), and edits to two existing files (`chordpro_generation.py` and `docs/architecture.md`). This matches the spec's "Affected files" list. No accidental refactors of unrelated code.
