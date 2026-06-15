"""Motor de audio para Stem Player."""

import os
import numpy as np
import librosa
import pyrubberband as pyrb
import soundfile as sf
import sounddevice as sd
from PySide6.QtCore import QThread, Signal
import threading 
from concurrent.futures import ThreadPoolExecutor

def fast_audio_load(file_path: str, target_sr: int = 44100):
    """Carga de audio optimizada usando soundfile nativo antes de librosa."""
    try:
        import soundfile as sf
        data, sr = sf.read(file_path)
        if len(data.shape) > 1:
            data = np.mean(data, axis=1) # Mezcla a mono
        if sr != target_sr:
            import librosa
            data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
        return data, target_sr
    except Exception as e:
        import librosa
        data, sr = librosa.load(file_path, sr=target_sr, mono=True)
        return data, sr

class StemLoaderThread(QThread):
    """Hilo para cargar stems y analizar key/BPM sin bloquear la GUI."""

    progress = Signal(str)          # Mensaje de progreso
    progress_pct = Signal(int)    # Porcentaje 0-100
    finished_loading = Signal(dict, str, int, int, list)  # stems, key, bpm, click_offset_samples, order
    error = Signal(str)
    def __init__(self, folder_path: str, mix_sr: int = 44100, pre_key: str = None, pre_bpm: int = None, cache_folder: str = None):
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
                fname = f.lower()
                if any(x in fname for x in ["click", "metro"]): return 0
                if any(x in fname for x in ["guide", "cue", "guia"]): return 1
                return 2

            files = [
                f for f in os.listdir(self.folder_path)
                if f.lower().endswith((".wav", ".mp3", ".m4a", ".flac"))
            ]
            files.sort(key=file_sort_key)
            
            total = len(files)
            
            # Pre-crear diccionario de stems de forma concurrente
            stems_lock = threading.Lock()
            click_audio_data = [None]  # Usamos lista mutable para modificar desde el thread
            
            mono_cache_dir = None
            if self.cache_folder:
                mono_cache_dir = os.path.join(self.cache_folder, "44100_mono")
                os.makedirs(mono_cache_dir, exist_ok=True)
                
            completed = [0]
                
            def process_file(file):
                if self._is_cancelled:
                    return
                
                stem_name = os.path.splitext(file)[0]
                fname = file.lower()
                file_path = os.path.join(self.folder_path, file)
                
                audio = None
                original_audio = None
                
                # 1. Intentar cargar original desde caché .npy
                npy_path = os.path.join(mono_cache_dir, f"{stem_name}.npy") if mono_cache_dir else None
                if npy_path and os.path.exists(npy_path):
                    try:
                        audio = np.load(npy_path)
                    except Exception as e:
                        print(f"Error loading npy cache {npy_path}: {e}")
                        
                if audio is None:
                    # Si no hay caché o falló, usar carga rápida
                    audio, sr = fast_audio_load(file_path, target_sr=self.mix_sr)
                    # Guardar en caché para futuras cargas
                    if npy_path:
                        try:
                            np.save(npy_path, audio)
                        except Exception as e:
                            print(f"Error saving npy cache {npy_path}: {e}")
                            
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
                from utils import KEY_MAP
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


class PitchTempoThread(QThread):
    """Hilo para aplicar pitch shift y time stretch sin bloquear la GUI."""

    progress = Signal(str)
    progress_pct = Signal(int)    # Porcentaje 0-100
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
            updated = {}
            total = len(self.originals)
            for i, (name, original) in enumerate(self.originals.items(), 1):
                if self._is_cancelled:
                    return
                self.progress.emit(f"Procesando {name} ({i}/{total}) ...")
                self.progress_pct.emit(int((i / total) * 100))
                audio = original
                # Aplicar pitch solo si FX está activado para este stem
                fx_on = self.fx_map.get(name, True)
                if self.pitch_shift != 0 and fx_on:
                    try:
                        audio = pyrb.pitch_shift(audio, self.mix_sr, self.pitch_shift)
                    except Exception as e:
                        print(f"Error applying pitch shift to {name}: {e}")
                        audio = original  # Use original if processing fails
                if self.tempo_ratio != 1.0:
                    try:
                        audio = pyrb.time_stretch(audio, self.mix_sr, self.tempo_ratio)
                    except Exception as e:
                        print(f"Error applying time stretch to {name}: {e}")
                        # Keep audio as is if time stretch fails
                updated[name] = audio
            self.progress.emit("Procesamiento completado.")
            self.progress_pct.emit(100)
            self.finished_processing.emit(updated)
        except Exception as e:
            self.error.emit(str(e))


class PlaybackThread(QThread):
    """Hilo para reproducir audio en tiempo real."""

    update_progress = Signal(float)
    peak_level = Signal(float)

    def __init__(self, stems: dict, bpm: int, mix_sr: int = 44100,
                 count_in_bars: int = 0, click_during_playback: bool = False,
                 master_volume: float = 1.0, metronome_volume: float = 0.5,
                 metronome_pan: float = 0.0, click_offset_samples: int = 0):
        super().__init__()
        self.stems = stems
        self.bpm = bpm
        self.mix_sr = mix_sr
        self.count_in_bars = count_in_bars
        self.click_during_playback = click_during_playback
        self.master_volume = master_volume
        self.metronome_volume = metronome_volume
        self.metronome_pan = metronome_pan
        self.click_offset_samples = click_offset_samples
        self.is_playing = False
        self._stop = False
        self._seek_pos = None
        self._seek_lock = threading.Lock()
        self.current_pos = 0

    def seek(self, new_pos_samples: int):
        """Solicita saltar a una posición absoluta en muestras."""
        with self._seek_lock:
            self._seek_pos = max(0, new_pos_samples)

    def set_master_volume(self, vol: float):
        self.master_volume = vol

    def set_metronome_volume(self, vol: float):
        self.metronome_volume = vol

    def set_metronome_pan(self, pan: float):
        self.metronome_pan = pan

    def _is_beat(self, pos: int, beat_sample: int, click_samples: int) -> bool:
        """Determina si en la posición actual debe sonar el click."""
        shifted_pos = pos - self.click_offset_samples
        return shifted_pos % beat_sample < click_samples

    def _generate_click(self, click_samples, sr):
        t = np.arange(click_samples) / sr
        # Frecuencia más baja y menos armónicos para evitar el sonido metálico
        freq = 440  
        
        # Envolvente más rápida (más "click" y menos "tono")
        envelope = np.exp(-t * 80) 
        
        # Onda senoidal simple sin armónicos complejos
        wave = np.sin(2 * np.pi * freq * t)
        
        click = wave * envelope
        
        # Filtrado paso bajo suave para quitar asperezas (suavizado)
        click = np.convolve(click, np.ones(15)/15, mode='same')
        
        # Normalizar y atenuar
        click = click / np.max(np.abs(click)) * 0.4
        return click

    def run(self):
        if not self.stems:
            return
            
        max_len = max(len(s["audio"]) for s in self.stems.values())
        beats_per_bar = 4
        count_in_beats = self.count_in_bars * beats_per_bar
        count_in_samples = int(count_in_beats * self.mix_sr * 60 / self.bpm) if count_in_beats > 0 else 0
        
        # 1. Pre-generar el buffer de click completo
        total_samples = max_len + count_in_samples
        click_track = np.zeros(total_samples)
        beat_sample = int(self.mix_sr * 60 / self.bpm)
        
        click_duration = 0.13
        click_samples = int(click_duration * self.mix_sr)
        click_base = self._generate_click(click_samples, self.mix_sr)
        
        for i in range(0, total_samples, beat_sample):
            end_idx = min(i + click_samples, total_samples)
            segment_len = end_idx - i
            click_track[i:end_idx] = click_base[:segment_len]
            
        blocksize = 1024
        pos = 0
        self.is_playing = True

        with sd.OutputStream(samplerate=self.mix_sr, channels=2, blocksize=blocksize) as stream:
            while self.is_playing and not self._stop and pos < total_samples:
				# --- Comprobar si hay una búsqueda pendiente ---
                with self._seek_lock:
                    if self._seek_pos is not None:
                        pos = self._seek_pos
                        self._seek_pos = None
                        
                self.current_pos = pos

                out = np.zeros((blocksize, 2))
                end = min(pos + blocksize, total_samples)

                # 2. Mezclar el click (si estamos en count-in o click activado)
                if self.click_during_playback or pos < count_in_samples:
                    segment = click_track[pos:end]
                    
                    pan = self.metronome_pan
                    pan_l = 1.0 - pan if pan >= 0 else 1.0
                    pan_r = 1.0 if pan >= 0 else 1.0 + pan
                    
                    out[:len(segment), 0] += segment * self.metronome_volume * pan_l
                    out[:len(segment), 1] += segment * self.metronome_volume * pan_r
                
                # 3. Mezclar los stems
                if end > count_in_samples:
                    start_stem = max(0, pos - count_in_samples)
                    end_stem = min(start_stem + blocksize, max_len)
                    
                    any_solo = any(s["solo"] for s in self.stems.values())
                    
                    for s in self.stems.values():
                        if s["muted"] or (any_solo and not s["solo"]):
                            continue
                            
                        audio = s["audio"]
                        if start_stem < len(audio):
                            seg_end = min(end_stem, len(audio))
                            segment = audio[start_stem:seg_end] * s["volume"]
                            
                            pan = s.get("pan", 0.0)
                            pan_l = 1.0 - pan if pan >= 0 else 1.0
                            pan_r = 1.0 if pan >= 0 else 1.0 + pan
                            
                            out[:len(segment), 0] += segment * pan_l * self.master_volume
                            out[:len(segment), 1] += segment * pan_r * self.master_volume
                
                stream.write(out.astype(np.float32))
                
                peak = np.max(np.abs(out))
                self.peak_level.emit(float(peak))
                
                pos += blocksize
                self.update_progress.emit(min(1.0, pos / total_samples))
                
        self.is_playing = False

    def stop(self):
        self._stop = True
        self.is_playing = False
