from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QLineEdit, QDialogButtonBox, QGroupBox,
    QInputDialog, QMessageBox, QTabWidget, QWidget, QSpinBox,
    QComboBox
)
from PySide6.QtCore import Qt, QSettings
from app.ui.theme import current as theme
from app.services.providers import get_available_providers


class SettingsDialog(QDialog):
    def __init__(self, stem_filters: dict, stream_port: int, config_mgr=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración")
        self.setMinimumWidth(580)
        self.setMinimumHeight(480)
        self.config_mgr = config_mgr
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
                color: #FFF;
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background-color: {theme.HOVER_BRIGHTEN};
            }}
        """)

        self._build_stem_filters_tab()
        self._build_streaming_tab()
        self._build_ai_tab()

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

        add_btn = QPushButton("+")
        add_btn.setFixedSize(26, 26)
        add_btn.setToolTip(f"Añadir patrón a «{title}»")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_SUCCESS};
                color: #FFFFFF;
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: #66BB6A; }}
        """)
        add_row.addWidget(add_btn)

        remove_btn = QPushButton("−")
        remove_btn.setFixedSize(26, 26)
        remove_btn.setToolTip(f"Eliminar patrón seleccionado de «{title}»")
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_DANGER_ALT};
                color: #FFFFFF;
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{ background-color: #FF3333; }}
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

        title = QLabel("Streaming de Karaoke")
        title.setStyleSheet(f"font-size: 15px; font-weight: bold; color: {theme.TEXT_PRIMARY};")
        tl.addWidget(title)

        desc = QLabel(
            "Configuración del servidor HTTP para transmitir el karaoke "
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

        self._toggle_key_btn = QPushButton("👁")
        self._toggle_key_btn.setFixedSize(28, 28)
        self._toggle_key_btn.setToolTip("Mostrar/ocultar API Key")
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

    def get_stem_filters(self) -> dict:
        return self._stem_filters

    def get_stream_port(self) -> int:
        return self._stream_port
