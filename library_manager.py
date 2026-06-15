"""Gestor de la librería de canciones."""

import json
import os
import shutil
from pathlib import Path
from typing import Optional


def get_library_songs(library_path: str) -> list:
    """Devuelve lista de carpetas (canciones) en la librería."""
    if not library_path or not os.path.exists(library_path):
        return []
    songs = []
    for item in sorted(os.listdir(library_path)):
        item_path = os.path.join(library_path, item)
        if os.path.isdir(item_path):
            songs.append(item)
    return songs


def get_song_metadata(library_path: str, song_name: str) -> Optional[dict]:
    """Carga el .json de metadatos de una canción."""
    json_path = os.path.join(library_path, song_name, f"{song_name}.json")
    if not os.path.exists(json_path):
        # Auto-crear si no existe
        stems = get_song_stem_files(library_path, song_name)
        stem_dicts = [{
            "name": os.path.splitext(s)[0],
            "category": "Other",
            "volume": 1.0,
            "pan": 0.0,
            "muted": False,
            "solo": False,
            "fx_enabled": True
        } for s in stems]
        metadata = create_default_metadata(name=song_name, detected_key="", detected_bpm=0, stems=stem_dicts)
        save_song_metadata(library_path, song_name, metadata)
        return metadata
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_song_metadata(library_path: str, song_name: str, metadata: dict):
    """Guarda el .json de metadatos de una canción."""
    song_folder = os.path.join(library_path, song_name)
    os.makedirs(song_folder, exist_ok=True)
    json_path = os.path.join(song_folder, f"{song_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def get_song_stem_files(library_path: str, song_name: str) -> list:
    """Devuelve lista de archivos de stems de una canción en la librería."""
    song_folder = os.path.join(library_path, song_name)
    if not os.path.exists(song_folder):
        return []
    stems = []
    for f in os.listdir(song_folder):
        if f.lower().endswith((".wav", ".mp3", ".m4a", ".flac")):
            stems.append(f)
    return sorted(stems)


def copy_folder_to_library(source_folder: str, library_path: str, song_name: str) -> str:
    """Copia una carpeta de stems a la librería. Devuelve la ruta destino."""
    dest_folder = os.path.join(library_path, song_name)
    if os.path.exists(dest_folder):
        # Si existe, generar nombre único
        i = 1
        while os.path.exists(dest_folder):
            dest_folder = os.path.join(library_path, f"{song_name}_{i}")
            i += 1
    shutil.copytree(source_folder, dest_folder)
    return dest_folder


def create_default_metadata(name: str, detected_key: str = "", detected_bpm: int = 0,
                            pitch_shift: int = 0, tempo_ratio: float = 1.0,
                            count_in_bars: int = 0, click_during_playback: bool = False,
                            metronome_volume: float = 0.5, master_volume: float = 1.0,
                            metronome_pan: float = 0.0, artist: str = "",
                            duration: str = "00:00", click_offset_samples: int = 0,
                            stems: list = None) -> dict:
    """Crea el diccionario de metadatos por defecto."""
    return {
        "name": name,
        "artist": artist,
        "detected_key": detected_key,
        "detected_bpm": detected_bpm,
        "pitch_shift": pitch_shift,
        "tempo_ratio": tempo_ratio,
        "count_in_bars": count_in_bars,
        "click_offset_samples": click_offset_samples,
        "duration": duration,
        "click_during_playback": click_during_playback,
        "metronome_volume": metronome_volume,
        "metronome_pan": metronome_pan,
        "master_volume": master_volume,
        "stems": stems if stems is not None else [],
    }


def rename_song_folder(library_path: str, old_name: str, new_name: str) -> bool:
    """Renombra una carpeta de canción en la librería."""
    old_path = os.path.join(library_path, old_name)
    new_path = os.path.join(library_path, new_name)
    if not os.path.exists(old_path) or os.path.exists(new_path):
        return False
    os.rename(old_path, new_path)
    # Renombrar el JSON interno
    old_json = os.path.join(new_path, f"{old_name}.json")
    new_json = os.path.join(new_path, f"{new_name}.json")
    if os.path.exists(old_json):
        os.rename(old_json, new_json)
    return True


def delete_song_folder(library_path: str, song_name: str):
    """Elimina una canción de la librería."""
    song_path = os.path.join(library_path, song_name)
    if os.path.exists(song_path):
        shutil.rmtree(song_path)


def add_stem_to_song(library_path: str, song_name: str, source_file: str) -> str:
    """Copia un archivo de stem a la carpeta de una canción en la librería."""
    dest_folder = os.path.join(library_path, song_name)
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


def remove_stem_from_song(library_path: str, song_name: str, stem_file: str):
    """Elimina un archivo de stem de una canción en la librería."""
    stem_path = os.path.join(library_path, song_name, stem_file)
    if os.path.exists(stem_path):
        os.remove(stem_path)
