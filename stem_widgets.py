"""Widgets personalizados para el panel de stems."""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
    QLineEdit, QComboBox, QMenu, QStyleOptionSlider, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QIcon, QColor, QPainter, QPen, QFont
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QSize
from utils import STEM_CATEGORIES


def svg_icon(path: str, color: str = "#FFFFFF") -> QIcon:
    """Carga un icono SVG y le aplica un color."""
    renderer = QSvgRenderer(path)
    from PySide6.QtGui import QPixmap, QPainter
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return QIcon(pixmap)


class VolumeSlider(QWidget):
    """Custom horizontal volume slider with dB scale and enhanced design."""
    
    valueChanged = Signal(float)
    
    def __init__(self, parent=None, icons_dir: str = "./icons/svgs"):
        super().__init__(parent)
        self.icons_dir = icons_dir
        self.setMinimumSize(120, 50)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Volume range: 0 (mute) to 1.2 (120% = +6dB)
        self._value = 1.0
        self._minimum = 0.0
        self._maximum = 1.2
        
        # Load slider handle icon
        self.handle_icon = None
        handle_path = os.path.join(icons_dir, "fad-sliderhandle-1-white.svg")
        if os.path.exists(handle_path):
            self.handle_icon = QSvgRenderer(handle_path)
        
        # Mouse tracking
        self.setMouseTracking(True)
        self._dragging = False
        
        # Scale points for piecewise linear visual mapping: (ratio, value, label)
        self.scale_points = [
            (0.0, 0.0, "-∞"),
            (0.25, 0.1, "-20dB"),
            (0.5, 0.5, "-6dB"),
            (0.75, 1.0, "0dB"),
            (1.0, 1.2, "+6dB")
        ]
    
    def value(self) -> float:
        return self._value
    
    def setValue(self, value: float):
        value = max(self._minimum, min(self._maximum, value))
        if value != self._value:
            self._value = value
            self.update()
            self.valueChanged.emit(value)
    
    def _value_to_ratio(self, value: float) -> float:
        for i in range(len(self.scale_points) - 1):
            r1, v1, _ = self.scale_points[i]
            r2, v2, _ = self.scale_points[i+1]
            if v1 <= value <= v2:
                if v2 == v1: return r1
                return r1 + (r2 - r1) * (value - v1) / (v2 - v1)
        if value < self.scale_points[0][1]: return self.scale_points[0][0]
        return self.scale_points[-1][0]
        
    def _ratio_to_value(self, ratio: float) -> float:
        for i in range(len(self.scale_points) - 1):
            r1, v1, _ = self.scale_points[i]
            r2, v2, _ = self.scale_points[i+1]
            if r1 <= ratio <= r2:
                if r2 == r1: return v1
                return v1 + (v2 - v1) * (ratio - r1) / (r2 - r1)
        if ratio < self.scale_points[0][0]: return self.scale_points[0][1]
        return self.scale_points[-1][1]

    def _value_to_x(self, value: float) -> int:
        """Convert value to X coordinate."""
        ratio = self._value_to_ratio(value)
        return int(10 + ratio * (self.width() - 20))
    
    def _x_to_value(self, x: int) -> float:
        """Convert X coordinate to value."""
        ratio = (x - 10) / (self.width() - 20)
        ratio = max(0.0, min(1.0, ratio))
        
        # Snap logic
        snap_threshold = 0.02
        for r, v, _ in self.scale_points:
            if abs(ratio - r) < snap_threshold:
                return v
                
        return self._ratio_to_value(ratio)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(42, 42, 42))

        # Desplazamiento vertical negativo para subir el slider
        y_offset = -8   # valores negativos suben, positivos bajan
        
        # Draw slider groove
        groove_rect = QRect(10, self.height() // 2 - 4 + y_offset, self.width() - 20, 8)
        painter.fillRect(groove_rect, QColor(68, 68, 68))
        
        # Draw dB scale marks
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.setFont(QFont("Arial", 7))
        
        for ratio, value, label in self.scale_points:
            x = int(10 + ratio * (self.width() - 20))
            # Draw tick mark
            painter.drawLine(x, self.height() // 2 + 10 + y_offset, x, self.height() // 2 + 18 + y_offset) 
            # Draw label
            text_rect = painter.fontMetrics().boundingRect(label)
            painter.drawText(x - text_rect.width() // 2, self.height() // 2 + 30 + y_offset, label)
        
        # Draw filled portion
        if self._value > 0.01:
            fill_x = self._value_to_x(self._value)
            fill_rect = QRect(groove_rect.left(), groove_rect.top(), 
                             fill_x - groove_rect.left(), groove_rect.height())
            painter.fillRect(fill_rect, QColor(0, 120, 215))
        
        # Draw handle
        handle_x = self._value_to_x(self._value)
        handle_rect = QRect(handle_x - 14, self.height() // 2 - 16 + y_offset, 28, 32)
        
        if self.handle_icon:
            self.handle_icon.render(painter, handle_rect)
        else:
            # Fallback: draw simple handle
            painter.fillRect(handle_rect, QColor(0, 120, 215))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawRect(handle_rect)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._update_value(event.position().x())
    
    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_value(event.position().x())
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
    
    def _update_value(self, x: float):
        new_value = self._x_to_value(int(x))
        self.setValue(new_value)


class PanSlider(QWidget):
    """Custom horizontal pan slider using fad-sliderhandle-2-white.svg."""
    
    valueChanged = Signal(float)
    
    def __init__(self, parent=None, icons_dir: str = "./icons/svgs"):
        super().__init__(parent)
        self.icons_dir = icons_dir
        self.setMinimumSize(80, 50)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        # Pan range: -1.0 (left) to 1.0 (right)
        self._value = 0.0
        self._minimum = -1.0
        self._maximum = 1.0
        
        # Load slider handle icon
        self.handle_icon = None
        handle_path = os.path.join(icons_dir, "fad-sliderhandle-2-white.svg")
        if os.path.exists(handle_path):
            self.handle_icon = QSvgRenderer(handle_path)
        
        # Mouse tracking
        self.setMouseTracking(True)
        self._dragging = False
    
    def value(self) -> float:
        return self._value
    
    def setValue(self, value: float):
        value = max(self._minimum, min(self._maximum, value))
        if value != self._value:
            self._value = value
            self.update()
            self.valueChanged.emit(value)
    
    def _value_to_x(self, value: float) -> int:
        """Convert value to X coordinate."""
        ratio = (value - self._minimum) / (self._maximum - self._minimum)
        return int(10 + ratio * (self.width() - 20))
    
    def _x_to_value(self, x: int) -> float:
        """Convert X coordinate to value."""
        ratio = (x - 10) / (self.width() - 20)
        ratio = max(0.0, min(1.0, ratio))
        return self._minimum + ratio * (self._maximum - self._minimum)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background
        painter.fillRect(self.rect(), QColor(42, 42, 42))
        
        # Draw slider groove
        groove_rect = QRect(10, self.height() // 2 - 2, self.width() - 20, 4)
        painter.fillRect(groove_rect, QColor(68, 68, 68))
        
        # Draw center detent
        center_x = self.width() // 2
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawLine(center_x, groove_rect.top() - 2, center_x, groove_rect.bottom() + 2)
        
        # Draw L/R labels
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.setFont(QFont("Arial", 7))
        painter.drawText(2, self.height() // 2 + 5, "L")
        painter.drawText(self.width() - 8, self.height() // 2 + 5, "R")
        
        # Draw handle
        handle_x = self._value_to_x(self._value)
        handle_rect = QRect(handle_x - 12, self.height() // 2 - 10, 24, 20)
        
        if self.handle_icon:
            self.handle_icon.render(painter, handle_rect)
        else:
            # Fallback: draw simple handle
            painter.fillRect(handle_rect, QColor(0, 120, 215))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawRect(handle_rect)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = True
            self._update_value(event.position().x())
    
    def mouseMoveEvent(self, event):
        if self._dragging:
            self._update_value(event.position().x())
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
    
    def _update_value(self, x: float):
        new_value = self._x_to_value(int(x))
        self.setValue(new_value)


class StemItemWidget(QWidget):
    """Widget que representa un stem en el panel izquierdo."""

    volume_changed = Signal(str, float)
    pan_changed = Signal(str, float)
    mute_toggled = Signal(str, bool)
    solo_toggled = Signal(str, bool)
    fx_toggled = Signal(str, bool)
    name_changed = Signal(str, str)      # old_name, new_name
    category_changed = Signal(str, str)    # stem_name, new_category
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

        # ==================== INFO (Nombre + Categoría) - Compacto ====================
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        
        self.name_edit = QLineEdit(name)
        self.name_edit.setMinimumWidth(130)
        self.name_edit.setMaximumWidth(180)           # ← Limitado
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
        
        layout.addLayout(info_layout, 0)   # stretch = 0 → no se expande

        # ==================== VOLUMEN - PRINCIPAL RESPONSIVE ====================
        vol_layout = QVBoxLayout()
        vol_layout.setSpacing(2)
        vol_label = QLabel("Vol")
        vol_label.setStyleSheet("color: #888888; font-size: 10px;")
        vol_layout.addWidget(vol_label, alignment=Qt.AlignCenter)
        
        self.volume_slider = VolumeSlider(parent=self, icons_dir=self.icons_dir)
        self.volume_slider.setValue(volume)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.volume_slider.setMinimumWidth(180)
        self.volume_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vol_layout.addWidget(self.volume_slider)
        
        layout.addLayout(vol_layout, 5)   # ← Mucho stretch

        # ==================== PANEO - También responsive ====================
        pan_layout = QVBoxLayout()
        pan_layout.setSpacing(2)
        pan_label = QLabel("Pan")
        pan_label.setStyleSheet("color: #888888; font-size: 10px;")
        pan_layout.addWidget(pan_label, alignment=Qt.AlignCenter)
        
        self.pan_slider = PanSlider(parent=self, icons_dir=self.icons_dir)
        self.pan_slider.setValue(0.0)
        self.pan_slider.valueChanged.connect(self._on_pan_changed)
        self.pan_slider.setMinimumWidth(120)
        self.pan_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        pan_layout.addWidget(self.pan_slider)
        
        layout.addLayout(pan_layout, 3)   # stretch importante

        # ==================== BOTONES M S FX - Compactos ====================
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        self.mute_btn = QPushButton()
        self.mute_btn.setCheckable(True)
        self.mute_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-mute.svg"), "#AAAAAA"))
        self.mute_btn.setFixedSize(34, 34)
        self.mute_btn.setToolTip("Mute")
        self.mute_btn.toggled.connect(self._on_mute_toggled)
        btn_layout.addWidget(self.mute_btn)

        self.solo_btn = QPushButton()
        self.solo_btn.setCheckable(True)
        self.solo_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-solo.svg"), "#AAAAAA"))
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

        # Stretch para empujar todo a la derecha
        layout.addStretch(1)

        # ==================== REORDER + DELETE ====================
        reorder_layout = QVBoxLayout()
        reorder_layout.setSpacing(1)
        
        self.up_btn = QPushButton()
        self.up_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-caret-up.svg"), "#FFFFFF"))
        self.up_btn.setFixedSize(28, 17)
        self.up_btn.clicked.connect(lambda: self.move_up_requested.emit(self.stem_name))
        reorder_layout.addWidget(self.up_btn)
        
        self.down_btn = QPushButton()
        self.down_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-caret-down.svg"), "#FFFFFF"))
        self.down_btn.setFixedSize(28, 17)
        self.down_btn.clicked.connect(lambda: self.move_down_requested.emit(self.stem_name))
        reorder_layout.addWidget(self.down_btn)
        
        layout.addLayout(reorder_layout, 0)

        self.delete_btn = QPushButton()
        self.delete_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-eraser.svg"), "#FF5555"))
        self.delete_btn.setFixedSize(34, 34)
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.stem_name))
        layout.addWidget(self.delete_btn, 0)

        #self.setMinimumWidth(500) 
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _apply_style(self):
        self.setStyleSheet("""
            StemItemWidget {
                background-color: #2A2A2A;
                border: 1px solid #3A3A3A;
                border-radius: 6px;
            }
            QLineEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 11px;
            }
            QComboBox {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 2px 4px;
                font-size: 11px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #1E1E1E;
                color: #FFFFFF;
                selection-background-color: #0078D7;
            }
            QPushButton {
                background-color: #333333;
                border: 1px solid #444444;
                border-radius: 4px;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 10px;
            }
			QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:checked {
                background-color: #0078D7;
                border: 1px solid #0078D7;
                color: #FFFFFF;
            }
            QSlider::groove:vertical {
                background: #444444;
                width: 6px;
                border-radius: 3px;
            }
            QSlider::handle:vertical {
                background: #0078D7;
                height: 14px;
                width: 14px;
                margin: 0 -4px;
                border-radius: 7px;
            }
        """)

    def _on_volume_changed(self, value: float):
        self.volume_changed.emit(self.stem_name, value)
    
    def _on_pan_changed(self, value: float):
        self.pan_changed.emit(self.stem_name, value)

    def _on_mute_toggled(self, checked: bool):
        self.mute_btn.setIcon(svg_icon(
            os.path.join(self.icons_dir, "fad-mute.svg"),
            "#FF5555" if checked else "#AAAAAA"
        ))
        self.mute_toggled.emit(self.stem_name, checked)

    def _on_solo_toggled(self, checked: bool):
        self.solo_btn.setIcon(svg_icon(
            os.path.join(self.icons_dir, "fad-solo.svg"),
            "#FFAA00" if checked else "#AAAAAA"
        ))
        self.solo_toggled.emit(self.stem_name, checked)

    def _on_fx_toggled(self, checked: bool):
        # El estilo en línea sobrescribe el global, pero con background color se mantiene bien
        if checked:
            self.fx_btn.setStyleSheet("color: #FFFFFF; font-weight: bold; background-color: #0078D7; border: 1px solid #0078D7; padding: 0px; font-size: 11px;")
        else:
            self.fx_btn.setStyleSheet("color: #888888; font-weight: bold; background-color: #333333; border: 1px solid #444444; padding: 0px; font-size: 11px;")
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
