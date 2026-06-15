import json
import re
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from app.ui.chordpro_editor import ChordProParser
from app.ui.theme import current as theme


class LiveChordWidget(QWidget):
    close_requested = Signal()

    def __init__(self):
        super().__init__()
        self.data = []
        self.sync_data = []
        self.current_section = None
        self._setup_ui()
        self.setStyleSheet(f"background-color: {theme.BG_DARK};")

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(0)

        close_btn_layout = QHBoxLayout()
        close_btn_layout.addStretch()
        self.close_btn = QPushButton("✕ Cerrar Karaoke")
        self.close_btn.setMaximumWidth(200)
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
                background-color: #FF3333;
            }}
        """)
        self.close_btn.clicked.connect(self.close_requested.emit)
        close_btn_layout.addWidget(self.close_btn)
        main_layout.addLayout(close_btn_layout)

        main_layout.addSpacing(20)

        self.section_label = QLabel("Esperando reproducción...")
        self.section_label.setAlignment(Qt.AlignCenter)
        self.section_label.setStyleSheet(f"""
            color: {theme.TEXT_MUTED};
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 2px;
            margin-bottom: 20px;
        """)
        main_layout.addWidget(self.section_label)

        main_layout.addStretch(1)

        chords_layout = QHBoxLayout()
        chords_layout.setSpacing(20)

        self.chord_label = QLabel("-")
        self.chord_label.setAlignment(Qt.AlignCenter)
        chord_font = QFont()
        chord_font.setPointSize(80)
        chord_font.setBold(True)
        self.chord_label.setFont(chord_font)
        self.chord_label.setStyleSheet(f"color: {theme.ACCENT_SUCCESS};")
        chords_layout.addWidget(self.chord_label, alignment=Qt.AlignCenter)

        self.next_chord_label = QLabel("")
        self.next_chord_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        next_font = QFont()
        next_font.setPointSize(32)
        next_font.setBold(True)
        self.next_chord_label.setFont(next_font)
        self.next_chord_label.setStyleSheet(f"color: {theme.TEXT_DISABLED};")
        chords_layout.addWidget(self.next_chord_label, alignment=Qt.AlignLeft)

        main_layout.addLayout(chords_layout)
        main_layout.addStretch(2)

        self.lyric_label = QLabel("")
        self.lyric_label.setAlignment(Qt.AlignCenter)
        lyric_font = QFont()
        lyric_font.setPointSize(28)
        self.lyric_label.setFont(lyric_font)
        self.lyric_label.setStyleSheet(f"color: {theme.TEXT_PRIMARY};")
        self.lyric_label.setWordWrap(True)
        main_layout.addWidget(self.lyric_label)

        main_layout.addStretch(1)

    def load_sync_data(self, chopro_path: str, sync_path: str):
        self.data = []
        self.sync_data = []

        if os.path.exists(sync_path):
            try:
                with open(sync_path, 'r', encoding='utf-8') as f:
                    sync_info = json.load(f)
                    self.sync_data = sync_info.get("sections", [])
            except Exception as e:
                print(f"[LiveDisplay] Error cargando sync.json: {e}")
                self.sync_data = []

        if not os.path.exists(chopro_path):
            print(f"[LiveDisplay] Archivo no encontrado: {chopro_path}")
            return

        try:
            parsed = ChordProParser.parse(chopro_path)

            self._process_sections(parsed["sections"])
            self.data.sort(key=lambda x: x["time"])

            print(f"[LiveDisplay] Datos sincronizados: {len(self.data)} eventos")
        except Exception as e:
            print(f"[LiveDisplay] Error procesando ChordPro: {e}")

    def _process_sections(self, sections: list):
        for section in sections:
            section_name = section.get("name", "Global")

            sync_section = next(
                (s for s in self.sync_data if s["label"].lower() == section_name.lower()),
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
            valid_lines = [l for l in lines if l.strip() and not l.startswith("{")]

            if not valid_lines:
                continue

            time_per_line = (end_time - start_time) / len(valid_lines) if valid_lines else 1.0
            current_time = start_time

            for line in lines:
                if not line.strip() or line.startswith("{"):
                    continue

                self._parse_line(line, section_name, current_time, time_per_line)
                current_time += time_per_line

    def _parse_line(self, line: str, section_name: str, base_time: float, duration: float):
        chord_pattern = r'\[([^\]]+)\]'
        text_parts = re.split(chord_pattern, line)

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
        self.section_label.setText("Esperando reproducción...")
        self.chord_label.setText("-")
        self.next_chord_label.setText("")
        self.lyric_label.setText("")
        self.current_section = None

    def update_position(self, current_seconds: float):
        if not self.data:
            return

        current_state = None
        next_chord = None
        last_chord_seen = "-"
        current_section_name = None

        for i, item in enumerate(self.data):
            if item["chord"]:
                last_chord_seen = item["chord"]

            if item["time"] <= current_seconds:
                current_state = item.copy()
                current_state["active_chord"] = last_chord_seen
                current_section_name = item["section"]
            else:
                if current_state:
                    for j in range(i, len(self.data)):
                        future_item = self.data[j]
                        if (future_item["chord"] and
                            future_item["chord"] != last_chord_seen and
                            future_item["time"] > current_seconds):
                            next_chord = future_item["chord"]
                            break
                break

        if current_state:
            if current_section_name != self.current_section:
                self.current_section = current_section_name
                self.section_label.setText(f"▶ {current_section_name.upper()}")

            self.chord_label.setText(current_state["active_chord"])

            if next_chord:
                self.next_chord_label.setText(f"→ {next_chord}")
            else:
                self.next_chord_label.setText("")

            if current_state["lyric"]:
                self.lyric_label.setText(current_state["lyric"])
            else:
                self.lyric_label.setText("")
        else:
            if self.section_label.text() == "Esperando reproducción...":
                return
            self.reset()
