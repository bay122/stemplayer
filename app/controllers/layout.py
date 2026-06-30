import os
from PySide6.QtWidgets import QMessageBox
from app.ui.svg_icon import svg_icon


class LayoutMixin:
    def _toggle_live_mode(self, checked):
        if checked:
            self.center_stack.setCurrentIndex(1)
            self.toggle_live_btn.setText("Mezclador")
        else:
            self.center_stack.setCurrentIndex(0)
            self.toggle_live_btn.setText("Karaoke")
            self.live_display_widget.reset()

    def _toggle_left_panel(self):
        self.left_panel_collapsed = not self.left_panel_collapsed
        if self.left_panel_collapsed:
            self.lib_panel.setMaximumWidth(0)
            self.lib_panel.setMinimumWidth(0)
            self.collapse_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-h-expand.svg"), "#888888"))
            self.collapse_btn.setToolTip("Expandir panel izquierdo")
        else:
            self.lib_panel.setMaximumWidth(340)
            self.lib_panel.setMinimumWidth(340)
            self.collapse_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-h-expand.svg"), "#888888"))
            self.collapse_btn.setToolTip("Contraer panel izquierdo")

    def closeEvent(self, event):
        self.live_display_widget.reset()
        pt = self.threads.playback_thread
        if pt:
            pt.stop()
            pt.wait(6000)
            self.threads.safe_replace('playback_thread', None)
        self.threads.cleanup_all()
        event.accept()

    def _close_song(self):
        if self.state.has_unsaved_changes:
            reply = QMessageBox.question(self, "Cambios sin guardar",
                                          "¿Guardar cambios antes de cerrar?",
                                          QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            if reply == QMessageBox.Cancel:
                return False
            if reply == QMessageBox.Yes:
                if self.state.current_song_source == "library":
                    self._save_changes()
                else:
                    self._save_to_library()

        self.threads.cleanup_all()

        self.state.reset_song()
        self._clear_stems_ui()
        self.song_name_label.setText("Canción: --")
        self.artist_input.blockSignals(True)
        self.artist_input.clear()
        self.artist_input.blockSignals(False)
        self.key_label.setText("Key: --")
        self.bpm_label.setText("BPM: --")
        self.orig_bpm_label.setText("--")
        self.bpm_spin.setValue(120)
        self.tempo_ratio_label.setText("100%")
        self.count_in_combo.setCurrentIndex(0)
        self.click_check.setChecked(False)
        self.master_volume_slider.setValue(1.0)
        self.metronome_volume_slider.setValue(0.5)
        self.metronome_pan_slider.setValue(0.0)
        self.metronome_volume_slider.setVisible(False)
        self.metronome_pan_slider.setVisible(False)
        self.metro_icon_btn.setEnabled(False)
        self.playback_progress.setValue(0)
        self.current_time_label.setText("00:00")
        self.total_time_label.setText("00:00")
        self.close_song_btn.setVisible(False)
        self.save_lib_btn.setVisible(False)
        self.save_changes_btn.setVisible(False)
        self.generate_chordpro_btn.setVisible(False)
        self.more_btn.setVisible(False)
        self._save_as_action.setVisible(False)
        self._edit_chordpro_action.setVisible(False)
        self._regenerate_sync_action.setVisible(False)
        self._edit_sync_action.setVisible(False)
        self._add_to_setlist_action.setVisible(False)
        self.toggle_live_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.bg_status_label.setVisible(False)
        self.chordpro_path = None
        self.chordpro_fullscreen_text.clear()
        self.chordpro_preview_widget.setVisible(False)
        self.live_display_widget.reset()
        self.toggle_live_btn.setEnabled(False)
        self.toggle_live_btn.setChecked(False)
        self.center_stack.setCurrentIndex(0)
        self.status_label.setText("Listo")
        self._update_save_buttons()
        self._update_undo_redo_btns()
        return True
