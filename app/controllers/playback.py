import os
from app.audio.playback import PlaybackThread
from app.ui.svg_icon import svg_icon


class PlaybackMixin:
    def _sync_deck_play_icon(self, icon):
        if getattr(self, 'deck_layout', None) is None:
            return
        try:
            self.deck_layout.deck_play_btn.setIcon(icon)
        except Exception:
            pass

    def _sync_deck_time(self, time_text, progress_value):
        if getattr(self, 'deck_layout', None) is None:
            return
        try:
            self.deck_layout.deck_current_time.setText(time_text)
            if progress_value is not None and not self.deck_layout.deck_progress.isSliderDown():
                self.deck_layout.deck_progress.blockSignals(True)
                self.deck_layout.deck_progress.setValue(int(progress_value * 1000))
                self.deck_layout.deck_progress.blockSignals(False)
            # Actualizar playhead del waveform global
            if progress_value is not None and self.deck_layout._global_waveform is not None:
                self.deck_layout._global_waveform.set_playhead(progress_value)
        except Exception:
            pass

    def _on_peak_level(self, peak):
        if getattr(self, 'meters_panel', None) is not None:
            try:
                self.meters_panel.update_peak(peak)
            except Exception:
                pass
        if getattr(self, 'deck_layout', None) is not None:
            try:
                self.deck_layout.update_peak(peak)
            except Exception:
                pass

    def _toggle_play(self):
        if self.threads.playback_thread and self.threads.playback_thread.is_playing:
            self._pause_playback()
        else:
            self._start_playback()

    def _start_playback(self):
        if not self.state.stems:
            self.status_label.setText("No hay stems cargados")
            return
        if self.threads.playback_thread and self.threads.playback_thread.isRunning():
            return

        new_thread = PlaybackThread(
            self.state.stems, self.state.detected_bpm, self.state.mix_sr,
            count_in_bars=self.state.count_in_bars,
            click_during_playback=self.state.click_during_playback,
            master_volume=self.state.master_volume,
            metronome_volume=self.state.metronome_volume,
            metronome_pan=self.state.metronome_pan,
            click_offset_samples=self.state.click_offset_samples
        )
        if self._pending_seek is not None:
            new_thread.seek(self._pending_seek)
            self._pending_seek = None
        new_thread.update_progress.connect(self._on_playback_progress)
        new_thread.peak_level.connect(self._on_peak_level)
        new_thread.finished.connect(self._on_playback_finished)
        self.threads.safe_replace('playback_thread', new_thread)
        self.threads.safe_start(self.threads.playback_thread)
        pause_icon = svg_icon(os.path.join(self.icons_dir, "fad-pause.svg"))
        self.play_btn.setIcon(pause_icon)
        self._sync_deck_play_icon(pause_icon)
        self._update_list_icons()

    def _pause_playback(self):
        self._is_manual_stop = True
        pt = self.threads.playback_thread
        if pt:
            if hasattr(pt, 'current_pos'):
                self._pending_seek = pt.current_pos
            pt.stop()
        self.threads.safe_replace('playback_thread', None)
        play_icon = svg_icon(os.path.join(self.icons_dir, "fad-play.svg"))
        self.play_btn.setIcon(play_icon)
        self._sync_deck_play_icon(play_icon)
        self._update_list_icons()

    def _stop_playback(self):
        self._is_manual_stop = True
        self._pending_seek = None
        pt = self.threads.playback_thread
        if pt:
            pt.stop()
        self.threads.safe_replace('playback_thread', None)
        play_icon = svg_icon(os.path.join(self.icons_dir, "fad-play.svg"))
        self.play_btn.setIcon(play_icon)
        self.playback_progress.blockSignals(True)
        self.playback_progress.setValue(0)
        self.playback_progress.blockSignals(False)
        self.current_time_label.setText("00:00")
        if getattr(self, 'deck_layout', None) is not None:
            try:
                self.deck_layout.update_playhead(0.0)
            except Exception:
                pass
        self._sync_deck_play_icon(play_icon)
        self._sync_deck_time("00:00", 0)
        self._update_list_icons()

    def _on_playback_progress(self, value: float):
        if not self.playback_progress.isSliderDown():
            self.playback_progress.blockSignals(True)
            self.playback_progress.setValue(int(value * 1000))
            self.playback_progress.blockSignals(False)

            if self.state.stems:
                max_len = max(len(s["audio"]) for s in self.state.stems.values())
                beats_per_bar = 4
                count_in_beats = self.state.count_in_bars * beats_per_bar
                count_in_samples = int(count_in_beats * self.state.mix_sr * 60 / self.state.detected_bpm) if count_in_beats > 0 else 0
                total_samples = max_len + count_in_samples

                current_samples = int(value * total_samples)

                if current_samples < count_in_samples:
                    current_seconds = 0
                else:
                    current_seconds = int((current_samples - count_in_samples) / self.state.mix_sr)

                total_seconds = int(max_len / self.state.mix_sr)

                current_min, current_sec = divmod(current_seconds, 60)
                total_min, total_sec = divmod(total_seconds, 60)

                self.current_time_label.setText(f"{current_min:02d}:{current_sec:02d}")
                self.total_time_label.setText(f"{total_min:02d}:{total_sec:02d}")

                # Actualizar total_duration del waveform global del deck
                if getattr(self, 'deck_layout', None) is not None:
                    try:
                        if self.deck_layout._global_waveform is not None:
                            self.deck_layout._global_waveform.set_total_duration(
                                float(total_seconds)
                            )
                    except Exception:
                        pass

                if current_seconds >= total_seconds and total_seconds > 0:
                    self._pause_playback()
                    if self.setlist_widget.current_setlist_index >= 0:
                        self.setlist_widget.play_next()
                    return

                if self.center_stack.currentIndex() == 1:
                    self.live_display_widget.update_position(current_seconds)

                if getattr(self, 'deck_layout', None) is not None and self.deck_layout is not None:
                    try:
                        playhead_ratio = value
                        self.deck_layout.update_playhead(playhead_ratio)
                    except Exception:
                        pass

                try:
                    self.deck_layout.deck_current_time.setText(f"{current_min:02d}:{current_sec:02d}")
                    self.deck_layout.deck_total_time.setText(f"{total_min:02d}:{total_sec:02d}")
                    if not self.deck_layout.deck_progress.isSliderDown():
                        self.deck_layout.deck_progress.blockSignals(True)
                        self.deck_layout.deck_progress.setValue(int(value * 1000))
                        self.deck_layout.deck_progress.blockSignals(False)
                    # Actualizar el total_duration del waveform global
                    if self.deck_layout._global_waveform is not None:
                        self.deck_layout._global_waveform.set_total_duration(
                            float(total_seconds)
                        )
                except Exception:
                    pass

                fullscreen = getattr(self.live_display_widget, '_fullscreen_window', None)
                if fullscreen and fullscreen.isVisible():
                    fullscreen.update_progress(current_seconds, total_seconds)

    def _on_playback_preview(self, value: int):
        if not self.state.stems:
            return
        max_len = max(len(s["audio"]) for s in self.state.stems.values())
        beats_per_bar = 4
        count_in_beats = self.state.count_in_bars * beats_per_bar
        count_in_samples = int(count_in_beats * self.state.mix_sr * 60 / self.state.detected_bpm) if count_in_beats > 0 else 0
        total_samples = max_len + count_in_samples

        desired_sample = int((value / 1000.0) * total_samples)

        if desired_sample < count_in_samples:
            current_seconds = 0
        else:
            current_seconds = (desired_sample - count_in_samples) // self.state.mix_sr

        current_min, current_sec = divmod(current_seconds, 60)
        time_text = f"{current_min:02d}:{current_sec:02d}"
        self.current_time_label.setText(time_text)
        try:
            self.deck_layout.deck_current_time.setText(time_text)
        except Exception:
            pass

    def _on_playback_seek(self, value=None):
        if not self.state.stems:
            return
        if value is None:
            value = self.playback_progress.value()
        ratio = value / 1000.0
        self._seek_to_ratio(ratio)

    def _on_waveform_seek(self, ratio: float):
        """Seek desde el waveform global del deck."""
        if not self.state.stems:
            return
        self._seek_to_ratio(ratio)

    def _seek_to_ratio(self, ratio: float):
        if not self.state.stems:
            return
        ratio = max(0.0, min(1.0, ratio))
        max_len = max(len(s["audio"]) for s in self.state.stems.values())
        beats_per_bar = 4
        count_in_beats = self.state.count_in_bars * beats_per_bar
        count_in_samples = int(count_in_beats * self.state.mix_sr * 60 / self.state.detected_bpm) if count_in_beats > 0 else 0
        total_samples = max_len + count_in_samples
        absolute_pos = int(ratio * total_samples)

        # Sincronizar slider del clásico
        slider_value = int(ratio * 1000)
        self.playback_progress.blockSignals(True)
        self.playback_progress.setValue(slider_value)
        self.playback_progress.blockSignals(False)
        # Sincronizar slider del deck
        try:
            self.deck_layout.deck_progress.blockSignals(True)
            self.deck_layout.deck_progress.setValue(slider_value)
            self.deck_layout.deck_progress.blockSignals(False)
        except Exception:
            pass

        if self.threads.playback_thread and self.threads.playback_thread.isRunning():
            self.threads.playback_thread.seek(absolute_pos)
        else:
            self._pending_seek = absolute_pos
        self._on_playback_preview(slider_value)

    def _on_playback_finished(self):
        sender = self.sender()
        if sender is not None and sender is not self.threads.playback_thread:
            return

        is_natural = not self._is_manual_stop
        self._is_manual_stop = False

        if is_natural:
            self._pending_seek = None

        self.play_btn.setIcon(svg_icon(os.path.join(self.icons_dir, "fad-play.svg")))
        self._sync_deck_play_icon(svg_icon(os.path.join(self.icons_dir, "fad-play.svg")))
        if is_natural:
            if getattr(self, 'deck_layout', None) is not None:
                try:
                    self.deck_layout.update_playhead(0.0)
                except Exception:
                    pass
            self._sync_deck_time("00:00", 0)
            self.status_label.setText("Reproducción finalizada")
            self.current_time_label.setText("00:00")
            self.playback_progress.blockSignals(True)
            self.playback_progress.setValue(0)
            self.playback_progress.blockSignals(False)
        self.threads.playback_thread = None
        self._update_list_icons()

        if is_natural and self.setlist_widget.current_setlist_index >= 0:
            if self.setlist_widget.current_setlist_song_index < self.setlist_widget.setlist_songs_list.count() - 1:
                if self.auto_play_btn.isChecked():
                    self._auto_play_pending = True
                self.setlist_widget.play_next()
