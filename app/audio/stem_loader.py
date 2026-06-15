import os
import unicodedata
import numpy as np
import soundfile as sf
import librosa
import threading
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QThread, Signal
from app.audio.fast_audio import fast_audio_load
from app.utils.constants import KEY_MAP


def _strip_accents(text: str) -> str:
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')


class StemLoaderThread(QThread):
    """Hilo para cargar stems y analizar key/BPM sin bloquear la GUI."""

    progress = Signal(str)
    progress_pct = Signal(int)
    finished_loading = Signal(dict, str, int, int, list)
    error = Signal(str)

    def __init__(self, folder_path: str, mix_sr: int = 44100, pre_key: str = None,
                 pre_bpm: int = None, cache_folder: str = None):
        super().__init__()
        self.folder_path = folder_path
        self.mix_sr = mix_sr
        self.pre_key = pre_key
        self.pre_bpm = pre_bpm
        self.cache_folder = cache_folder
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        stems = {}
        originals = {}
        try:
            def file_sort_key(f):
                fname = _strip_accents(f.lower())
                if any(x in fname for x in ["click", "metro"]):
                    return 0
                if any(x in fname for x in ["guide", "cue", "guia"]):
                    return 1
                return 2

            files = [
                f for f in os.listdir(self.folder_path)
                if f.lower().endswith((".wav", ".mp3", ".m4a", ".flac"))
            ]
            files.sort(key=file_sort_key)

            total = len(files)

            stems_lock = threading.Lock()
            click_audio_data = [None]

            mono_cache_dir = None
            if self.cache_folder:
                mono_cache_dir = os.path.join(self.cache_folder, "44100_mono")
                os.makedirs(mono_cache_dir, exist_ok=True)

            completed = [0]

            def process_file(file):
                if self._is_cancelled:
                    return

                stem_name = os.path.splitext(file)[0]
                fname = _strip_accents(file.lower())
                file_path = os.path.join(self.folder_path, file)

                audio = None
                original_audio = None

                wav_path = os.path.join(mono_cache_dir, f"{stem_name}.wav") if mono_cache_dir else None
                if wav_path and os.path.exists(wav_path):
                    try:
                        audio, _ = sf.read(wav_path)
                        audio = audio.astype(np.float32)
                    except Exception as e:
                        print(f"Error loading wav cache {wav_path}: {e}")

                if audio is None:
                    audio, sr = fast_audio_load(file_path, target_sr=self.mix_sr)
                    if wav_path:
                        try:
                            sf.write(wav_path, audio, self.mix_sr, subtype='PCM_16')
                        except Exception as e:
                            print(f"Error saving wav cache {wav_path}: {e}")

                original_audio = audio

                is_click = any(x in fname for x in ["click", "metro"])
                if is_click:
                    with stems_lock:
                        if click_audio_data[0] is None:
                            click_audio_data[0] = audio

                muted = is_click or any(x in fname for x in ["guide", "cue", "guia"])
                fx_enabled = not any(x in fname for x in ["drum", "drums", "bateria", "batería"])

                with stems_lock:
                    stems[stem_name] = {
                        "audio": audio,
                        "sr": self.mix_sr,
                        "volume": 1.0,
                        "pan": 0.0,
                        "muted": muted,
                        "solo": False,
                        "category": "Click" if is_click else ("Drums" if not fx_enabled else "Other"),
                        "fx_enabled": fx_enabled,
                    }
                    originals[stem_name] = original_audio.copy()
                    completed[0] += 1
                    pct = int((completed[0] / total) * 100)
                    self.progress.emit(f"Cargando stems... ({completed[0]}/{total})")
                    self.progress_pct.emit(pct)

            with ThreadPoolExecutor(max_workers=4) as executor:
                for file in files:
                    executor.submit(process_file, file)

            if self._is_cancelled:
                return

            click_audio = click_audio_data[0]

            if not stems:
                self.error.emit("No se encontraron stems válidos.")
                return

            if self.pre_key and self.pre_bpm:
                self.progress.emit("Metadatos encontrados. Omitiendo análisis pesado...")
                key = self.pre_key
                bpm = self.pre_bpm

                click_offset_samples = 0
                if click_audio is not None:
                    tempo, beats = librosa.beat.beat_track(y=click_audio, sr=self.mix_sr)
                    if len(beats) > 0:
                        click_offset_samples = librosa.frames_to_samples(beats[0])
            else:
                self.progress.emit("Analizando mix ...")
                mix = np.zeros(max(len(s["audio"]) for s in stems.values()))
                for s in stems.values():
                    if self._is_cancelled:
                        return
                    length = min(len(mix), len(s["audio"]))
                    mix[:length] += s["audio"][:length] * s["volume"]

                self.progress.emit("Detectando tonalidad ...")
                chroma = librosa.feature.chroma_cqt(y=mix, sr=self.mix_sr)
                chroma_mean = np.mean(chroma, axis=1)
                key = KEY_MAP[int(np.argmax(chroma_mean))]

                self.progress.emit("Detectando BPM ...")
                click_offset_samples = 0
                if click_audio is not None:
                    tempo, beats = librosa.beat.beat_track(y=click_audio, sr=self.mix_sr)
                    if len(beats) > 0:
                        click_offset_samples = librosa.frames_to_samples(beats[0])
                else:
                    tempo, _ = librosa.beat.beat_track(y=mix, sr=self.mix_sr)

                bpm = round(float(np.ravel(tempo)[0]))

            if self._is_cancelled:
                return

            self.progress.emit("Listo.")
            self.progress_pct.emit(100)

            order = list(stems.keys())
            self.finished_loading.emit(stems, key, bpm, click_offset_samples, order)
        except Exception as e:
            self.error.emit(str(e))
