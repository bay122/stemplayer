import os
import unicodedata
import hashlib
import numpy as np
import soundfile as sf
import librosa
import threading
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QThread, Signal
from app.audio.fast_audio import fast_audio_load
from app.utils.constants import KEY_MAP


_BEAT_PROBE_SECONDS = 30
_BEAT_PROBE_SR = 22050
_BEAT_TRACK_CACHE = {}


def _strip_accents(text: str) -> str:
    return unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')


def _probe_click_offset(click_audio: np.ndarray, sr: int, start_bpm: float = None):
    """Detecta el offset del primer beat sobre una versión resumida del click.

    Devuelve el offset en samples del sr original. Usa una versión mono y
    downsampleada a 22050 Hz (suficiente para onset detection) y un máximo
    de _BEAT_PROBE_SECONDS, que es más que bastante para encontrar el primer
    downbeat y reduce el coste de O(n) -> O(1) en duración.
    """
    if click_audio is None or len(click_audio) == 0:
        return 0

    if click_audio.ndim > 1:
        click_audio = np.mean(click_audio, axis=1)

    max_samples = _BEAT_PROBE_SECONDS * sr
    if len(click_audio) > max_samples:
        probe = click_audio[:max_samples]
    else:
        probe = click_audio

    if sr != _BEAT_PROBE_SR:
        probe = librosa.resample(probe, orig_sr=sr, target_sr=_BEAT_PROBE_SR)
        probe_sr = _BEAT_PROBE_SR
    else:
        probe_sr = sr

    cache_key = (
        hashlib.md5(np.ascontiguousarray(probe).tobytes()).hexdigest(),
        int(sr),
        float(start_bpm) if start_bpm else 0.0,
    )
    cached = _BEAT_TRACK_CACHE.get(cache_key)
    if cached is not None:
        return cached

    kwargs = {}
    if start_bpm and start_bpm > 0:
        kwargs["start_bpm"] = float(start_bpm)
    tempo, beats = librosa.beat.beat_track(y=probe, sr=probe_sr, **kwargs)
    if len(beats) == 0:
        offset_samples = 0
    else:
        offset_samples = librosa.frames_to_samples(beats[0])
        scale = sr / probe_sr
        offset_samples = int(round(offset_samples * scale))

    if len(_BEAT_TRACK_CACHE) > 32:
        _BEAT_TRACK_CACHE.clear()
    _BEAT_TRACK_CACHE[cache_key] = offset_samples
    return offset_samples


class StemLoaderThread(QThread):
    """Hilo para cargar stems y analizar key/BPM sin bloquear la GUI."""

    progress = Signal(str)
    progress_pct = Signal(int)
    finished_loading = Signal(dict, str, int, int, list)
    error = Signal(str)

    def __init__(self, folder_path: str, mix_sr: int = 44100, pre_key: str = None,
                 pre_bpm: int = None, pre_click_offset_samples: int = None,
                 cache_folder: str = None, stem_filters: dict = None):
        super().__init__()
        self.folder_path = folder_path
        self.mix_sr = mix_sr
        self.pre_key = pre_key
        self.pre_bpm = pre_bpm
        self.pre_click_offset_samples = (
            int(pre_click_offset_samples)
            if pre_click_offset_samples is not None and int(pre_click_offset_samples) > 0
            else None
        )
        self.cache_folder = cache_folder
        self._is_cancelled = False
        self.stem_filters = stem_filters or {
            "click_patterns": ["click", "metro"],
            "guide_patterns": ["guide", "cue", "guia"],
            "no_fx_patterns": ["drum", "drums", "bateria", "batería"],
        }

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        stems = {}
        originals = {}
        try:
            def file_sort_key(f):
                fname = _strip_accents(f.lower())
                if any(x in fname for x in self.stem_filters["click_patterns"]):
                    return 0
                if any(x in fname for x in self.stem_filters["guide_patterns"]):
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

                is_click = any(x in fname for x in self.stem_filters["click_patterns"])
                if is_click:
                    with stems_lock:
                        if click_audio_data[0] is None:
                            click_audio_data[0] = audio

                muted = is_click or any(x in fname for x in self.stem_filters["guide_patterns"])
                fx_enabled = not any(x in fname for x in self.stem_filters["no_fx_patterns"])

                from app.utils.stem_classifier import get_stem_category
                if is_click:
                    category = "Ref"
                elif any(x in fname for x in self.stem_filters["guide_patterns"]):
                    category = "Ref"
                elif not fx_enabled:
                    category = "Drums"
                else:
                    category = get_stem_category(stem_name)

                with stems_lock:
                    stems[stem_name] = {
                        "audio": audio,
                        "sr": self.mix_sr,
                        "volume": 1.0,
                        "pan": 0.0,
                        "muted": muted,
                        "solo": False,
                        "category": category,
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

                if self.pre_click_offset_samples is not None:
                    click_offset_samples = self.pre_click_offset_samples
                elif click_audio is not None:
                    click_offset_samples = _probe_click_offset(
                        click_audio, self.mix_sr, start_bpm=bpm
                    )
                else:
                    click_offset_samples = 0
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
                if click_audio is not None:
                    tempo, _ = librosa.beat.beat_track(y=click_audio, sr=self.mix_sr)
                else:
                    tempo, _ = librosa.beat.beat_track(y=mix, sr=self.mix_sr)

                bpm = round(float(np.ravel(tempo)[0]))

                click_offset_samples = 0
                if click_audio is not None:
                    click_offset_samples = _probe_click_offset(
                        click_audio, self.mix_sr, start_bpm=bpm
                    )

            if self._is_cancelled:
                return

            self.progress.emit("Listo.")
            self.progress_pct.emit(100)

            order = list(stems.keys())
            self.finished_loading.emit(stems, key, bpm, click_offset_samples, order)
        except Exception as e:
            self.error.emit(str(e))
