import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from app.utils.constants import STEM_CATEGORIES
from app.ui.svg_icon import svg_icon
from app.ui.volume_slider import VolumeSlider
from app.ui.pan_slider import PanSlider
from app.ui.theme import DARK_THEME as theme


class StemItemWidget(QWidget):
    volume_changed = Signal(str, float)
    pan_changed = Signal(str, float)
    mute_toggled = Signal(str, bool)
    solo_toggled = Signal(str, bool)
    fx_toggled = Signal(str, bool)
    name_changed = Signal(str, str)
    category_changed = Signal(str, str)
    delete_requested = Signal(str)
    move_up_requested = Signal(str)
    move_down_requested = Signal(str)

    def __init__(self, name: str, category: str, volume: float = 1.0,
                 icons_dir: str = "./icons/svgs", parent=None):
        super().__init__(parent)
        self.stem_name = name
        self.icons_dir = icons_dir
        self._build_ui(name, category, volume)
        self._apply_style()

    def _build_ui(self, name: str, category: str, volume: float):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)

        self.name_edit = QLineEdit(name)
        self.name_edit.setMinimumWidth(130)
        self.name_edit.setMaximumWidth(180)
        self.name_edit.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.name_edit.setToolTip("Doble clic para editar nombre")
        self.name_edit.editingFinished.connect(self._on_name_edited)
        info_layout.addWidget(self.name_edit)

        self.category_combo = QComboBox()
        self.category_combo.addItems(STEM_CATEGORIES)
        self.category_combo.setCurrentText(category)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        self.category_combo.setMinimumWidth(110)
        self.category_combo.setMaximumWidth(150)
        self.category_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        info_layout.addWidget(self.category_combo)

        layout.addLayout(info_layout, 0)

        vol_layout = QVBoxLayout()
        vol_layout.setSpacing(2)
        vol_label = QLabel("Vol")
        vol_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 10px;")
        vol_layout.addWidget(vol_label, alignment=Qt.AlignCenter)

        self.volume_slider = VolumeSlider(parent=self, icons_dir=self.icons_dir)
        self.volume_slider.setValue(volume)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.volume_slider.setMinimumWidth(180)
        self.volume_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vol_layout.addWidget(self.volume_slider)

        layout.addLayout(vol_layout, 5)

        pan_layout = QVBoxLayout()
        pan_layout.setSpacing(2)
        pan_label = QLabel("Pan")
        pan_label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 10px;")
        pan_layout.addWidget(pan_label, alignment=Qt.AlignCenter)

        self.pan_slider = PanSlider(parent=self, icons_dir=self.icons_dir)
        self.pan_slider.setValue(0.0)
        self.pan_slider.valueChanged.connect(self._on_pan_changed)
        self.pan_slider.setMinimumWidth(120)
        self.pan_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pan_layout.addWidget(self.pan_slider)

        layout.addLayout(pan_layout, 3)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        self.mute_btn = QPushButton()
        self.mute_btn.setCheckable(True)
        self.mute_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-mute.svg"), theme.SVG_ICON_DEFAULT))
        self.mute_btn.setFixedSize(34, 34)
        self.mute_btn.setToolTip("Mute")
        self.mute_btn.toggled.connect(self._on_mute_toggled)
        btn_layout.addWidget(self.mute_btn)

        self.solo_btn = QPushButton()
        self.solo_btn.setCheckable(True)
        self.solo_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-solo.svg"), theme.SVG_ICON_DEFAULT))
        self.solo_btn.setFixedSize(34, 34)
        self.solo_btn.setToolTip("Solo")
        self.solo_btn.toggled.connect(self._on_solo_toggled)
        btn_layout.addWidget(self.solo_btn)

        self.fx_btn = QPushButton("FX")
        self.fx_btn.setCheckable(True)
        self.fx_btn.setChecked(True)
        self.fx_btn.setFixedSize(42, 34)
        self.fx_btn.setToolTip("FX: activa/desactiva efectos de pitch para este stem")
        self.fx_btn.toggled.connect(self._on_fx_toggled)
        btn_layout.addWidget(self.fx_btn)

        layout.addLayout(btn_layout, 0)
        layout.addStretch(1)

        reorder_layout = QVBoxLayout()
        reorder_layout.setSpacing(1)

        self.up_btn = QPushButton()
        self.up_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-caret-up.svg"), theme.SVG_ICON_ACTIVE))
        self.up_btn.setFixedSize(28, 17)
        self.up_btn.clicked.connect(lambda: self.move_up_requested.emit(self.stem_name))
        reorder_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton()
        self.down_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-caret-down.svg"), theme.SVG_ICON_ACTIVE))
        self.down_btn.setFixedSize(28, 17)
        self.down_btn.clicked.connect(lambda: self.move_down_requested.emit(self.stem_name))
        reorder_layout.addWidget(self.down_btn)

        layout.addLayout(reorder_layout, 0)

        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-eraser.svg"), theme.SVG_ICON_DANGER))
        self.delete_btn.setFixedSize(34, 34)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.stem_name))
        layout.addWidget(self.delete_btn, 0)

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _apply_style(self):
        self.setStyleSheet(f"""
            StemItemWidget {{
                background-color: {theme.BG_TERTIARY};
                border: 1px solid {theme.BORDER_WIDGET};
                border-radius: {theme.BORDER_RADIUS_MD};
            }}
            QLineEdit {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 2px 4px;
                font-size: 11px;
            }}
            QComboBox {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 2px 4px;
                font-size: 11px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                selection-background-color: {theme.ACCENT_PRIMARY};
            }}
            QPushButton {{
                background-color: #333333;
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                color: {theme.TEXT_PRIMARY};
                font-weight: bold;
                font-size: 10px;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_ACCENT};
            }}
            QPushButton:checked {{
                background-color: {theme.ACCENT_PRIMARY};
                border: 1px solid {theme.ACCENT_PRIMARY};
                color: {theme.TEXT_PRIMARY};
            }}
            QSlider::groove:vertical {{
                background: {theme.BORDER};
                width: 6px;
                border-radius: 3px;
            }}
            QSlider::handle:vertical {{
                background: {theme.ACCENT_PRIMARY};
                height: 14px;
                width: 14px;
                margin: 0 -4px;
                border-radius: 7px;
            }}
        """)

    def _on_volume_changed(self, value: float):
        self.volume_changed.emit(self.stem_name, value)

    def _on_pan_changed(self, value: float):
        self.pan_changed.emit(self.stem_name, value)

    def _on_mute_toggled(self, checked: bool):
        self.mute_btn.setIcon(svg_icon(
            os.path.join(self.icons_dir, "fad-mute.svg"),
            theme.SVG_ICON_DANGER if checked else theme.SVG_ICON_DEFAULT
        ))
        self.mute_toggled.emit(self.stem_name, checked)

    def _on_solo_toggled(self, checked: bool):
        self.solo_btn.setIcon(svg_icon(
            os.path.join(self.icons_dir, "fad-solo.svg"),
            theme.SVG_ICON_SOLO if checked else theme.SVG_ICON_DEFAULT
        ))
        self.solo_toggled.emit(self.stem_name, checked)

    def _on_fx_toggled(self, checked: bool):
        if checked:
            self.fx_btn.setStyleSheet(
                f"color: {theme.TEXT_PRIMARY}; font-weight: bold; "
                f"background-color: {theme.ACCENT_PRIMARY}; "
                f"border: 1px solid {theme.ACCENT_PRIMARY}; padding: 0px; font-size: 11px;"
            )
        else:
            self.fx_btn.setStyleSheet(
                f"color: {theme.TEXT_SECONDARY}; font-weight: bold; "
                f"background-color: #333333; border: 1px solid {theme.BORDER}; padding: 0px; font-size: 11px;"
            )
        self.fx_toggled.emit(self.stem_name, checked)

    def _on_name_edited(self):
        new_name = self.name_edit.text().strip()
        if new_name and new_name != self.stem_name:
            old_name = self.stem_name
            self.stem_name = new_name
            self.name_changed.emit(old_name, new_name)

    def _on_category_changed(self, category: str):
        self.category_changed.emit(self.stem_name, category)

    def set_volume(self, volume: float):
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(volume)
        self.volume_slider.blockSignals(False)

    def set_pan(self, pan: float):
        self.pan_slider.blockSignals(True)
        self.pan_slider.setValue(pan)
        self.pan_slider.blockSignals(False)

    def set_mute(self, muted: bool):
        self.mute_btn.blockSignals(True)
        self.mute_btn.setChecked(muted)
        self.mute_btn.blockSignals(False)
        self._on_mute_toggled(muted)

    def set_solo(self, solo: bool):
        self.solo_btn.blockSignals(True)
        self.solo_btn.setChecked(solo)
        self.solo_btn.blockSignals(False)
        self._on_solo_toggled(solo)

    def set_fx(self, fx: bool):
        self.fx_btn.blockSignals(True)
        self.fx_btn.setChecked(fx)
        self.fx_btn.blockSignals(False)
        self._on_fx_toggled(fx)
