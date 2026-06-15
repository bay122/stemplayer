import subprocess
import time
import traceback
import librosa
import scipy.signal
import numpy as np
from PySide6.QtCore import QThread, Signal
from app.services import _log
from app.services.whisper import transcribe_guide_audio


NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def find_guide_audio(stems: dict):
    for name, data in stems.items():
        fname = name.lower()
        if any(token in fname for token in ["guide", "guia", "cue", "vocal"]):
            return name, data["audio"]
    return None, None


def build_harmonic_mix(stems: dict):
    _log("Harmonic Mix", f"Iniciando la fusión de stems")
    mixed_audio = None
    included = []
    skipped = []

    for name, data in stems.items():
        cat = data.get("category", "").lower()
        fname = name.lower()

        should_skip = (
            "click" in cat or
            "click" in fname or
            "guide" in fname or
            "cue" in fname or
            "drum" in cat or
            "bateria" in fname or
            "drum" in fname
        )
        if should_skip:
            skipped.append(name)
            continue

        included.append(name)
        if mixed_audio is None:
            mixed_audio = data["audio"].copy()
        else:
            length = max(len(mixed_audio), len(data["audio"]))
            new_mixed = np.zeros(length, dtype=np.float32)
            new_mixed[:len(mixed_audio)] += mixed_audio
            new_mixed[:len(data["audio"])] += data["audio"]
            mixed_audio = new_mixed

    return mixed_audio, included, skipped


def extract_chords(y: np.ndarray, sr: int):
    _log("Extract Chords", f"Iniciando la extracción de acordes")
    sr_proc = 22050
    y_resampled = librosa.resample(y, orig_sr=sr, target_sr=sr_proc)
    y_harmonic, _ = librosa.effects.hpss(y_resampled)
    tuning = librosa.estimate_tuning(y=y_harmonic, sr=sr_proc)

    hop_length = 2048
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr_proc, tuning=tuning, hop_length=hop_length)

    templates = []
    labels = []

    for i, root in enumerate(NOTES):
        t_maj = np.zeros(12); t_maj[i] = t_maj[(i+4)%12] = t_maj[(i+7)%12] = 1.0
        templates.append(t_maj / np.linalg.norm(t_maj))
        labels.append(root)

        t_min = np.zeros(12); t_min[i] = t_min[(i+3)%12] = t_min[(i+7)%12] = 1.0
        templates.append(t_min / np.linalg.norm(t_min))
        labels.append(f"{root}m")

        t_dom7 = np.zeros(12); t_dom7[i] = t_dom7[(i+4)%12] = t_dom7[(i+7)%12] = t_dom7[(i+10)%12] = 1.0
        templates.append(t_dom7 / np.linalg.norm(t_dom7))
        labels.append(f"{root}7")

        t_min7 = np.zeros(12); t_min7[i] = t_min7[(i+3)%12] = t_min7[(i+7)%12] = t_min7[(i+10)%12] = 1.0
        templates.append(t_min7 / np.linalg.norm(t_min7))
        labels.append(f"{root}m7")

        t_maj7 = np.zeros(12); t_maj7[i] = t_maj7[(i+4)%12] = t_maj7[(i+7)%12] = t_maj7[(i+11)%12] = 1.0
        templates.append(t_maj7 / np.linalg.norm(t_maj7))
        labels.append(f"{root}maj7")

    templates = np.array(templates)
    similarity = np.dot(templates, chroma)
    best_matches = np.argmax(similarity, axis=0)
    smoothed_matches = scipy.signal.medfilt(best_matches, kernel_size=15).astype(int)

    chords = []
    current_chord = labels[smoothed_matches[0]]
    start_frame = 0

    for i in range(1, len(smoothed_matches)):
        chord = labels[smoothed_matches[i]]
        if chord != current_chord:
            dur_frames = i - start_frame
            start_time = librosa.frames_to_time(start_frame, sr=sr_proc, hop_length=hop_length)
            dur_time = librosa.frames_to_time(dur_frames, sr=sr_proc, hop_length=hop_length)

            if dur_time >= 0.5:
                chords.append({
                    "time": round(start_time, 2),
                    "duration": round(dur_time, 2),
                    "chord": current_chord
                })

            current_chord = chord
            start_frame = i

    dur_frames = len(smoothed_matches) - start_frame
    start_time = librosa.frames_to_time(start_frame, sr=sr_proc, hop_length=hop_length)
    dur_time = librosa.frames_to_time(dur_frames, sr=sr_proc, hop_length=hop_length)
    if dur_time >= 0.5:
        chords.append({
            "time": round(start_time, 2),
            "duration": round(dur_time, 2),
            "chord": current_chord
        })

    return chords


def map_chords_to_sections(sections: list, all_chords: list):
    chords_by_section = {}
    if sections and all_chords:
        for i, sec in enumerate(sections):
            sec_name = sec["label"]
            start = sec["start"]
            end = sections[i + 1]["start"] if i + 1 < len(sections) else (all_chords[-1]["time"] + 10)
            sec["end"] = end

            sec_chords = [c for c in all_chords if start <= c["time"] < end]
            simplified = []
            for chord in sec_chords:
                if not simplified or simplified[-1]["chord"] != chord["chord"]:
                    simplified.append(chord)

            chords_by_section[sec_name] = simplified
    else:
        chords_by_section["Global"] = all_chords

    return chords_by_section


class ChordAnalysisThread(QThread):
    progress = Signal(str)
    progress_pct = Signal(int)
    finished_analysis = Signal(dict)
    error = Signal(str)

    def __init__(self, song_folder: str, stems: dict, mix_sr: int = 44100):
        super().__init__()
        self.song_folder = song_folder
        self.stems = stems
        self.mix_sr = mix_sr
        self._is_cancelled = False
        self._worker_process_holder = {"process": None}

    def cancel(self):
        self._is_cancelled = True
        process = self._worker_process_holder.get("process")
        if process and process.poll() is None:
            _log("ChordAnalysis", "Cancelando worker de CREMA...")
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _log("ChordAnalysis", "El worker no respondio al terminate(); forzando kill()")
                process.kill()

    def run(self):
        start_time = time.perf_counter()
        try:
            _log("ChordAnalysis", f"Inicio de analisis para '{self.song_folder}' con {len(self.stems)} stems")
            self.progress.emit("Iniciando analisis de IA (puede tomar un momento)...")
            self.progress_pct.emit(5)

            guide_name, guide_audio = find_guide_audio(self.stems)
            sections = []

            if guide_audio is not None:
                _log("ChordAnalysis", f"Guide detectado: {guide_name}")
                self.progress.emit("Cargando modelo Whisper...")
                self.progress_pct.emit(8)
                if self._is_cancelled:
                    return

                self.progress.emit("Transcribiendo secciones con Whisper...")
                self.progress_pct.emit(10)
                try:
                    sections = transcribe_guide_audio(guide_audio, self.mix_sr)
                except Exception as exc:
                    _log("Whisper", f"Fallo durante la transcripcion: {exc!r}")
                    traceback.print_exc()
                    sections = []
            else:
                _log("ChordAnalysis", "No se encontro pista guide; se usara agrupacion Global")

            if self._is_cancelled:
                return

            self.progress.emit("Mezclando instrumentos para deteccion de acordes...")
            self.progress_pct.emit(40)
            mixed_audio, included_stems, skipped_stems = build_harmonic_mix(self.stems)
            _log("ChordAnalysis", f"Stems incluidos para analisis armonico: {included_stems}")
            _log("ChordAnalysis", f"Stems omitidos: {skipped_stems}")

            all_chords = []
            if mixed_audio is not None:
                self.progress.emit("Detectando acordes con DSP (Librosa)...")
                self.progress_pct.emit(50)

                if self._is_cancelled:
                    return

                all_chords = extract_chords(mixed_audio, self.mix_sr)
                _log("Extract Chords", f"Total de acordes detectados: {len(all_chords)}")
            else:
                _log("ChordAnalysis", "No hubo stems aptos para analizar acordes")

            if self._is_cancelled:
                return

            self.progress.emit("Consolidando resultados...")
            self.progress_pct.emit(90)
            chords_by_section = map_chords_to_sections(sections, all_chords)

            result = {
                "sections": sections,
                "chords_by_section": chords_by_section,
                "raw_chords": all_chords,
            }

            elapsed = time.perf_counter() - start_time
            _log(
                "ChordAnalysis",
                f"Analisis completado en {elapsed:.2f}s | secciones={len(sections)} | acordes={len(all_chords)}",
            )
            self.progress.emit("Analisis completado.")
            self.progress_pct.emit(100)
            self.finished_analysis.emit(result)

        except Exception:
            _log("ChordAnalysis", "Excepcion no controlada durante el analisis")
            traceback.print_exc()
            if not self._is_cancelled:
                self.error.emit("No se pudo completar el analisis musical necesario para generar el sheet.")
