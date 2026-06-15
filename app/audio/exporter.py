import os
import zipfile
import tempfile
import numpy as np
import soundfile as sf
from PySide6.QtCore import QThread, Signal
from app.audio.fast_audio import fast_audio_load


class ExportThread(QThread):
    progress = Signal(str)
    progress_pct = Signal(int)
    finished_export = Signal(str)
    error = Signal(str)

    def __init__(self, export_type: str, dest_path: str, song_folder: str,
                 metadata: dict, mix_sr: int = 44100):
        super().__init__()
        self.export_type = export_type
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
                self._export_wav(apply_config=False)
            elif self.export_type == 'wav_cfg':
                self._export_wav(apply_config=True)
        except Exception as e:
            self.error.emit(str(e))

    def _get_stems(self):
        stems = []
        for f in os.listdir(self.song_folder):
            if f.lower().endswith(('.wav', '.mp3', '.m4a', '.flac')):
                stems.append(f)
        return sorted(stems)

    def _load_audio_for_stem(self, stem_name: str):
        """Carga audio de un stem desde cache .wav o desde archivo."""
        audio = None
        cache_dir = os.path.join(self.song_folder, "cache", "44100_mono")
        wav_path = os.path.join(cache_dir, f"{stem_name}.wav")
        if os.path.exists(wav_path):
            try:
                audio, _ = sf.read(wav_path)
                audio = audio.astype(np.float32)
            except Exception:
                pass
        if audio is None:
            file_path = os.path.join(self.song_folder, stem_name)
            audio, sr = fast_audio_load(file_path, target_sr=self.mix_sr)
        return audio

    def _export_zip_orig(self):
        stems = self._get_stems()
        total = len(stems)
        self.progress.emit("Creando archivo ZIP...")

        with zipfile.ZipFile(self.dest_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for i, stem in enumerate(stems, 1):
                if self._is_cancelled:
                    return
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
                if self._is_cancelled:
                    return
                self.progress.emit(f"Procesando y aplicando config a {stem} ({i}/{total})...")
                self.progress_pct.emit(int(((i - 0.5) / total) * 100))

                stem_name = os.path.splitext(stem)[0]
                audio = self._load_audio_for_stem(stem_name)
                stem_name = os.path.splitext(stem)[0]
                meta = stems_meta.get(stem_name, {})
                fx_on = meta.get("fx_enabled", True)

                if (pitch_shift != 0 or tempo_ratio != 1.0) and fx_on:
                    import pyrubberband as pyrb
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

    def _process_stem_audio(self, stem_name: str, meta: dict, pitch_shift: int,
                             tempo_ratio: int) -> np.ndarray:
        """Carga y procesa un stem individual aplicando config si corresponde."""
        audio = self._load_audio_for_stem(stem_name)
        fx_on = meta.get("fx_enabled", True)

        if (pitch_shift != 0 or tempo_ratio != 1.0) and fx_on:
            import pyrubberband as pyrb
            try:
                if pitch_shift != 0:
                    audio = pyrb.pitch_shift(audio, self.mix_sr, pitch_shift)
                if tempo_ratio != 1.0:
                    audio = pyrb.time_stretch(audio, self.mix_sr, tempo_ratio)
            except Exception:
                pass

        vol = meta.get("volume", 1.0)
        if meta.get("muted", False):
            vol = 0.0
        audio = audio * vol
        return audio

    def _mix_stems(self, stems: list, apply_config: bool) -> np.ndarray:
        """Mezcla stems en una sola pista. Si apply_config es True, aplica pitch/tempo/volumen."""
        pitch_shift = self.metadata.get("pitch_shift", 0) if apply_config else 0
        tempo_ratio = self.metadata.get("tempo_ratio", 1.0) if apply_config else 1.0
        stems_meta = {s["name"]: s for s in self.metadata.get("stems", [])} if apply_config else {}

        mixed = None
        total = len(stems)

        for i, stem in enumerate(stems, 1):
            if self._is_cancelled:
                return mixed

            stem_name = os.path.splitext(stem)[0]

            if apply_config:
                meta = stems_meta.get(stem_name, {})
                audio = self._process_stem_audio(stem_name, meta, pitch_shift, tempo_ratio)
                progress_msg = f"Procesando y mezclando {stem} ({i}/{total})..."
            else:
                audio = self._load_audio_for_stem(stem_name)
                progress_msg = f"Mezclando stem original {stem} ({i}/{total})..."

            self.progress.emit(progress_msg)

            if mixed is None:
                mixed = audio
            else:
                length = max(len(mixed), len(audio))
                new_mixed = np.zeros(length)
                new_mixed[:len(mixed)] += mixed
                new_mixed[:len(audio)] += audio
                mixed = new_mixed

            self.progress_pct.emit(int((i / total) * 100))

        return mixed

    def _export_wav(self, apply_config: bool):
        stems = self._get_stems()
        mixed = self._mix_stems(stems, apply_config)

        if mixed is not None:
            label = "con configuración" if apply_config else "original"
            self.progress.emit(f"Guardando pista {label}...")
            sf.write(self.dest_path, mixed, self.mix_sr)
            self.progress.emit("Listo.")
            self.progress_pct.emit(100)
            self.finished_export.emit(self.dest_path)
        else:
            self.error.emit("No se pudo mezclar la pista.")
