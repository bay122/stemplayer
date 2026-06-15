class CountInClickMixin:
    def _on_count_in_changed(self, index: int):
        self.state.count_in_bars = index
        self._push_state_if_needed()

    def _on_click_during_changed(self, state):
        self.state.click_during_playback = bool(state)
        show = self.state.click_during_playback
        self.metronome_volume_slider.setVisible(show)
        self.metronome_pan_slider.setVisible(show)
        self.metro_icon_btn.setEnabled(show)
        self._push_state_if_needed()
