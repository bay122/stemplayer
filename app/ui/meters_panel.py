import psutil
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QWidget
from PySide6.QtCore import QTimer, Qt
from app.ui.svg_icon import svg_icon
from app.ui.theme import current as theme
import os


class MeterBar(QProgressBar):
    def __init__(self, is_peak=False, parent=None):
        super().__init__(parent)
        self.is_peak = is_peak
        self.setRange(0, 100)
        self.setTextVisible(True)
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(14)

    def set_value_with_color(self, val):
        self.setValue(int(val))

        if self.is_peak:
            if val < 80:
                color = theme.ACCENT_SUCCESS
            elif val < 95:
                color = theme.ACCENT_WARNING
            else:
                color = theme.ACCENT_DANGER
        else:
            if val < 60:
                color = theme.ACCENT_SUCCESS
            elif val < 85:
                color = theme.ACCENT_WARNING
            else:
                color = theme.ACCENT_DANGER

        self.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme.BG_TERTIARY};
                border: 1px solid {theme.BORDER_DARK};
                border-radius: {theme.BORDER_RADIUS_SM};
                color: {theme.TEXT_PRIMARY};
                text-align: center;
                font-size: 10px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: {theme.BORDER_RADIUS_SM};
            }}
        """)


class SystemMetersPanel(QWidget):
    def __init__(self, icons_dir: str, parent=None):
        super().__init__(parent)
        self.icons_dir = icons_dir
        self._build_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_meters)
        self.timer.start(1000)

        self.peak_val = 0.0
        self.peak_timer = QTimer(self)
        self.peak_timer.timeout.connect(self._decay_peak)
        self.peak_timer.start(50)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(6)

        cpu_layout = QHBoxLayout()
        cpu_lbl = QLabel()
        cpu_lbl.setPixmap(svg_icon(os.path.join(self.icons_dir, "fad-cpu.svg"), theme.SVG_ICON_DEFAULT).pixmap(14, 14))
        cpu_lbl.setFixedWidth(20)
        self.cpu_meter = MeterBar()
        cpu_layout.addWidget(cpu_lbl)
        cpu_layout.addWidget(self.cpu_meter)
        layout.addLayout(cpu_layout)

        ram_layout = QHBoxLayout()
        ram_lbl = QLabel()
        ram_lbl.setPixmap(svg_icon(os.path.join(self.icons_dir, "fad-ram.svg"), theme.SVG_ICON_DEFAULT).pixmap(14, 14))
        ram_lbl.setFixedWidth(20)
        self.ram_meter = MeterBar()
        ram_layout.addWidget(ram_lbl)
        ram_layout.addWidget(self.ram_meter)
        layout.addLayout(ram_layout)

        peak_layout = QHBoxLayout()
        peak_lbl = QLabel()
        peak_lbl.setPixmap(svg_icon(os.path.join(self.icons_dir, "fad-logo-audacity.svg"), theme.SVG_ICON_DEFAULT).pixmap(14, 14))
        peak_lbl.setFixedWidth(20)
        self.peak_meter = MeterBar(is_peak=True)
        self.peak_meter.setFormat("")
        peak_layout.addWidget(peak_lbl)
        peak_layout.addWidget(self.peak_meter)
        layout.addLayout(peak_layout)

    def _update_meters(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.cpu_meter.set_value_with_color(cpu)
        self.cpu_meter.setFormat(f"{cpu}%")
        self.ram_meter.set_value_with_color(ram)
        self.ram_meter.setFormat(f"{ram}%")

    def update_peak(self, peak_val):
        if peak_val > self.peak_val:
            self.peak_val = peak_val

    def _decay_peak(self):
        self.peak_val = max(0.0, self.peak_val - 0.05)
        pct = min(100, int(self.peak_val * 100))
        self.peak_meter.set_value_with_color(pct)
        if self.peak_val >= 0.99:
            self.peak_meter.setFormat("CLIP")
        else:
            self.peak_meter.setFormat("")
