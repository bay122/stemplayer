import json
import re
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextBrowser,
    QApplication, QInputDialog, QGraphicsOpacityEffect, QDialog, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QEvent, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QPainter, QPen, QBrush, QColor, QPixmap, QFont
from app.ui.chordpro_editor import ChordProParser
from app.ui.theme import current as theme
from app.ui.karaoke_streamer import KaraokeStreamer
try:
    import qrcode
    from io import BytesIO
    HAS_QR = True
except ImportError:
    HAS_QR = False


def seconds_to_str(seconds: float) -> str:
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:05.2f}"


class SectionMarkersBar(QWidget):
    def __init__(self):
        super().__init__()
        self._marks = []
        self._current_pos = 0.0
        self.setFixedHeight(28)
        self.setMinimumWidth(80)

    def set_marks(self, ratios):
        self._marks = sorted(ratios)
        self.update()

    def set_current_pos(self, ratio):
        self._current_pos = max(0.0, min(1.0, ratio))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        bar_h = 8
        radius = 4
        bar_y = (h - bar_h) // 2

        bg_color = QColor(theme.BG_TERTIARY)
        fill_color = QColor(theme.ACCENT_INFO)
        marker_color = QColor(theme.ACCENT_WARNING)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(0, bar_y, w, bar_h, radius, radius)

        if self._current_pos > 0:
            played_px = int(self._current_pos * w)
            if played_px > 0:
                painter.save()
                painter.setClipRect(0, bar_y, played_px, bar_h)
                painter.setBrush(QBrush(fill_color))
                painter.drawRoundedRect(0, bar_y, w, bar_h, radius, radius)
                painter.restore()

        if self._marks:
            painter.setPen(QPen(marker_color, 2))
            for ratio in self._marks:
                x = int(ratio * w)
                painter.drawLine(x, bar_y - 2, x, bar_y + bar_h + 2)

        painter.end()


class KaraokeFullscreenWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setStyleSheet(f"background-color: {theme.BG_DARK};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 40, 60, 40)

        self.song_info_label = QLabel()
        self.song_info_label.setAlignment(Qt.AlignCenter)
        self.song_info_label.setStyleSheet(f"""
            color: {theme.TEXT_MUTED};
            font-size: 18px;
            margin-bottom: 4px;
        """)
        layout.addWidget(self.song_info_label)

        self.section_label = QLabel()
        self.section_label.setAlignment(Qt.AlignCenter)
        self.section_label.setStyleSheet(f"""
            color: {theme.TEXT_MUTED};
            font-size: 32px;
            font-weight: bold;
            letter-spacing: 3px;
            margin-bottom: 20px;
        """)
        layout.addWidget(self.section_label)

        self.section_content = QTextBrowser()
        self.section_content.setOpenExternalLinks(False)
        self.section_content.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                border: none;
                color: {theme.TEXT_PRIMARY};
            }}
        """)
        layout.addWidget(self.section_content, stretch=1)

        self.markers_bar = SectionMarkersBar()
        layout.addWidget(self.markers_bar)

        time_row = QHBoxLayout()
        self.time_elapsed = QLabel("00:00.00")
        self.time_elapsed.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 14px;")
        time_row.addWidget(self.time_elapsed)

        time_row.addStretch()

        self.countdown_label = QLabel("")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet(f"color: {theme.ACCENT_WARNING}; font-size: 15px; font-weight: bold;")
        time_row.addWidget(self.countdown_label)

        time_row.addStretch()

        self.time_total = QLabel("00:00.00")
        self.time_total.setAlignment(Qt.AlignRight)
        self.time_total.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 14px;")
        time_row.addWidget(self.time_total)

        layout.addLayout(time_row)

    def set_content(self, section_text, html, next_html=""):
        self.section_label.setText(section_text)
        full_html = html
        if next_html:
            full_html += f"<hr style='border: none; border-top: 1px solid {theme.BG_TERTIARY}; margin: 30px 0 10px 0;'><div style='opacity: 0.5;'>{next_html}</div>"
        self._animate_set_html(self.section_content, full_html)

    def _animate_set_html(self, text_browser, html_content):
        effect = text_browser.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(text_browser)
            text_browser.setGraphicsEffect(effect)

        if hasattr(text_browser, "_anim") and text_browser._anim:
            text_browser._anim.stop()

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(150)
        anim.setStartValue(effect.opacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutQuad)

        def on_fade_out_finished():
            text_browser.setHtml(html_content)
            fade_in = QPropertyAnimation(effect, b"opacity")
            fade_in.setDuration(150)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.InQuad)
            text_browser._anim = fade_in
            fade_in.start()

        anim.finished.connect(on_fade_out_finished)
        text_browser._anim = anim
        anim.start()

    def set_song_info(self, name, artist):
        if name:
            text = name
            if artist:
                text += f" — {artist}"
            self.song_info_label.setText(text)

    def update_progress(self, current_seconds, total_seconds):
        if total_seconds > 0:
            self.time_elapsed.setText(seconds_to_str(current_seconds))
            self.time_total.setText(seconds_to_str(total_seconds))
            self.markers_bar.set_current_pos(current_seconds / total_seconds)

    def set_markers(self, ratios):
        self.markers_bar.set_marks(ratios)

    def set_countdown(self, remaining, next_section=""):
        if remaining > 0:
            text = f"Próxima sección en {remaining:.1f}s"
            if next_section:
                text += f" → {next_section}"
            self.countdown_label.setText(text)
        else:
            self.countdown_label.setText("")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)


class LiveChordWidget(QWidget):
    close_requested = Signal()

    def __init__(self):
        super().__init__()
        self.data = []
        self.sync_data = []
        self.section_chordpro = {}
        self._section_raw_lines = {}
        self.current_section = None
        self._font_size_index = 0
        self._base_font_size = 22
        self._fullscreen_window = None
        self._song_name = ""
        self._song_artist = ""
        self._section_order = []
        self._streamer = None
        self._stream_dialog = None
        self._stream_port = 8080
        self._last_tick_time = 0.0
        self._setup_ui()
        self.setStyleSheet(f"background-color: {theme.BG_DARK};")
        self.section_content.installEventFilter(self)
        self.section_content.viewport().installEventFilter(self)

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

    def _current_font_size(self):
        return self._base_font_size + self._font_size_index * 2

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(0)

        top_btn_layout = QHBoxLayout()

        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setFixedSize(32, 28)
        self.fullscreen_btn.setToolTip("Pantalla completa (solo Live Chords)")
        self.fullscreen_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {theme.ACCENT_INFO};
            }}
        """)
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        top_btn_layout.addWidget(self.fullscreen_btn)

        top_btn_layout.addStretch()

        self.close_btn = QPushButton("✕ Cerrar Live Chords")
        self.close_btn.setMaximumWidth(200)
        self.close_btn.setToolTip("Cerrar la ventana de Live Chords")
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_DANGER_ALT};
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme.ACCENT_DANGER_ALT_HOVER};
            }}
        """)
        self.close_btn.clicked.connect(self.close_requested.emit)
        top_btn_layout.addWidget(self.close_btn)

        main_layout.addLayout(top_btn_layout)

        main_layout.addSpacing(12)

        self.section_label = QLabel("Esperando reproduccion...")
        self.section_label.setAlignment(Qt.AlignCenter)
        self.section_label.setStyleSheet(f"""
            color: {theme.TEXT_MUTED};
            font-size: 22px;
            font-weight: bold;
            letter-spacing: 2px;
            margin-bottom: 16px;
        """)
        main_layout.addWidget(self.section_label)

        self.section_content = QTextBrowser()
        self.section_content.setOpenExternalLinks(False)
        self.section_content.setStyleSheet(f"""
            QTextBrowser {{
                background-color: transparent;
                border: none;
                color: {theme.TEXT_PRIMARY};
            }}
        """)
        main_layout.addWidget(self.section_content, stretch=1)

        main_layout.addSpacing(8)

        self.markers_bar = SectionMarkersBar()
        main_layout.addWidget(self.markers_bar)

        info_layout = QHBoxLayout()
        self.time_elapsed = QLabel("00:00.00")
        self.time_elapsed.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px;")
        info_layout.addWidget(self.time_elapsed)

        info_layout.addStretch()

        self.countdown_label = QLabel("")
        self.countdown_label.setAlignment(Qt.AlignCenter)
        self.countdown_label.setStyleSheet(f"color: {theme.ACCENT_WARNING}; font-size: 13px; font-weight: bold;")
        info_layout.addWidget(self.countdown_label)

        info_layout.addStretch()

        self.time_total = QLabel("00:00.00")
        self.time_total.setAlignment(Qt.AlignRight)
        self.time_total.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px;")
        info_layout.addWidget(self.time_total)

        main_layout.addLayout(info_layout)

    def set_song_info(self, name, artist):
        self._song_name = name
        self._song_artist = artist
        if self._fullscreen_window and self._fullscreen_window.isVisible():
            self._fullscreen_window.set_song_info(name, artist)

    def eventFilter(self, obj, event):
        if (obj is self.section_content or obj is self.section_content.viewport()) and event.type() == QEvent.Wheel:
            if event.modifiers() & Qt.ControlModifier:
                delta = event.angleDelta().y()
                old_idx = self._font_size_index
                if delta > 0:
                    self._font_size_index = min(3, self._font_size_index + 1)
                else:
                    self._font_size_index = max(-3, self._font_size_index - 1)
                if self._font_size_index != old_idx and self.current_section and self.current_section in self._section_raw_lines:
                    self._refresh_section()
                return True
            return False
        return super().eventFilter(obj, event)

    def set_stream_port(self, port: int):
        self._stream_port = port

    def get_stream_state(self) -> dict:
        total = self._get_total_seconds()
        progress = 0.0
        current = getattr(self, '_last_tick_time', 0.0)
        if total > 0:
            progress = current / total
        markers = []
        if total > 0:
            if self.section_chordpro:
                for info in self.section_chordpro.values():
                    markers.append(info["start"] / total)
                    markers.append(info["end"] / total)
            elif self.sync_data:
                for sec in self.sync_data:
                    markers.append(float(sec.get("start", 0)) / total)
                    markers.append(float(sec.get("end", 0)) / total)
            markers = sorted(set(markers))

        section_name = self.current_section if self.current_section else ""
        section_html = ""
        next_name = ""
        next_html = ""
        countdown_remaining = 0.0
        if section_name and section_name in self.section_chordpro:
            section_html = self.section_chordpro[section_name]["html"]
            countdown_remaining = max(0.0, self.section_chordpro[section_name]["end"] - current)
            next_name = self._get_next_section_name(section_name)
            if next_name and next_name in self.section_chordpro:
                next_html = self.section_chordpro[next_name]["html"]

        return {
            "song_name": self._song_name,
            "song_artist": self._song_artist,
            "section_name": section_name.upper() if section_name else "",
            "section_html": section_html,
            "next_section_name": next_name.upper() if next_name else "",
            "next_section_html": next_html,
            "countdown_remaining": countdown_remaining,
            "elapsed": current,
            "total": total,
            "progress": progress,
            "markers": markers,
        }

    def _toggle_fullscreen(self):
        if self._fullscreen_window and self._fullscreen_window.isVisible():
            self._fullscreen_window.close()
            self._fullscreen_window = None
            return
        if self._streamer and self._streamer.running:
            if self._stream_dialog and not self._stream_dialog.isVisible():
                self._stream_dialog.show()
                self._stream_dialog.raise_()
            else:
                self._stop_stream()
            return

        screens = QApplication.screens()
        screen = screens[0] if screens else None
        items = [f"Pantalla {i+1}: {s.name()}" for i, s in enumerate(screens)]
        items.append("🌐 Stream a navegador (Web)")
        item, ok = QInputDialog.getItem(self, "Seleccionar pantalla",
            "¿En qué pantalla mostrar el Live Chords?", items, 0, False)
        if not ok or not item:
            return

        if item == items[-1]:
            self._start_stream()
            return

        self._fullscreen_window = KaraokeFullscreenWindow()
        idx = items.index(item)
        screen = screens[idx]
        if screen:
            self._fullscreen_window.setGeometry(screen.geometry())
        self._fullscreen_window.setScreen(screen)
        self._fullscreen_window.showFullScreen()
        if hasattr(self, '_song_name'):
            self._fullscreen_window.set_song_info(self._song_name, self._song_artist)
        self._sync_fullscreen_window()

    def _sync_fullscreen_window(self):
        if not self._fullscreen_window or not self._fullscreen_window.isVisible():
            return

        total = self._get_total_seconds()
        if total > 0:
            ratios = set()
            if self.section_chordpro:
                for info in self.section_chordpro.values():
                    ratios.add(info["start"] / total)
                    ratios.add(info["end"] / total)
            elif self.sync_data:
                for sec in self.sync_data:
                    ratios.add(float(sec.get("start", 0)) / total)
                    ratios.add(float(sec.get("end", 0)) / total)
            self._fullscreen_window.set_markers(list(ratios))

        if self.current_section and self.current_section in self.section_chordpro:
            label = f"▶ {self.current_section.upper()}"
            html = self.section_chordpro[self.current_section]["html"]
            next_html = self._render_next_section(self.current_section)
            self._fullscreen_window.set_content(label, html, next_html)

    def _start_stream(self):
        if self._streamer and self._streamer.running:
            if self._stream_dialog and not self._stream_dialog.isVisible():
                self._stream_dialog.show()
                self._stream_dialog.raise_()
            return
        self._streamer = KaraokeStreamer(get_state=self.get_stream_state)
        self._streamer.start(self._stream_port)
        self._show_stream_dialog()

    def _stop_stream(self):
        if self._streamer:
            self._streamer.stop()
            self._streamer = None
        if self._stream_dialog:
            self._stream_dialog.close()
            self._stream_dialog = None

    def _show_stream_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Streaming de Live Chords")
        dialog.setMinimumWidth(420)
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {theme.BG_PRIMARY};
                color: {theme.TEXT_PRIMARY};
            }}
            QLabel {{ color: {theme.TEXT_PRIMARY}; }}
        """)
        dl = QVBoxLayout(dialog)
        dl.setSpacing(12)
        dl.setContentsMargins(24, 24, 24, 24)

        title = QLabel("🌐 Streaming activo")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        dl.addWidget(title)

        url_input = QLineEdit(self._streamer.url)
        url_input.setReadOnly(True)
        url_input.setAlignment(Qt.AlignCenter)
        url_input.setCursorPosition(0)
        url_input.setStyleSheet(f"""
            QLineEdit {{
                font-size: 20px; font-weight: bold;
                color: {theme.ACCENT_SUCCESS};
                font-family: monospace;
                padding: 10px;
                background-color: {theme.BG_INPUT};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                selection-background-color: {theme.ACCENT_INFO};
            }}
        """)
        dl.addWidget(url_input)

        instr = QLabel("Abre esta URL en el navegador de otro dispositivo\nconectado a la misma red. Puedes copiar la URL o escanear el código QR.")
        instr.setAlignment(Qt.AlignCenter)
        instr.setWordWrap(True)
        instr.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px;")
        dl.addWidget(instr)

        qr_btn_row = QHBoxLayout()
        qr_btn_row.addStretch()

        qr_toggle_btn = QPushButton("📱 Mostrar QR")
        qr_toggle_btn.setCheckable(True)
        qr_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.BG_TERTIARY};
                color: {theme.TEXT_PRIMARY};
                border: 1px solid {theme.BORDER};
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {theme.HOVER_BRIGHTEN}; }}
            QPushButton:checked {{
                background-color: {theme.ACCENT_INFO};
                color: {theme.TEXT_PRIMARY};
                border-color: {theme.ACCENT_INFO};
            }}
        """)
        qr_toggle_btn.setToolTip("Mostrar u ocultar el código QR")
        qr_btn_row.addWidget(qr_toggle_btn)

        qr_btn_row.addStretch()
        dl.addLayout(qr_btn_row)

        qr_container = QWidget()
        qr_container.setVisible(False)
        qr_cl = QVBoxLayout(qr_container)
        qr_cl.setContentsMargins(0, 0, 0, 0)
        qr_cl.setAlignment(Qt.AlignCenter)

        if HAS_QR:
            qr_img = qrcode.make(self._streamer.url)
            buf = BytesIO()
            qr_img.save(buf, format="PNG")
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            qr_label = QLabel()
            qr_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            qr_label.setAlignment(Qt.AlignCenter)
            qr_cl.addWidget(qr_label)

        qr_toggle_btn.toggled.connect(lambda checked: qr_container.setVisible(checked))
        dl.addWidget(qr_container)

        stop_btn = QPushButton("Detener Stream")
        stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme.ACCENT_DANGER_ALT};
                color: {theme.TEXT_PRIMARY};
                border: none;
                border-radius: {theme.BORDER_RADIUS_SM};
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {theme.ACCENT_DANGER_ALT_HOVER}; }}
        """)
        stop_btn.clicked.connect(lambda: self._stop_stream())
        dl.addWidget(stop_btn)

        self._stream_dialog = dialog
        dialog.show()

    def mouseDoubleClickEvent(self, event):
        self._toggle_fullscreen()
        super().mouseDoubleClickEvent(event)

    def _refresh_section(self):
        if self.current_section and self.current_section in self._section_raw_lines:
            lines = self._section_raw_lines[self.current_section]
            new_html = self._render_section_html(lines)
            next_html = self._render_next_section(self.current_section)
            if next_html:
                full_html = new_html + f"<hr style='border: none; border-top: 1px solid {theme.BG_TERTIARY}; margin: 30px 0 10px 0;'><div style='opacity: 0.5;'>{next_html}</div>"
                self._animate_set_html(self.section_content, full_html)
            else:
                self._animate_set_html(self.section_content, new_html)
            self._sync_fullscreen_window()

    def _animate_set_html(self, text_browser, html_content):
        effect = text_browser.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(text_browser)
            text_browser.setGraphicsEffect(effect)

        if hasattr(text_browser, "_anim") and text_browser._anim:
            text_browser._anim.stop()

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(150)
        anim.setStartValue(effect.opacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.OutQuad)

        def on_fade_out_finished():
            text_browser.setHtml(html_content)
            fade_in = QPropertyAnimation(effect, b"opacity")
            fade_in.setDuration(150)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.InQuad)
            text_browser._anim = fade_in
            fade_in.start()

        anim.finished.connect(on_fade_out_finished)
        text_browser._anim = anim
        anim.start()

    def _render_section_html(self, lines):
        fs = self._current_font_size()
        chord_fs = fs + 2
        parts = []
        parts.append(f"<div style='font-family: monospace; font-size: {fs}px; text-align: center;'>")

        for line in lines:
            normalized = re.sub(r'\{chord:\s*([^}]+)\}', r'[\1]', line)

            segments = re.split(r'(\[[^\]]+\])', normalized)
            chord_row = ""
            lyric_row = ""

            for i, seg in enumerate(segments):
                if seg.startswith("[") and seg.endswith("]"):
                    chord = seg[1:-1]
                    chord_row += f"<span style='color: {theme.ACCENT_SUCCESS}; font-weight: bold; font-size: {chord_fs}px;'>{chord}</span>"
                    prev_seg = segments[i-1] if i > 0 else ""
                    next_seg = segments[i+1] if i+1 < len(segments) else ""
                    prev_cont = bool(prev_seg) and not prev_seg[-1].isspace()
                    next_cont = bool(next_seg) and not next_seg[0].isspace()
                    if prev_cont and next_cont:
                        lyric_row += f"<span style='color: rgba(128,128,128,0.35);'>-</span>"
                        lyric_row += f"<span style='color: transparent;'>{' ' * max(0, len(chord)-1)}</span>"
                    else:
                        lyric_row += f"<span style='color: transparent;'>{chord}</span>"
                else:
                    safe = seg.replace('<', '&lt;').replace('>', '&gt;')
                    chord_row += f"<span style='color: transparent;'>{safe}</span>"
                    lyric_row += safe

            has_chords = theme.ACCENT_SUCCESS in chord_row
            if has_chords:
                parts.append(f"<div style='line-height: 1.15; white-space: pre-wrap;'>{chord_row}</div>")
            parts.append(f"<div style='line-height: 1.5; white-space: pre-wrap; margin-bottom: 10px;'>{lyric_row}</div>")

        parts.append("</div>")
        return "".join(parts)

    def _render_next_section(self, current_section_name):
        if not hasattr(self, '_section_order') or not self._section_order:
            return ""
        try:
            idx = self._section_order.index(current_section_name)
        except ValueError:
            return ""
        if idx + 1 >= len(self._section_order):
            return ""
        next_name = self._section_order[idx + 1]
        if next_name not in self._section_raw_lines:
            return ""
        fs = self._current_font_size()
        next_fs = max(10, fs - 2)
        lines = self._section_raw_lines[next_name]
        chord_fs = next_fs + 2
        parts = []
        parts.append(f"<div style='font-family: monospace; font-size: {next_fs}px; text-align: center; opacity: 0.5;'>")
        parts.append(f"<div style='margin-bottom: 8px; opacity: 0.4;'><em>— Siguiente: {next_name} —</em></div>")

        for line in lines:
            normalized = re.sub(r'\{chord:\s*([^}]+)\}', r'[\1]', line)
            segments = re.split(r'(\[[^\]]+\])', normalized)
            chord_row = ""
            lyric_row = ""

            for i, seg in enumerate(segments):
                if seg.startswith("[") and seg.endswith("]"):
                    chord = seg[1:-1]
                    chord_row += f"<span style='color: {theme.ACCENT_SUCCESS}; font-weight: bold; font-size: {chord_fs}px;'>{chord}</span>"
                    prev_seg = segments[i-1] if i > 0 else ""
                    next_seg = segments[i+1] if i+1 < len(segments) else ""
                    prev_cont = bool(prev_seg) and not prev_seg[-1].isspace()
                    next_cont = bool(next_seg) and not next_seg[0].isspace()
                    if prev_cont and next_cont:
                        lyric_row += f"<span style='color: rgba(128,128,128,0.35);'>-</span>"
                        lyric_row += f"<span style='color: transparent;'>{' ' * max(0, len(chord)-1)}</span>"
                    else:
                        lyric_row += f"<span style='color: transparent;'>{chord}</span>"
                else:
                    safe = seg.replace('<', '&lt;').replace('>', '&gt;')
                    chord_row += f"<span style='color: transparent;'>{safe}</span>"
                    lyric_row += safe

            has_chords = theme.ACCENT_SUCCESS in chord_row
            if has_chords:
                parts.append(f"<div style='line-height: 1.15; white-space: pre-wrap;'>{chord_row}</div>")
            parts.append(f"<div style='line-height: 1.5; white-space: pre-wrap; margin-bottom: 10px;'>{lyric_row}</div>")

        parts.append("</div>")
        return "".join(parts)

    def load_sync_data(self, chopro_path: str, sync_path: str):
        self.data = []
        self.sync_data = []
        self.section_chordpro = {}
        self._section_raw_lines = {}

        if os.path.exists(sync_path):
            try:
                with open(sync_path, 'r', encoding='utf-8') as f:
                    sync_info = json.load(f)
                    self.sync_data = sync_info.get("sections", [])
                print(f"[LiveDisplay] Sync data cargado: {len(self.sync_data)} secciones")
            except Exception as e:
                print(f"[LiveDisplay] Error cargando sync.json: {e}")
                self.sync_data = []

        if not os.path.exists(chopro_path):
            if self.sync_data:
                print(f"[LiveDisplay] Modo secciones (sin chordpro): {len(self.sync_data)} secciones")
            else:
                print(f"[LiveDisplay] Sin datos de sincronizacion: {chopro_path}")
            return

        try:
            parsed = ChordProParser.parse(chopro_path)

            self._process_sections(parsed["sections"])
            self.data.sort(key=lambda x: x["time"])

            _directives = ("{c:", "{comment:", "{start_of_", "{end_of_",
                           "{title:", "{t:", "{artist:", "{a:", "{key:", "{k:", "{bpm:",
                           "{soc}", "{sov}", "{sob}")
            for sec in parsed["sections"]:
                name = sec.get("name", "Global")
                sec_lines = sec.get("lines", [])
                content_lines = [l for l in sec_lines if l.strip() and not l.strip().startswith(_directives)]
                if not content_lines:
                    continue

                self._section_raw_lines[name] = content_lines
                html = self._render_section_html(content_lines)

                sync_sec = next(
                    (s for s in self.sync_data if self._match_sync_section(name, s["label"])),
                    None
                )
                if sync_sec:
                    start = float(sync_sec.get("start", 0.0))
                    end = float(sync_sec.get("end", start + 10.0))
                else:
                    events = [d for d in self.data if d["section"] == name]
                    if events:
                        start = events[0]["time"]
                        end = events[-1]["time"] + 1.0
                    else:
                        continue

                self.section_chordpro[name] = {"html": html, "start": start, "end": end}

            self._section_order = sorted(self.section_chordpro.keys(), key=lambda n: self.section_chordpro[n]["start"])

            print(f"[LiveDisplay] Datos sincronizados: {len(self.data)} eventos, {len(self.section_chordpro)} secciones")
        except Exception as e:
            print(f"[LiveDisplay] Error procesando ChordPro: {e}")

        self._update_markers()

    def _process_sections(self, sections: list):
        for section in sections:
            section_name = section.get("name", "Global")

            sync_section = next(
                (s for s in self.sync_data if self._match_sync_section(section_name, s["label"])),
                None
            )

            if sync_section:
                start_time = float(sync_section.get("start", 0.0))
                end_time = float(sync_section.get("end", start_time + 20.0))
            else:
                if self.data:
                    start_time = self.data[-1]["time"] + 1.0
                else:
                    start_time = 0.0
                end_time = start_time + 20.0

            lines = section.get("lines", [])
            _directives = ("{c:", "{comment:", "{start_of_", "{end_of_",
                           "{title:", "{t:", "{artist:", "{a:", "{key:", "{k:", "{bpm:",
                           "{soc}", "{sov}", "{sob}")
            chordpro_lines = [l for l in lines if l.strip() and not l.strip().startswith(_directives)]

            if not chordpro_lines:
                continue

            time_per_line = (end_time - start_time) / len(chordpro_lines) if chordpro_lines else 1.0
            current_time = start_time

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if stripped.startswith(_directives):
                    continue

                self._parse_line(line, section_name, current_time, time_per_line)
                current_time += time_per_line

    def _parse_line(self, line: str, section_name: str, base_time: float, duration: float):
        line_normalized = re.sub(r'\{chord:\s*([^}]+)\}', r'[\1]', line)
        chord_pattern = r'\[([^\]]+)\]'
        text_parts = re.split(chord_pattern, line_normalized)

        lyric_text = ""
        chords_in_line = []

        for i, part in enumerate(text_parts):
            if i % 2 == 0:
                lyric_text += part
            else:
                chords_in_line.append(part)

        lyric_text = lyric_text.strip()

        if chords_in_line:
            chord_interval = duration / len(chords_in_line) if chords_in_line else 1.0

            for i, chord in enumerate(chords_in_line):
                self.data.append({
                    "time": base_time + (i * chord_interval),
                    "section": section_name,
                    "chord": chord.strip(),
                    "lyric": lyric_text
                })
        else:
            self.data.append({
                "time": base_time,
                "section": section_name,
                "chord": None,
                "lyric": lyric_text
            })

    def reset(self):
        self.section_label.setText("Esperando reproduccion...")
        self.section_content.clear()
        self.current_section = None
        self.time_elapsed.setText("00:00.00")
        self.time_total.setText("00:00.00")
        self.countdown_label.setText("")
        self.markers_bar.set_marks([])
        self.markers_bar.set_current_pos(0)
        if self._fullscreen_window:
            self._fullscreen_window.close()
            self._fullscreen_window = None
        self._stop_stream()

    def _get_total_seconds(self):
        if self.section_chordpro:
            return max(info["end"] for info in self.section_chordpro.values())
        if self.sync_data:
            return max(float(sec.get("end", 0)) for sec in self.sync_data)
        return 0

    def _get_next_section_name(self, current_name):
        if not hasattr(self, '_section_order') or not self._section_order:
            return None
        try:
            idx = self._section_order.index(current_name)
        except ValueError:
            return None
        if idx + 1 < len(self._section_order):
            return self._section_order[idx + 1]
        return None

    def _update_markers(self):
        total = self._get_total_seconds()
        if total <= 0:
            self.markers_bar.set_marks([])
            if self._fullscreen_window and self._fullscreen_window.isVisible():
                self._fullscreen_window.set_markers([])
            return
        ratios = set()
        if self.section_chordpro:
            for info in self.section_chordpro.values():
                ratios.add(info["start"] / total)
                ratios.add(info["end"] / total)
        elif self.sync_data:
            for sec in self.sync_data:
                s = float(sec.get("start", 0)) / total
                e = float(sec.get("end", 0)) / total
                ratios.add(s)
                ratios.add(e)
        self.markers_bar.set_marks(list(ratios))
        if self._fullscreen_window and self._fullscreen_window.isVisible():
            self._fullscreen_window.set_markers(list(ratios))

    def _time_tick(self, current_seconds: float):
        self._last_tick_time = current_seconds
        total = self._get_total_seconds()
        if total > 0:
            self.time_elapsed.setText(seconds_to_str(current_seconds))
            self.time_total.setText(seconds_to_str(total))
            self.markers_bar.set_current_pos(current_seconds / total)

        if self._fullscreen_window and self._fullscreen_window.isVisible():
            self._fullscreen_window.update_progress(current_seconds, total)

    def _update_countdown(self, current_seconds: float, active_section: str = None):
        if active_section and active_section in self.section_chordpro:
            remaining = self.section_chordpro[active_section]["end"] - current_seconds
            if remaining > 0:
                next_name = self._get_next_section_name(active_section)
                next_text = f" → {next_name.upper()}" if next_name else " (última)"
                self.countdown_label.setText(f"Próxima sección en {remaining:.1f}s{next_text}")
                if self._fullscreen_window and self._fullscreen_window.isVisible():
                    self._fullscreen_window.set_countdown(remaining, next_name.upper() if next_name else "")
                return
        self.countdown_label.setText("")
        if self._fullscreen_window and self._fullscreen_window.isVisible():
            self._fullscreen_window.set_countdown(0)

    def update_position(self, current_seconds: float):
        if not self.section_chordpro and not self.sync_data:
            if self.section_label.text() == "Esperando reproduccion...":
                self.section_label.setText("▶ REPRODUCIENDO")
            self._time_tick(current_seconds)
            return

        if not self.section_chordpro and self.sync_data:
            current_section_name = None
            for sec in self.sync_data:
                start = float(sec.get("start", 0))
                end = float(sec.get("end", start + 10))
                if start <= current_seconds < end:
                    current_section_name = sec["label"]
                    break
            if current_section_name and current_section_name != self.current_section:
                self.current_section = current_section_name
                self.section_label.setText(f"▶ {current_section_name.upper()}")
            elif not current_section_name and self.section_label.text() == "Esperando reproduccion...":
                self.section_label.setText("▶ REPRODUCIENDO")
            self._time_tick(current_seconds)
            self._update_countdown(current_seconds, current_section_name)
            return

        active_section = None
        for name, info in self.section_chordpro.items():
            if info["start"] <= current_seconds < info["end"]:
                active_section = name
                break

        if active_section:
            if active_section != self.current_section:
                self.current_section = active_section
                self.section_label.setText(f"▶ {active_section.upper()}")
                html = self.section_chordpro[active_section]["html"]
                next_html = self._render_next_section(active_section)
                if next_html:
                    full_html = html + f"<hr style='border: none; border-top: 1px solid {theme.BG_TERTIARY}; margin: 30px 0 10px 0;'><div style='opacity: 0.5;'>{next_html}</div>"
                else:
                    full_html = html
                self._animate_set_html(self.section_content, full_html)
                if self._fullscreen_window and self._fullscreen_window.isVisible():
                    self._fullscreen_window.set_content(f"▶ {active_section.upper()}", html, next_html)
            self._time_tick(current_seconds)
            self._update_countdown(current_seconds, active_section)
        else:
            if self.section_label.text() != "Esperando reproduccion...":
                self.section_label.setText("▶ REPRODUCIENDO")
                self.section_content.clear()
            self._time_tick(current_seconds)
