import os
import sys


def get_base_path():
    """Obtiene la ruta base del ejecutable o del script."""
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_project_root():
    """Obtiene la raíz del proyecto (donde están assets/, main.py, etc.).

    En desarrollo, apunta al directorio que contiene la carpeta `app/`.
    En un build de PyInstaller, apunta a la raíz del bundle (_MEIPASS) que
    también contiene los assets/.
    """
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_icons_dir():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, "icons")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "icons", "svgs")


def get_config_dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        path = os.path.join(base, "StemPlayer")
    elif sys.platform == "darwin":
        path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "StemPlayer")
    else:
        base = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
        path = os.path.join(base, "stemsplayer")
    os.makedirs(path, exist_ok=True)
    return path


def get_config_file():
    return os.path.join(get_config_dir(), "config.json")
