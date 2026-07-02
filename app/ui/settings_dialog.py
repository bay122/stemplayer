import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QLineEdit, QDialogButtonBox, QGroupBox,
    QInputDialog, QMessageBox, QTabWidget, QWidget, QSpinBox,
    QComboBox, QFrame, QGridLayout
)
from PySide6.QtCore import Qt, QSettings, Signal
from PySide6.QtGui import QColor, QPixmap
from app.ui.theme import current as theme
from app.ui.svg_icon import svg_icon
from app.services.providers import get_available_providers
from app.version import (
    APP_NAME, APP_VERSION, APP_AUTHOR, APP_AUTHOR_EMAIL,
    APP_GITHUB, APP_WEBSITE, APP_LICENSE
)


# Categorías que se pueden personalizar
CATEGORY_COLOR_NAMES = [
    "Vocals", "Drums", "Percussion", "Bass", "Guitars", "Keys",
    "Strings", "Brass", "Winds", "Synths", "FX", "Ref", "Other"
]

DEFAULT_CATEGORY_COLORS = {
    "Vocals":     "#FF5555",
    "Drums":      "#FFAA00",
    "Percussion": "#FF6644",
    "Bass":       "#FFCC00",
    "Guitars":    "#55CC55",
    "Keys":       theme.ACCENT_PURPLE,
    "Strings":    "#00BFFF",
    "Brass":      "#FF8800",
    "Winds":      "#88CCFF",
    "Synths":     "#CC88FF",
    "FX":         "#888888",
    "Ref":        "#666666",
    "Other":      "#AAAAAA",
}


class ColorSwatchButton(QPushButton):
    """Botón que muestra el color actual y al click abre QColorDialog."""

    color_changed = Signal(str)

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 26)
        self.set_color(color)
        self.clicked.connect(self._pick_color)

    def set_color(self, color: str):
        self._color = color
        self.setStyleSheet(
            f"background-color: {color}; border: 1px solid {theme.BORDER}; "
            f"border-radius: 4px;"
        )
        self.setToolTip(color)

    def get_color(self) -> str:
        return self._color

    def _pick_color(self):
        col = QColorDialog.getColor(QColor(self._color), self, "Seleccionar color")
        if col.isValid():
            self.set_color(col.name())
            self.color_changed.emit(col.name())


from PySide6.QtWidgets import QColorDialog


class SettingsDialog(QDialog):
    def __init__(self, stem_filters: dict, stream_port: int, config_mgr=None, icons_dir=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setMinimumWidth(580)
        self.setMinimumHeight(480)
        self.config_mgr = config_mgr
        self.icons_dir = icons_dir
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {theme.BG_PRIMARY};
                color: {theme.TEXT_PRIMARY};
            }}
            QLabel {{
                color: {theme.TEXT_PRIMARY};
            }}
        """)

        self._stem_filters = stem_filters.copy()
        self._stream_port = stream_port
        if config_mgr is not None:
            self._category_colors = config_mgr.get_category_colors()
        else:
            self._category_colors = dict(DEFAULT_CATEGORY_COLORS)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: {theme.BG_SECONDARY};
                border: 1px solid {theme.BG_TERTIARY};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 12px;
            }}
            QTabBar::tab {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_MUTED};
                border: none;
                padding: 8px 16px;
                border-radius: {theme.BORDER_RADIUS_SM};
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {theme.ACCENT_INFO};
                color: {theme.TEXT_PRIMARY};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background-color: {theme.HOVER_BRIGHTEN};
            }}
        """)

        self._build_stem_filters_tab()
        self._build_streaming_tab()
        self._build_ai_tab()
        self._build_about_tab()

        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---- Tab: Filtros de Stems ----

    def _build_stem_filters_tab(self):
        tab = QWidget()
        tl = QVBoxLayout(tab)
        tl.setSpacing(10)

        title = QLabel("Filtros de identificación de stems")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.TEXT_PRIMARY};")
        tl.addWidget(title)

        desc = QLabel(
            "Estos patrones se usan al cargar stems para determinar "
            "automáticamente qué pistas son clic/metrónomo, guía, "
            "o deben excluirse de efectos de pitch."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px; margin-bottom: 4px;")
        tl.addWidget(desc)

        self._build_group(tl, "click_patterns", "Pistas de clic / metrónomo",
            "Patrones que identifican pistas de clic o metrónomo (se silencian y ordenan primero).",
            self._stem_filters.get("click_patterns", []))
        self._build_group(tl, "guide_patterns", "Pistas de guía / cue",
            "Patrones que identifican pistas de guía o referencia (se silencian y ordenan segundo).",
            self._stem_filters.get("guide_patterns", []))
        self._build_group(tl, "no_fx_patterns", "Pistas sin efectos de pitch",
            "Patrones que identifican pistas a las que NO se les aplica pitch shift (batería, percusión).",
            self._stem_filters.get("no_fx_patterns", []))

        self.tabs.addTab(tab, "Filtros de Stems")

    def _build_group(self, parent_layout, key, title, description, items):
        group = QGroupBox(title)
        group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {theme.BG_PRIMARY};
                border: 1px solid {theme.BG_TERTIARY};
                border-radius: {theme.BORDER_RADIUS_SM};
                margin-top: 8px;
                padding-top: 16px;
                font-weight: bold;
                color: {theme.TEXT_PRIMARY};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: {theme.TEXT_PRIMARY};
            }}
        """)
        gl = QVBoxLayout(group)
        gl.setSpacing(4)

        d = QLabel(description)
        d.setWordWrap(True)
        d.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px; font-weight: normal;")
        gl.addWidget(d)

        add_row = QHBoxLayout()
        input_field = QLineEdit()
        input_field.setPlaceholderText("Nuevo patrón...")
        input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 3px 6px;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme.ACCENT_INFO};
            }}
        """)
        add_row.addWidget(input_field, 1)

        add_btn = QPushButton()
        add_btn.setFixedSize(26, 26)
        add_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-plus.svg")))
        add_btn.setToolTip(f"Añadir patrón a «{title}»")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_SUCCESS};
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {theme.ACCENT_SUCCESS_HOVER}; }}
        """)
        add_row.addWidget(add_btn)

        remove_btn = QPushButton()
        remove_btn.setFixedSize(26, 26)
        remove_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-eraser.svg")))
        remove_btn.setToolTip(f"Eliminar patrón seleccionado de «{title}»")
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_DANGER_ALT};
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: {theme.ACCENT_DANGER_ALT_HOVER}; }}
        """)
        add_row.addWidget(remove_btn)
        gl.addLayout(add_row)

        _list = QListWidget()
        _list.setMaximumHeight(80)
        _list.setStyleSheet(f"""
            QListWidget {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                font-family: monospace;
                font-size: 11px;
            }}
            QListWidget::item:selected {{
                background-color: {theme.ACCENT_INFO};
            }}
        """)
        for item in items:
            _list.addItem(item)
        gl.addWidget(_list)

        add_btn.clicked.connect(lambda: self._add_pattern(input_field, _list))
        remove_btn.clicked.connect(lambda: self._remove_pattern(_list))

        setattr(self, f"_{key}_list", _list)
        parent_layout.addWidget(group)

    def _add_pattern(self, input_field, _list):
        text = input_field.text().strip()
        if not text:
            return
        if _list.findItems(text, Qt.MatchExactly):
            return
        _list.addItem(text)
        input_field.clear()

    def _remove_pattern(self, _list):
        item = _list.currentItem()
        if item:
            _list.takeItem(_list.row(item))

    # ---- Tab: Streaming ----

    def _build_streaming_tab(self):
        tab = QWidget()
        tl = QVBoxLayout(tab)
        tl.setSpacing(12)

        title = QLabel("Streaming de Live Chords")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.TEXT_PRIMARY};")
        tl.addWidget(title)

        desc = QLabel(
            "Configuración del servidor HTTP para transmitir el Live Chords "
            "a otros dispositivos en la misma red a través del navegador."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px; margin-bottom: 8px;")
        tl.addWidget(desc)

        port_row = QHBoxLayout()
        port_row.addWidget(QLabel("Puerto:"))
        self._port_spin = QSpinBox()
        self._port_spin.setRange(1024, 65535)
        self._port_spin.setValue(self._stream_port)
        self._port_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 4px 8px;
                font-size: 13px;
            }}
        """)
        port_row.addWidget(self._port_spin)
        port_row.addWidget(QLabel("(1024-65535)"))
        port_row.addStretch()
        tl.addLayout(port_row)

        note = QLabel("Nota: Los cambios de puerto se aplicarán al iniciar el stream.")
        note.setStyleSheet(f"color: {theme.ACCENT_WARNING}; font-size: 11px;")
        tl.addWidget(note)

        tl.addStretch()
        self.tabs.addTab(tab, "Streaming")

    # ---- Tab: IA ----

    def _build_ai_tab(self):
        tab = QWidget()
        tl = QVBoxLayout(tab)
        tl.setSpacing(12)

        title = QLabel("Servicios de IA")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.TEXT_PRIMARY};")
        tl.addWidget(title)

        desc = QLabel(
            "Configuración de los proveedores de IA utilizados "
            "para generación de ChordPro y sincronización."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px; margin-bottom: 8px;")
        tl.addWidget(desc)

        settings = QSettings("StemPlayer", "StemPlayer")

        providers = get_available_providers()

        prov_row = QHBoxLayout()
        prov_row.addWidget(QLabel("Proveedor:"))
        self._provider_combo = QComboBox()
        self._provider_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 4px 8px;
            }}
            QComboBox::drop-down {{ border: none; width: 16px; }}
            QComboBox QAbstractItemView {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                selection-background-color: {theme.ACCENT_INFO};
            }}
        """)
        for p in providers:
            self._provider_combo.addItem(p.display_name, p.id)
        saved_provider = settings.value("ai/provider", "openrouter")
        idx = self._provider_combo.findData(saved_provider)
        if idx >= 0:
            self._provider_combo.setCurrentIndex(idx)

        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        prov_row.addWidget(self._provider_combo, 1)
        tl.addLayout(prov_row)

        api_row = QHBoxLayout()
        api_row.addWidget(QLabel("API Key:"))
        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("Ingresa tu API Key...")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        saved_key = settings.value(f"ai/api_key/{saved_provider}", "")
        if saved_key:
            self._api_key_input.setText(saved_key)
        self._api_key_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme.ACCENT_INFO};
            }}
        """)
        api_row.addWidget(self._api_key_input, 1)

        self._toggle_key_btn = QPushButton()
        self._toggle_key_btn.setFixedSize(28, 28)
        self._toggle_key_btn.setToolTip("Mostrar/ocultar API Key")
        self._toggle_key_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-eye.svg")))
        self._toggle_key_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
            }}
            QPushButton:hover {{ background-color: {theme.HOVER_BRIGHTEN}; }}
        """)
        self._toggle_key_btn.clicked.connect(self._toggle_api_key_visibility)
        api_row.addWidget(self._toggle_key_btn)
        tl.addLayout(api_row)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Modelo:"))
        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText("Dejar vacío para usar el modelo por defecto")
        saved_model = settings.value(f"ai/model/{saved_provider}", "")
        if saved_model:
            self._model_input.setText(saved_model)
        self._model_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {theme.BG_INPUT};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 4px 8px;
            }}
            QLineEdit:focus {{
                border: 1px solid {theme.ACCENT_INFO};
            }}
        """)
        model_row.addWidget(self._model_input, 1)
        tl.addLayout(model_row)

        tl.addStretch()
        self.tabs.addTab(tab, "IA")

        # ---- Tab: Categorías (colores) ----
        self._build_categories_tab()

    def _on_provider_changed(self, index):
        provider_id = self._provider_combo.itemData(index)
        settings = QSettings("StemPlayer", "StemPlayer")
        saved_key = settings.value(f"ai/api_key/{provider_id}", "")
        self._api_key_input.setText(saved_key)
        saved_model = settings.value(f"ai/model/{provider_id}", "")
        self._model_input.setText(saved_model)

    def _toggle_api_key_visibility(self):
        if self._api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

    def _on_accept(self):
        for key in ("click_patterns", "guide_patterns", "no_fx_patterns"):
            lst = getattr(self, f"_{key}_list")
            self._stem_filters[key] = [lst.item(i).text() for i in range(lst.count())]

        self._stream_port = self._port_spin.value()

        provider_id = self._provider_combo.currentData()
        api_key = self._api_key_input.text().strip()
        model = self._model_input.text().strip()

        settings = QSettings("StemPlayer", "StemPlayer")
        settings.setValue("ai/provider", provider_id)
        if api_key:
            settings.setValue(f"ai/api_key/{provider_id}", api_key)
        if model:
            settings.setValue(f"ai/model/{provider_id}", model)

        self.accept()

    def _build_about_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QHBoxLayout()
        header.setSpacing(16)

        icon_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "assets", "icons", "icon.png"
        )
        icon_label = QLabel()
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            icon_label.setPixmap(pixmap.scaled(72, 72, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        icon_label.setFixedSize(80, 80)
        icon_label.setAlignment(Qt.AlignCenter)
        header.addWidget(icon_label)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_label = QLabel(APP_NAME)
        name_label.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {theme.TEXT_PRIMARY};")
        info_col.addWidget(name_label)

        version_label = QLabel(f"Versión {APP_VERSION}")
        version_label.setStyleSheet(f"font-size: 13px; color: {theme.TEXT_MUTED};")
        info_col.addWidget(version_label)

        desc_label = QLabel("Reproductor y mezclador de stems de audio")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet(f"font-size: 11px; color: {theme.TEXT_SECONDARY};")
        info_col.addWidget(desc_label)

        info_col.addStretch()
        header.addLayout(info_col, 1)
        layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(f"background-color: {theme.BORDER}; max-height: 1px;")
        layout.addWidget(sep)

        details_style = f"font-size: 12px; color: {theme.TEXT_PRIMARY};"
        muted_style = f"font-size: 11px; color: {theme.TEXT_MUTED};"
        link_style = f"font-size: 12px; color: {theme.ACCENT_INFO};"

        details = QVBoxLayout()
        details.setSpacing(4)

        def row(label, value, is_link=False):
            r = QHBoxLayout()
            r.setSpacing(8)
            l = QLabel(label)
            l.setStyleSheet(muted_style)
            l.setFixedWidth(80)
            r.addWidget(l)
            v = QLabel(value)
            v.setStyleSheet(link_style if is_link else details_style)
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            if is_link:
                v.setOpenExternalLinks(True)
            r.addWidget(v, 1)
            details.addLayout(r)

        row("Autor:", APP_AUTHOR)
        row("Email:", APP_AUTHOR_EMAIL)
        row("Web:", f'<a href="{APP_WEBSITE}" style="color: {theme.ACCENT_INFO};">{APP_WEBSITE}</a>', is_link=True)
        row("GitHub:", f'<a href="{APP_GITHUB}" style="color: {theme.ACCENT_INFO};">{APP_GITHUB}</a>', is_link=True)
        row("Licencia:", APP_LICENSE)

        layout.addLayout(details)

        layout.addStretch()

        license_note = QLabel(
            "Este software se distribuye bajo licencia CC BY-NC-SA 4.0.\n"
            "Puedes compartir y modificar el código con atribución,\n"
            "pero no está permitido su uso comercial."
        )
        license_note.setStyleSheet(f"font-size: 10px; color: {theme.TEXT_MUTED}; padding-top: 8px;")
        license_note.setAlignment(Qt.AlignCenter)
        layout.addWidget(license_note)

        self.tabs.addTab(tab, "Acerca de")

    def get_stem_filters(self) -> dict:
        return self._stem_filters

    def get_stream_port(self) -> int:
        return self._stream_port

    def get_category_colors(self) -> dict:
        return dict(self._category_colors)

    def _build_categories_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)
        layout.setContentsMargins(12, 12, 12, 12)

        title = QLabel("Colores de categorías de stems")
        title.setStyleSheet(
            f"color: {theme.TEXT_PRIMARY}; font-size: 13px; font-weight: bold;"
        )
        layout.addWidget(title)

        desc = QLabel(
            "Personaliza el color asociado a cada categoría. El color se "
            "aplica en el waveform, los chips y las cards de presencia."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px;")
        layout.addWidget(desc)

        grid = QGridLayout()
        grid.setSpacing(10)
        self._color_buttons = {}
        for i, cat in enumerate(CATEGORY_COLOR_NAMES):
            row = i // 2
            col = (i % 2) * 2
            lbl = QLabel(cat)
            lbl.setStyleSheet(
                f"color: {theme.TEXT_PRIMARY}; font-size: 11px; min-width: 90px;"
            )
            grid.addWidget(lbl, row, col)

            color = self._category_colors.get(cat, DEFAULT_CATEGORY_COLORS[cat])
            btn = ColorSwatchButton(color)
            btn.color_changed.connect(
                lambda new_color, c=cat: self._on_category_color_changed(c, new_color)
            )
            grid.addWidget(btn, row, col + 1)
            self._color_buttons[cat] = btn

        layout.addLayout(grid)
        layout.addStretch()

        # Botón "Restablecer defaults"
        reset_btn = QPushButton("Restablecer colores por defecto")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BUTTON_BG};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 4px 12px;
            }}
            QPushButton:hover {{ background-color: {theme.HOVER_BRIGHTEN}; }}
        """)
        reset_btn.clicked.connect(self._reset_category_colors)
        layout.addWidget(reset_btn)

        self.tabs.addTab(tab, "Categorías")

    def _on_category_color_changed(self, category: str, color: str):
        self._category_colors[category] = color

    def _reset_category_colors(self):
        for cat, btn in self._color_buttons.items():
            color = DEFAULT_CATEGORY_COLORS[cat]
            btn.set_color(color)
            self._category_colors[cat] = color
