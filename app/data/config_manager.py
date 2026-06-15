import json
import os

CONFIG_FILE = "config.json"


class ConfigManager:
    """Gestor de configuración global persistente con estado."""

    def __init__(self, config_file: str = CONFIG_FILE):
        self.config_file = config_file
        self.config = self._load()

    # ---- Internos ----

    def _load(self) -> dict:
        if not os.path.exists(self.config_file):
            config = self._defaults()
            self._save(config)
            return config
        with open(self.config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        defaults = self._defaults()
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
        return config

    def _save(self, config: dict = None):
        if config is None:
            config = self.config
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _defaults() -> dict:
        return {
            "library_path": "",
            "setlists": [],
            "window": {
                "width": 1200,
                "height": 800,
            },
        }

    # ---- API pública ----

    def reload(self):
        """Recarga la configuración desde disco."""
        self.config = self._load()

    def save(self):
        self._save()

    def get_library_path(self) -> str:
        return self.config.get("library_path", "")

    def set_library_path(self, path: str):
        old_path = self.config.get("library_path", "")
        self.config["library_path"] = path
        if path != old_path:
            self.config["setlists"] = []
        self._save()

    def get_setlists(self) -> list:
        return self.config.get("setlists", [])

    def add_setlist(self, name: str, song_ids: list):
        self.config["setlists"].append({"name": name, "song_ids": song_ids})
        self._save()

    def update_setlist(self, index: int, name: str, song_ids: list):
        if 0 <= index < len(self.config["setlists"]):
            self.config["setlists"][index] = {"name": name, "song_ids": song_ids}
            self._save()

    def remove_setlist(self, index: int):
        if 0 <= index < len(self.config["setlists"]):
            self.config["setlists"].pop(index)
            self._save()


# ---- Conveniencia: API de funciones con singleton global ----
_manager = ConfigManager()


def load_config() -> dict:
    _manager.reload()
    return _manager.config


def save_config(config: dict):
    _manager.config = config
    _manager.save()


def get_library_path(config: dict = None) -> str:
    if config is not None:
        return config.get("library_path", "")
    return _manager.get_library_path()


def set_library_path(config: dict, path: str):
    old_path = config.get("library_path", "")
    config["library_path"] = path
    if path != old_path:
        config["setlists"] = []
    _manager.config = config
    _manager.save()


def get_setlists(config: dict = None) -> list:
    if config is not None:
        return config.get("setlists", [])
    return _manager.get_setlists()


def add_setlist(config: dict, name: str, song_ids: list):
    config["setlists"].append({"name": name, "song_ids": song_ids})
    _manager.config = config
    _manager.save()


def update_setlist(config: dict, index: int, name: str, song_ids: list):
    if 0 <= index < len(config["setlists"]):
        config["setlists"][index] = {"name": name, "song_ids": song_ids}
        _manager.config = config
        _manager.save()


def remove_setlist(config: dict, index: int):
    if 0 <= index < len(config["setlists"]):
        config["setlists"].pop(index)
        _manager.config = config
        _manager.save()
