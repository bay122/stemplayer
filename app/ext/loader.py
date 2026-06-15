"""Carga dinámica de temas desde app/ext/themes/<nombre>/.

Cada tema es una subcarpeta dentro de ``app/ext/themes/`` que debe
contener al menos un archivo ``theme.py`` con una variable ``theme``
que sea una instancia de ``app.ui.theme.Theme``.

Opcionalmente puede contener:

* ``layout.py`` → debe exponer una función ``apply_layout(window)``
  que recibe la instancia de ``StemPlayer`` y puede modificar la UI
  (reordenar widgets, añadir secciones nuevas, etc.).

* Cualquier otro módulo Python necesario para los componentes que
  ``layout.py`` o ``theme.py`` importen.
"""

import importlib.util
import os
import sys

from app.ui.theme import Theme, DARK_THEME

_THEMES_DIR = os.path.join(os.path.dirname(__file__), "themes")


def load_theme(name: str) -> Theme:
    """Carga el tema ``name`` desde ``ext/themes/<name>/theme.py``.

    Si la carpeta o el archivo no existen, o el módulo no expone
    una variable ``theme`` válida, se devuelve ``DARK_THEME``.
    """
    theme_dir = os.path.join(_THEMES_DIR, name)
    theme_py = os.path.join(theme_dir, "theme.py")

    if not os.path.isdir(theme_dir) or not os.path.isfile(theme_py):
        print(f"[themes] Tema '{name}' no encontrado en {theme_py}. Usando DARK_THEME.")
        return DARK_THEME

    spec = importlib.util.spec_from_file_location(f"_ext_theme_{name}", theme_py)
    mod = importlib.util.module_from_spec(spec)

    # Agregar la carpeta del tema a sys.path para que pueda hacer
    # imports relativos a otros módulos que incluya (ej. widgets propios).
    if theme_dir not in sys.path:
        sys.path.insert(0, theme_dir)

    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        print(f"[themes] Error al cargar '{name}/theme.py': {exc}. Usando DARK_THEME.")
        return DARK_THEME

    if not hasattr(mod, "theme") or not isinstance(mod.theme, Theme):
        print(f"[themes] '{name}/theme.py' no expone una variable 'theme' de tipo Theme. Usando DARK_THEME.")
        return DARK_THEME

    print(f"[themes] Tema '{name}' cargado correctamente.")
    return mod.theme


def load_layout(name: str):
    """Carga el módulo ``layout.py`` del tema ``name``, o ``None``.

    El módulo debe exponer una función ``apply_layout(window)``
    que será invocada por ``main.py`` después de construir la
    ventana principal.
    """
    layout_py = os.path.join(_THEMES_DIR, name, "layout.py")

    if not os.path.isfile(layout_py):
        return None

    spec = importlib.util.spec_from_file_location(f"_ext_layout_{name}", layout_py)
    mod = importlib.util.module_from_spec(spec)

    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        print(f"[themes] Error al cargar '{name}/layout.py': {exc}. Ignorando layout.")
        return None

    if not hasattr(mod, "apply_layout"):
        print(f"[themes] '{name}/layout.py' no expone 'apply_layout(window)'. Ignorando layout.")
        return None

    print(f"[themes] Layout del tema '{name}' cargado.")
    return mod
