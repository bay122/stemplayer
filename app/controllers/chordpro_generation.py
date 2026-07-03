import os
import json
from PySide6.QtCore import QSettings, QThread, Signal
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDialogButtonBox
from app.ui.chordpro_editor import ChordProEditorWindow
from app.ui.sync_editor import SyncEditor
from app.services import create_sync_file
from app.services.chord_analysis import ChordAnalysisThread
from app.services.openrouter_service import (OpenRouterLLMThread, build_sync_prompt, _parse_sync_response)
from app.services.providers import get_available_providers, get_provider
from app.controllers.deck_sync import DeckStatusMixin


class SyncRegeneratorThread(QThread):
    finished = Signal(list)
    error = Signal(str)

    def __init__(self, audio, sr):
        super().__init__()
        self.audio = audio
        self.sr = sr
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            from app.services.whisper import transcribe_guide_audio
            sections = transcribe_guide_audio(self.audio, self.sr)
            if not self._is_cancelled:
                self.finished.emit(sections)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


class SyncAIRefinerThread(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, provider, model, api_key, sections, chordpro_content, song_title, artist):
        super().__init__()
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.sections = sections
        self.chordpro_content = chordpro_content
        self.song_title = song_title
        self.artist = artist
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            prompt = build_sync_prompt(
                song_title=self.song_title,
                artist=self.artist,
                sections=self.sections,
                chordpro_content=self.chordpro_content,
            )
            content = self.provider.chat_completion(
                prompt=prompt,
                model=self.model,
                api_key=self.api_key,
                temperature=0.1,
                max_tokens=1000,
                use_web_search=False,
                timeout=(20, 300),
            )
            if self._is_cancelled:
                return
            sync_data = _parse_sync_response(content)
            self.finished.emit(sync_data)
        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


_PROVIDER_SETTING = "ai/provider"
_API_KEY_TPL = "ai/api_key/{}"
_MODEL_TPL = "ai/model/{}"


class ChordProGenerationMixin(DeckStatusMixin):
    def _get_ai_config(self):
        settings = QSettings("StemPlayer", "StemPlayer")
        provider_id = settings.value(_PROVIDER_SETTING, "openrouter")
        api_key = settings.value(_API_KEY_TPL.format(provider_id), "")
        model = settings.value(_MODEL_TPL.format(provider_id), "")
        if not model:
            try:
                model = get_provider(provider_id).default_model
            except ValueError:
                model = ""
        return provider_id, api_key, model

    def _save_ai_config(self, provider_id: str, api_key: str, model: str):
        settings = QSettings("StemPlayer", "StemPlayer")
        settings.setValue(_PROVIDER_SETTING, provider_id)
        settings.setValue(_API_KEY_TPL.format(provider_id), api_key)
        if model:
            settings.setValue(_MODEL_TPL.format(provider_id), model)

    def _prompt_ai_config(self):
        providers = get_available_providers()
        provider_names = [p.display_name for p in providers]
        provider_ids = [p.id for p in providers]

        current_id, current_key, current_model = self._get_ai_config()
        current_idx = 0
        try:
            current_idx = provider_ids.index(current_id)
        except ValueError:
            pass

        dialog = QDialog(self)
        dialog.setWindowTitle("Configurar proveedor de IA")
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Selecciona el proveedor de IA:"))

        provider_combo = QComboBox()
        provider_combo.addItems(provider_names)
        provider_combo.setCurrentIndex(current_idx)
        layout.addWidget(provider_combo)

        layout.addWidget(QLabel("API Key:"))

        api_key_input = QLineEdit()
        api_key_input.setEchoMode(QLineEdit.Password)
        api_key_input.setPlaceholderText("Ingresa tu API Key...")
        api_key_input.setText(current_key)
        layout.addWidget(api_key_input)

        model_label = QLabel("Modelo (dejar vacio para usar el default):")
        layout.addWidget(model_label)

        model_input = QLineEdit()
        model_input.setPlaceholderText("Ej: gemini-2.5-flash-lite")
        model_input.setText(current_model)
        layout.addWidget(model_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return None, None, None

        idx = provider_combo.currentIndex()
        provider_id = provider_ids[idx]
        api_key = api_key_input.text().strip()
        model = model_input.text().strip()

        if not api_key:
            QMessageBox.warning(self, "Error", "La API Key no puede estar vacia.")
            return self._prompt_ai_config()

        self._save_ai_config(provider_id, api_key, model)
        return provider_id, api_key, model

    def _ensure_ai_config(self):
        provider_id, api_key, model = self._get_ai_config()
        if not api_key:
            return self._prompt_ai_config()
        return provider_id, api_key, model

    def _prompt_lyrics_generation_mode(self):
        reply = QMessageBox.question(self, "Letra de la cancion",
                                       "Quieres que la IA busque la letra automaticamente?",
                                       QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if reply == QMessageBox.Cancel:
            return None
        if reply == QMessageBox.No:
            lyrics, ok = QInputDialog.getMultiLineText(self, "Letra de la cancion",
                                                         "Pega la letra de la cancion:")
            if not ok:
                return None
            if not lyrics.strip():
                QMessageBox.warning(self, "Error", "La letra no puede estar vacia.")
                return self._prompt_lyrics_generation_mode()
            return lyrics
        return ""

    def _set_generation_feedback(self, status: str, progress: int = -1):
        self.bg_status_label.setText(status)
        self.bg_status_label.setVisible(True)
        self._sync_deck_bg_status(status, True)
        if progress >= 0:
            self.progress_bar.setValue(progress)
            self.progress_bar.setVisible(True)
            self._sync_deck_progress(progress, True)

    def _reset_generation_feedback(self):
        self.bg_status_label.setVisible(False)
        self._sync_deck_bg_status("", False)
        self.progress_bar.setVisible(False)
        self._sync_deck_progress(0, False)

    def _on_chord_analysis_progress(self, msg: str):
        self._set_generation_feedback(msg)

    def _on_chord_analysis_progress_pct(self, pct: int):
        self.progress_bar.setValue(pct)
        self.progress_bar.setVisible(True)
        self._sync_deck_progress(pct, True)

    def _on_ai_progress(self, msg: str):
        self._set_generation_feedback(msg)

    def _on_generate_chordpro_clicked(self):
        if self.state.current_song_source != "library" or not self.state.current_song_name:
            QMessageBox.warning(self, "Error", "Debes guardar la cancion en la libreria primero.")
            return

        provider_id, api_key, model = self._ensure_ai_config()
        if api_key is None:
            return

        lyrics_text = self._prompt_lyrics_generation_mode()
        if lyrics_text is None:
            return

        self._pending_lyrics_text = lyrics_text
        self._pending_api_key = api_key
        self._pending_provider_id = provider_id
        self._pending_model = model

        meta = self.lib_mgr.get_metadata(self.state.current_song_name)
        sections = meta.get("sections") if meta else None
        chords_by_section = meta.get("chords_by_section") if meta else None
        has_valid_sections = isinstance(sections, list) and len(sections) > 0
        has_valid_chords = isinstance(chords_by_section, dict) and len(chords_by_section) > 0

        if has_valid_sections and has_valid_chords:
            self._start_ai_thread(sections, chords_by_section, provider_id, api_key, model)
            return

        self._set_generation_feedback("Iniciando analisis musical...", 5)

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

            if sections:
                song_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
                sync_path = os.path.join(song_folder, f"{self.state.current_song_name}.sync.json")
                create_sync_file(sections, sync_path)

        provider_id = getattr(self, '_pending_provider_id', '')
        if not provider_id:
            provider_id, _, _ = self._get_ai_config()
        api_key = getattr(self, '_pending_api_key', '')
        if not api_key:
            _, api_key, _ = self._get_ai_config()
        model = getattr(self, '_pending_model', '')
        if not model:
            _, _, model = self._get_ai_config()

        self._start_ai_thread(sections, chords_by_section, provider_id, api_key, model)

    def _on_chord_generation_error(self, msg: str):
        sender = self.sender()
        if sender is not None:
            if sender is self.threads.chord_analysis_thread:
                self.threads.safe_replace('chord_analysis_thread', None)
            elif sender is self.threads.openrouter_thread:
                self.threads.safe_replace('openrouter_thread', None)
        self.bg_status_label.setVisible(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", msg)

    def _start_ai_thread(self, sections: list, chords_by_section: dict,
                         provider_id: str, api_key: str, model: str):
        self._set_generation_feedback("Generando sheet de acordes con IA...", 50)

        lyrics_text = getattr(self, '_pending_lyrics_text', '')
        use_web_search = not bool(lyrics_text)

        provider = get_provider(provider_id)

        new_thread = OpenRouterLLMThread(
            provider=provider,
            song_title=self.state.current_song_name,
            artist=self.state.current_song_artist,
            sections=sections,
            chords_by_section=chords_by_section,
            global_key=self.state.detected_key,
            bpm=self.state.detected_bpm,
            api_key=api_key,
            model=model or provider.default_model,
            lyrics_text=lyrics_text,
            use_web_search=use_web_search,
        )
        new_thread.progress.connect(self._on_ai_progress)
        new_thread.finished_chordpro_and_sync.connect(self._on_ai_finished)
        new_thread.error.connect(self._on_chord_generation_error)
        self.threads.safe_replace('openrouter_thread', new_thread)
        self.threads.safe_start(self.threads.openrouter_thread)

    def _on_ai_finished(self, chordpro_content: str, sync_data: dict):
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
                "El proveedor de IA respondio correctamente, pero no se pudo guardar el archivo .chopro."
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
        self.toggle_live_btn.setVisible(True)
        self.toggle_live_btn.setEnabled(True)
        self.threads.openrouter_thread = None
        self.status_label.setText("Sheet de acordes generado.")

    def _on_regenerate_sync_clicked(self):
        if not self.state.stems:
            QMessageBox.warning(self, "Error", "No hay stems cargados.")
            return

        stem_names = list(self.state.stems.keys())
        stem_name, ok = QInputDialog.getItem(
            self, "Regenerar Sync", "Selecciona la pista para transcribir:",
            stem_names, 0, False
        )
        if not ok or not stem_name:
            return

        stem_data = self.state.stems.get(stem_name)
        if stem_data is None:
            return

        self._set_generation_feedback(f"Transcribiendo '{stem_name}' con Whisper...", 50)

        self._sync_thread = SyncRegeneratorThread(stem_data["audio"], self.state.mix_sr)
        self._sync_thread.finished.connect(self._on_sync_regenerated)
        self._sync_thread.error.connect(self._on_sync_regeneration_error)
        self._sync_thread.start()

    def _on_sync_regenerated(self, sections: list):
        self._sync_thread = None
        self.bg_status_label.setVisible(False)
        self.progress_bar.setVisible(False)

        if not self.state.current_song_name:
            return

        song_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name) \
            if self.state.current_song_source == "library" else None
        if not song_folder or not os.path.isdir(song_folder):
            QMessageBox.warning(self, "Error", "La cancion debe estar guardada en la libreria.")
            return

        sync_path = os.path.join(song_folder, f"{self.state.current_song_name}.sync.json")
        chopro_path = os.path.join(song_folder, f"{self.state.current_song_name}.chopro")

        create_sync_file(sections, sync_path)

        if os.path.exists(chopro_path):
            provider_id, api_key, model = self._get_ai_config()
            if api_key:
                self._set_generation_feedback("Refinando sync con IA...", 75)
                try:
                    with open(chopro_path, 'r', encoding='utf-8') as f:
                        chordpro_content = f.read()
                except OSError:
                    chordpro_content = ""

                if chordpro_content.strip():
                    provider = get_provider(provider_id)
                    model_name = model or provider.default_model
                    ai_thread = SyncAIRefinerThread(
                        provider=provider,
                        model=model_name,
                        api_key=api_key,
                        sections=sections,
                        chordpro_content=chordpro_content,
                        song_title=self.state.current_song_name,
                        artist=self.state.current_song_artist,
                    )
                    ai_thread.finished.connect(self._on_sync_ai_refined)
                    ai_thread.error.connect(self._on_sync_ai_refine_error)
                    self.threads.safe_replace('sync_ai_thread', ai_thread)
                    self.threads.safe_start(self.threads.sync_ai_thread)
                    return

        self.live_display_widget.load_sync_data(chopro_path, sync_path)
        self.toggle_live_btn.setVisible(True)
        self.toggle_live_btn.setEnabled(True)
        self.status_label.setText("Sync regenerado correctamente.")

    def _on_sync_ai_refined(self, sync_data: dict):
        self.threads.safe_replace('sync_ai_thread', None)
        self.bg_status_label.setVisible(False)
        self.progress_bar.setVisible(False)

        if not self.state.current_song_name or self.state.current_song_source != "library":
            return

        song_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
        sync_path = os.path.join(song_folder, f"{self.state.current_song_name}.sync.json")
        chopro_path = os.path.join(song_folder, f"{self.state.current_song_name}.chopro")

        try:
            with open(sync_path, 'w', encoding='utf-8') as f:
                json.dump(sync_data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            QMessageBox.critical(self, "Error", f"No se pudo guardar sync.json:\n{e}")
            return

        self.live_display_widget.load_sync_data(chopro_path, sync_path)
        self.toggle_live_btn.setVisible(True)
        self.toggle_live_btn.setEnabled(True)
        self.status_label.setText("Sync regenerado y refinado con IA.")

    def _on_sync_ai_refine_error(self, msg: str):
        self.threads.safe_replace('sync_ai_thread', None)
        self.bg_status_label.setVisible(False)
        self.progress_bar.setVisible(False)

        if self.state.current_song_name and self.state.current_song_source == "library":
            song_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
            sync_path = os.path.join(song_folder, f"{self.state.current_song_name}.sync.json")
            chopro_path = os.path.join(song_folder, f"{self.state.current_song_name}.chopro")
            self.live_display_widget.load_sync_data(chopro_path, sync_path)
            self.toggle_live_btn.setVisible(True)
            self.toggle_live_btn.setEnabled(True)

        QMessageBox.warning(self, "Sync sin refinar",
            f"La IA no pudo refinar el sync:\n{msg}\n\nSe usara el sync basado en Whisper.")

    def _on_sync_regeneration_error(self, msg: str):
        self._sync_thread = None
        self.bg_status_label.setVisible(False)
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", f"No se pudo regenerar el sync:\n{msg}")

    def _on_edit_sync_clicked(self):
        if not self.state.current_song_name or self.state.current_song_source != "library":
            QMessageBox.warning(self, "Error", "No hay una cancion de la libreria abierta.")
            return

        song_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
        sync_path = os.path.join(song_folder, f"{self.state.current_song_name}.sync.json")

        if not os.path.exists(sync_path):
            QMessageBox.warning(self, "Error", "No se encontro el archivo sync.json.")
            return

        chopro_path = os.path.join(song_folder, f"{self.state.current_song_name}.chopro")

        self.sync_editor = SyncEditor(self, sync_path, chopro_path)
        self.sync_editor.show()

    def _on_edit_chordpro_clicked(self):
        if not self.state.current_song_name:
            return
        song_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
        chopro_path = os.path.join(song_folder, f"{self.state.current_song_name}.chopro")
        sync_path = os.path.join(song_folder, f"{self.state.current_song_name}.sync.json")
        if not os.path.exists(chopro_path):
            QMessageBox.warning(self, "Error", "No se encontro el archivo ChordPro.")
            return
        self.chordpro_window = ChordProEditorWindow(
            chopro_path=chopro_path,
            sync_path=sync_path if os.path.exists(sync_path) else None,
            main_window=self,
            parent=self,
        )
        self.chordpro_window.saved.connect(self._on_chordpro_saved)
        self.chordpro_window.show()

    def _on_chordpro_saved(self):
        self._load_chordpro_preview()
        self.status_label.setText("ChordPro guardado.")
