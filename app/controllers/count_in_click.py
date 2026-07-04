class CountInClickMixin:
    def _on_count_in_changed(self, index: int):
        self.state.count_in_bars = index
        if getattr(self, 'deck_layout', None) is not None:
            try:
                self.deck_layout.deck_count_in_combo.blockSignals(True)
                self.deck_layout.deck_count_in_combo.setCurrentIndex(index)
                self.deck_layout.deck_count_in_combo.blockSignals(False)
            except Exception:
                pass
        self._push_state_if_needed()

    def _on_click_during_changed(self, state):
        self.state.click_during_playback = bool(state)
        show = self.state.click_during_playback
        self.metronome_volume_slider.setVisible(show)
        self.metronome_pan_slider.setVisible(show)
        self.metro_icon_btn.setEnabled(show)
        if getattr(self, 'deck_layout', None) is not None:
            try:
                self.deck_layout.deck_metro_vol_slider.setVisible(show)
                self.deck_layout.deck_metro_pan_slider.setVisible(show)
                self.deck_layout.deck_click_check.blockSignals(True)
                self.deck_layout.deck_click_check.setChecked(show)
                self.deck_layout.deck_click_check.blockSignals(False)
            except Exception:
                pass
        self._push_state_if_needed()
