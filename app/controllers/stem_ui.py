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
            order = list(self.state.stem_order)
            for i, n in enumerate(order):
                if n == old_name:
                    order[i] = new_name
                    break
            self.state.stem_order = order
            self._rename_stem_widget(old_name, new_name)
            self._push_state_if_needed()

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
                order = [n for n in self.state.stem_order if n != name]
                self.state.stem_order = order
                self._remove_stem_widget(name)
                self._push_state_if_needed()

    def _on_stem_move_up(self, name: str):
        keys = list(self.state.stems.keys())
        if name in keys:
            idx = keys.index(name)
            if idx > 0:
                self._swap_stem_in_layouts(idx, idx - 1)
                self._push_state_if_needed()

    def _on_stem_move_down(self, name: str):
        keys = list(self.state.stems.keys())
        if name in keys:
            idx = keys.index(name)
            if idx < len(keys) - 1:
                self._swap_stem_in_layouts(idx, idx + 1)
                self._push_state_if_needed()

    def _rename_stem_widget(self, old_name: str, new_name: str):
        """Actualiza el nombre interno del widget de stem en ambos layouts sin recrearlo."""
        layout = getattr(self, 'stems_layout', None)
        if layout is not None:
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if w is not None and getattr(w, 'stem_name', None) == old_name:
                    w.set_name(new_name)
                    break
        deck = getattr(self, 'deck_layout', None)
        if deck is not None:
            rows = getattr(deck, '_deck_rows', None)
            if rows is not None and old_name in rows:
                w = rows.pop(old_name)
                rows[new_name] = w
                if hasattr(w, 'set_name'):
                    w.set_name(new_name)

    def _remove_stem_widget(self, name: str):
        """Elimina el widget de stem en ambos layouts sin reconstruir el resto."""
        layout = getattr(self, 'stems_layout', None)
        if layout is not None:
            for i in range(layout.count() - 1, -1, -1):
                w = layout.itemAt(i).widget()
                if w is not None and getattr(w, 'stem_name', None) == name:
                    layout.takeAt(i)
                    w.setParent(None)
                    w.deleteLater()
                    break
        deck = getattr(self, 'deck_layout', None)
        if deck is not None:
            rows = getattr(deck, '_deck_rows', None)
            if rows is not None and name in rows:
                w = rows.pop(name)
                deck_layout = getattr(deck, 'stems_layout', None)
                if deck_layout is not None:
                    for i in range(deck_layout.count() - 1, -1, -1):
                        wi = deck_layout.itemAt(i).widget()
                        if wi is w:
                            deck_layout.takeAt(i)
                            break
                w.setParent(None)
                w.deleteLater()

    def _swap_stem_in_layouts(self, idx_a: int, idx_b: int):
        """Intercambia visualmente la posición de dos stems en ambos layouts.

        Reordena el dict state.stems y la lista stem_order, y mueve los
        widgets existentes en los layouts (clásico y deck) sin destruirlos.
        """
        keys = list(self.state.stems.keys())
        if not (0 <= idx_a < len(keys)) or not (0 <= idx_b < len(keys)):
            return
        if idx_a == idx_b:
            return
        keys[idx_a], keys[idx_b] = keys[idx_b], keys[idx_a]
        self.state.stems = {k: self.state.stems[k] for k in keys}
        if self.state.stem_order:
            order = list(self.state.stem_order)
            if idx_a < len(order) and idx_b < len(order):
                order[idx_a], order[idx_b] = order[idx_b], order[idx_a]
                self.state.stem_order = order

        layout = getattr(self, 'stems_layout', None)
        if layout is not None and idx_a < layout.count() and idx_b < layout.count():
            item_a = layout.takeAt(idx_a)
            item_b = layout.takeAt(idx_b - 1) if idx_b > idx_a else layout.takeAt(idx_b)
            widget_b = item_b.widget() if item_b is not None else None
            widget_a = item_a.widget() if item_a is not None else None
            if widget_a is not None and widget_b is not None:
                layout.insertWidget(idx_b, widget_a)
                layout.insertWidget(idx_a, widget_b)

        deck = getattr(self, 'deck_layout', None)
        if deck is not None:
            deck_layout = getattr(deck, 'stems_layout', None)
            if deck_layout is not None and idx_a < deck_layout.count() and idx_b < deck_layout.count():
                item_a = deck_layout.takeAt(idx_a)
                item_b = deck_layout.takeAt(idx_b - 1) if idx_b > idx_a else deck_layout.takeAt(idx_b)
                widget_b = item_b.widget() if item_b is not None else None
                widget_a = item_a.widget() if item_a is not None else None
                if widget_a is not None and widget_b is not None:
                    deck_layout.insertWidget(idx_b, widget_a)
                    deck_layout.insertWidget(idx_a, widget_b)
