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

    def __init__(self, parent=None, icons_dir: str = "./icons/svgs"):
        super().__init__(parent)
        self._doc = None
        self._icons_dir = icons_dir
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

        # All three label+input pairs in one QWidget so we control the gaps
        # precisely: small (2px) inside each pair, larger (12px) between pairs.
        fields_widget = QWidget()
        fields_layout = QHBoxLayout(fields_widget)
        fields_layout.setContentsMargins(0, 0, 0, 0)
        fields_layout.setSpacing(12)
        for i, (label, widget) in enumerate((("Título", self._title_edit),
                                            ("Artista", self._artist_edit),
                                            ("Tono", self._key_edit))):
            lbl = QLabel(f"{label}:")
            lbl.setBuddy(widget)
            pair = QWidget()
            pair_layout = QHBoxLayout(pair)
            pair_layout.setContentsMargins(0, 0, 0, 0)
            pair_layout.setSpacing(2)
            pair_layout.addWidget(lbl)
            pair_layout.addWidget(widget)
            fields_layout.addWidget(pair)
        header.addWidget(fields_widget)
        # Spacer pushes Save to the right
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        header.addWidget(spacer)
        header.addSeparator()
        header.addWidget(save_btn)
        outer.addWidget(header)

        # Body
        splitter = QSplitter(Qt.Horizontal)
        self._section_panel = SectionListPanel(icons_dir=self._icons_dir)
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
