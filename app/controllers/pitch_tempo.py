import os
import numpy as np
import soundfile as sf
from app.utils.constants import get_key_at_semitone_shift
from app.audio.pitch_tempo import PitchTempoThread


class PitchTempoMixin:
    def _on_apply_tempo_clicked(self):
        target_bpm = self.bpm_spin.value()
        self.state.current_tempo_ratio = target_bpm / self.state.detected_bpm if self.state.detected_bpm > 0 else 1.0
        self.tempo_ratio_label.setText(f"{self.state.current_tempo_ratio*100:.1f}%")
        if getattr(self, 'deck_layout', None) is not None:
            try:
                self.deck_layout.info_cards.update_info(self.state)
            except Exception:
                pass
        self._apply_pitch_tempo()

    def _on_pitch_clicked(self, shift: int):
        if self.state.current_pitch_shift == shift:
            return
        self.state.current_pitch_shift = shift
        for s, btn in self.pitch_buttons.items():
            btn.setChecked(s == shift)
        self._update_pitch_button_labels()
        self._apply_pitch_tempo()
        self._push_state_if_needed()

    def _update_pitch_button_labels(self):
        for shift, btn in self.pitch_buttons.items():
            if self.state.detected_key:
                key = get_key_at_semitone_shift(self.state.detected_key, shift)
                btn.setText(key)
            else:
                if shift == 0:
                    btn.setText("Original")
                else:
                    sign = "+" if shift > 0 else ""
                    btn.setText(f"{sign}{shift}")
        if getattr(self, 'deck_layout', None) is not None:
            try:
                self.deck_layout.info_cards.update_info(self.state)
            except Exception:
                pass

    def _apply_pitch_tempo(self):
        if not self.state.originals:
            return

        self.threads.safe_replace('pitch_tempo_thread', None)

        target_key = get_key_at_semitone_shift(self.state.detected_key, self.state.current_pitch_shift)
        target_bpm = round(self.state.detected_bpm * self.state.current_tempo_ratio)

        if self.state.current_song_source == "library" and self.state.current_song_name:
            song_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
            cache_folder = os.path.join(song_folder, "cache", f"{target_key}-{target_bpm}bpm")

            if os.path.exists(cache_folder) and any(f.endswith(".wav") for f in os.listdir(cache_folder)):
                self.status_label.setText("Cargando desde caché...")
                for name in self.state.stems:
                    cached_file = os.path.join(cache_folder, f"{name}.wav")
                    if os.path.exists(cached_file):
                        self.state.stems[name]["audio"] = sf.read(cached_file)[0].astype(np.float32)

                meta = self.lib_mgr.get_metadata(self.state.current_song_name)
                if meta:
                    if self.state.current_pitch_shift != 0 or self.state.current_tempo_ratio != 1.0:
                        meta["cached_audio_path"] = f"cache/{target_key}-{target_bpm}bpm"
                    else:
                        meta.pop("cached_audio_path", None)
                    meta["pitch_shift"] = self.state.current_pitch_shift
                    meta["tempo_ratio"] = self.state.current_tempo_ratio
                    self.lib_mgr.save_metadata(self.state.current_song_name, meta)

                self.status_label.setText("Listo")
                return

        self.status_label.setText("Aplicando pitch/tempo ...")
        self._sync_deck_status("Aplicando pitch/tempo ...")
        self.progress_bar.setVisible(True)
        self._sync_deck_progress(0, True)
        fx_map = {name: data.get("fx_enabled", True) for name, data in self.state.stems.items()}
        new_thread = PitchTempoThread(
            self.state.originals, self.state.current_pitch_shift,
            self.state.current_tempo_ratio, fx_map, self.state.mix_sr
        )
        new_thread.progress.connect(self._on_pt_progress)
        new_thread.progress_pct.connect(self._on_pt_progress_pct)
        new_thread.finished_processing.connect(self._on_pt_finished)
        new_thread.error.connect(self._on_pt_error)
        self.threads._pt_cache_dir = cache_folder if self.state.current_song_source == "library" else None
        self.progress_bar.setVisible(True)
        self._sync_deck_progress(0, True)
        self.threads.safe_replace('pitch_tempo_thread', new_thread)
        self.threads.safe_start(self.threads.pitch_tempo_thread)

    def _on_pt_progress(self, msg: str):
        self.status_label.setText(msg)
        self._sync_deck_status(msg)

    def _on_pt_progress_pct(self, pct: int):
        self.progress_bar.setValue(pct)
        self._sync_deck_progress(pct, True)

    def _on_pt_finished(self, updated: dict):
        sender = self.sender()
        if sender is not None and sender is not self.threads.pitch_tempo_thread:
            return

        for name, audio in updated.items():
            if name in self.state.stems:
                self.state.stems[name]["audio"] = audio

        cache_dir = getattr(self.threads, '_pt_cache_dir', None)
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)
            for name, audio in updated.items():
                wav_path = os.path.join(cache_dir, f"{name}.wav")
                try:
                    sf.write(wav_path, audio, self.state.mix_sr, subtype='PCM_16')
                except Exception:
                    pass

        if self.state.current_song_source == "library" and self.state.current_song_name:
            meta = self.lib_mgr.get_metadata(self.state.current_song_name)
            if meta:
                if self.state.current_pitch_shift != 0 or self.state.current_tempo_ratio != 1.0:
                    target_key = get_key_at_semitone_shift(self.state.detected_key, self.state.current_pitch_shift)
                    target_bpm = round(self.state.detected_bpm * self.state.current_tempo_ratio)
                    meta["cached_audio_path"] = f"cache/{target_key}-{target_bpm}bpm"
                else:
                    meta.pop("cached_audio_path", None)
                meta["pitch_shift"] = self.state.current_pitch_shift
                meta["tempo_ratio"] = self.state.current_tempo_ratio
                self.lib_mgr.save_metadata(self.state.current_song_name, meta)

        self.progress_bar.setVisible(False)
        self._sync_deck_progress(0, False)
        self.status_label.setText("Listo")
        self._sync_deck_status("Listo")
        self.threads.pitch_tempo_thread = None

    def _on_pt_error(self, msg: str):
        self.status_label.setText(f"Error: {msg}")
        self._sync_deck_status(f"Error: {msg}")
        self.progress_bar.setVisible(False)
        self._sync_deck_progress(0, False)
        self.threads.pitch_tempo_thread = None

    def _reset_all(self):
        self.threads.safe_replace('pitch_tempo_thread', None)

        self.state.current_pitch_shift = 0
        self.state.current_tempo_ratio = 1.0
        self.state.count_in_bars = 0
        self.state.click_during_playback = False

        for name in self.state.stems:
            if name in self.state.originals:
                self.state.stems[name]["audio"] = self.state.originals[name].copy()

        if self.state.current_song_source == "library" and self.state.current_song_name:
            meta = self.lib_mgr.get_metadata(self.state.current_song_name)
            if meta and meta.get("stems"):
                for stem_meta in meta["stems"]:
                    name = stem_meta.get("name")
                    if name in self.state.stems:
                        self.state.stems[name]["category"] = stem_meta.get("category", "Other")
                        self.state.stems[name]["volume"] = stem_meta.get("volume", 1.0)
                        self.state.stems[name]["pan"] = stem_meta.get("pan", 0.0)
                        self.state.stems[name]["muted"] = stem_meta.get("muted", False)
                        self.state.stems[name]["solo"] = stem_meta.get("solo", False)
                        self.state.stems[name]["fx_enabled"] = stem_meta.get("fx_enabled", True)
        else:
            for name in self.state.stems:
                self.state.stems[name]["category"] = "Other"
                self.state.stems[name]["volume"] = 1.0
                self.state.stems[name]["pan"] = 0.0
                self.state.stems[name]["muted"] = False
                self.state.stems[name]["solo"] = False
                self.state.stems[name]["fx_enabled"] = True

        for s, btn in self.pitch_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(s == 0)
            btn.blockSignals(False)
        self.bpm_spin.blockSignals(True)
        self.bpm_spin.setValue(self.state.detected_bpm)
        self.bpm_spin.blockSignals(False)
        self.tempo_ratio_label.setText("100%")
        self.count_in_combo.setCurrentIndex(0)
        self.click_check.setChecked(False)
        self.metronome_volume_slider.setVisible(False)
        self.metronome_pan_slider.setVisible(False)
        self.metro_icon_btn.setEnabled(False)
        if getattr(self, 'deck_layout', None) is not None:
            try:
                self.deck_layout.deck_count_in_combo.setCurrentIndex(0)
                self.deck_layout.deck_click_check.setChecked(False)
                self.deck_layout.deck_metro_vol_slider.setVisible(False)
                self.deck_layout.deck_metro_pan_slider.setVisible(False)
            except Exception:
                pass
        self._rebuild_stems_ui()
        self.state.has_unsaved_changes = False
        self._update_save_buttons()
        self._push_state_if_needed()
        self.state.has_unsaved_changes = False
        self._update_save_buttons()
        self.status_label.setText("Restablecido")
