"""Tema inspirado en StemDeck — DAW oscuro con acento dorado.

Referencia de diseño:
  docs/new_theme/stemdeck-design-guide.md  (colores, tipografía, QSS)
  docs/new_theme/layout.md                  (distribución)
  docs/new_theme/svgs.md                    (iconos SVG)
"""

import os
from app.ui.theme import Theme

theme = Theme(
    # ── Fondos ──────────────────────────────────────────────
    BG_PRIMARY="#0b0f12",
    BG_SECONDARY="#0f1418",
    BG_TERTIARY="#131a1f",
    BG_DARK="#080c0f",
    BG_INPUT="#131a1f",
    BG_EDITOR="#131a1f",
    BG_MENU="#182026",

    # ── Texto ───────────────────────────────────────────────
    TEXT_PRIMARY="#e8ecf0",
    TEXT_DEFAULT="#c2c9d1",
    TEXT_SECONDARY="#8a939c",
    TEXT_MUTED="#5d666e",
    TEXT_EDITOR="#e8ecf0",
    TEXT_DISABLED="#5d666e",

    # ── Acentos ─────────────────────────────────────────────
    ACCENT_PRIMARY="#f4b740",
    ACCENT_PRIMARY_HOVER="#d99a2b",
    ACCENT_CYAN="#f4b740",
    ACCENT_SUCCESS="#4caf7d",
    ACCENT_DANGER="#d65a4a",
    ACCENT_DANGER_ALT="#e54e4e",
    ACCENT_WARNING="#f4b740",
    ACCENT_INFO="#f4b740",
    ACCENT_PURPLE="#a855f7",
    ACCENT_SOLO="#f4b740",

    # ── Bordes ──────────────────────────────────────────────
    BORDER="#232c34",
    BORDER_LIGHT="#2e3942",
    BORDER_DARK="#1d262d",
    BORDER_ALT="#232c34",
    BORDER_WIDGET="#232c34",

    # ── Geometría ───────────────────────────────────────────
    BORDER_RADIUS_SM="6px",
    BORDER_RADIUS_MD="8px",
    FONT_FAMILY=(
        "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', "
        "Roboto, Helvetica, Arial, sans-serif"
    ),
    FONT_SIZE_BASE="13px",
    FONT_MONO=(
        "'JetBrains Mono', ui-monospace, 'SF Mono', "
        "Menlo, Consolas, monospace"
    ),

    # ── Estados ─────────────────────────────────────────────
    HOVER_BRIGHTEN="#1d262d",
    HOVER_ACCENT="#f8c054",
    PRESSED_DARKEN="#182026",

    # ── SVG helper ──────────────────────────────────────────
    SVG_ICON_DEFAULT="#c2c9d1",
    SVG_ICON_MUTED="#8a939c",
    SVG_ICON_ACTIVE="#e8ecf0",
    SVG_ICON_DANGER="#d65a4a",
    SVG_ICON_SOLO="#f4b740",

    # ── Overrides ───────────────────────────────────────────
    icons_dir=os.path.join(os.path.dirname(__file__), "icons"),

    # ── QSS personalizado ───────────────────────────────────
    custom_qss="""
        /* ══════════════════════════════════════════════════════════
           StemDeck — Widget overrides
           ══════════════════════════════════════════════════════════ */

        /* ── QPushButton ───────────────────────────────────── */
        QPushButton {
            background-color: #182026;
            border: 1px solid #232c34;
            border-radius: 8px;
            padding: 6px 14px;
            color: #e8ecf0;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #1d262d;
            border: 1px solid #2e3942;
        }
        QPushButton:pressed {
            background-color: #131a1f;
            border: 1px solid #3a4752;
        }
        QPushButton:checked {
            background-color: rgba(244, 183, 64, 36);
            border: 1px solid rgba(244, 183, 64, 71);
            color: #f4b740;
        }
        QPushButton:checked:hover {
            background-color: rgba(244, 183, 64, 51);
        }
        QPushButton:disabled {
            background-color: #0f1418;
            border: 1px solid #1d262d;
            color: #5d666e;
        }

        /* ── QGroupBox ────────────────────────────────────── */
        QGroupBox {
            background-color: #131a1f;
            border: 1px solid #232c34;
            border-radius: 10px;
            margin-top: 14px;
            padding-top: 10px;
            font-weight: 600;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
            color: #8a939c;
            font-size: 10px;
            font-weight: 600;
        }
        QGroupBox#analysisBox,
        QGroupBox#pitchBox,
        QGroupBox#tempoBox,
        QGroupBox#playBox {
            background-color: #131a1f;
            border: 1px solid #232c34;
        }

        /* ── QLineEdit ────────────────────────────────────── */
        QLineEdit {
            background-color: #131a1f;
            border: 1px solid #2e3942;
            border-radius: 8px;
            padding: 8px 12px;
            color: #e8ecf0;
            selection-background-color: #f4b740;
            selection-color: #0b0f12;
        }
        QLineEdit:focus {
            border: 1px solid #f4b740;
        }
        QLineEdit:disabled {
            background-color: #0f1418;
            border: 1px solid #1d262d;
            color: #5d666e;
        }

        /* ── QComboBox ────────────────────────────────────── */
        QComboBox {
            background-color: #131a1f;
            color: #e8ecf0;
            border: 1px solid #2e3942;
            border-radius: 8px;
            padding: 6px 12px;
        }
        QComboBox:hover {
            border: 1px solid #f4b740;
        }
        QComboBox::drop-down {
            border: none;
            width: 24px;
        }
        QComboBox QAbstractItemView {
            background-color: #182026;
            color: #e8ecf0;
            selection-background-color: rgba(244, 183, 64, 36);
            selection-color: #f4b740;
            border: 1px solid #232c34;
            border-radius: 6px;
            padding: 4px;
            outline: none;
        }

        /* ── QCheckBox ────────────────────────────────────── */
        QCheckBox {
            spacing: 8px;
            color: #c2c9d1;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid #2e3942;
            background-color: #131a1f;
        }
        QCheckBox::indicator:checked {
            background-color: #f4b740;
            border: 1px solid #f4b740;
        }
        QCheckBox::indicator:hover {
            border: 1px solid #f4b740;
        }

        /* ── QListWidget ──────────────────────────────────── */
        QListWidget {
            background-color: #0f1418;
            border: 1px solid #232c34;
            border-radius: 8px;
            color: #e8ecf0;
            outline: none;
        }
        QListWidget::item {
            padding: 6px 8px;
            border-radius: 4px;
        }
        QListWidget::item:selected {
            background-color: rgba(244, 183, 64, 36);
            color: #f4b740;
        }
        QListWidget::item:hover:!selected {
            background-color: #1d262d;
        }

        /* ── QProgressBar ─────────────────────────────────── */
        QProgressBar {
            background-color: #1d262d;
            border: none;
            border-radius: 4px;
            text-align: center;
            color: #e8ecf0;
            font-size: 11px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f4b740, stop:1 #d99a2b);
            border-radius: 4px;
        }

        /* ── QSpinBox ─────────────────────────────────────── */
        QSpinBox {
            background-color: #131a1f;
            border: 1px solid #2e3942;
            border-radius: 8px;
            padding: 6px;
            color: #e8ecf0;
        }
        QSpinBox:focus {
            border: 1px solid #f4b740;
        }

        /* ── QScrollBar vertical ──────────────────────────── */
        QScrollBar:vertical {
            background: transparent;
            width: 8px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: rgba(148, 163, 184, 102);
            border-radius: 4px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: rgba(148, 163, 184, 153);
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0;
        }
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {
            background: none;
        }

        /* ── QScrollBar horizontal ────────────────────────── */
        QScrollBar:horizontal {
            background: transparent;
            height: 8px;
            margin: 0;
        }
        QScrollBar::handle:horizontal {
            background: rgba(148, 163, 184, 102);
            border-radius: 4px;
            min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover {
            background: rgba(148, 163, 184, 153);
        }
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {
            width: 0;
        }
        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {
            background: none;
        }

        /* ── QSlider ::horizontal (playback) ──────────────── */
        QSlider::groove:horizontal {
            border: none;
            height: 4px;
            background: #1d262d;
            border-radius: 2px;
        }
        QSlider::sub-page:horizontal {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 rgba(244,183,64,153), stop:1 #f4b740);
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #f4b740;
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }
        QSlider::handle:horizontal:hover {
            background: #f8c054;
        }

        /* ── QMenu ────────────────────────────────────────── */
        QMenu {
            background-color: #182026;
            color: #e8ecf0;
            border: 1px solid #232c34;
            border-radius: 8px;
            padding: 4px;
        }
        QMenu::item {
            padding: 6px 24px;
            border-radius: 4px;
        }
        QMenu::item:selected {
            background-color: rgba(244, 183, 64, 36);
            color: #f4b740;
        }

        /* ── QTextEdit (chordpro) ─────────────────────────── */
        QTextEdit {
            background-color: #131a1f;
            border: 1px solid #232c34;
            border-radius: 8px;
            color: #e8ecf0;
            selection-background-color: #f4b740;
            selection-color: #0b0f12;
        }

        /* ── QScrollArea ──────────────────────────────────── */
        QScrollArea {
            border: none;
            background-color: transparent;
        }
    """,
)
