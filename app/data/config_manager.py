import json
import os

CONFIG_FILE = "config.json"


class ConfigManager:
	"""Gestor de configuración global persistente con soporte multi-librería."""

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
		if "library_path" in config or "setlists" in config:
			config = self._migrate_old_format(config)
		defaults = self._defaults()
		for key, value in defaults.items():
			if key not in config:
				config[key] = value
		for lib in config.get("libraries", []):
			for lkey, lvalue in defaults["libraries"][0].items():
				if lkey not in lib:
					lib[lkey] = lvalue
		return config

	def _migrate_old_format(self, old: dict) -> dict:
		return {
			"libraries": [
				{
					"name": "Librería",
					"path": old.get("library_path", ""),
					"last_used": True,
					"last_setlist": "",
					"recent_played": [],
					"favorites": [],
					"setlists": old.get("setlists", []),
					"collapsed_sections": {},
				}
			],
			"window": old.get("window", {"width": 1200, "height": 800}),
			"stem_filters": old.get("stem_filters", {
				"click_patterns": ["click", "metro"],
				"guide_patterns": ["guide", "cue", "guia"],
				"no_fx_patterns": ["drum", "drums", "bateria", "batería"],
			}),
			"stream_port": old.get("stream_port", 8080),
		}

	def _save(self, config: dict = None):
		if config is None:
			config = self.config
		with open(self.config_file, "w", encoding="utf-8") as f:
			json.dump(config, f, indent=2, ensure_ascii=False)

	@staticmethod
	def _defaults() -> dict:
		return {
			"libraries": [
				{
					"name": "Librería",
					"path": "",
					"last_used": True,
					"last_setlist": "",
					"recent_played": [],
					"favorites": [],
					"setlists": [],
					"collapsed_sections": {},
				}
			],
			"window": {
				"width": 1200,
				"height": 800,
			},
			"stem_filters": {
				"click_patterns": ["click", "metro"],
				"guide_patterns": ["guide", "cue", "guia"],
				"no_fx_patterns": ["drum", "drums", "bateria", "batería"],
			},
			"stream_port": 8080,
			"splash_muted": False,
			"category_colors": {
				"Vocals":     "#FF5555",
				"Drums":      "#FFAA00",
				"Percussion": "#FF6644",
				"Bass":       "#FFCC00",
				"Guitars":    "#55CC55",
				"Keys":       "#5555AA",
				"Strings":    "#00BFFF",
				"Brass":      "#FF8800",
				"Winds":      "#88CCFF",
				"Synths":     "#CC88FF",
				"FX":         "#888888",
				"Ref":        "#666666",
				"Other":      "#AAAAAA",
			},
		}

	# ---- API pública ----

	def reload(self):
		self.config = self._load()

	def save(self):
		self._save()

	# ---- Librerías ----

	def get_libraries(self) -> list:
		return self.config.get("libraries", [])

	def _active_lib(self) -> dict:
		for lib in self.config.get("libraries", []):
			if lib.get("last_used"):
				return lib
		libraries = self.config.get("libraries", [])
		if libraries:
			libraries[0]["last_used"] = True
			return libraries[0]
		return None

	def get_library_path(self) -> str:
		lib = self._active_lib()
		return lib["path"] if lib else ""

	def set_library_path(self, path: str):
		lib = self._active_lib()
		if lib:
			lib["path"] = path
			self._save()

	def get_active_library(self) -> dict:
		return self._active_lib()

	def set_active_library(self, index: int):
		for i, lib in enumerate(self.config.get("libraries", [])):
			lib["last_used"] = (i == index)
		self._save()

	def add_library(self, name: str, path: str) -> int:
		for lib in self.config.get("libraries", []):
			lib["last_used"] = False
		self.config.setdefault("libraries", []).append({
			"name": name,
			"path": path,
			"last_used": True,
			"last_setlist": "",
			"recent_played": [],
			"favorites": [],
			"setlists": [],
		})
		self._save()
		return len(self.config["libraries"]) - 1

	def remove_library(self, index: int):
		libraries = self.config.get("libraries", [])
		if 0 <= index < len(libraries):
			libraries.pop(index)
			if libraries and not any(l.get("last_used") for l in libraries):
				libraries[0]["last_used"] = True
			self._save()

	# ---- Setlists (operan sobre la librería activa) ----

	def get_setlists(self) -> list:
		lib = self._active_lib()
		return lib["setlists"] if lib else []

	def add_setlist(self, name: str, song_ids: list):
		lib = self._active_lib()
		if lib:
			lib["setlists"].append({"name": name, "song_ids": song_ids})
			self._save()

	def update_setlist(self, index: int, name: str, song_ids: list):
		lib = self._active_lib()
		if lib and 0 <= index < len(lib["setlists"]):
			lib["setlists"][index] = {"name": name, "song_ids": song_ids}
			self._save()

	def remove_setlist(self, index: int):
		lib = self._active_lib()
		if lib and 0 <= index < len(lib["setlists"]):
			lib["setlists"].pop(index)
			self._save()

	# ---- Favoritos ----

	def get_favorites(self) -> list:
		lib = self._active_lib()
		return lib.get("favorites", []) if lib else []

	def add_favorite(self, song_name: str):
		lib = self._active_lib()
		if lib and song_name not in lib.get("favorites", []):
			lib.setdefault("favorites", []).append(song_name)
			self._save()

	def remove_favorite(self, song_name: str):
		lib = self._active_lib()
		if lib:
			favs = lib.get("favorites", [])
			if song_name in favs:
				favs.remove(song_name)
				self._save()

	def is_favorite(self, song_name: str) -> bool:
		lib = self._active_lib()
		return song_name in lib.get("favorites", []) if lib else False

	# ---- Recientes ----

	def get_recent_played(self) -> list:
		lib = self._active_lib()
		return lib.get("recent_played", []) if lib else []

	def add_recent_played(self, song_name: str):
		lib = self._active_lib()
		if lib:
			recent = lib.setdefault("recent_played", [])
			if song_name in recent:
				recent.remove(song_name)
			recent.insert(0, song_name)
			if len(recent) > 20:
				recent[:] = recent[:20]
			self._save()

	# ---- Collapsed sections ----

	def get_collapsed_sections(self) -> dict:
		lib = self._active_lib()
		return lib.get("collapsed_sections", {}) if lib else {}

	def set_collapsed_section(self, section_id: str, collapsed: bool):
		lib = self._active_lib()
		if lib:
			lib.setdefault("collapsed_sections", {})[section_id] = collapsed
			self._save()

	# ---- Stem filters ----

	def get_stem_filters(self) -> dict:
		return self.config.get("stem_filters", self._defaults()["stem_filters"])

	def set_stem_filters(self, filters: dict):
		self.config["stem_filters"] = filters
		self._save()

	# ---- Stream ----

	def get_stream_port(self) -> int:
		return self.config.get("stream_port", 8080)

	def set_stream_port(self, port: int):
		self.config["stream_port"] = port
		self._save()

	# ---- Splash ----

	def get_splash_muted(self) -> bool:
		return self.config.get("splash_muted", False)

	def set_splash_muted(self, muted: bool):
		self.config["splash_muted"] = muted
		self._save()

	# ---- Colores de categorías ----

	def get_category_colors(self) -> dict:
		defaults = self._defaults()["category_colors"]
		stored = self.config.get("category_colors", {})
		merged = dict(defaults)
		merged.update(stored)
		return merged

	def set_category_colors(self, colors: dict):
		self.config["category_colors"] = dict(colors)
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
		for lib in config.get("libraries", []):
			if lib.get("last_used"):
				return lib.get("path", "")
		return config.get("libraries", [{}])[0].get("path", "") if config.get("libraries") else ""
	return _manager.get_library_path()


def set_library_path(config: dict, path: str):
	lib = None
	for l in config.get("libraries", []):
		if l.get("last_used"):
			lib = l
			break
	if not lib and config.get("libraries"):
		lib = config["libraries"][0]
	if lib:
		old_path = lib.get("path", "")
		lib["path"] = path
		if path != old_path:
			lib["setlists"] = []
	_manager.config = config
	_manager.save()


def get_setlists(config: dict = None) -> list:
	if config is not None:
		for lib in config.get("libraries", []):
			if lib.get("last_used"):
				return lib.get("setlists", [])
		return config.get("libraries", [{}])[0].get("setlists", []) if config.get("libraries") else []
	return _manager.get_setlists()


def add_setlist(config: dict, name: str, song_ids: list):
	lib = None
	for l in config.get("libraries", []):
		if l.get("last_used"):
			lib = l
			break
	if not lib and config.get("libraries"):
		lib = config["libraries"][0]
	if lib:
		lib.setdefault("setlists", []).append({"name": name, "song_ids": song_ids})
		_manager.config = config
		_manager.save()


def update_setlist(config: dict, index: int, name: str, song_ids: list):
	lib = None
	for l in config.get("libraries", []):
		if l.get("last_used"):
			lib = l
			break
	if lib and 0 <= index < len(lib.get("setlists", [])):
		lib["setlists"][index] = {"name": name, "song_ids": song_ids}
		_manager.config = config
		_manager.save()


def remove_setlist(config: dict, index: int):
	lib = None
	for l in config.get("libraries", []):
		if l.get("last_used"):
			lib = l
			break
	if lib and 0 <= index < len(lib.get("setlists", [])):
		lib["setlists"].pop(index)
		_manager.config = config
		_manager.save()
