import os
import zipfile
import tempfile
import shutil
import numpy as np
import librosa
import pyrubberband as pyrb
import soundfile as sf
from PySide6.QtCore import QThread, Signal
from audio_engine import fast_audio_load

class ExportThread(QThread):
    progress = Signal(str)
    progress_pct = Signal(int)
    finished_export = Signal(str)
    error = Signal(str)

    def __init__(self, export_type: str, dest_path: str, song_folder: str, metadata: dict, mix_sr: int = 44100):
        super().__init__()
        self.export_type = export_type # 'zip_orig', 'zip_cfg', 'wav_orig', 'wav_cfg'
        self.dest_path = dest_path
        self.song_folder = song_folder
        self.metadata = metadata
        self.mix_sr = mix_sr
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            if self.export_type == 'zip_orig':
                self._export_zip_orig()
            elif self.export_type == 'zip_cfg':
                self._export_zip_cfg()
            elif self.export_type == 'wav_orig':
                self._export_wav_orig()
            elif self.export_type == 'wav_cfg':
                self._export_wav_cfg()
        except Exception as e:
            self.error.emit(str(e))

    def _get_stems(self):
        stems = []
        for f in os.listdir(self.song_folder):
            if f.lower().endswith(('.wav', '.mp3', '.m4a', '.flac')):
                stems.append(f)
        return sorted(stems)

    def _export_zip_orig(self):
        stems = self._get_stems()
        total = len(stems)
        self.progress.emit("Creando archivo ZIP...")
        
        with zipfile.ZipFile(self.dest_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for i, stem in enumerate(stems, 1):
                if self._is_cancelled: return
                self.progress.emit(f"Añadiendo {stem} al ZIP ({i}/{total})...")
                self.progress_pct.emit(int((i / total) * 100))
                file_path = os.path.join(self.song_folder, stem)
                zipf.write(file_path, arcname=stem)
                
        self.progress.emit("Listo.")
        self.progress_pct.emit(100)
        self.finished_export.emit(self.dest_path)

    def _export_zip_cfg(self):
        stems = self._get_stems()
        total = len(stems)
        pitch_shift = self.metadata.get("pitch_shift", 0)
        tempo_ratio = self.metadata.get("tempo_ratio", 1.0)
        stems_meta = {s["name"]: s for s in self.metadata.get("stems", [])}
        
        with tempfile.TemporaryDirectory() as tmpdir:
            for i, stem in enumerate(stems, 1):
                if self._is_cancelled: return
                self.progress.emit(f"Procesando y aplicando config a {stem} ({i}/{total})...")
                self.progress_pct.emit(int(((i - 0.5) / total) * 100))
                
                stem_name = os.path.splitext(stem)[0]
                
                audio = None
                cache_dir = os.path.join(self.song_folder, "cache", "44100_mono")
                npy_path = os.path.join(cache_dir, f"{stem_name}.npy")
                if os.path.exists(npy_path):
                    try:
                        audio = np.load(npy_path)
                    except:
                        pass
                        
                if audio is None:
                    file_path = os.path.join(self.song_folder, stem)
                    audio, sr = fast_audio_load(file_path, target_sr=self.mix_sr)
                
                stem_name = os.path.splitext(stem)[0]
                meta = stems_meta.get(stem_name, {})
                fx_on = meta.get("fx_enabled", True)
                
                if (pitch_shift != 0 or tempo_ratio != 1.0) and fx_on:
                    try:
                        if pitch_shift != 0:
                            audio = pyrb.pitch_shift(audio, self.mix_sr, pitch_shift)
                        if tempo_ratio != 1.0:
                            audio = pyrb.time_stretch(audio, self.mix_sr, tempo_ratio)
                    except Exception as e:
                        print(f"Error pyrubberband: {e}")
                        
                vol = meta.get("volume", 1.0)
                if meta.get("muted", False):
                    vol = 0.0
                audio = audio * vol
                
                tmp_file = os.path.join(tmpdir, stem)
                sf.write(tmp_file, audio, self.mix_sr)
                self.progress_pct.emit(int((i / total) * 100))
                
            self.progress.emit("Empaquetando en ZIP...")
            with zipfile.ZipFile(self.dest_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for stem in stems:
                    zipf.write(os.path.join(tmpdir, stem), arcname=stem)
                    
        self.progress.emit("Listo.")
        self.progress_pct.emit(100)
        self.finished_export.emit(self.dest_path)

    def _export_wav_orig(self):
        stems = self._get_stems()
        total = len(stems)
        mixed = None
        
        for i, stem in enumerate(stems, 1):
            if self._is_cancelled: return
            self.progress.emit(f"Mezclando stem original {stem} ({i}/{total})...")
            self.progress_pct.emit(int((i / total) * 100))
            
            stem_name = os.path.splitext(stem)[0]
            audio = None
            cache_dir = os.path.join(self.song_folder, "cache", "44100_mono")
            npy_path = os.path.join(cache_dir, f"{stem_name}.npy")
            if os.path.exists(npy_path):
                try:
                    audio = np.load(npy_path)
                except:
                    pass
            if audio is None:
                file_path = os.path.join(self.song_folder, stem)
                audio, sr = fast_audio_load(file_path, target_sr=self.mix_sr)
            
            if mixed is None:
                mixed = audio
            else:
                length = max(len(mixed), len(audio))
                new_mixed = np.zeros(length)
                new_mixed[:len(mixed)] += mixed
                new_mixed[:len(audio)] += audio
                mixed = new_mixed
                
        if mixed is not None:
            self.progress.emit("Guardando pista original...")
            sf.write(self.dest_path, mixed, self.mix_sr)
            self.progress.emit("Listo.")
            self.progress_pct.emit(100)
            self.finished_export.emit(self.dest_path)
        else:
            self.error.emit("No se pudo mezclar la pista.")

    def _export_wav_cfg(self):
        stems = self._get_stems()
        total = len(stems)
        mixed = None
        pitch_shift = self.metadata.get("pitch_shift", 0)
        tempo_ratio = self.metadata.get("tempo_ratio", 1.0)
        stems_meta = {s["name"]: s for s in self.metadata.get("stems", [])}
        
        for i, stem in enumerate(stems, 1):
            if self._is_cancelled: return
            self.progress.emit(f"Procesando y mezclando {stem} ({i}/{total})...")
            
            stem_name = os.path.splitext(stem)[0]
            audio = None
            cache_dir = os.path.join(self.song_folder, "cache", "44100_mono")
            npy_path = os.path.join(cache_dir, f"{stem_name}.npy")
            if os.path.exists(npy_path):
                try:
                    audio = np.load(npy_path)
                except:
                    pass
            if audio is None:
                file_path = os.path.join(self.song_folder, stem)
                audio, sr = fast_audio_load(file_path, target_sr=self.mix_sr)
            meta = stems_meta.get(stem_name, {})
            fx_on = meta.get("fx_enabled", True)
            
            if (pitch_shift != 0 or tempo_ratio != 1.0) and fx_on:
                try:
                    if pitch_shift != 0:
                        audio = pyrb.pitch_shift(audio, self.mix_sr, pitch_shift)
                    if tempo_ratio != 1.0:
                        audio = pyrb.time_stretch(audio, self.mix_sr, tempo_ratio)
                except Exception as e:
                    pass
                    
            vol = meta.get("volume", 1.0)
            if meta.get("muted", False):
                vol = 0.0
            audio = audio * vol
            
            if mixed is None:
                mixed = audio
            else:
                length = max(len(mixed), len(audio))
                new_mixed = np.zeros(length)
                new_mixed[:len(mixed)] += mixed
                new_mixed[:len(audio)] += audio
                mixed = new_mixed
                
            self.progress_pct.emit(int((i / total) * 100))
            
        if mixed is not None:
            self.progress.emit("Guardando pista con configuración...")
            sf.write(self.dest_path, mixed, self.mix_sr)
            self.progress.emit("Listo.")
            self.progress_pct.emit(100)
            self.finished_export.emit(self.dest_path)
        else:
            self.error.emit("No se pudo exportar la pista configurada.")
