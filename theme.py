def apply_dark_theme(widget):
    widget.setStyleSheet("""
        QMainWindow {
            background-color: #121212;
        }
        QWidget {
            background-color: #121212;
            color: #FFFFFF;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            font-size: 13px;
        }
        QLineEdit {
            background-color: #1E1E1E;
            border: 1px solid #444444;
            border-radius: 4px;
            padding: 6px;
            color: #FFFFFF;
            selection-background-color: #0078D7;
        }
        QLineEdit:focus {
            border: 1px solid #0078D7;
        }
        QGroupBox {
            border: 1px solid #333333;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 8px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 6px;
            color: #AAAAAA;
        }
        QGroupBox#analysisBox {
            background-color: #1E1E1E;
            border: 1px solid #2A2A2A;
        }
        QGroupBox#pitchBox {
            background-color: #1E1E1E;
        }
        QGroupBox#tempoBox {
            background-color: #1E1E1E;
        }
        QGroupBox#playBox {
            background-color: #1E1E1E;
        }
        QPushButton {
            background-color: #333333;
            border: 1px solid #444444;
            border-radius: 6px;
            padding: 6px 12px;
            color: #FFFFFF;
        }
        QPushButton:hover {
            background-color: #444444;
            border: 1px solid #555555;
        }
        QPushButton:pressed {
            background-color: #222222;
        }
        QPushButton:checked {
            background-color: #0078D7;
            border: 1px solid #0078D7;
            color: #FFFFFF;
        }
        QPushButton:checked:hover {
            background-color: #006ABB;
        }
        QCheckBox {
            spacing: 6px;
            color: #CCCCCC;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 1px solid #555555;
            background-color: #222222;
        }
        QCheckBox::indicator:checked {
            background-color: #0078D7;
            border: 1px solid #0078D7;
        }
        QSpinBox {
            background-color: #1E1E1E;
            border: 1px solid #444444;
            border-radius: 4px;
            padding: 4px;
            color: #FFFFFF;
        }
        QComboBox {
            background-color: #1E1E1E;
            color: #FFFFFF;
            border: 1px solid #444444;
            border-radius: 4px;
            padding: 4px;
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
        QListWidget {
            background-color: #1E1E1E;
            border: 1px solid #333333;
            border-radius: 4px;
            color: #FFFFFF;
        }
        QListWidget::item:selected {
            background-color: #0078D7;
        }
        QProgressBar {
            background-color: #2A2A2A;
            border: 1px solid #333333;
            border-radius: 4px;
            text-align: center;
            color: #FFFFFF;
        }
        QProgressBar::chunk {
            background-color: #0078D7;
            border-radius: 4px;
        }
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        QLabel {
            color: #CCCCCC;
        }
    """)
