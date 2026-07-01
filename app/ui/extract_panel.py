"""Panel de chips de extracción/filtro por categoría.

Cada chip se muestra solo si la canción tiene al menos un stem de esa
categoría. Al hacer click en un chip (no "All"), se filtran los stems
para que solo se escuchen los de esa categoría (solo en los demás)."""

import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from app.ui.svg_icon import svg_icon
from app.ui.theme import current as theme


CHIP_ORDER = ["All", "Vocals", "Drums", "Bass", "Guitars", "Keys", "Other", "Ref"]


def _default_colors():
    return {
        "All":     theme.ACCENT_PRIMARY,
        "Vocals":  "#FF5555",
        "Drums":   "#FFAA00",
        "Bass":    "#FFCC00",
        "Guitars": "#55CC55",
        "Keys":    theme.ACCENT_PURPLE,
        "Other":   "#AAAAAA",
        "Ref":     "#888888",
    }


class CategoryChip(QPushButton):
    def __init__(self, label: str, color: str, parent=None):
        super().__init__(label, parent)
        self.label = label
        self.color = color
        self.setCheckable(True)
        self.setFixedHeight(24)
        self.setMinimumWidth(56)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style(False)

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._apply_style(checked)

    def _apply_style(self, active: bool):
        if active:
            bg = self.color
            text = "#FFFFFF"
            border = self.color
        else:
            bg = theme.BG_TERTIARY
            text = theme.TEXT_DEFAULT
            border = theme.BORDER
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 2px 12px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 1px solid {self.color};
            }}
        """)


class ExtractPanel(QFrame):
    """Barra horizontal con chips de filtro por categoría."""

    chip_selected = Signal(object)
    """Emite la categoría seleccionada (str) o None para 'All'."""

    def __init__(self, config_mgr=None, parent=None):
        super().__init__(parent)
        self.setObjectName("extractPanel")
        self.setFrameShape(QFrame.NoFrame)
        self.config_mgr = config_mgr
        self._icons_dir = "./icons/svgs"
        self.chips = {}
        self._active = "All"
        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        self._icons_dir = getattr(self, '_icons_dir', './icons/svgs')

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 4, 10, 4)
        layout.setSpacing(6)

        self.extract_label = QLabel("FILTRO")
        self.extract_label.setStyleSheet(
            f"color: {theme.TEXT_SECONDARY}; font-size: 10px; font-weight: bold; "
            f"letter-spacing: 1px; background: transparent;"
        )
        self.extract_label.setFixedWidth(58)
        layout.addWidget(self.extract_label, 0, Qt.AlignVCenter)

        colors = self._get_colors()
        for label in CHIP_ORDER:
            color = colors.get(label, theme.TEXT_SECONDARY)
            chip = CategoryChip(label, color)
            chip.clicked.connect(lambda checked, l=label: self._on_chip_clicked(l, checked))
            self.chips[label] = chip
            layout.addWidget(chip, 0, Qt.AlignVCenter)

        layout.addStretch(1)
        self.setVisible(False)

    def _get_colors(self):
        if self.config_mgr is not None:
            try:
                cfg = self.config_mgr.get_category_colors()
                result = dict(_default_colors())
                result.update(cfg)
                return result
            except Exception:
                pass
        return _default_colors()

    def set_icons_dir(self, icons_dir: str):
        self._icons_dir = icons_dir

    def _apply_style(self):
        self.setStyleSheet(f"""
            QFrame#extractPanel {{
                background-color: {theme.BG_DARK};
                border-bottom: 1px solid {theme.BORDER_DARK};
            }}
        """)

    def update_visibility(self, present_categories: list):
        """Muestra solo los chips de categorías presentes. 'All' siempre visible."""
        always_visible = {"All"}
        for label, chip in self.chips.items():
            should_show = label in always_visible or label in present_categories
            chip.setVisible(should_show)
        self.setVisible(bool(present_categories))

    def _on_chip_clicked(self, label: str, checked: bool):
        if not checked:
            chip = self.chips[label]
            chip.blockSignals(True)
            chip.setChecked(True)
            chip.blockSignals(False)
            return
        for l, chip in self.chips.items():
            if l != label:
                chip.blockSignals(True)
                chip.setChecked(False)
                chip._apply_style(False)
                chip.blockSignals(False)
        self._active = label
        if label == "All":
            self.chip_selected.emit(None)
        else:
            self.chip_selected.emit(label)
