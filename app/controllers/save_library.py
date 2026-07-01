import os
import shutil
import numpy as np
import soundfile as sf
from PySide6.QtWidgets import QInputDialog, QMessageBox, QFileDialog
from app.data.metadata import build_metadata
from app.audio.exporter import ExportThread
from app.controllers.deck_sync import DeckStatusMixin


class SaveLibraryMixin(DeckStatusMixin):
    def _save_to_library(self):
        self.lib_mgr.library_path = self.config_mgr.get_library_path()
        if not self.state.stems:
            self.status_label.setText("No hay stems para guardar")
            return False
        lib_path = self.lib_mgr.library_path
        if not lib_path:
            self.status_label.setText("Primero configura la carpeta de librería")
            return False

        title, ok = QInputDialog.getText(self, "Guardar en librería", "Nombre de la canción:")
        if not ok or not title.strip():
            return False
        title = title.strip()

        if self.state.current_song_source == "folder" and self.state.current_song_name:
            source = self.state.current_song_name
            if os.path.isdir(source):
                song_folder = self.lib_mgr.copy_folder(source, title)
            else:
                song_folder = os.path.join(lib_path, title)
                os.makedirs(song_folder, exist_ok=True)
        else:
            song_folder = os.path.join(lib_path, title)
            os.makedirs(song_folder, exist_ok=True)

        for stem_name, stem_data in self.state.stems.items():
            if "audio" in stem_data and stem_data["audio"] is not None:
                stem_path = os.path.join(song_folder, f"{stem_name}.wav")
                sf.write(stem_path, stem_data["audio"], self.state.mix_sr)

        stems_list = [{"name": n, "category": d.get("category", "Other"),
                       "volume": d.get("volume", 1.0), "pan": d.get("pan", 0.0),
                       "muted": d.get("muted", False), "solo": d.get("solo", False),
                       "fx_enabled": d.get("fx_enabled", True)}
                      for n, d in self.state.stems.items()]
        metadata = build_metadata(
            name=title, artist=self.state.current_song_artist,
            detected_key=self.state.detected_key,
            detected_bpm=self.state.detected_bpm,
            pitch_shift=self.state.current_pitch_shift,
            tempo_ratio=self.state.current_tempo_ratio,
            count_in_bars=self.state.count_in_bars,
            click_during_playback=self.state.click_during_playback,
            metronome_volume=self.state.metronome_volume,
            metronome_pan=self.state.metronome_pan,
            master_volume=self.state.master_volume,
            duration=self._compute_duration(),
            click_offset_samples=self.state.click_offset_samples,
            stems=stems_list,
        )

        old_meta = self.lib_mgr.get_metadata(title)
        if old_meta and "cached_audio_path" in old_meta:
            metadata["cached_audio_path"] = old_meta["cached_audio_path"]

        self.lib_mgr.save_metadata(title, metadata)
        self.state.current_song_name = title
        self.state.current_song_source = "library"
        self.state.has_unsaved_changes = False
        self.state.saved_history_idx = self.state.history_idx
        self._update_save_buttons()
        self.library_widget.refresh_ui()
        self.status_label.setText(f"Guardado: {title}")
        self._sync_deck_status(f"Guardado: {title}")

        if self.setlist_widget.current_setlist_index >= 0:
            self.setlist_widget.add_song_to_current(title)

        return True

    def _save_changes(self):
        self.lib_mgr.library_path = self.config_mgr.get_library_path()
        if self.state.current_song_source != "library" or not self.state.current_song_name:
            return
        stems_list = [{"name": n, "category": d.get("category", "Other"),
                       "volume": d.get("volume", 1.0), "pan": d.get("pan", 0.0),
                       "muted": d.get("muted", False), "solo": d.get("solo", False),
                       "fx_enabled": d.get("fx_enabled", True)}
                      for n, d in self.state.stems.items()]
        metadata = build_metadata(
            name=self.state.current_song_name,
            artist=self.state.current_song_artist,
            detected_key=self.state.detected_key,
            detected_bpm=self.state.detected_bpm,
            pitch_shift=self.state.current_pitch_shift,
            tempo_ratio=self.state.current_tempo_ratio,
            count_in_bars=self.state.count_in_bars,
            click_during_playback=self.state.click_during_playback,
            metronome_volume=self.state.metronome_volume,
            metronome_pan=self.state.metronome_pan,
            master_volume=self.state.master_volume,
            duration=self._compute_duration(),
            click_offset_samples=self.state.click_offset_samples,
            stems=stems_list,
        )
        self.lib_mgr.save_metadata(self.state.current_song_name, metadata)
        self.state.has_unsaved_changes = False
        self.state.saved_history_idx = self.state.history_idx
        self._update_save_buttons()
        self.library_widget.refresh_ui()
        self.status_label.setText("Cambios guardados.")
        self._sync_deck_status("Cambios guardados.")

    def _save_as(self):
        self.lib_mgr.library_path = self.config_mgr.get_library_path()
        if self.state.current_song_source != "library" or not self.state.current_song_name:
            return
        new_name, ok = QInputDialog.getText(self, "Guardar Como", "Nuevo nombre:", text=self.state.current_song_name)
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()

        src_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
        dst_folder = os.path.join(self.lib_mgr.library_path, new_name)
        if os.path.exists(dst_folder):
            QMessageBox.warning(self, "Error", "Ya existe una canción con ese nombre.")
            return

        shutil.copytree(src_folder, dst_folder)
        stems_list = [{"name": n, "category": d.get("category", "Other"),
                       "volume": d.get("volume", 1.0), "pan": d.get("pan", 0.0),
                       "muted": d.get("muted", False), "solo": d.get("solo", False),
                       "fx_enabled": d.get("fx_enabled", True)}
                      for n, d in self.state.stems.items()]
        metadata = build_metadata(
            name=new_name, artist=self.state.current_song_artist,
            detected_key=self.state.detected_key,
            detected_bpm=self.state.detected_bpm,
            pitch_shift=self.state.current_pitch_shift,
            tempo_ratio=self.state.current_tempo_ratio,
            count_in_bars=self.state.count_in_bars,
            click_during_playback=self.state.click_during_playback,
            metronome_volume=self.state.metronome_volume,
            metronome_pan=self.state.metronome_pan,
            master_volume=self.state.master_volume,
            duration=self._compute_duration(),
            click_offset_samples=self.state.click_offset_samples,
            stems=stems_list,
        )
        self.lib_mgr.save_metadata(new_name, metadata)
        self.state.current_song_name = new_name
        self.state.has_unsaved_changes = False
        self.state.saved_history_idx = self.state.history_idx
        self.song_name_label.setText(f"Canción: {new_name}")
        self._update_save_buttons()
        self.library_widget.refresh_ui()
        self.status_label.setText(f"Guardado como: {new_name}")
        self._sync_deck_status(f"Guardado como: {new_name}")

    def _on_song_export_requested(self, song_name: str, export_type: str):
        if self.threads.export_thread and self.threads.export_thread.isRunning():
            QMessageBox.warning(self, "Exportación en curso", "Ya hay una exportación en curso. Por favor espera.")
            return

        song_folder = os.path.join(self.lib_mgr.library_path, song_name)
        if not os.path.isdir(song_folder):
            return

        meta = self.lib_mgr.get_metadata(song_name) or {}

        ext = ".wav" if export_type.startswith("wav") else ".zip"
        default_name = song_name
        if export_type.endswith("_cfg"):
            pitch = meta.get("pitch_shift", 0)
            tempo = meta.get("tempo_ratio", 1.0)
            if pitch != 0 or tempo != 1.0:
                default_name += f"_P{pitch}_T{int(tempo*100)}"
        default_path = os.path.join(os.path.expanduser("~"), "Desktop", default_name + ext)

        dest_path, _ = QFileDialog.getSaveFileName(self, "Guardar exportación", default_path,
                                                        f"Audio Files (*{ext})")
        if not dest_path:
            return

        new_thread = ExportThread(export_type, dest_path, song_folder, meta, self.state.mix_sr)
        new_thread.progress.connect(self._on_export_progress)
        new_thread.progress_pct.connect(self._on_export_progress_pct)
        new_thread.finished_export.connect(self._on_export_finished)
        new_thread.error.connect(self._on_export_error)
        self.progress_bar.setVisible(True)
        self._sync_deck_progress(0, True)
        self.progress_bar.setValue(0)
        self.threads.safe_replace('export_thread', new_thread)
        self.threads.safe_start(self.threads.export_thread)

    def _on_export_progress(self, msg: str):
        self.status_label.setText(msg)
        self._sync_deck_status(msg)

    def _on_export_finished(self, path: str):
        sender = self.sender()
        if sender is not None and sender is not self.threads.export_thread:
            return

        self.status_label.setText(f"Exportado: {os.path.basename(path)}")
        self._sync_deck_status(f"Exportado: {os.path.basename(path)}")
        self.progress_bar.setVisible(False)
        self._sync_deck_progress(0, False)
        self.threads.export_thread = None
        QMessageBox.information(self, "Exportación", f"Archivo guardado en:\n{path}")

    def _on_export_error(self, msg: str):
        sender = self.sender()
        if sender is not None and sender is not self.threads.export_thread:
            return
        self.status_label.setText(f"Error de exportación: {msg}")
        self._sync_deck_status(f"Error de exportación: {msg}")
        self.progress_bar.setVisible(False)
        self._sync_deck_progress(0, False)
        self.threads.export_thread = None

    def _on_export_progress_pct(self, pct: int):
        self.progress_bar.setValue(pct)
        self._sync_deck_progress(pct, True)
        QMessageBox.information(self, "Exportación", f"Archivo guardado en:\n{path}")

    def _on_export_error(self, msg: str):
        self.status_label.setText(f"Error de exportación: {msg}")
        self.progress_bar.setVisible(False)
        self.threads.export_thread = None

    def _compute_duration(self) -> str:
        max_len = 0
        for stem_data in self.state.stems.values():
            if "audio" in stem_data and stem_data["audio"] is not None:
                max_len = max(max_len, len(stem_data["audio"]))
        total_secs = max_len / self.state.mix_sr if max_len > 0 else 0
        mins = int(total_secs // 60)
        secs = int(total_secs % 60)
        return f"{mins:02d}:{secs:02d}"
