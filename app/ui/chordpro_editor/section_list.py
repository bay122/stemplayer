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
import os
from app.ui.chordpro_editor.constants import SECTION_LABELS, SECTION_TYPES
from app.ui.theme import current as theme
from app.ui.svg_icon import svg_icon


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
        self._add_btn = QPushButton()
		#icon plus
        self._add_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-plus.svg")))
        self._add_btn.setToolTip("Añadir sección")
        self._add_btn.clicked.connect(self._on_add_clicked)
        self._dup_btn = QPushButton()
        self._dup_btn.setToolTip("Duplicar sección")
        self._dup_btn.clicked.connect(self._on_duplicate_clicked)
        self._dup_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-copy.svg")))
        self._del_btn = QPushButton()
        self._del_btn.setToolTip("Eliminar sección")
        self._del_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-eraser.svg")))
        self._del_btn.clicked.connect(self._on_remove_clicked)
        self._up_btn = QPushButton()
        self._up_btn.setToolTip("Subir")
        self._up_btn.clicked.connect(self._on_up_clicked)
        self._up_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-caret-up.svg")))
        self._down_btn = QPushButton()
        self._down_btn.setToolTip("Bajar")
        self._down_btn.clicked.connect(self._on_down_clicked)
        self._down_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-caret-down.svg")))
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
