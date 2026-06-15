import json
import os
import shutil
from pathlib import Path
from typing import Optional
from app.data.metadata import build_metadata


class LibraryManager:
    """Gestor de la librería de canciones con estado."""

    def __init__(self, library_path: str = ""):
        self.library_path = library_path

    def set_library_path(self, path: str):
        self.library_path = path

    # ---- Canciones ----

    def get_songs(self) -> list:
        if not self.library_path or not os.path.exists(self.library_path):
            return []
        songs = []
        for item in sorted(os.listdir(self.library_path)):
            item_path = os.path.join(self.library_path, item)
            if os.path.isdir(item_path):
                songs.append(item)
        return songs

    # ---- Metadatos ----

    def get_metadata(self, song_name: str) -> Optional[dict]:
        json_path = self._metadata_path(song_name)
        if not os.path.exists(json_path):
            stems = self.get_stem_files(song_name)
            stem_dicts = [{
                "name": os.path.splitext(s)[0],
                "category": "Other",
                "volume": 1.0,
                "pan": 0.0,
                "muted": False,
                "solo": False,
                "fx_enabled": True
            } for s in stems]
            duration = self._compute_folder_duration(song_name)
            metadata = build_metadata(name=song_name, detected_key="", detected_bpm=0, stems=stem_dicts,
                                      duration=duration)
            self.save_metadata(song_name, metadata)
            return metadata
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _compute_folder_duration(self, song_name: str) -> str:
        import soundfile as sf
        song_folder = os.path.join(self.library_path, song_name)
        max_frames = 0
        sr = 44100
        for fname in self.get_stem_files(song_name):
            try:
                info = sf.info(os.path.join(song_folder, fname))
                frames = info.frames
                sr = info.samplerate
                if frames > max_frames:
                    max_frames = frames
                    sr = info.samplerate
            except Exception:
                pass
        if max_frames > 0:
            total_secs = max_frames / sr
            return f"{int(total_secs // 60):02d}:{int(total_secs % 60):02d}"
        return "00:00"

    def save_metadata(self, song_name: str, metadata: dict):
        song_folder = os.path.join(self.library_path, song_name)
        os.makedirs(song_folder, exist_ok=True)
        json_path = self._metadata_path(song_name)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def _metadata_path(self, song_name: str) -> str:
        return os.path.join(self.library_path, song_name, f"{song_name}.json")

    # ---- Stems ----

    def get_stem_files(self, song_name: str) -> list:
        song_folder = os.path.join(self.library_path, song_name)
        if not os.path.exists(song_folder):
            return []
        stems = []
        for f in os.listdir(song_folder):
            if f.lower().endswith((".wav", ".mp3", ".m4a", ".flac")):
                stems.append(f)
        return sorted(stems)

    # ---- Operaciones de disco ----

    def copy_folder(self, source_folder: str, song_name: str) -> str:
        dest_folder = os.path.join(self.library_path, song_name)
        if os.path.exists(dest_folder):
            i = 1
            while os.path.exists(dest_folder):
                dest_folder = os.path.join(self.library_path, f"{song_name}_{i}")
                i += 1
        shutil.copytree(source_folder, dest_folder)
        return dest_folder

    def rename_song(self, old_name: str, new_name: str) -> bool:
        old_path = os.path.join(self.library_path, old_name)
        new_path = os.path.join(self.library_path, new_name)
        if not os.path.exists(old_path) or os.path.exists(new_path):
            return False
        os.rename(old_path, new_path)
        old_json = os.path.join(new_path, f"{old_name}.json")
        new_json = os.path.join(new_path, f"{new_name}.json")
        if os.path.exists(old_json):
            os.rename(old_json, new_json)
        return True

    def delete_song(self, song_name: str):
        song_path = os.path.join(self.library_path, song_name)
        if os.path.exists(song_path):
            shutil.rmtree(song_path)

    def add_stem(self, song_name: str, source_file: str) -> str:
        dest_folder = os.path.join(self.library_path, song_name)
        os.makedirs(dest_folder, exist_ok=True)
        dest_file = os.path.join(dest_folder, os.path.basename(source_file))
        if os.path.exists(dest_file):
            base, ext = os.path.splitext(os.path.basename(source_file))
            i = 1
            while os.path.exists(dest_file):
                dest_file = os.path.join(dest_folder, f"{base}_{i}{ext}")
                i += 1
        shutil.copy2(source_file, dest_file)
        return dest_file

    def remove_stem(self, song_name: str, stem_file: str):
        stem_path = os.path.join(self.library_path, song_name, stem_file)
        if os.path.exists(stem_path):
            os.remove(stem_path)


# ---- Conveniencia: API de funciones con singleton global ----
_lib_manager = LibraryManager()


def get_library_songs(library_path: str) -> list:
    _lib_manager.set_library_path(library_path)
    return _lib_manager.get_songs()


def get_song_metadata(library_path: str, song_name: str) -> dict:
    _lib_manager.set_library_path(library_path)
    return _lib_manager.get_metadata(song_name)


def save_song_metadata(library_path: str, song_name: str, metadata: dict):
    _lib_manager.set_library_path(library_path)
    _lib_manager.save_metadata(song_name, metadata)


def rename_song_folder(library_path: str, old_name: str, new_name: str) -> bool:
    _lib_manager.set_library_path(library_path)
    return _lib_manager.rename_song(old_name, new_name)


def delete_song_folder(library_path: str, song_name: str):
    _lib_manager.set_library_path(library_path)
    _lib_manager.delete_song(song_name)
