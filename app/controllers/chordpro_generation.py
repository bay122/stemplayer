import os
import json
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox
from app.ui.chordpro_editor import ChordProEditor
from app.services.chord_analysis import ChordAnalysisThread
from app.services.openrouter_service import OpenRouterLLMThread


class ChordProGenerationMixin:
    def _ensure_openrouter_api_key(self):
        settings = QSettings("StemPlayer", "StemPlayer")
        api_key = settings.value("openrouter_api_key", "")
        if not api_key:
            api_key, ok = QInputDialog.getText(self, "API Key de OpenRouter",
                                                 "Ingresa tu API Key de OpenRouter:",
                                                 QLineEdit.Password)
            if not ok or not api_key.strip():
                return None
            api_key = api_key.strip()
            settings.setValue("openrouter_api_key", api_key)
        return api_key

    def _prompt_lyrics_generation_mode(self):
        reply = QMessageBox.question(self, "Letra de la canción",
                                       "¿Quieres que la IA busque la letra automáticamente?",
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if reply == QMessageBox.Cancel:
            return None
        if reply == QMessageBox.No:
            lyrics, ok = QInputDialog.getMultiLineText(self, "Letra de la canción",
                                                         "Pega la letra de la canción:")
            if not ok:
                return None
            if not lyrics.strip():
                QMessageBox.warning(self, "Error", "La letra no puede estar vacía.")
                return self._prompt_lyrics_generation_mode()
            return lyrics
        return ""

    def _set_generation_feedback(self, status: str, progress: int = -1):
        self.bg_status_label.setText(status)
        self.bg_status_label.setVisible(True)
        if progress >= 0:
            self.progress_bar.setValue(progress)
            self.progress_bar.setVisible(True)

    def _on_chord_analysis_progress(self, msg: str):
        self._set_generation_feedback(msg)

    def _on_chord_analysis_progress_pct(self, pct: int):
        self.progress_bar.setValue(pct)
        self.progress_bar.setVisible(True)

    def _on_openrouter_progress(self, msg: str):
        self._set_generation_feedback(msg)

    def _on_generate_chordpro_clicked(self):
        if self.state.current_song_source != "library" or not self.state.current_song_name:
            QMessageBox.warning(self, "Error", "Debes guardar la canción en la librería primero.")
            return

        api_key = self._ensure_openrouter_api_key()
        if api_key is None:
            return

        lyrics_text = self._prompt_lyrics_generation_mode()
        if lyrics_text is None:
            return

        self._pending_lyrics_text = lyrics_text
        self._pending_api_key = api_key

        meta = self.lib_mgr.get_metadata(self.state.current_song_name)
        sections = meta.get("sections") if meta else None
        chords_by_section = meta.get("chords_by_section") if meta else None
        has_valid_sections = isinstance(sections, list) and len(sections) > 0
        has_valid_chords = isinstance(chords_by_section, dict) and len(chords_by_section) > 0

        if has_valid_sections and has_valid_chords:
            self._start_openrouter_thread(sections, chords_by_section, api_key)
            return

        self._set_generation_feedback("Iniciando análisis musical...", 5)

        new_thread = ChordAnalysisThread(
            os.path.join(self.lib_mgr.library_path, self.state.current_song_name),
            self.state.stems, self.state.mix_sr
        )
        new_thread.progress.connect(self._on_chord_analysis_progress)
        new_thread.progress_pct.connect(self._on_chord_analysis_progress_pct)
        new_thread.finished_analysis.connect(self._on_chord_analysis_finished)
        new_thread.error.connect(self._on_chord_generation_error)
        self.threads.safe_replace('chord_analysis_thread', new_thread)
        self.threads.safe_start(self.threads.chord_analysis_thread)

    def _on_chord_analysis_finished(self, result: dict):
        sender = self.sender()
        if sender is not None and sender is not self.threads.chord_analysis_thread:
            return

        self.threads.chord_analysis_thread = None

        sections = result.get("sections", [])
        chords_by_section = result.get("chords_by_section", {})

        if self.state.current_song_source == "library" and self.state.current_song_name:
            meta = self.lib_mgr.get_metadata(self.state.current_song_name)
            if meta:
                meta["sections"] = sections
                meta["chords_by_section"] = chords_by_section
                self.lib_mgr.save_metadata(self.state.current_song_name, meta)

        api_key = getattr(self, '_pending_api_key', QSettings("StemPlayer", "StemPlayer").value("openrouter_api_key", ""))
        self._start_openrouter_thread(sections, chords_by_section, api_key)

    def _on_chord_generation_error(self, msg: str):
        self.bg_status_label.setVisible(False)
        self.progress_bar.setVisible(False)
        self.threads.chord_analysis_thread = None
        self.threads.openrouter_thread = None
        QMessageBox.critical(self, "Error", msg)

    def _start_openrouter_thread(self, sections: list, chords_by_section: dict, api_key: str):
        self._set_generation_feedback("Generando sheet de acordes con IA...", 50)

        lyrics_text = getattr(self, '_pending_lyrics_text', '')
        use_web_search = not bool(lyrics_text)

        new_thread = OpenRouterLLMThread(
            song_title=self.state.current_song_name,
            artist=self.state.current_song_artist,
            sections=sections,
            chords_by_section=chords_by_section,
            global_key=self.state.detected_key,
            bpm=self.state.detected_bpm,
            api_key=api_key,
            lyrics_text=lyrics_text,
            use_web_search=use_web_search,
        )
        new_thread.progress.connect(self._on_openrouter_progress)
        new_thread.finished_chordpro_and_sync.connect(self._on_openrouter_finished)
        new_thread.error.connect(self._on_chord_generation_error)
        self.threads.safe_replace('openrouter_thread', new_thread)
        self.threads.safe_start(self.threads.openrouter_thread)

    def _on_openrouter_finished(self, chordpro_content: str, sync_data: dict):
        sender = self.sender()
        if sender is not None and sender is not self.threads.openrouter_thread:
            return

        self.bg_status_label.setVisible(False)
        self.progress_bar.setVisible(False)

        song_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
        chopro_path = os.path.join(song_folder, f"{self.state.current_song_name}.chopro")
        sync_path = os.path.join(song_folder, f"{self.state.current_song_name}.sync.json")

        try:
            with open(chopro_path, 'w', encoding='utf-8') as f:
                f.write(chordpro_content)
        except OSError as exc:
            self._on_chord_generation_error(
                "OpenRouter respondió correctamente, pero no se pudo guardar el archivo .chopro."
            )
            return

        if sync_data.get("sections"):
            try:
                with open(sync_path, 'w', encoding='utf-8') as f:
                    json.dump(sync_data, f, indent=2, ensure_ascii=False)
            except OSError:
                pass

        self._load_chordpro_preview()
        self._update_save_buttons()
        self.threads.openrouter_thread = None
        self.status_label.setText("Sheet de acordes generado.")

    def _on_edit_chordpro_clicked(self):
        if not self.state.current_song_name:
            return
        song_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
        chopro_path = os.path.join(song_folder, f"{self.state.current_song_name}.chopro")

        if not os.path.exists(chopro_path):
            QMessageBox.warning(self, "Error", "No se encontró el archivo ChordPro.")
            return

        self.chordpro_window = ChordProEditor(chopro_path)
        self.chordpro_window.setWindowTitle(f"ChordPro Editor — {self.state.current_song_name}")
        self.chordpro_window.resize(900, 700)
        screen = self.screen().geometry() if hasattr(self, 'screen') else None
        if screen:
            self.chordpro_window.move(
                (screen.width() - 900) // 2,
                (screen.height() - 700) // 2
            )

        def _on_chordpro_saved():
            self._load_chordpro_preview()
            self.status_label.setText("ChordPro guardado.")

        self.chordpro_window.saved.connect(_on_chordpro_saved)
        self.chordpro_window.show()
