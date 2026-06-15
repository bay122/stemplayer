"""
Sistema de temas centralizado para la aplicación.

Todas las definiciones visuales (colores, bordes, tipografía)
viven AQUÍ. Para crear un nuevo tema basta con instanciar Theme
con valores distintos y llamar a apply_theme(window, mi_tema).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Theme:
    # ── Fondos ──────────────────────────────────────────────
    BG_PRIMARY: str = "#121212"
    BG_SECONDARY: str = "#1E1E1E"
    BG_TERTIARY: str = "#2A2A2A"
    BG_DARK: str = "#111111"
    BG_INPUT: str = "#1E1E1E"
    BG_EDITOR: str = "#1e1e1e"
    BG_MENU: str = "#2A2A2A"

    # ── Texto ───────────────────────────────────────────────
    TEXT_PRIMARY: str = "#FFFFFF"
    TEXT_DEFAULT: str = "#CCCCCC"
    TEXT_SECONDARY: str = "#888888"
    TEXT_MUTED: str = "#AAAAAA"
    TEXT_EDITOR: str = "#d4d4d4"
    TEXT_DISABLED: str = "#666666"

    # ── Acentos ─────────────────────────────────────────────
    ACCENT_PRIMARY: str = "#0078D7"
    ACCENT_PRIMARY_HOVER: str = "#006ABB"
    ACCENT_CYAN: str = "#00BFFF"
    ACCENT_SUCCESS: str = "#4CAF50"
    ACCENT_DANGER: str = "#F44336"
    ACCENT_DANGER_ALT: str = "#FF5555"
    ACCENT_WARNING: str = "#FFC107"
    ACCENT_INFO: str = "#2196F3"
    ACCENT_PURPLE: str = "#5555AA"
    ACCENT_SOLO: str = "#FFAA00"

    # ── Bordes ──────────────────────────────────────────────
    BORDER: str = "#444444"
    BORDER_LIGHT: str = "#555555"
    BORDER_DARK: str = "#333333"
    BORDER_ALT: str = "#3e3e42"
    BORDER_WIDGET: str = "#3A3A3A"

    # ── Geometría ───────────────────────────────────────────
    BORDER_RADIUS_SM: str = "4px"
    BORDER_RADIUS_MD: str = "6px"
    FONT_FAMILY: str = (
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', "
        "Roboto, Helvetica, Arial, sans-serif"
    )
    FONT_SIZE_BASE: str = "13px"
    FONT_MONO: str = "Consolas, 'Courier New', monospace"

    # ── Estados ─────────────────────────────────────────────
    HOVER_BRIGHTEN: str = "#444444"
    HOVER_ACCENT: str = "#106ebe"
    PRESSED_DARKEN: str = "#222222"

    # ── SVG helper ──────────────────────────────────────────
    SVG_ICON_DEFAULT: str = "#AAAAAA"
    SVG_ICON_MUTED: str = "#888888"
    SVG_ICON_ACTIVE: str = "#FFFFFF"
    SVG_ICON_DANGER: str = "#FF5555"
    SVG_ICON_SOLO: str = "#FFAA00"

    # ══════════════════════════════════════════════════════════
    # Métodos de ayuda: generan QSS reutilizable
    # ══════════════════════════════════════════════════════════

    # ── Botón de acción (azul) ──────────────────────────────
    def action_button_qss(self) -> str:
        return f"""
            QPushButton {{
                background-color: {self.ACCENT_PRIMARY};
                color: {self.TEXT_PRIMARY};
                border: 1px solid {self.ACCENT_PRIMARY};
                border-radius: {self.BORDER_RADIUS_SM};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.ACCENT_PRIMARY_HOVER};
            }}
        """

    # ── Menú contextual ─────────────────────────────────────
    def menu_qss(self) -> str:
        return (
            f"QMenu {{ background-color: {self.BG_MENU}; color: {self.TEXT_PRIMARY}; }}"
            f"QMenu::item:selected {{ background-color: {self.ACCENT_PRIMARY}; }}"
        )

    # ── Slider de reproducción horizontal ───────────────────
    def playback_slider_qss(self) -> str:
        return f"""
            QSlider::groove:horizontal {{
                border: 1px solid {self.BORDER_ALT};
                height: 6px;
                background: {self.BG_TERTIARY};
                border-radius: 3px;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.ACCENT_PRIMARY};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {self.TEXT_PRIMARY};
                width: 12px;
                height: 12px;
                margin: -3px 0;
                border-radius: 6px;
            }}
        """

    # ── Theme completo como QSS global ──────────────────────
    def global_stylesheet(self) -> str:
        return f"""
            QMainWindow {{
                background-color: {self.BG_PRIMARY};
            }}
            QWidget {{
                background-color: {self.BG_PRIMARY};
                color: {self.TEXT_PRIMARY};
                font-family: {self.FONT_FAMILY};
                font-size: {self.FONT_SIZE_BASE};
            }}
            QLineEdit {{
                background-color: {self.BG_INPUT};
                border: 1px solid {self.BORDER};
                border-radius: {self.BORDER_RADIUS_SM};
                padding: 6px;
                color: {self.TEXT_PRIMARY};
                selection-background-color: {self.ACCENT_PRIMARY};
            }}
            QLineEdit:focus {{
                border: 1px solid {self.ACCENT_PRIMARY};
            }}
            QGroupBox {{
                border: 1px solid {self.BORDER_DARK};
                border-radius: {self.BORDER_RADIUS_MD};
                margin-top: 12px;
                padding-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 6px;
                color: {self.TEXT_MUTED};
            }}
            QGroupBox#analysisBox {{
                background-color: {self.BG_SECONDARY};
                border: 1px solid {self.BG_TERTIARY};
            }}
            QGroupBox#pitchBox {{
                background-color: {self.BG_SECONDARY};
            }}
            QGroupBox#tempoBox {{
                background-color: {self.BG_SECONDARY};
            }}
            QGroupBox#playBox {{
                background-color: {self.BG_SECONDARY};
            }}
            QPushButton {{
                background-color: #333333;
                border: 1px solid {self.BORDER};
                border-radius: {self.BORDER_RADIUS_MD};
                padding: 6px 12px;
                color: {self.TEXT_PRIMARY};
            }}
            QPushButton:hover {{
                background-color: {self.HOVER_BRIGHTEN};
                border: 1px solid {self.BORDER_LIGHT};
            }}
            QPushButton:pressed {{
                background-color: {self.PRESSED_DARKEN};
            }}
            QPushButton:checked {{
                background-color: {self.ACCENT_PRIMARY};
                border: 1px solid {self.ACCENT_PRIMARY};
                color: {self.TEXT_PRIMARY};
            }}
            QPushButton:checked:hover {{
                background-color: {self.ACCENT_PRIMARY_HOVER};
            }}
            QCheckBox {{
                spacing: 6px;
                color: {self.TEXT_DEFAULT};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: {self.BORDER_RADIUS_SM};
                border: 1px solid {self.BORDER_LIGHT};
                background-color: {self.PRESSED_DARKEN};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.ACCENT_PRIMARY};
                border: 1px solid {self.ACCENT_PRIMARY};
            }}
            QSpinBox {{
                background-color: {self.BG_INPUT};
                border: 1px solid {self.BORDER};
                border-radius: {self.BORDER_RADIUS_SM};
                padding: 4px;
                color: {self.TEXT_PRIMARY};
            }}
            QComboBox {{
                background-color: {self.BG_INPUT};
                color: {self.TEXT_PRIMARY};
                border: 1px solid {self.BORDER};
                border-radius: {self.BORDER_RADIUS_SM};
                padding: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.BG_INPUT};
                color: {self.TEXT_PRIMARY};
                selection-background-color: {self.ACCENT_PRIMARY};
            }}
            QListWidget {{
                background-color: {self.BG_SECONDARY};
                border: 1px solid {self.BORDER_DARK};
                border-radius: {self.BORDER_RADIUS_SM};
                color: {self.TEXT_PRIMARY};
            }}
            QListWidget::item:selected {{
                background-color: {self.ACCENT_PRIMARY};
            }}
            QProgressBar {{
                background-color: {self.BG_TERTIARY};
                border: 1px solid {self.BORDER_DARK};
                border-radius: {self.BORDER_RADIUS_SM};
                text-align: center;
                color: {self.TEXT_PRIMARY};
            }}
            QProgressBar::chunk {{
                background-color: {self.ACCENT_PRIMARY};
                border-radius: {self.BORDER_RADIUS_SM};
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QLabel {{
                color: {self.TEXT_DEFAULT};
            }}
        """


# ── Tema por defecto ───────────────────────────────────────
DARK_THEME = Theme()


# ── Función de aplicación ──────────────────────────────────
def apply_theme(window, theme: Theme = DARK_THEME):
    """Aplica un tema completo a la ventana principal."""
    window.setStyleSheet(theme.global_stylesheet())
