import os
import json
import numpy as np
import copy
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QSlider, QLineEdit,
    QHeaderView, QMessageBox, QAbstractItemView, QStyleOptionSlider, QStyle,
    QSplitter, QPlainTextEdit, QDialog, QComboBox, QDialogButtonBox,
    QTextEdit, QToolTip
)
from PySide6.QtCore import Qt, Signal, QRect, QRegularExpression
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QDoubleValidator, QRegularExpressionValidator, QFont, QShortcut, QKeySequence
from app.ui.theme import current as theme
from app.ui.chordpro_editor import ChordProParser


class InsertSectionDialog(QDialog):
    def __init__(self, parent, options, default_index):
        super().__init__(parent)
        self.setWindowTitle("Añadir Nueva Sección")
        self.resize(350, 120)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme.BG_PRIMARY};
                color: {theme.TEXT_PRIMARY};
            }}
        """)
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("¿Dónde deseas añadir la nueva sección?"))

        self.combo = QComboBox()
        self.combo.addItems(options)
        self.combo.setCurrentIndex(default_index)
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 4px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                selection-background-color: {theme.ACCENT_PRIMARY};
            }}
        """)
        layout.addWidget(self.combo)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        # Style dialog buttons using theme
        self.buttons.button(QDialogButtonBox.Ok).setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_PRIMARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.ACCENT_PRIMARY};
                border-radius: {theme.BORDER_RADIUS_SM};
                font-weight: bold;
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: {theme.ACCENT_PRIMARY_HOVER};
            }}
        """)
        self.buttons.button(QDialogButtonBox.Cancel).setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 6px 14px;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_BRIGHTEN};
            }}
        """)
        layout.addWidget(self.buttons)

    def selected_index(self):
        return self.combo.currentIndex()


def seconds_to_str(seconds: float) -> str:
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:05.2f}"


def str_to_seconds(text: str) -> float:
    text = text.strip()
    if not text:
        return 0.0
    parts = text.split(':')
    if len(parts) == 1:
        return float(parts[0].replace(',', '.'))
    elif len(parts) == 2:
        m = float(parts[0])
        s = float(parts[1].replace(',', '.'))
        return m * 60.0 + s
    else:
        raise ValueError("Format error")


class SpinBoxWidget(QWidget):
    valueChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0.0
        self._min = 0.0
        self._max = 999999.0
        self._step = 0.5
        self._decimals = 2
        self._signals_blocked = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        btn_size = 22

        self.dec_btn = QPushButton("−")
        self.dec_btn.setFixedSize(btn_size, btn_size)
        self.dec_btn.setToolTip("Disminuir tiempo")
        self.dec_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: 3px;
                font-weight: bold;
                font-size: 12px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_BRIGHTEN};
                border: 1px solid {theme.BORDER_LIGHT};
            }}
            QPushButton:pressed {{
                background-color: {theme.PRESSED_DARKEN};
            }}
        """)
        self.dec_btn.clicked.connect(self._decrement)
        layout.addWidget(self.dec_btn)

        self.line_edit = QLineEdit()
        self.line_edit.setFixedWidth(90)
        self.line_edit.setAlignment(Qt.AlignCenter)
        self.line_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme.BG_PRIMARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BG_TERTIARY};
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme.ACCENT_PRIMARY};
            }}
        """)
        rx = QRegularExpression(r"^[0-9:,.]*$")
        validator = QRegularExpressionValidator(rx, self.line_edit)
        self.line_edit.setValidator(validator)
        self.line_edit.editingFinished.connect(self._on_editing_finished)
        self.line_edit.returnPressed.connect(self._on_editing_finished)
        layout.addWidget(self.line_edit)

        self.inc_btn = QPushButton("+")
        self.inc_btn.setFixedSize(btn_size, btn_size)
        self.inc_btn.setToolTip("Aumentar tiempo")
        self.inc_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: 3px;
                font-weight: bold;
                font-size: 12px;
                padding: 0px;
            }}
            QPushButton:hover {{
                background-color: {theme.HOVER_BRIGHTEN};
                border: 1px solid {theme.BORDER_LIGHT};
            }}
            QPushButton:pressed {{
                background-color: {theme.PRESSED_DARKEN};
            }}
        """)
        self.inc_btn.clicked.connect(self._increment)
        layout.addWidget(self.inc_btn)

        self._update_display()

    def setRange(self, min_val, max_val):
        self._min = float(min_val)
        self._max = float(max_val)
        self._clamp()

    def setDecimals(self, decimals):
        self._decimals = decimals
        format_str = f"{{:.{decimals}f}}"
        self._format_str = format_str
        self._update_display()

    def setSingleStep(self, step):
        self._step = float(step)

    def setValue(self, value):
        value = float(value)
        self._value = round(value, self._decimals)
        self._clamp()
        self._update_display()

    def value(self):
        return self._value

    def blockSignals(self, block):
        self._signals_blocked = block

    def set_decrement_enabled(self, enabled):
        self.dec_btn.setEnabled(enabled)

    def set_increment_enabled(self, enabled):
        self.inc_btn.setEnabled(enabled)

    def _clamp(self):
        if self._value < self._min:
            self._value = self._min
        if self._value > self._max:
            self._value = self._max

    def _update_display(self):
        self.line_edit.setText(seconds_to_str(self._value))

    def _emit_changed(self):
        if not self._signals_blocked:
            self.valueChanged.emit(self._value)

    def _find_parent_editor(self):
        p = self.parent()
        while p:
            if p.__class__.__name__ == "SyncEditor":
                return p
            p = p.parent()
        return None

    def _decrement(self):
        new_val = round(self._value - self._step, self._decimals)
        if new_val >= self._min:
            parent_editor = self._find_parent_editor()
            if parent_editor:
                parent_editor.push_undo_state()
            self._value = new_val
            self._update_display()
            self._emit_changed()

    def _increment(self):
        new_val = round(self._value + self._step, self._decimals)
        if new_val <= self._max:
            parent_editor = self._find_parent_editor()
            if parent_editor:
                parent_editor.push_undo_state()
            self._value = new_val
            self._update_display()
            self._emit_changed()

    def _on_editing_finished(self):
        text = self.line_edit.text().strip()
        if not text:
            self._update_display()
            return
        try:
            val = round(str_to_seconds(text), self._decimals)
            if val < self._min:
                val = self._min
            elif val > self._max:
                val = self._max
            if abs(val - self._value) > 0.001:
                parent_editor = self._find_parent_editor()
                if parent_editor:
                    parent_editor.push_undo_state()
                self._value = val
                self._update_display()
                self._emit_changed()
            else:
                self._update_display()
        except ValueError:
            self._update_display()


class WaveformSlider(QSlider):
    def __init__(self, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self._marks = []
        self._waveform = None
        self.setMouseTracking(True)

    def _find_parent_editor(self):
        p = self.parent()
        while p:
            if p.__class__.__name__ == "SyncEditor":
                return p
            p = p.parent()
        return None

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        parent_editor = self._find_parent_editor()
        if not parent_editor:
            return
        total_seconds = parent_editor._get_total_seconds()
        if total_seconds <= 0:
            return

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        groove_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderGroove, self
        )
        handle_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderHandle, self
        )
        groove_left = groove_rect.left() + handle_rect.width() // 2
        groove_right = groove_rect.right() - handle_rect.width() // 2
        groove_width = groove_right - groove_left

        if groove_width > 0:
            mouse_x = event.position().x()
            ratio = (mouse_x - groove_left) / groove_width
            ratio = max(0.0, min(1.0, ratio))
        else:
            ratio = 0.0

        target_seconds = ratio * total_seconds
        sections = parent_editor._get_sections_from_table()
        hovered_section_name = None
        for sec in sections:
            if sec["start"] <= target_seconds <= sec["end"]:
                hovered_section_name = sec["label"]
                break

        if hovered_section_name:
            tooltip_text = f"{hovered_section_name}\n{seconds_to_str(target_seconds)}"
            QToolTip.showText(self.mapToGlobal(event.pos()), tooltip_text, self)
        else:
            QToolTip.hideText()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        QToolTip.hideText()

    def set_marks(self, positions_0_1000):
        self._marks = sorted(positions_0_1000)
        self.update()

    def set_waveform(self, waveform):
        self._waveform = waveform
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        groove_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderGroove, self
        )

        handle_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider, opt,
            QStyle.SubControl.SC_SliderHandle, self
        )

        groove_left = groove_rect.left() + handle_rect.width() // 2
        groove_right = groove_rect.right() - handle_rect.width() // 2
        groove_width = groove_right - groove_left

        if groove_width <= 0:
            super().paintEvent(event)
            painter.end()
            return

        custom_groove_height = 36
        groove_top = (self.height() - custom_groove_height) // 2
        groove_bg = QRect(groove_left, groove_top, groove_width, custom_groove_height)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(theme.BG_TERTIARY)))
        painter.drawRoundedRect(groove_bg, 4, 4)

        value_range = max(1, self.maximum() - self.minimum())
        playhead_ratio = self.value() / value_range
        sub_width = int(playhead_ratio * groove_width)
        if sub_width > 0:
            sub_rect = QRect(groove_left, groove_top, sub_width, custom_groove_height)
            highlight_color = QColor(theme.ACCENT_INFO)
            highlight_color.setAlpha(40)
            painter.setBrush(QBrush(highlight_color))
            painter.drawRoundedRect(sub_rect, 4, 4)

        if self._waveform is not None and len(self._waveform) > 1:
            num_points = len(self._waveform)
            mid_y = groove_bg.center().y()
            half_h = (custom_groove_height - 6) // 2

            for i in range(num_points):
                x = groove_left + int((i / (num_points - 1)) * groove_width)
                amplitude = self._waveform[i]
                bar_h = max(2, int(amplitude * half_h * 2))
                
                bar_ratio = i / (num_points - 1)
                if bar_ratio <= playhead_ratio:
                    color = QColor(theme.ACCENT_INFO)
                else:
                    color = QColor(theme.TEXT_MUTED)
                    color.setAlpha(120)
                
                painter.setBrush(QBrush(color))
                painter.drawRect(x, mid_y - bar_h // 2, max(1, groove_width // num_points), bar_h)

        handle_x = groove_left + sub_width - handle_rect.width() // 2
        handle_y = groove_bg.center().y() - handle_rect.height() // 2
        handle_r = QRect(handle_x, handle_y, handle_rect.width(), handle_rect.height())
        painter.setBrush(QBrush(QColor(theme.ACCENT_INFO)))
        painter.setPen(QPen(QColor(theme.TEXT_PRIMARY), 1))
        painter.drawEllipse(handle_r)

        if self._marks:
            painter.setPen(QPen(QColor(theme.ACCENT_WARNING), 2))
            for pos in self._marks:
                x = groove_left + int(pos / 1000.0 * groove_width)
                if 0 <= pos <= 1000:
                    painter.drawLine(x, groove_top, x, groove_top + custom_groove_height)

        painter.end()


class SyncEditor(QWidget):
    saved = Signal()

    def __init__(self, controller, sync_path, chopro_path):
        super().__init__()
        self.controller = controller
        self.sync_path = sync_path
        self.chopro_path = chopro_path
        self._ignore_progress = False

        # Undo/Redo & ChordPro parsing
        self.undo_stack = []
        self.redo_stack = []
        self._chopro_text_modified = False
        self.parsed_chopro = ChordProParser.parse(chopro_path)

        song_name = controller.state.current_song_name or "Sin cancion"
        self.setWindowTitle(f"Editor de Sincronizacion - {song_name}")
        self.resize(950, 650)

        self._setup_ui()
        self._compute_waveform()
        self._load_sync()

        # Connect rename handler after loading sync, so we don't trigger it on load
        self.table.itemChanged.connect(self._on_item_changed)
        self._update_full_chopro_display()

    def _compute_waveform(self):
        stems = self.controller.state.stems
        if not stems:
            return
        max_len = max(len(s["audio"]) for s in stems.values())
        if max_len <= 0:
            return

        target_points = 500
        mix = np.zeros(max_len, dtype=np.float32)
        for s in stems.values():
            audio = s["audio"]
            if len(audio) > 0:
                mix[:len(audio)] += audio.astype(np.float32) * s.get("volume", 1.0)

        step = max(1, len(mix) // target_points)
        envelope = np.zeros(target_points)
        for i in range(target_points):
            start = i * step
            end = min(start + step, len(mix))
            segment = mix[start:end]
            if len(segment) > 0:
                envelope[i] = np.max(np.abs(segment))

        peak = np.max(envelope)
        if peak > 0:
            envelope /= peak
        self.seek_slider.set_waveform(envelope)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)
        self._build_playback_bar(layout)

        # Horizontal splitter for Table and ChordPro Editor
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {theme.BG_TERTIARY}; }}")

        # Left widget (table)
        table_container = QWidget()
        table_layout = QVBoxLayout(table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(8)

        self._build_table(table_layout)

        self.splitter.addWidget(table_container)

        # Right widget (ChordPro Editor)
        chopro_container = QWidget()
        chopro_layout = QVBoxLayout(chopro_container)
        chopro_layout.setContentsMargins(0, 0, 0, 0)
        chopro_layout.setSpacing(8)

        self.chopro_title = QLabel("Contenido de Sección (ChordPro)")
        self.chopro_title.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {theme.TEXT_PRIMARY};")
        chopro_layout.addWidget(self.chopro_title)

        self.chopro_status = QLabel("Seleccione una sección en la tabla")
        self.chopro_status.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        chopro_layout.addWidget(self.chopro_status)

        self.chopro_edit = QPlainTextEdit()
        self.chopro_edit.setFont(QFont("Consolas", 11))
        self.chopro_edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {theme.BG_SECONDARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BG_TERTIARY};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 8px;
            }}
        """)
        self.chopro_edit.setEnabled(False)
        self.chopro_edit.textChanged.connect(self._on_chopro_text_changed)
        chopro_layout.addWidget(self.chopro_edit)

        self.splitter.addWidget(chopro_container)

        # Full ChordPro view container
        full_chopro_container = QWidget()
        full_chopro_layout = QVBoxLayout(full_chopro_container)
        full_chopro_layout.setContentsMargins(0, 0, 0, 0)
        full_chopro_layout.setSpacing(8)

        self.full_chopro_title = QLabel("Contenido Completo (ChoPro)")
        self.full_chopro_title.setStyleSheet(f"font-weight: bold; font-size: 13px; color: {theme.TEXT_PRIMARY};")
        full_chopro_layout.addWidget(self.full_chopro_title)

        self.full_chopro_status = QLabel("Archivo ChordPro completo")
        self.full_chopro_status.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px;")
        full_chopro_layout.addWidget(self.full_chopro_status)

        self.full_chopro_view = QTextEdit()
        self.full_chopro_view.setReadOnly(True)
        self.full_chopro_view.setFont(QFont("Consolas", 11))
        self.full_chopro_view.setStyleSheet(f"""
            QTextEdit {{
                background-color: {theme.BG_SECONDARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BG_TERTIARY};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 8px;
            }}
        """)
        full_chopro_layout.addWidget(self.full_chopro_view)

        self.splitter.addWidget(full_chopro_container)

        # Set initial sizes (Table: 40%, Active section: 30%, Full ChordPro: 30%)
        self.splitter.setSizes([450, 275, 275])
        layout.addWidget(self.splitter, stretch=1)

        self._build_buttons(layout)

        # Shortcuts for Undo/Redo
        self.undo_shortcut = QShortcut(QKeySequence.Undo, self)
        self.undo_shortcut.activated.connect(self._on_undo)
        self.redo_shortcut = QShortcut(QKeySequence.Redo, self)
        self.redo_shortcut.activated.connect(self._on_redo)

    def _build_playback_bar(self, parent_layout):
        playback_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶")
        self.play_btn.setFixedSize(40, 32)
        self.play_btn.setToolTip("Reproducir / Pausar")
        self.play_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_SUCCESS};
                color: #FFFFFF;
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                font-weight: bold;
                font-size: 16px;
            }}
            QPushButton:hover {{ background-color: #66BB6A; }}
        """)
        self.play_btn.clicked.connect(self._toggle_playback)
        playback_layout.addWidget(self.play_btn)

        self.seek_slider = WaveformSlider()
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setValue(0)
        self.seek_slider.setFixedHeight(48)
        self.seek_slider.setStyleSheet("QSlider { background: transparent; }")
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.seek_slider.valueChanged.connect(self._on_seek_value_changed)
        playback_layout.addWidget(self.seek_slider, stretch=1)

        self.time_label = QLabel("00:00.00 / 00:00.00")
        self.time_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 13px;")
        playback_layout.addWidget(self.time_label)

        self.copy_time_btn = QPushButton("📋")
        self.copy_time_btn.setToolTip("Copiar tiempo actual")
        self.copy_time_btn.setFixedSize(32, 32)
        self.copy_time_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {theme.HOVER_BRIGHTEN}; }}
        """)
        self.copy_time_btn.clicked.connect(self._copy_current_time)
        playback_layout.addWidget(self.copy_time_btn)

        parent_layout.addLayout(playback_layout)

    def _build_table(self, parent_layout):
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Seccion", "Inicio", "Fin", ""])
        h = self.table.horizontalHeader()
        h.setStretchLastSection(False)
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 150)
        self.table.setColumnWidth(3, 60)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setDefaultSectionSize(28)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {theme.BG_SECONDARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BG_TERTIARY};
                border-radius: {theme.BORDER_RADIUS_SM};
                gridline-color: {theme.BG_TERTIARY};
            }}
            QTableWidget::item {{ padding: 2px 6px; }}
            QHeaderView::section {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_MUTED};
                padding: 6px;
                border: none;
                font-weight: bold;
            }}
        """)
        self.table.currentCellChanged.connect(self._on_cell_changed)
        parent_layout.addWidget(self.table, stretch=1)

    def _build_buttons(self, parent_layout):
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ Anadir seccion")
        self.add_btn.setToolTip("Añadir una nueva sección a la tabla")
        self.add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_INFO};
                color: #FFFFFF;
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 6px 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #42A5F5; }}
        """)
        self.add_btn.clicked.connect(self._add_section)
        btn_layout.addWidget(self.add_btn)

        self.undo_btn = QPushButton("↩ Deshacer")
        self.undo_btn.setToolTip("Deshacer ultima accion (Ctrl+Z)")
        self.undo_btn.setEnabled(False)
        self.undo_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 6px 14px;
            }}
            QPushButton:hover {{ background-color: {theme.HOVER_BRIGHTEN}; }}
            QPushButton:disabled {{ opacity: 0.5; color: {theme.TEXT_MUTED}; }}
        """)
        self.undo_btn.clicked.connect(self._on_undo)
        btn_layout.addWidget(self.undo_btn)

        self.redo_btn = QPushButton("↪ Rehacer")
        self.redo_btn.setToolTip("Rehacer ultima accion (Ctrl+Y)")
        self.redo_btn.setEnabled(False)
        self.redo_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 6px 14px;
            }}
            QPushButton:hover {{ background-color: {theme.HOVER_BRIGHTEN}; }}
            QPushButton:disabled {{ opacity: 0.5; color: {theme.TEXT_MUTED}; }}
        """)
        self.redo_btn.clicked.connect(self._on_redo)
        btn_layout.addWidget(self.redo_btn)

        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.setToolTip("Descartar cambios y salir del editor")
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 6px 14px;
            }}
            QPushButton:hover {{ background-color: {theme.HOVER_BRIGHTEN}; }}
        """)
        self.cancel_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Guardar")
        self.save_btn.setToolTip("Guardar sincronización y archivo ChordPro")
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_SUCCESS};
                color: #FFFFFF;
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 6px 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #66BB6A; }}
        """)
        self.save_btn.clicked.connect(self._save)
        btn_layout.addWidget(self.save_btn)
        parent_layout.addLayout(btn_layout)

    def _spin_value(self, row, col):
        spin = self.table.cellWidget(row, col)
        return spin.value() if spin else 0.0

    def _set_spin(self, row, col, value):
        spin = self.table.cellWidget(row, col)
        if spin:
            spin.blockSignals(True)
            spin.setValue(round(value, 2))
            spin.blockSignals(False)

    def _on_start_changed(self, row):
        value = self._spin_value(row, 1)
        if row > 0:
            self._set_spin(row - 1, 2, value)
        self._update_marks()
        self._update_button_states()

    def _on_end_changed(self, row):
        value = self._spin_value(row, 2)
        if row + 1 < self.table.rowCount():
            self._set_spin(row + 1, 1, value)
        self._update_marks()
        self._update_button_states()

    def _update_button_states(self):
        total_s = self._get_total_seconds()
        for r in range(self.table.rowCount()):
            start_spin = self.table.cellWidget(r, 1)
            end_spin = self.table.cellWidget(r, 2)
            if start_spin and end_spin:
                start_spin.set_decrement_enabled(r > 0 or start_spin.value() > 0.001)
                end_spin.set_increment_enabled(
                    r + 1 < self.table.rowCount() or
                    (total_s > 0 and end_spin.value() + end_spin._step < total_s)
                )

    def _get_total_samples(self):
        stems = self.controller.state.stems
        if not stems:
            return 0
        max_len = max(len(s["audio"]) for s in stems.values())
        bpm = self.controller.state.detected_bpm or 120
        mix_sr = self.controller.state.mix_sr
        beats_per_bar = 4
        count_in_beats = self.controller.state.count_in_bars * beats_per_bar
        count_in_samples = int(count_in_beats * mix_sr * 60 / bpm) if count_in_beats > 0 else 0
        return max_len + count_in_samples

    def _get_total_seconds(self):
        total_samples = self._get_total_samples()
        mix_sr = self.controller.state.mix_sr
        if total_samples <= 0 or mix_sr <= 0:
            return 0
        return total_samples / mix_sr

    def _load_sync(self):
        self.table.setRowCount(0)
        if not os.path.exists(self.sync_path):
            return
        try:
            with open(self.sync_path, 'r', encoding='utf-8') as f:
                sync_data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo leer sync.json:\n{e}")
            return

        sections = sync_data.get("sections", [])
        for sec in sections:
            self._add_row(sec.get("label", ""), float(sec.get("start", 0)), float(sec.get("end", 10)))
        self._update_marks()
        self._update_button_states()

    def _add_row(self, label="Nueva seccion", start=0.0, end=10.0, row=None):
        if row is None:
            row = self.table.rowCount()
        self.table.insertRow(row)

        name_item = QTableWidgetItem(label)
        name_item.setData(Qt.UserRole, label)
        self.table.setItem(row, 0, name_item)

        start_spin = SpinBoxWidget()
        start_spin.setRange(0, 999999)
        start_spin.setDecimals(2)
        start_spin.setSingleStep(0.5)
        start_spin.setValue(round(start, 2))
        start_spin.valueChanged.connect(lambda val, w=start_spin: self._on_start_changed(self._row_of_widget(w, 1)))
        self.table.setCellWidget(row, 1, start_spin)

        end_spin = SpinBoxWidget()
        end_spin.setRange(0, 999999)
        end_spin.setDecimals(2)
        end_spin.setSingleStep(0.5)
        end_spin.setValue(round(end, 2))
        end_spin.valueChanged.connect(lambda val, w=end_spin: self._on_end_changed(self._row_of_widget(w, 2)))
        self.table.setCellWidget(row, 2, end_spin)

        del_btn = QPushButton("✕")
        del_btn.setFixedSize(32, 28)
        del_btn.setToolTip("Eliminar esta sección")
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_DANGER_ALT};
                color: #FFFFFF;
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: #FF3333; }}
        """)
        del_btn.clicked.connect(lambda checked=False, b=del_btn: self._delete_row(self._row_of_widget(b, 3)))
        self.table.setCellWidget(row, 3, del_btn)

    def _row_of_widget(self, widget, col):
        for r in range(self.table.rowCount()):
            if self.table.cellWidget(r, col) is widget:
                return r
        return -1

    def _delete_row(self, row):
        if row < 0 or row >= self.table.rowCount():
            return
        if self.table.rowCount() <= 1:
            QMessageBox.warning(self, "Error", "Debe haber al menos una seccion.")
            return

        # Confirmation dialog before deletion
        reply = QMessageBox.question(
            self, 
            "Confirmar eliminación", 
            "¿Está seguro de que desea eliminar esta sección?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.push_undo_state()

        self.table.blockSignals(True)
        deleted_start = self._spin_value(row, 1)

        self.table.removeRow(row)

        # Timestamp auto-adjust: update next and previous sections if they exist
        if row < self.table.rowCount():
            self._set_spin(row, 1, deleted_start)
            if row > 0:
                self._set_spin(row - 1, 2, deleted_start)
        self.table.blockSignals(False)

        # Select the active row
        new_row = self.table.currentRow()
        self._on_row_selected(new_row, -1)

        self._update_marks()
        self._update_button_states()
        self._update_full_chopro_display()

    def _add_section(self):
        self.push_undo_state()
        total_rows = self.table.rowCount()

        if total_rows == 0:
            self.table.blockSignals(True)
            self._add_row("Nueva seccion", 0.0, 10.0, row=0)
            self.table.blockSignals(False)
            idx = 0
        else:
            options = ["Al principio"]
            for r in range(total_rows):
                name_item = self.table.item(r, 0)
                name = name_item.text().strip() if name_item else f"Seccion {r+1}"
                options.append(f"Despues de: {r+1}. {name}")

            dialog = InsertSectionDialog(self, options, total_rows)
            if dialog.exec() != QDialog.Accepted:
                return

            idx = dialog.selected_index()

            self.table.blockSignals(True)

            if idx == 0:
                n_start = self._spin_value(0, 1)
                n_end = self._spin_value(0, 2)
                n_dur = n_end - n_start
                take_n = min(1.0, n_dur - 0.1) if n_dur > 0.1 else 0.0

                self._set_spin(0, 1, n_start + take_n)
                self._add_row("Nueva seccion", n_start, n_start + take_n, row=0)

            elif idx == total_rows:
                p_start = self._spin_value(total_rows - 1, 1)
                p_end = self._spin_value(total_rows - 1, 2)
                p_dur = p_end - p_start
                take_p = min(1.0, p_dur - 0.1) if p_dur > 0.1 else 0.0

                self._set_spin(total_rows - 1, 2, p_end - take_p)
                self._add_row("Nueva seccion", p_end - take_p, p_end, row=total_rows)

            else:
                p_start = self._spin_value(idx - 1, 1)
                p_end = self._spin_value(idx - 1, 2)

                n_start = self._spin_value(idx, 1)
                n_end = self._spin_value(idx, 2)

                mid = p_end
                p_dur = p_end - p_start
                n_dur = n_end - n_start

                take_p = min(0.5, p_dur - 0.1) if p_dur > 0.1 else 0.0
                take_n = min(0.5, n_dur - 0.1) if n_dur > 0.1 else 0.0

                self._set_spin(idx - 1, 2, mid - take_p)
                self._set_spin(idx, 1, mid + take_n)

                self._add_row("Nueva seccion", mid - take_p, mid + take_n, row=idx)

            self.table.blockSignals(False)

        self.table.setCurrentCell(idx, 0)
        self._on_row_selected(idx, -1)

        self._update_marks()
        self._update_button_states()
        self._update_full_chopro_display()

    def _get_sections_from_table(self):
        sections = []
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            start = self._spin_value(r, 1)
            end = self._spin_value(r, 2)
            if name_item:
                name = name_item.text().strip()
                if not name:
                    name = f"Seccion {r+1}"
                sections.append({"label": name, "start": start, "end": end})
        return sections

    def _validate_sections(self):
        sections = self._get_sections_from_table()
        if not sections:
            QMessageBox.warning(self, "Error", "Debe haber al menos una seccion.")
            return False
        for i, sec in enumerate(sections):
            if sec["end"] <= sec["start"]:
                QMessageBox.warning(self, "Error",
                    f"'{sec['label']}': fin ({sec['end']}) <= inicio ({sec['start']}).")
                return False
        return True

    def _update_marks(self):
        sections = self._get_sections_from_table()
        total_s = self._get_total_seconds()
        if total_s <= 0:
            return
        marks = []
        for sec in sections:
            for pos in (int((sec["start"] / total_s) * 1000), int((sec["end"] / total_s) * 1000)):
                if 0 <= pos <= 1000:
                    marks.append(pos)
        self.seek_slider.set_marks(marks)

    def _toggle_playback(self):
        controller = self.controller
        pt = controller.threads.playback_thread
        if pt and pt.is_playing:
            controller._pause_playback()
            self.play_btn.setText("▶")
        else:
            controller._start_playback()
            self.play_btn.setText("⏸")
            self._connect_progress()

    def _connect_progress(self):
        pt = self.controller.threads.playback_thread
        if pt:
            try:
                pt.update_progress.connect(self.update_progress, Qt.ConnectionType.UniqueConnection)
            except Exception:
                pass

    def _on_seek_pressed(self):
        self._ignore_progress = True

    def _on_seek_released(self):
        self._ignore_progress = False
        self._apply_seek()

    def _on_seek_value_changed(self, value):
        if self._ignore_progress:
            self._update_time_label(value)

    def _apply_seek(self):
        value = self.seek_slider.value()
        total_samples = self._get_total_samples()
        if total_samples <= 0:
            return
        absolute_pos = int((value / 1000.0) * total_samples)
        controller = self.controller
        pt = controller.threads.playback_thread
        if pt and pt.isRunning():
            pt.seek(absolute_pos)
        else:
            controller._pending_seek = absolute_pos
        self._update_time_label(value)

    def _update_time_label(self, slider_value):
        total_seconds = self._get_total_seconds()
        if total_seconds <= 0:
            self.time_label.setText("00:00.00 / 00:00.00")
            return
        current_seconds = (slider_value / 1000.0) * total_seconds
        self.time_label.setText(f"{seconds_to_str(current_seconds)} / {seconds_to_str(total_seconds)}")

    def _copy_current_time(self):
        total_seconds = self._get_total_seconds()
        if total_seconds <= 0:
            return
        value = self.seek_slider.value()
        current_seconds = (value / 1000.0) * total_seconds
        time_str = seconds_to_str(current_seconds)

        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(time_str)
        self.controller.status_label.setText(f"Tiempo copiado: {time_str}")

    def _highlight_section_at_time(self, seconds):
        sections = self._get_sections_from_table()
        found = -1
        for i, sec in enumerate(sections):
            if sec["start"] <= seconds < sec["end"]:
                found = i
                break

        for r in range(self.table.rowCount()):
            if r == found:
                bg = QColor(theme.ACCENT_PRIMARY)
                bg.setAlpha(40)
            elif r % 2 == 0:
                bg = QColor(theme.BG_SECONDARY)
            else:
                bg = QColor(theme.BG_TERTIARY).lighter(110)
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item:
                    item.setBackground(bg)

    def update_progress(self, value: float):
        if self._ignore_progress:
            return
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(int(value * 1000))
        self.seek_slider.blockSignals(False)
        self._update_time_label(int(value * 1000))

        total_seconds = self._get_total_seconds()
        if total_seconds > 0:
            self._highlight_section_at_time(value * total_seconds)

    def _save(self):
        if not self._validate_sections():
            return

        # Save current active row's text first
        row = self.table.currentRow()
        if row >= 0 and self.chopro_edit.isEnabled():
            self._save_active_chopro_section(row)

        # 1. Save sync.json
        sections = self._get_sections_from_table()
        sync_data = {"sections": sections}
        try:
            with open(self.sync_path, 'w', encoding='utf-8') as f:
                json.dump(sync_data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar sync.json:\n{e}")
            return

        # 2. Save .chopro file matching the exact table order
        ordered_sections = []
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            label = name_item.text().strip() if name_item else f"Seccion {r+1}"
            sec = self._find_chopro_section(label)
            if not sec:
                sec = {"name": label, "lines": [], "tag": "comment"}
            ordered_sections.append(sec)

        try:
            with open(self.chopro_path, "w", encoding="utf-8") as f:
                meta = self.parsed_chopro.get("metadata", {})
                if meta.get("title"):
                    f.write(f"{{title: {meta['title']}}}\n")
                if meta.get("artist"):
                    f.write(f"{{artist: {meta['artist']}}}\n")
                if meta.get("key"):
                    f.write(f"{{key: {meta['key']}}}\n\n")

                for sec in ordered_sections:
                    tag = sec.get("tag", "comment")
                    if tag == "comment":
                        f.write(f"{{c: {sec['name']}}}\n")
                    elif tag and tag.startswith("start_of_"):
                        f.write(f"{{{tag}: {sec['name']}}}\n")
                    else:
                        f.write(f"{{c: {sec['name']}}}\n")

                    for line in sec["lines"]:
                        f.write(line + "\n")

                    if tag and tag.startswith("start_of_"):
                        end_tag = tag.replace("start_of_", "end_of_")
                        f.write(f"{{{end_tag}}}\n")

                    f.write("\n")
        except OSError as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar el archivo ChordPro:\n{e}")
            return

        self.controller.live_display_widget.load_sync_data(self.chopro_path, self.sync_path)
        self.controller.status_label.setText("Sincronización y contenido ChordPro guardados.")
        self.saved.emit()

    def closeEvent(self, event):
        controller = self.controller
        pt = controller.threads.playback_thread
        if pt and pt.is_playing:
            controller._pause_playback()
        super().closeEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._connect_progress()

    def _on_cell_changed(self, currentRow, currentColumn, previousRow, previousColumn):
        if currentRow != previousRow:
            self._on_row_selected(currentRow, previousRow)

    def _on_row_selected(self, new_row, old_row):
        # Save old row's text
        if old_row >= 0 and self.chopro_edit.isEnabled():
            self._save_active_chopro_section(old_row)

        if new_row < 0 or new_row >= self.table.rowCount():
            self.chopro_edit.clear()
            self.chopro_edit.setEnabled(False)
            self.chopro_status.setText("Seleccione una sección")
            self._update_full_chopro_display()
            return

        name_item = self.table.item(new_row, 0)
        label = name_item.text().strip() if name_item else f"Seccion {new_row + 1}"

        # Find matching chopro section
        sec = self._find_chopro_section(label)
        self.chopro_edit.blockSignals(True)
        if sec:
            self.chopro_edit.setPlainText("\n".join(sec["lines"]))
            self.chopro_status.setText(f"Vinculado a sección: '{sec['name']}'")
        else:
            self.chopro_edit.setPlainText("")
            self.chopro_status.setText(f"Nueva sección (se creará en ChordPro): '{label}'")
        self.chopro_edit.blockSignals(False)
        self.chopro_edit.setEnabled(True)
        self._chopro_text_modified = False
        self._update_full_chopro_display()

    def _find_chopro_section(self, sync_label):
        if not self.parsed_chopro or "sections" not in self.parsed_chopro:
            return None
        for sec in self.parsed_chopro["sections"]:
            if self._match_sync_section(sec.get("name", ""), sync_label):
                return sec
        return None

    def _match_sync_section(self, section_name, sync_label):
        a = section_name.lower().rstrip('.')
        b = sync_label.lower().rstrip('.')
        if a == b:
            return True
        a_first = a.split()[0] if a.split() else a
        b_first = b.split()[0] if b.split() else b
        if len(a_first) > 2 and a_first == b_first:
            return True
        return False

    def _save_active_chopro_section(self, row):
        if row < 0 or row >= self.table.rowCount():
            return False
        name_item = self.table.item(row, 0)
        label = name_item.text().strip() if name_item else f"Seccion {row+1}"

        sec = self._find_chopro_section(label)
        if not sec:
            sec = {"name": label, "lines": [], "tag": "comment"}
            self.parsed_chopro["sections"].append(sec)

        new_lines = self.chopro_edit.toPlainText().split('\n')
        if sec["lines"] != new_lines:
            sec["lines"] = new_lines
            return True
        return False

    def _on_chopro_text_changed(self):
        if not self._chopro_text_modified:
            self.push_undo_state()
            self._chopro_text_modified = True
        self._update_full_chopro_display()

    def _on_item_changed(self, item):
        if item.column() != 0:
            return

        row = item.row()
        new_name = item.text().strip()
        old_name = item.data(Qt.UserRole)

        if not new_name:
            self.table.blockSignals(True)
            item.setText(old_name)
            self.table.blockSignals(False)
            return

        if new_name == old_name:
            return

        self.push_undo_state()

        sec = self._find_chopro_section(old_name)
        if sec:
            sec["name"] = new_name
            if row == self.table.currentRow():
                self.chopro_status.setText(f"Vinculado a sección: '{new_name}'")

        item.setData(Qt.UserRole, new_name)

        self._update_marks()
        self._update_full_chopro_display()

    def _update_full_chopro_display(self):
        row = self.table.currentRow()
        active_label = None
        if row >= 0:
            name_item = self.table.item(row, 0)
            if name_item:
                active_label = name_item.text().strip()

        # Build HTML representation
        html_parts = []
        html_parts.append("<div style='font-family: Consolas, monospace; font-size: 11pt; line-height: 1.3;'>")

        # Metadata
        meta = self.parsed_chopro.get("metadata", {})
        if meta.get("title"):
            html_parts.append(f"{{title: {meta['title']}}}<br>")
        if meta.get("artist"):
            html_parts.append(f"{{artist: {meta['artist']}}}<br>")
        if meta.get("key"):
            html_parts.append(f"{{key: {meta['key']}}}<br>")
        html_parts.append("<br>")

        # Traverse rows in order to construct the full text
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            label = name_item.text().strip() if name_item else f"Seccion {r+1}"
            sec = self._find_chopro_section(label)
            if not sec:
                sec = {"name": label, "lines": [], "tag": "comment"}

            is_active = (active_label is not None and self._match_sync_section(sec.get("name", ""), active_label))

            if is_active:
                lines = self.chopro_edit.toPlainText().split('\n')
                color_val = theme.ACCENT_CYAN
                span_start = f"<span style='color: {color_val}; font-weight: bold;'>"
                span_end = "</span>"
            else:
                lines = sec.get("lines", [])
                color_val = theme.TEXT_MUTED
                span_start = f"<span style='color: {color_val};'>"
                span_end = "</span>"

            tag = sec.get("tag", "comment")
            if tag == "comment":
                header = f"{{c: {sec['name']}}}"
            elif tag and tag.startswith("start_of_"):
                header = f"{{{tag}: {sec['name']}}}"
            else:
                header = f"{{c: {sec['name']}}}"

            anchor_str = "<a name='active_sec'></a>" if is_active else ""
            html_parts.append(f"{anchor_str}{span_start}{header}{span_end}<br>")

            for line in lines:
                escaped_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                html_parts.append(f"{span_start}{escaped_line}{span_end}<br>")

            if tag and tag.startswith("start_of_"):
                end_tag = tag.replace("start_of_", "end_of_")
                html_parts.append(f"{span_start}{{{end_tag}}}{span_end}<br>")

            html_parts.append("<br>")

        html_parts.append("</div>")
        self.full_chopro_view.setHtml("".join(html_parts))
        if active_label:
            self.full_chopro_view.scrollToAnchor("active_sec")

    def push_undo_state(self):
        state = self.get_current_editor_state()
        self.undo_stack.append(state)
        self.redo_stack.clear()
        self._update_undo_redo_actions()

    def get_current_editor_state(self):
        table_sections = []
        for r in range(self.table.rowCount()):
            name_item = self.table.item(r, 0)
            label = name_item.text() if name_item else ""
            start = self._spin_value(r, 1)
            end = self._spin_value(r, 2)
            table_sections.append({"label": label, "start": start, "end": end})

        chopro_state = copy.deepcopy(self.parsed_chopro)

        return {
            "table_sections": table_sections,
            "chopro": chopro_state,
            "selected_row": self.table.currentRow()
        }

    def restore_editor_state(self, state):
        if not state:
            return

        self.table.blockSignals(True)
        self.chopro_edit.blockSignals(True)

        self.parsed_chopro = copy.deepcopy(state["chopro"])

        self.table.setRowCount(0)
        for sec in state["table_sections"]:
            self._add_row(sec["label"], sec["start"], sec["end"])

        self.table.blockSignals(False)
        self.chopro_edit.blockSignals(False)

        sel_row = state["selected_row"]
        if 0 <= sel_row < self.table.rowCount():
            self.table.setCurrentCell(sel_row, 0)
            self._on_row_selected(sel_row, -1)
        else:
            self.chopro_edit.clear()
            self.chopro_edit.setEnabled(False)
            self.chopro_status.setText("Seleccione una sección")

        self._update_marks()
        self._update_button_states()
        self._chopro_text_modified = False
        self._update_full_chopro_display()

    def _on_undo(self):
        row = self.table.currentRow()
        if row >= 0 and self.chopro_edit.isEnabled():
            self._save_active_chopro_section(row)

        current_state = self.get_current_editor_state()
        prev_state = self.undo_stack.pop() if self.undo_stack else None
        if prev_state:
            self.redo_stack.append(current_state)
            self.restore_editor_state(prev_state)
            self._update_undo_redo_actions()

    def _on_redo(self):
        row = self.table.currentRow()
        if row >= 0 and self.chopro_edit.isEnabled():
            self._save_active_chopro_section(row)

        current_state = self.get_current_editor_state()
        next_state = self.redo_stack.pop() if self.redo_stack else None
        if next_state:
            self.undo_stack.append(current_state)
            self.restore_editor_state(next_state)
            self._update_undo_redo_actions()

    def _update_undo_redo_actions(self):
        self.undo_btn.setEnabled(len(self.undo_stack) > 0)
        self.redo_btn.setEnabled(len(self.redo_stack) > 0)
