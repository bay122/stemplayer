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
