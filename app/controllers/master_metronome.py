from PySide6.QtWidgets import QMessageBox


class MasterMetronomeMixin:
    def _sync_deck_master(self, value):
        if getattr(self, 'deck_layout', None) is None:
            return
        try:
            self.deck_layout.deck_master_slider.blockSignals(True)
            self.deck_layout.deck_master_slider.setValue(value)
            self.deck_layout.deck_master_slider.blockSignals(False)
        except Exception:
            pass

    def _sync_deck_metro_vol(self, value):
        if getattr(self, 'deck_layout', None) is None:
            return
        try:
            self.deck_layout.deck_metro_vol_slider.blockSignals(True)
            self.deck_layout.deck_metro_vol_slider.setValue(value)
            self.deck_layout.deck_metro_vol_slider.blockSignals(False)
        except Exception:
            pass

    def _sync_deck_metro_pan(self, value):
        if getattr(self, 'deck_layout', None) is None:
            return
        try:
            self.deck_layout.deck_metro_pan_slider.blockSignals(True)
            self.deck_layout.deck_metro_pan_slider.setValue(value)
            self.deck_layout.deck_metro_pan_slider.blockSignals(False)
        except Exception:
            pass

    def _on_master_volume_changed(self, value: float):
        self.state.master_volume = value
        if self.threads.playback_thread:
            self.threads.playback_thread.set_master_volume(value)
        self._sync_deck_master(value)

    def _on_master_volume_released(self):
        self._push_state_if_needed()

    def _on_metronome_volume_changed(self, value: float):
        self.state.metronome_volume = value
        if self.threads.playback_thread:
            self.threads.playback_thread.set_metronome_volume(value)
        self._sync_deck_metro_vol(value)

    def _on_metronome_volume_released(self):
        self._push_state_if_needed()

    def _on_metronome_pan_changed(self, value: float):
        self.state.metronome_pan = value
        if self.threads.playback_thread:
            self.threads.playback_thread.set_metronome_pan(value)
        self._sync_deck_metro_pan(value)

    def _on_metronome_pan_released(self):
        self._push_state_if_needed()

    def _on_artist_changed(self, text: str):
        self.state.current_song_artist = text
        self._push_state_if_needed()

    def _on_add_to_setlist_clicked(self):
        if self.state.current_song_source != "library" or not self.state.current_song_name:
            QMessageBox.warning(self, "Aviso", "La canción debe estar guardada en la librería primero para añadirla a un setlist.\nUsa el botón 'Guardar en librería'.")
            return
        if self.setlist_widget.current_setlist_index >= 0:
            if self.setlist_widget.add_song_to_current(self.state.current_song_name):
                QMessageBox.information(self, "Info", f"Canción '{self.state.current_song_name}' añadida al setlist actual.")
        else:
            if self.setlist_widget.create_and_add(self.state.current_song_name):
                QMessageBox.information(self, "Info", f"Nuevo setlist creado y canción '{self.state.current_song_name}' añadida.")
