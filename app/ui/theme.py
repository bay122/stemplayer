"""
Sistema de temas centralizado para la aplicación.

Todas las definiciones visuales (colores, bordes, tipografía)
viven AQUÍ. Para crear un nuevo tema basta con instanciar Theme
con valores distintos y llamar a apply_theme(window, mi_tema).

Los widgets importan `current` (proxy dinámico) en lugar de
`DARK_THEME` directamente, para reflejar cambios de tema en
tiempo de ejecución sin necesidad de re-importar.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Theme:
    # ── Fondos (paleta StemDeck-inspired) ────────────────────
    BG_PRIMARY: str = "#0b0f12"
    BG_SECONDARY: str = "#131a1f"
    BG_TERTIARY: str = "#1d262d"
    BG_DARK: str = "#0f1418"
    BG_INPUT: str = "#182026"
    BG_EDITOR: str = "#0f1418"
    BG_MENU: str = "#131a1f"

    # ── Texto ───────────────────────────────────────────────
    TEXT_PRIMARY: str = "#e8ecf0"
    TEXT_DEFAULT: str = "#c2c9d1"
    TEXT_SECONDARY: str = "#8a939c"
    TEXT_MUTED: str = "#5d666e"
    TEXT_EDITOR: str = "#c2c9d1"
    TEXT_DISABLED: str = "#5d666e"

    # ── Acentos (paleta StemDeck-inspired) ──────────────────
    ACCENT_PRIMARY: str = "#0078D7"
    ACCENT_PRIMARY_HOVER: str = "#1a8de0"
    ACCENT_CYAN: str = "#00BFFF"
    ACCENT_SUCCESS: str = "#4caf7d"
    ACCENT_SUCCESS_HOVER: str = "#5dc78f"
    ACCENT_DANGER: str = "#d65a4a"
    ACCENT_DANGER_ALT: str = "#ef4444"
    ACCENT_DANGER_ALT_HOVER: str = "#ff5555"
    ACCENT_WARNING: str = "#FFAA00"
    ACCENT_INFO: str = "#2196F3"
    ACCENT_INFO_HOVER: str = "#42A5F5"
    ACCENT_PURPLE: str = "#a855f7"
    ACCENT_SOLO: str = "#FFAA00"
    ACCENT_GOLD: str = "#f4b740"

    # ── Bordes ──────────────────────────────────────────────
    BORDER: str = "#232c34"
    BORDER_LIGHT: str = "#2e3942"
    BORDER_DARK: str = "#1d262d"
    BORDER_ALT: str = "#2e3942"
    BORDER_WIDGET: str = "#232c34"

    # ── Geometría (StemDeck usa 10/8/6 px) ─────────────────
    BORDER_RADIUS_SM: str = "6px"
    BORDER_RADIUS_MD: str = "8px"
    BORDER_RADIUS_LG: str = "10px"
    FONT_FAMILY: str = (
        "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', "
        "Roboto, Helvetica, Arial, sans-serif"
    )
    FONT_SIZE_BASE: str = "13px"
    FONT_MONO: str = "'JetBrains Mono', 'Consolas', 'Courier New', monospace"

    # ── Estados ─────────────────────────────────────────────
    HOVER_BRIGHTEN: str = "#1d262d"
    HOVER_ACCENT: str = "#106ebe"
    PRESSED_DARKEN: str = "#0f1418"
    BUTTON_BG: str = "#182026"

    # ── Sliders custom (QPainter) ───────────────────────────
    SLIDER_GROOVE: str = "#232c34"
    SLIDER_CENTER: str = "#5d666e"
    SLIDER_TEXT: str = "#8a939c"

    # ── SVG helper ──────────────────────────────────────────
    SVG_ICON_DEFAULT: str = "#c2c9d1"
    SVG_ICON_MUTED: str = "#8a939c"
    SVG_ICON_ACTIVE: str = "#e8ecf0"
    SVG_ICON_DANGER: str = "#ef4444"
    SVG_ICON_SOLO: str = "#FFAA00"
    SVG_ICON_PLAYING: str = "#4caf7d"

    # ── Impresión (exportación a PDF) ───────────────────────
    TEXT_PRINT: str = "#5d666e"
    TEXT_PRINT_HEADING: str = "#2e3942"

    # ── Overrides por theme ─────────────────────────────────
    custom_qss: str = ""
    icons_dir: str = ""

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
                background-image: qradialgradient(
                    cx: 0.5, cy: 0, radius: 0.7,
                    fx: 0.5, fy: 0,
                    stop: 0 rgba(216, 168, 74, 0.03),
                    stop: 1 transparent
                );
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
                background-color: {self.BG_SECONDARY};
                border: 1px solid {self.BORDER_DARK};
                border-radius: {self.BORDER_RADIUS_LG};
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
            QPushButton {{
                background-color: {self.BUTTON_BG};
                background-image: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255,255,255,0.04),
                    stop:1 transparent
                );
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
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.ACCENT_PRIMARY},
                    stop:1 {self.ACCENT_PRIMARY_HOVER}
                );
                border-radius: {self.BORDER_RADIUS_SM};
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background: {self.BG_DARK};
                width: 8px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {self.BORDER_LIGHT};
                border-radius: 4px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {self.ACCENT_PRIMARY};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar:horizontal {{
                background: {self.BG_DARK};
                height: 8px;
                margin: 0;
            }}
            QScrollBar::handle:horizontal {{
                background: {self.BORDER_LIGHT};
                border-radius: 4px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {self.ACCENT_PRIMARY};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0;
            }}
            QLabel {{
                color: {self.TEXT_DEFAULT};
            }}
            QToolTip {{
                background-color: {self.BG_SECONDARY};
                color: {self.TEXT_PRIMARY};
                border: 1px solid {self.BORDER_LIGHT};
                border-radius: {self.BORDER_RADIUS_SM};
                padding: 4px 8px;
            }}
        """ + self.custom_qss


# ── Tema por defecto ───────────────────────────────────────
DARK_THEME = Theme()

# ── Proxy dinámico ─────────────────────────────────────────
_current_theme = DARK_THEME


class _ThemeProxy:
    """Proxy que delega toda lectura de atributos al tema activo.

    Los widgets importan ``current`` en vez de ``DARK_THEME``;
    de esta forma, si se cambia el tema en tiempo de ejecución,
    las referencias a ``theme.COLOR`` siguen funcionando sin
    necesidad de re-importar.
    """

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(_current_theme, name)


current = _ThemeProxy()


# ── Función de aplicación ──────────────────────────────────
def apply_theme(window, theme: Theme = DARK_THEME):
    """Aplica un tema completo a la ventana principal."""
    global _current_theme
    _current_theme = theme
    window.setStyleSheet(theme.global_stylesheet())
