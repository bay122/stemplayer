from PySide6.QtCore import Qt, Signal, QStringListModel
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
