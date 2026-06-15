"""Gestor de configuración global persistente."""

import json
import os
from pathlib import Path

CONFIG_FILE = "config.json"


def get_default_config() -> dict:
    return {
        "library_path": "",
        "setlists": [],
        "window": {
            "width": 1200,
            "height": 800,
        },
    }


def load_config() -> dict:
    """Carga la configuración global desde config.json."""
    if not os.path.exists(CONFIG_FILE):
        config = get_default_config()
        save_config(config)
        return config
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    # Asegurar campos por defecto
    defaults = get_default_config()
    for key, value in defaults.items():
        if key not in config:
            config[key] = value
    return config


def save_config(config: dict):
    """Guarda la configuración global en config.json."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_library_path(config: dict) -> str:
    """Devuelve la ruta de la librería o cadena vacía."""
    return config.get("library_path", "")


def set_library_path(config: dict, path: str):
    config["library_path"] = path
    save_config(config)


def get_setlists(config: dict) -> list:
    return config.get("setlists", [])


def add_setlist(config: dict, name: str, song_ids: list):
    config["setlists"].append({"name": name, "song_ids": song_ids})
    save_config(config)


def update_setlist(config: dict, index: int, name: str, song_ids: list):
    if 0 <= index < len(config["setlists"]):
        config["setlists"][index] = {"name": name, "song_ids": song_ids}
        save_config(config)


def remove_setlist(config: dict, index: int):
    if 0 <= index < len(config["setlists"]):
        config["setlists"].pop(index)
        save_config(config)
