import os
import sys


def get_base_path():
    """Obtiene la ruta base del ejecutable o del script."""
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_icons_dir():
    return os.path.join(get_base_path(), "..", "..", "icons", "svgs")
