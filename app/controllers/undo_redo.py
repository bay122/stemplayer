import os
import numpy as np
from app.ui.theme import DARK_THEME as theme


class UndoRedoMixin:
    def _get_current_state(self):
        return {
            "artist": self.state.current_song_artist,
            "master_volume": self.state.master_volume,
            "metronome_volume": self.state.metronome_volume,
            "metronome_pan": self.state.metronome_pan,
            "pitch_shift": self.state.current_pitch_shift,
            "tempo_ratio": self.state.current_tempo_ratio,
            "click_during": self.state.click_during_playback,
            "count_in_bars": self.state.count_in_bars,
            "stems": {
                name: {
                    "volume": data["volume"],
                    "pan": data.get("pan", 0.0),
                    "muted": data.get("muted", False),
                    "solo": data.get("solo", False),
                    "fx": data.get("fx_enabled", True),
                    "category": data.get("category", "Other")
                }
                for name, data in self.state.stems.items()
            }
        }

    def _apply_state(self, state: dict):
        self.state.current_song_artist = state["artist"]
        self.artist_input.blockSignals(True)
        self.artist_input.setText(self.state.current_song_artist)
        self.artist_input.blockSignals(False)

        self.state.master_volume = state["master_volume"]
        self.master_volume_slider.blockSignals(True)
        self.master_volume_slider.setValue(self.state.master_volume)
        self.master_volume_slider.blockSignals(False)
        if self.threads.playback_thread:
            self.threads.playback_thread.set_master_volume(self.state.master_volume)

        self.state.metronome_volume = state["metronome_volume"]
        self.metronome_volume_slider.blockSignals(True)
        self.metronome_volume_slider.setValue(self.state.metronome_volume)
        self.metronome_volume_slider.blockSignals(False)
        if self.threads.playback_thread:
            self.threads.playback_thread.set_metronome_volume(self.state.metronome_volume)

        self.state.metronome_pan = state["metronome_pan"]
        self.metronome_pan_slider.blockSignals(True)
        self.metronome_pan_slider.setValue(self.state.metronome_pan)
        self.metronome_pan_slider.blockSignals(False)
        if self.threads.playback_thread:
            self.threads.playback_thread.set_metronome_pan(self.state.metronome_pan)

        self.state.click_during_playback = state["click_during"]
        self.click_check.blockSignals(True)
        self.click_check.setChecked(self.state.click_during_playback)
        self.click_check.blockSignals(False)
        show = self.state.click_during_playback
        self.metronome_volume_slider.setVisible(show)
        self.metronome_pan_slider.setVisible(show)
        self.metro_icon_btn.setEnabled(show)

        self.state.count_in_bars = state["count_in_bars"]
        self.count_in_combo.blockSignals(True)
        self.count_in_combo.setCurrentIndex(self.state.count_in_bars)
        self.count_in_combo.blockSignals(False)

        pitch_changed = self.state.current_pitch_shift != state["pitch_shift"]
        tempo_changed = self.state.current_tempo_ratio != state["tempo_ratio"]
        self.state.current_pitch_shift = state["pitch_shift"]
        self.state.current_tempo_ratio = state["tempo_ratio"]
        self.bpm_spin.blockSignals(True)
        self.bpm_spin.setValue(int(self.state.detected_bpm * self.state.current_tempo_ratio))
        self.bpm_spin.blockSignals(False)
        self.tempo_ratio_label.setText(f"{self.state.current_tempo_ratio*100:.1f}%")
        for s, btn in self.pitch_buttons.items():
            btn.blockSignals(True)
            btn.setChecked(s == self.state.current_pitch_shift)
            btn.blockSignals(False)

        for name, data in state["stems"].items():
            if name in self.state.stems:
                self.state.stems[name]["volume"] = data["volume"]
                self.state.stems[name]["pan"] = data["pan"]
                self.state.stems[name]["muted"] = data["muted"]
                self.state.stems[name]["solo"] = data["solo"]
                self.state.stems[name]["fx_enabled"] = data["fx"]
                self.state.stems[name]["category"] = data["category"]

        self._rebuild_stems_ui()

        if pitch_changed or tempo_changed:
            self._apply_pitch_tempo()

    def _push_state_if_needed(self):
        if not self.state.stems:
            return
        state = self._get_current_state()
        if self.state.history_idx >= 0 and self.state.history_idx < len(self.state.history):
            if self.state.history[self.state.history_idx] == state:
                return

        self.state.history = self.state.history[:self.state.history_idx + 1]
        self.state.history.append(state)
        self.state.history_idx += 1
        self._update_undo_redo_btns()
        self._mark_changes()

    def _undo(self):
        if self.state.history_idx > 0:
            self.state.history_idx -= 1
            self._apply_state(self.state.history[self.state.history_idx])
            self._update_undo_redo_btns()
            self.state.has_unsaved_changes = (self.state.history_idx != self.state.saved_history_idx)
            self._update_save_buttons()

    def _redo(self):
        if self.state.history_idx < len(self.state.history) - 1:
            self.state.history_idx += 1
            self._apply_state(self.state.history[self.state.history_idx])
            self._update_undo_redo_btns()
            self.state.has_unsaved_changes = (self.state.history_idx != self.state.saved_history_idx)
            self._update_save_buttons()

    def _update_undo_redo_btns(self):
        self.undo_btn.setEnabled(self.state.history_idx > 0)
        self.redo_btn.setEnabled(self.state.history_idx < len(self.state.history) - 1)

    def _mark_changes(self):
        self.state.has_unsaved_changes = True
        self._update_save_buttons()

    def _update_save_buttons(self):
        self.save_lib_btn.setVisible(False)
        self.save_changes_btn.setVisible(False)
        self.save_as_btn.setVisible(False)
        self.generate_chordpro_btn.setVisible(False)
        self.edit_chordpro_btn.setVisible(False)

        btn_style = theme.action_button_qss()

        if self.state.current_song_source == "library":
            self.save_changes_btn.setVisible(self.state.has_unsaved_changes)
            if self.state.has_unsaved_changes:
                self.save_changes_btn.setStyleSheet(btn_style)

            self.save_as_btn.setVisible(True)

            chopro_path = os.path.join(self.lib_mgr.library_path, self.state.current_song_name, f"{self.state.current_song_name}.chopro")
            if os.path.exists(chopro_path):
                self.generate_chordpro_btn.setText("Regenerar Sheet de acordes")
                self.edit_chordpro_btn.setVisible(True)
            else:
                self.generate_chordpro_btn.setText("Generar Sheet de acordes")
                self.edit_chordpro_btn.setVisible(False)

            self.generate_chordpro_btn.setVisible(True)
        elif self.state.current_song_source == "folder":
            self.save_lib_btn.setVisible(True)
            self.save_lib_btn.setStyleSheet(btn_style)
        else:
            self.save_lib_btn.setVisible(False)
            self.save_changes_btn.setVisible(False)
            self.generate_chordpro_btn.setVisible(False)
            self.edit_chordpro_btn.setVisible(False)
