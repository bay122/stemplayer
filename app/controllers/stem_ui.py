import os
from PySide6.QtWidgets import QMessageBox
from app.ui.stem_item_widget import StemItemWidget
from app.ui.svg_icon import svg_icon
from app.ui.theme import current as theme


class StemUIMixin:
    def _clear_stems_ui(self):
        while self.stems_layout.count():
            item = self.stems_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _on_library_item_clicked(self, item):
        self.setlist_widget.setlist_songs_list.clearSelection()

    def _on_setlist_item_clicked(self, item):
        self.library_widget.library_list.clearSelection()

    def _toggle_blink(self):
        self.blink_state = not self.blink_state
        self._update_list_icons()

    def _update_list_icons(self):
        is_playing = self.threads.playback_thread and self.threads.playback_thread.is_playing
        playing = is_playing and bool(self.state.current_song_name)

        self.library_widget.update_icons(
            self.state.current_song_name, playing, self.blink_state, self.icons_dir
        )
        self.setlist_widget.update_icons(
            self.state.current_song_name, playing, self.blink_state, self.icons_dir
        )

    def _on_auto_play_toggled(self, checked):
        color = theme.SVG_ICON_PLAYING if checked else theme.SVG_ICON_ACTIVE
        icon = svg_icon(os.path.join(self.icons_dir, "fad-preset-ab.svg"), color)
        self.auto_play_btn.setIcon(icon)
        if getattr(self, 'deck_layout', None) is not None:
            try:
                self.deck_layout.deck_auto_play_btn.blockSignals(True)
                self.deck_layout.deck_auto_play_btn.setChecked(checked)
                self.deck_layout.deck_auto_play_btn.blockSignals(False)
                self.deck_layout.deck_auto_play_btn.setIcon(icon)
            except Exception:
                pass

    def _rebuild_stems_ui(self):
        self._clear_stems_ui()
        was_updates_enabled = self.updatesEnabled() if hasattr(self, 'updatesEnabled') else True
        self.setUpdatesEnabled(False)
        try:
            for name, data in self.state.stems.items():
                widget = StemItemWidget(
                    name, data.get("category", "Other"),
                    data.get("volume", 1.0), self.icons_dir
                )
                widget.set_pan(data.get("pan", 0.0))
                widget.set_mute(data.get("muted", False))
                widget.set_solo(data.get("solo", False))
                widget.set_fx(data.get("fx_enabled", True))
                widget.volume_changed.connect(lambda n, v: self._on_stem_volume_changed(n, v))
                widget.volume_slider.sliderReleased.connect(lambda n=name: self._on_stem_volume_released(n))
                widget.pan_changed.connect(lambda n, v: self._on_stem_pan_changed(n, v))
                widget.pan_slider.sliderReleased.connect(lambda n=name: self._on_stem_pan_released(n))
                widget.mute_toggled.connect(lambda n, m: self._on_stem_mute_toggled(n, m))
                widget.solo_toggled.connect(lambda n, s: self._on_stem_solo_toggled(n, s))
                widget.fx_toggled.connect(lambda n, f: self._on_stem_fx_toggled(n, f))
                widget.name_changed.connect(lambda o, n: self._on_stem_name_changed(o, n))
                widget.category_changed.connect(lambda n, c: self._on_stem_category_changed(n, c))
                widget.delete_requested.connect(lambda n: self._on_stem_delete(n))
                widget.move_up_requested.connect(lambda n: self._on_stem_move_up(n))
                widget.move_down_requested.connect(lambda n: self._on_stem_move_down(n))
                self.stems_layout.addWidget(widget)
        finally:
            self.setUpdatesEnabled(was_updates_enabled)

        if getattr(self, 'deck_layout', None) is not None:
            try:
                self.deck_layout.rebuild_stems()
            except Exception:
                pass

    def _sync_deck_volume_visual(self, name: str):
        """Sincroniza la amplitud del waveform del deck tras cambio de volumen."""
        if getattr(self, 'deck_layout', None) is None:
            return
        try:
            row = self.deck_layout._deck_rows.get(name)
            if row is None:
                return
            data = self.state.stems.get(name)
            if data is None:
                return
            row.set_volume_visual(data.get("volume", 1.0))
        except Exception:
            pass

    def _on_stem_volume_changed(self, name: str, value: float):
        if name in self.state.stems:
            self.state.stems[name]["volume"] = value
        self._sync_deck_volume_visual(name)

    def _on_stem_volume_released(self, name: str):
        self._push_state_if_needed()

    def _on_stem_pan_changed(self, name: str, value: float):
        if name in self.state.stems:
            self.state.stems[name]["pan"] = value

    def _on_stem_pan_released(self, name: str):
        self._push_state_if_needed()

    def _on_stem_mute_toggled(self, name: str, muted: bool):
        if name in self.state.stems:
            self.state.stems[name]["muted"] = muted
            self._push_state_if_needed()

    def _on_stem_solo_toggled(self, name: str, solo: bool):
        if name in self.state.stems:
            self.state.stems[name]["solo"] = solo
            self._push_state_if_needed()

    def _on_stem_fx_toggled(self, name: str, enabled: bool):
        if name in self.state.stems:
            self.state.stems[name]["fx_enabled"] = enabled
            self._push_state_if_needed()

    def _on_stem_name_changed(self, old_name: str, new_name: str):
        if old_name in self.state.stems and new_name not in self.state.stems:
            self.state.stems[new_name] = self.state.stems.pop(old_name)
            self.state.originals[new_name] = self.state.originals.pop(old_name)
            self._rebuild_stems_ui()

    def _on_stem_category_changed(self, name: str, category: str):
        if name in self.state.stems:
            self.state.stems[name]["category"] = category
            self._push_state_if_needed()

    def _on_stem_delete(self, name: str):
        if name in self.state.stems:
            reply = QMessageBox.question(self, "Eliminar stem",
                                          f"¿Eliminar '{name}' de la sesión actual?",
                                          QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                del self.state.stems[name]
                if name in self.state.originals:
                    del self.state.originals[name]
                self._rebuild_stems_ui()
                self._push_state_if_needed()

    def _on_stem_move_up(self, name: str):
        keys = list(self.state.stems.keys())
        if name in keys:
            idx = keys.index(name)
            if idx > 0:
                keys[idx], keys[idx-1] = keys[idx-1], keys[idx]
                self.state.stems = {k: self.state.stems[k] for k in keys}
                self._rebuild_stems_ui()
                self._push_state_if_needed()

    def _on_stem_move_down(self, name: str):
        keys = list(self.state.stems.keys())
        if name in keys:
            idx = keys.index(name)
            if idx < len(keys) - 1:
                keys[idx], keys[idx+1] = keys[idx+1], keys[idx]
                self.state.stems = {k: self.state.stems[k] for k in keys}
                self._rebuild_stems_ui()
                self._push_state_if_needed()
