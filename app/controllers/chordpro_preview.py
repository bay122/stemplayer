import os
from PySide6.QtWidgets import QMessageBox


class ChordProPreviewMixin:
    def _load_chordpro_preview(self):
        if self.state.current_song_source != "library" or not self.state.current_song_name:
            self.chordpro_preview_widget.setVisible(False)
            return

        chopro_path = os.path.join(self.lib_mgr.library_path, self.state.current_song_name, f"{self.state.current_song_name}.chopro")
        sync_path = os.path.join(self.lib_mgr.library_path, self.state.current_song_name, f"{self.state.current_song_name}.sync.json")

        if os.path.exists(chopro_path):
            self.chordpro_path = chopro_path
            self.chordpro_preview_widget.load_chopro_content(chopro_path)
            self.chordpro_preview_widget.setVisible(True)

            # También cargar en la instancia del deck
            if self.deck_layout is not None and self.deck_layout._chordpro_preview is not None:
                try:
                    self.deck_layout._chordpro_preview.load_chopro_content(chopro_path)
                    self.deck_layout._update_chordpro_section()
                except Exception:
                    pass

            if os.path.exists(sync_path):
                self.live_display_widget.load_sync_data(chopro_path, sync_path)

            try:
                from chordpro import Song
                from chordpro.renderers.html import render as render_html
                song = Song(chopro_path)
                html_content = render_html(song)
                try:
                    html_content = html_content.encode('cp1252').decode('utf-8')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    html_content = html_content.encode('latin-1').decode('utf-8')

                if '<head>' not in html_content:
                    html_content = '<meta charset="UTF-8">\n' + html_content
                else:
                    html_content = html_content.replace('<head>', '<head>\n<meta charset="UTF-8">', 1)

                self.chordpro_fullscreen_text.setHtml(html_content)
            except Exception:
                try:
                    with open(chopro_path, 'r', encoding='utf-8') as f:
                        raw_text = f.read()
                    self.chordpro_fullscreen_text.setPlainText(raw_text)
                except Exception:
                    self.chordpro_fullscreen_text.setPlainText("Error al cargar acordes")
        else:
            self.chordpro_preview_widget.setVisible(False)

    def _show_chordpro_fullscreen(self):
        if self.chordpro_path and os.path.exists(self.chordpro_path):
            self.center_stack.setCurrentIndex(2)
        else:
            QMessageBox.warning(self, "Error", "No hay archivo de acordes cargado")

    def _hide_chordpro_fullscreen(self):
        self.center_stack.setCurrentIndex(0)
