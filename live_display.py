import json
import re
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

class LiveChordWidget(QWidget):
    """Widget que muestra los acordes y letras en formato Karaoke/Teleprompter."""
    
    close_requested = Signal()  # Señal para cerrar el modo live
    
    def __init__(self):
        super().__init__()
        self.data = []
        self.sync_data = []
        self.current_section = None
        self._setup_ui()
        self.setStyleSheet("background-color: #111111;")
        
    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(0)
        
        # Botón de cierre (Arriba a la derecha)
        close_btn_layout = QHBoxLayout()
        close_btn_layout.addStretch()
        self.close_btn = QPushButton("✕ Cerrar Karaoke")
        self.close_btn.setMaximumWidth(200)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5555;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #FF3333;
            }
        """)
        self.close_btn.clicked.connect(self.close_requested.emit)
        close_btn_layout.addWidget(self.close_btn)
        main_layout.addLayout(close_btn_layout)
        
        main_layout.addSpacing(20)
        
        # Nombre de sección (Arriba)
        self.section_label = QLabel("Esperando reproducción...")
        self.section_label.setAlignment(Qt.AlignCenter)
        self.section_label.setStyleSheet("""
            color: #AAAAAA;
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 2px;
            margin-bottom: 20px;
        """)
        main_layout.addWidget(self.section_label)
        
        main_layout.addStretch(1)
        
        # Fila de acordes
        chords_layout = QHBoxLayout()
        chords_layout.setSpacing(20)
        
        # Acorde actual (grande y verde)
        self.chord_label = QLabel("-")
        self.chord_label.setAlignment(Qt.AlignCenter)
        chord_font = QFont()
        chord_font.setPointSize(80)
        chord_font.setBold(True)
        self.chord_label.setFont(chord_font)
        self.chord_label.setStyleSheet("color: #4CAF50;")
        chords_layout.addWidget(self.chord_label, alignment=Qt.AlignCenter)
        
        # Próximo acorde (más pequeño y gris)
        self.next_chord_label = QLabel("")
        self.next_chord_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        next_font = QFont()
        next_font.setPointSize(32)
        next_font.setBold(True)
        self.next_chord_label.setFont(next_font)
        self.next_chord_label.setStyleSheet("color: #666666;")
        chords_layout.addWidget(self.next_chord_label, alignment=Qt.AlignLeft)
        
        main_layout.addLayout(chords_layout)
        main_layout.addStretch(2)
        
        # Letra actual (Abajo)
        self.lyric_label = QLabel("")
        self.lyric_label.setAlignment(Qt.AlignCenter)
        lyric_font = QFont()
        lyric_font.setPointSize(28)
        self.lyric_label.setFont(lyric_font)
        self.lyric_label.setStyleSheet("color: #FFFFFF;")
        self.lyric_label.setWordWrap(True)
        main_layout.addWidget(self.lyric_label)
        
        main_layout.addStretch(1)
        
    def load_sync_data(self, chopro_path: str, sync_path: str):
        """
        Carga los datos de sincronización desde los archivos .chopro y .sync.json
        
        Args:
            chopro_path: Ruta al archivo .chopro
            sync_path: Ruta al archivo .sync.json
        """
        self.data = []
        self.sync_data = []
        
        # Cargar datos de sincronización (timestamps de secciones)
        if os.path.exists(sync_path):
            try:
                with open(sync_path, 'r', encoding='utf-8') as f:
                    sync_info = json.load(f)
                    self.sync_data = sync_info.get("sections", [])
            except Exception as e:
                print(f"[LiveDisplay] Error cargando sync.json: {e}")
                self.sync_data = []
        
        # Cargar y parsear el archivo .chopro
        if not os.path.exists(chopro_path):
            print(f"[LiveDisplay] Archivo no encontrado: {chopro_path}")
            return
        
        try:
            from chordpro_editor import ChordProParser
            parsed = ChordProParser.parse(chopro_path)
            
            self._process_sections(parsed["sections"])
            self.data.sort(key=lambda x: x["time"])
            
            print(f"[LiveDisplay] Datos sincronizados: {len(self.data)} eventos")
        except Exception as e:
            print(f"[LiveDisplay] Error procesando ChordPro: {e}")
    
    def _process_sections(self, sections: list):
        """Procesa las secciones del ChordPro y las sincroniza con los timestamps"""
        for section in sections:
            section_name = section.get("name", "Global")
            
            # Buscar los timestamps de esta sección en sync_data
            sync_section = next(
                (s for s in self.sync_data if s["label"].lower() == section_name.lower()),
                None
            )
            
            if sync_section:
                start_time = float(sync_section.get("start", 0.0))
                end_time = float(sync_section.get("end", start_time + 20.0))
            else:
                # Si no hay sincronización, estimar tiempos basados en posición
                if self.data:
                    start_time = self.data[-1]["time"] + 1.0
                else:
                    start_time = 0.0
                end_time = start_time + 20.0
            
            lines = section.get("lines", [])
            valid_lines = [l for l in lines if l.strip() and not l.startswith("{")]
            
            if not valid_lines:
                continue
            
            # Distribuir líneas uniformemente en el tiempo de la sección
            time_per_line = (end_time - start_time) / len(valid_lines) if valid_lines else 1.0
            current_time = start_time
            
            for line in lines:
                if not line.strip() or line.startswith("{"):
                    continue
                
                # Extraer acordes y letras de la línea
                self._parse_line(line, section_name, current_time, time_per_line)
                current_time += time_per_line
    
    def _parse_line(self, line: str, section_name: str, base_time: float, duration: float):
        """Parsea una línea del ChordPro y crea eventos de sincronización"""
        # Buscar acordes entre corchetes [Chord]
        chord_pattern = r'\[([^\]]+)\]'
        text_parts = re.split(chord_pattern, line)
        
        # Reconstruir la línea sin acordes para obtener la letra limpia
        lyric_text = ""
        chords_in_line = []
        
        for i, part in enumerate(text_parts):
            if i % 2 == 0:  # Texto (no acorde)
                lyric_text += part
            else:  # Acorde
                chords_in_line.append(part)
        
        lyric_text = lyric_text.strip()
        
        if chords_in_line:
            # Distribuir acordes uniformemente en la duración de la línea
            chord_interval = duration / len(chords_in_line) if chords_in_line else 1.0
            
            for i, chord in enumerate(chords_in_line):
                self.data.append({
                    "time": base_time + (i * chord_interval),
                    "section": section_name,
                    "chord": chord.strip(),
                    "lyric": lyric_text
                })
        else:
            # Línea sin acordes - hereda el anterior
            self.data.append({
                "time": base_time,
                "section": section_name,
                "chord": None,
                "lyric": lyric_text
            })
    
    def reset(self):
        """Reinicia el widget a su estado inicial"""
        self.section_label.setText("Esperando reproducción...")
        self.chord_label.setText("-")
        self.next_chord_label.setText("")
        self.lyric_label.setText("")
        self.current_section = None
        
    def update_position(self, current_seconds: float):
        """Actualiza la visualización según la posición actual de reproducción"""
        if not self.data:
            return
        
        # Encontrar el evento actual
        current_state = None
        next_chord = None
        last_chord_seen = "-"
        current_section_name = None
        
        for i, item in enumerate(self.data):
            # Rastrear el último acorde visto
            if item["chord"]:
                last_chord_seen = item["chord"]
            
            # Buscar el evento que coincida con el tiempo actual
            if item["time"] <= current_seconds:
                current_state = item.copy()
                current_state["active_chord"] = last_chord_seen
                current_section_name = item["section"]
            else:
                # Buscar el siguiente acorde diferente
                if current_state:
                    for j in range(i, len(self.data)):
                        future_item = self.data[j]
                        if (future_item["chord"] and 
                            future_item["chord"] != last_chord_seen and
                            future_item["time"] > current_seconds):
                            next_chord = future_item["chord"]
                            break
                break
        
        # Actualizar UI con los datos encontrados
        if current_state:
            # Actualizar sección si cambió
            if current_section_name != self.current_section:
                self.current_section = current_section_name
                self.section_label.setText(f"▶ {current_section_name.upper()}")
            
            # Actualizar acorde actual
            self.chord_label.setText(current_state["active_chord"])
            
            # Actualizar próximo acorde
            if next_chord:
                self.next_chord_label.setText(f"→ {next_chord}")
            else:
                self.next_chord_label.setText("")
            
            # Actualizar letra
            if current_state["lyric"]:
                self.lyric_label.setText(current_state["lyric"])
            else:
                self.lyric_label.setText("")
        else:
            # Si no hay estado actual, mostrar estado inicial
            if self.section_label.text() == "Esperando reproducción...":
                return
            self.reset()
