from PySide6.QtCore import QThread, Signal


class PitchTempoThread(QThread):
    """Hilo para aplicar pitch shift y time stretch sin bloquear la GUI."""

    progress = Signal(str)
    progress_pct = Signal(int)
    finished_processing = Signal(dict)
    error = Signal(str)

    def __init__(self, originals: dict, pitch_shift: int, tempo_ratio: float,
                 fx_map: dict = None, mix_sr: int = 44100):
        super().__init__()
        self.originals = originals
        self.pitch_shift = pitch_shift
        self.tempo_ratio = tempo_ratio
        self.fx_map = fx_map or {}
        self.mix_sr = mix_sr
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            import pyrubberband as pyrb
            updated = {}
            total = len(self.originals)
            for i, (name, original) in enumerate(self.originals.items(), 1):
                if self._is_cancelled:
                    return
                self.progress.emit(f"Procesando {name} ({i}/{total}) ...")
                self.progress_pct.emit(int((i / total) * 100))
                audio = original
                fx_on = self.fx_map.get(name, True)
                if self.pitch_shift != 0 and fx_on:
                    try:
                        audio = pyrb.pitch_shift(audio, self.mix_sr, self.pitch_shift)
                    except Exception as e:
                        print(f"Error applying pitch shift to {name}: {e}")
                        audio = original
                if self.tempo_ratio != 1.0:
                    try:
                        audio = pyrb.time_stretch(audio, self.mix_sr, self.tempo_ratio)
                    except Exception as e:
                        print(f"Error applying time stretch to {name}: {e}")
                updated[name] = audio
            self.progress.emit("Procesamiento completado.")
            self.progress_pct.emit(100)
            self.finished_processing.emit(updated)
        except Exception as e:
            self.error.emit(str(e))
