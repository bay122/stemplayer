from os import name
import os
import numpy as np
from PySide6.QtWidgets import QFileDialog, QInputDialog
from PySide6.QtCore import QTimer
from app.audio.stem_loader import StemLoaderThread
from app.controllers.deck_sync import DeckStatusMixin


class SongLoadingMixin(DeckStatusMixin):
    def _load_stems(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar carpeta de stems")
        if not folder:
            return
        self._load_folder_internal(folder, folder, "folder")

    def _on_song_load_requested(self, song_folder: str, song_name: str, metadata: dict):
        self._load_folder_internal(song_folder, song_name, "library", metadata)

    def _on_library_song_renamed(self, old_name: str, new_name: str):
        if self.state.current_song_name == old_name:
            self.state.current_song_name = new_name
            self.song_name_label.setText(f"Canción: {new_name}")
        self.library_widget.refresh_ui()

    def _on_library_song_deleted(self, song_name: str):
        if self.state.current_song_name == song_name and self.state.current_song_source == "library":
            self._close_song()

    def _load_folder_internal(self, folder: str, song_name: str, source: str, metadata: dict = None):
        if not self._close_song():
            return

        if hasattr(self, 'preloaded_song_cache') and self.preloaded_song_cache and self.preloaded_song_cache["name"] == song_name:
            self.status_label.setText("Cargando desde caché...")
            self._sync_deck_status("Cargando desde caché...")
            cache = self.preloaded_song_cache
            self._on_loader_finished(cache["stems"], cache["key"], cache["bpm"], metadata, cache["click_offset_samples"], cache["order"])
            self.preloaded_song_cache = None
            return

        self.status_label.setText("Cargando stems...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self._sync_deck_status("Cargando stems...")
        self._sync_deck_progress(0, True)
        self.state.current_song_name = song_name
        self.state.current_song_source = source
        self.save_lib_btn.setVisible(source == "folder")

        new_thread = StemLoaderThread(
            folder, self.state.mix_sr,
            pre_key=metadata.get("detected_key") if metadata else None,
            pre_bpm=metadata.get("detected_bpm") if metadata else None,
            cache_folder=folder if source == "library" else None,
            stem_filters=self.config_mgr.get_stem_filters()
        )
        new_thread.progress.connect(self._on_loader_progress)
        new_thread.progress_pct.connect(self._on_loader_progress_pct)
        new_thread.finished_loading.connect(
            lambda stems, key, bpm, offset, order: self._on_loader_finished(stems, key, bpm, metadata, offset, order)
        )
        new_thread.error.connect(self._on_loader_error)
        self.threads.safe_replace('loader_thread', new_thread)
        self.threads.safe_start(self.threads.loader_thread)

    def _on_loader_progress(self, msg: str):
        self.status_label.setText(msg)
        self._sync_deck_status(msg)

    def _on_loader_progress_pct(self, pct: int):
        self.progress_bar.setValue(pct)
        self._sync_deck_progress(pct, True)

    def _on_loader_error(self, msg: str):
        self.status_label.setText(f"Error: {msg}")
        self.progress_bar.setVisible(False)
        self._sync_deck_status(f"Error: {msg}")
        self._sync_deck_progress(0, False)

    def _on_loader_finished(self, stems, key, bpm, metadata=None, offset=0, order=None):
        sender = self.sender()
        if sender is not None and sender is not self.threads.loader_thread:
            return

        if metadata is None:
            metadata = {}
        self.state.click_offset_samples = offset
        if order:
            self.state.stems = {k: stems[k] for k in order}
        else:
            self.state.stems = stems
        self.state.stem_order = list(self.state.stems.keys())
        self.state.originals = {k: v["audio"].copy() for k, v in self.state.stems.items()}
        self.state.detected_key = key
        self.state.detected_bpm = bpm if bpm > 0 else 120
        self.state.current_pitch_shift = metadata.get("pitch_shift", 0)
        self.state.current_tempo_ratio = metadata.get("tempo_ratio", 1.0)
        self.state.count_in_bars = metadata.get("count_in_bars", 0)
        self.state.click_during_playback = metadata.get("click_during_playback", False)
        self.state.metronome_volume = metadata.get("metronome_volume", 0.5)
        self.state.metronome_pan = metadata.get("metronome_pan", 0.0)
        self.state.master_volume = metadata.get("master_volume", 1.0)
        self.state.detected_key = metadata.get("detected_key") or key
        self.state.detected_bpm = meta_bpm if (meta_bpm := metadata.get("detected_bpm")) and meta_bpm > 0 else self.state.detected_bpm
        if self.state.current_song_source == "library":
            self.lib_mgr.library_path = self.config_mgr.get_library_path()
            if (metadata
                and (m_bpm := metadata.get("detected_bpm")) is not None
                and m_bpm <= 0):
                metadata["detected_bpm"] = self.state.detected_bpm
                self.lib_mgr.save_metadata(self.state.current_song_name, metadata)
        self.state.current_song_artist = metadata.get("artist", "")

        if metadata.get("stems") and metadata.get("detected_key"):
            for stem_meta in metadata.get("stems", []):
                name = stem_meta.get("name")
                if name in self.state.stems:
                    self.state.stems[name]["category"] = stem_meta.get("category", "Other")
                    self.state.stems[name]["volume"] = stem_meta.get("volume", 1.0)
                    self.state.stems[name]["pan"] = stem_meta.get("pan", 0.0)
                    self.state.stems[name]["muted"] = stem_meta.get("muted", False)
                    self.state.stems[name]["solo"] = stem_meta.get("solo", False)
                    self.state.stems[name]["fx_enabled"] = stem_meta.get("fx_enabled", True)
            meta_order = [s["name"] for s in metadata["stems"] if s["name"] in self.state.stems]
            if meta_order:
                extra = [k for k in self.state.stems if k not in meta_order]
                self.state.stems = {k: self.state.stems[k] for k in meta_order + extra}

        self.song_name_label.setText(f"Canción: {self.state.current_song_name}")
        self.artist_input.blockSignals(True)
        self.artist_input.setText(self.state.current_song_artist)
        self.artist_input.blockSignals(False)

        if getattr(self, 'deck_layout', None) is not None:
            try:
                self.deck_layout.update_song_header(
                    self.state.current_song_name,
                    self.state.current_song_artist
                )
                self.deck_layout.update_visibility(
                    self.state.current_song_source,
                    bool(self.state.current_song_name)
                )
                self.deck_layout.update_save_buttons()
                self.deck_layout.rebuild_stems()
            except Exception:
                pass

        self.key_label.setText(f"Key: {self.state.detected_key}")
        self.bpm_label.setText(f"BPM: {self.state.detected_bpm}")
        self.orig_bpm_label.setText(str(self.state.detected_bpm))
        self.bpm_spin.blockSignals(True)
        self.bpm_spin.setValue(int(self.state.detected_bpm * self.state.current_tempo_ratio))
        self.bpm_spin.blockSignals(False)
        self.tempo_ratio_label.setText(f"{self.state.current_tempo_ratio*100:.1f}%")
        self.count_in_combo.blockSignals(True)
        self.count_in_combo.setCurrentIndex(self.state.count_in_bars)
        self.count_in_combo.blockSignals(False)
        self.click_check.blockSignals(True)
        self.click_check.setChecked(self.state.click_during_playback)
        self.click_check.blockSignals(False)
        self.master_volume_slider.blockSignals(True)
        self.master_volume_slider.setValue(self.state.master_volume)
        self.master_volume_slider.blockSignals(False)
        self.metronome_volume_slider.blockSignals(True)
        self.metronome_volume_slider.setValue(self.state.metronome_volume)
        self.metronome_volume_slider.blockSignals(False)
        self.metronome_pan_slider.blockSignals(True)
        self.metronome_pan_slider.setValue(self.state.metronome_pan)
        self.metronome_pan_slider.blockSignals(False)

        show_controls = self.state.click_during_playback
        self.metronome_volume_slider.setVisible(show_controls)
        self.metronome_pan_slider.setVisible(show_controls)
        self.metro_icon_btn.setEnabled(show_controls)

        for s, btn in self.pitch_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(s == self.state.current_pitch_shift)
            btn.blockSignals(False)
        self._update_pitch_button_labels()

        self._rebuild_stems_ui()
        self.status_label.setText("Listo")
        self.progress_bar.setVisible(False)
        self.bg_status_label.setVisible(False)
        self._sync_deck_status("Listo")
        self._sync_deck_progress(0, False)
        self._sync_deck_bg_status("", False)
        self.close_song_btn.setVisible(True)
        self.chordpro_preview_widget.setVisible(False)
        self.threads.loader_thread = None

        self.state.history.clear()
        self.state.history_idx = -1
        self._push_state_if_needed()
        self.state.saved_history_idx = self.state.history_idx
        self._update_undo_redo_btns()
        self._update_list_icons()

        self.state.has_unsaved_changes = False
        self._update_save_buttons()

        if self.state.current_song_source == "library":
            self.lib_mgr.library_path = self.config_mgr.get_library_path()
            meta = self.lib_mgr.get_metadata(self.state.current_song_name)
            if meta:
                meta["detected_key"] = key
                meta["detected_bpm"] = bpm if bpm > 0 else 120
                meta["click_offset_samples"] = offset
                max_len = max(len(s["audio"]) for s in stems.values()) if stems else 0
                total_secs = max_len / self.state.mix_sr if max_len > 0 else 0
                meta["duration"] = f"{int(total_secs // 60):02d}:{int(total_secs % 60):02d}"
                meta["stems"] = [
                    {"name": n, "category": d.get("category", "Other"),
                     "volume": d.get("volume", 1.0), "pan": d.get("pan", 0.0),
                     "muted": d.get("muted", False), "solo": d.get("solo", False),
                     "fx_enabled": d.get("fx_enabled", True)}
                    for n, d in self.state.stems.items()
                ]
                self.lib_mgr.save_metadata(self.state.current_song_name, meta)

        if self.state.current_song_source == "library":
            self.library_widget.refresh_ui()

        if metadata and (self.state.current_pitch_shift != 0 or self.state.current_tempo_ratio != 1.0):
            self._apply_pitch_tempo()

        if self.state.current_song_source == "library":
            folder_path = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
            chopro_path = os.path.join(folder_path, f"{self.state.current_song_name}.chopro")
            sync_path = os.path.join(folder_path, f"{self.state.current_song_name}.sync.json")

            if not os.path.exists(sync_path) and os.path.exists(chopro_path) and metadata:
                meta_sections = metadata.get("sections", [])
                if meta_sections:
                    from app.services import create_sync_file
                    create_sync_file(meta_sections, sync_path)

            if os.path.exists(chopro_path) or os.path.exists(sync_path):
                self.live_display_widget.load_sync_data(chopro_path, sync_path)
                self.live_display_widget.set_song_info(self.state.current_song_name, self.state.current_song_artist)
                self.toggle_live_btn.setVisible(True)
                self.toggle_live_btn.setEnabled(True)
                self._edit_chordpro_action.setVisible(os.path.exists(chopro_path))
            else:
                self.live_display_widget.reset()
                self.toggle_live_btn.setVisible(False)
                self.toggle_live_btn.setEnabled(False)
                self.toggle_live_btn.setChecked(False)
                self._edit_chordpro_action.setVisible(False)
                self.center_stack.setCurrentIndex(0)
            self._load_chordpro_preview()
        else:
            self.live_display_widget.reset()
            self.toggle_live_btn.setVisible(False)
            self.toggle_live_btn.setEnabled(False)
            self.toggle_live_btn.setChecked(False)
            self._edit_chordpro_action.setVisible(False)
            self.center_stack.setCurrentIndex(0)
            self.chordpro_preview_widget.setVisible(False)

        self._preload_next_setlist_song()

        if getattr(self, '_auto_play_pending', False):
            self._auto_play_pending = False
            QTimer.singleShot(100, self._start_playback)

    def _preload_next_setlist_song(self):
        self.threads.safe_replace('preloader_thread', None)
        self.bg_status_label.setVisible(False)
        self._sync_deck_bg_status("", False)
        self.preloaded_song_cache = None

        if self.setlist_widget.current_setlist_index < 0:
            return

        setlists = self.config_mgr.get_setlists()
        sl = setlists[self.setlist_widget.current_setlist_index]
        songs = sl["song_ids"]

        current_idx = self.setlist_widget.current_setlist_song_index
        if current_idx < 0 or current_idx >= len(songs):
            return

        next_idx = current_idx + 1
        if next_idx >= len(songs):
            return

        next_name = songs[next_idx]
        lib_path = self.lib_mgr.library_path
        song_folder = os.path.join(lib_path, next_name)
        if not os.path.isdir(song_folder):
            return

        self._preloaded_song_name = next_name
        meta = self.lib_mgr.get_metadata(next_name)
        new_thread = StemLoaderThread(
            song_folder, self.state.mix_sr,
            pre_key=meta.get("detected_key") if meta else None,
            pre_bpm=meta.get("detected_bpm") if meta else None,
            cache_folder=song_folder,
            stem_filters=self.config_mgr.get_stem_filters()
        )
        new_thread.progress.connect(self._on_preload_progress)
        new_thread.finished_loading.connect(self._on_preload_finished)
        self.threads.safe_replace('preloader_thread', new_thread)
        self.threads.safe_start(self.threads.preloader_thread)

    def _on_preload_progress(self, msg: str):
        self.bg_status_label.setText(f"Pre-cargando: {msg}")
        self.bg_status_label.setVisible(True)
        self._sync_deck_bg_status(f"Pre-cargando: {msg}", True)

    def _on_preload_finished(self, stems, key, bpm, offset, order):
        sender = self.sender()
        if sender is not None and sender is not self.threads.preloader_thread:
            return
        # Only accept preload if no newer preloader has been started
        if self.threads.preloader_thread is None:
            return

        preloaded_name = getattr(self, '_preloaded_song_name', '')
        self.preloaded_song_cache = {
            "name": preloaded_name,
            "stems": stems,
            "key": key,
            "bpm": bpm,
            "click_offset_samples": offset,
            "order": order,
        }
        self.bg_status_label.setVisible(False)
        self._sync_deck_bg_status("", False)
        self.threads.preloader_thread = None
