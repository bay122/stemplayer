# Sistema de Temas

La aplicación usa un **sistema de temas** que permite cambiar tanto la apariencia visual como la distribución de la interfaz. Los temas se definen como plugins autocontenidos dentro de `app/ext/themes/`.

---

## Arquitectura

```
app/
├── ext/
│   ├── __init__.py
│   ├── loader.py              ← Carga dinámica de temas
│   └── themes/
│       ├── theme2/            ← Tema solo visual
│       │   └── theme.py
│       └── theme3/            ← Tema con layout extendido
│           ├── theme.py
│           ├── layout.py
│           └── ... (módulos extra que el theme necesite)
│
└── ui/
    └── theme.py               ← Clase Theme + proxy `current` + apply_theme()
```

### Flujo de carga

1. `main.py` recibe `-theme <nombre>` vía `argparse`.
2. `app/ext/loader.py` busca la carpeta `app/ext/themes/<nombre>/`.
3. Carga `theme.py` del tema y obtiene la instancia `theme` (de tipo `Theme`).
4. Si existe `layout.py`, lo carga para su posterior aplicación.
5. `StemPlayer(theme=instancia)` se construye con el tema indicado.
6. Si hay `layout`, se ejecuta `layout.apply_layout(player)` **después** de construir la ventana.
7. Los widgets que importan `current` desde `app.ui.theme` ven automáticamente el tema activo sin re-importar.

---

## Tema solo visual (theme.py)

### Estructura mínima

```
app/ext/themes/mi-tema/
└── theme.py
```

### Contrato

`theme.py` debe exponer una variable **`theme`** que sea una instancia de `app.ui.theme.Theme`:

```python
from app.ui.theme import Theme

theme = Theme(
    BG_PRIMARY="#F5F5F5",
    BG_SECONDARY="#FFFFFF",
    TEXT_PRIMARY="#222222",
    TEXT_SECONDARY="#666666",
    ACCENT_PRIMARY="#0066CC",
    # ... resto de atributos que se quieran cambiar
)
```

**Solo es necesario redefinir los atributos que se deseen cambiar.** El resto conserva los valores de `DARK_THEME`.

### Lista completa de atributos

| Grupo | Atributo | Default | Uso |
|---|---|---|---|
| **Fondos** | `BG_PRIMARY` | `#121212` | Fondo principal |
| | `BG_SECONDARY` | `#1E1E1E` | Paneles, inputs |
| | `BG_TERTIARY` | `#2A2A2A` | Widgets de stems, menús |
| | `BG_DARK` | `#111111` | Karaoke / live display |
| | `BG_INPUT` | `#1E1E1E` | QLineEdit, QComboBox |
| | `BG_EDITOR` | `#1e1e1e` | Editor ChordPro |
| | `BG_MENU` | `#2A2A2A` | Fondos de menú contextual |
| **Texto** | `TEXT_PRIMARY` | `#FFFFFF` | Labels principales |
| | `TEXT_DEFAULT` | `#CCCCCC` | Texto general |
| | `TEXT_SECONDARY` | `#888888` | Texto secundario, timestamps |
| | `TEXT_MUTED` | `#AAAAAA` | Texto deshabilitado |
| | `TEXT_EDITOR` | `#d4d4d4` | Texto en editor |
| | `TEXT_DISABLED` | `#666666` | Next chord label |
| **Acentos** | `ACCENT_PRIMARY` | `#0078D7` | Azul principal (botones checked, slider) |
| | `ACCENT_PRIMARY_HOVER` | `#006ABB` | Hover del acento primario |
| | `ACCENT_CYAN` | `#00BFFF` | Label de key detectada |
| | `ACCENT_SUCCESS` | `#4CAF50` | Verde (acorde actual, meters OK) |
| | `ACCENT_DANGER` | `#F44336` | Rojo (meters peligro) |
| | `ACCENT_DANGER_ALT` | `#FF5555` | Rojo alternativo (close/delete) |
| | `ACCENT_WARNING` | `#FFC107` | Ámbar (meters warning) |
| | `ACCENT_INFO` | `#2196F3` | Azul info (botón PDF) |
| | `ACCENT_PURPLE` | `#5555AA` | Status de fondo (pre-carga) |
| | `ACCENT_SOLO` | `#FFAA00` | Naranja (botón Solo activo) |
| **Bordes** | `BORDER` | `#444444` | Borde estándar |
| | `BORDER_LIGHT` | `#555555` | Hover de botones |
| | `BORDER_DARK` | `#333333` | GroupBox, QListWidget |
| | `BORDER_ALT` | `#3e3e42` | Editor ChordPro |
| | `BORDER_WIDGET` | `#3A3A3A` | StemItemWidget |
| **Geometría** | `BORDER_RADIUS_SM` | `4px` | Inputs, botones pequeños |
| | `BORDER_RADIUS_MD` | `6px` | GroupBox, widgets grandes |
| | `FONT_FAMILY` | sistema | Tipografía global |
| | `FONT_SIZE_BASE` | `13px` | Tamaño de fuente base |
| | `FONT_MONO` | monospace | Timestamps, editor de código |
| **Estados** | `HOVER_BRIGHTEN` | `#444444` | Hover de botón genérico |
| | `HOVER_ACCENT` | `#106ebe` | Hover de botón acento |
| | `PRESSED_DARKEN` | `#222222` | Botón presionado |
| **SVG** | `SVG_ICON_DEFAULT` | `#AAAAAA` | Icono por defecto |
| | `SVG_ICON_MUTED` | `#888888` | Icono atenuado |
| | `SVG_ICON_ACTIVE` | `#FFFFFF` | Icono activo |
| | `SVG_ICON_DANGER` | `#FF5555` | Icono de peligro |
| | `SVG_ICON_SOLO` | `#FFAA00` | Icono de solo activo |
| **Overrides** | `custom_qss` | `""` | QSS adicional que se concatena al stylesheet global |
| | `icons_dir` | `""` | Ruta a carpeta con iconos SVG propios del theme |

### QSS personalizado (custom_qss)

El atributo `custom_qss` permite **sobrescribir o añadir reglas QSS** completas, no solo colores. El contenido se concatena al final de `global_stylesheet()`, por lo que las reglas aquí definidas tienen prioridad sobre las del theme base.

```python
theme = Theme(
    ...,
    custom_qss="""
        QPushButton {
            background-color: #182026;
            border: 1px solid #2e3942;
            border-radius: 8px;
            color: #e8ecf0;
        }
        QPushButton:hover {
            background-color: #1d262d;
        }
        QPushButton:checked {
            background-color: rgba(244, 183, 64, 36);
            border: 1px solid #f4b740;
            color: #f4b740;
        }
        QGroupBox {
            background-color: #131a1f;
            border: 1px solid #232c34;
            border-radius: 10px;
        }
        QScrollBar:vertical {
            background: transparent;
            width: 8px;
        }
        QScrollBar::handle:vertical {
            background: rgba(148, 163, 184, 102);
            border-radius: 4px;
        }
    """,
)
```

Se pueden sobrescribir todos los widgets Qt soportados por QSS: `QPushButton`, `QGroupBox`, `QLineEdit`, `QComboBox`, `QCheckBox`, `QListWidget`, `QProgressBar`, `QSpinBox`, `QScrollBar`, `QSlider`, `QMenu`, `QTextEdit`, etc.

### Iconos SVG propios (icons_dir)

Por defecto los iconos se cargan desde `icons/svgs/`. Un theme puede proporcionar su propia carpeta de iconos:

```python
import os

theme = Theme(
    ...,
    icons_dir=os.path.join(os.path.dirname(__file__), "icons"),
)
```

La estructura debe reflejar los nombres de archivo usados por la app (ej: `fad-play.svg`, `fad-stop.svg`, etc.). Los iconos que no existan en la carpeta del theme se cargarán desde la carpeta por defecto (ver `app/utils/paths.py`).

Los iconos deben ser SVG con `viewBox="0 0 24 24"` para que el coloreado dinámico funcione correctamente.

---

## Tema con layout extendido (theme.py + layout.py + módulos extra)

### Estructura

```
app/ext/themes/mi-tema/
├── theme.py                  ← Obligatorio (colores y estilos)
├── layout.py                 ← Opcional (modifica la UI)
├── widget_extra.py           ← Opcional (nuevos componentes)
└── ...                        ← Cualquier otro módulo .py
```

### Contrato de layout.py

Debe exponer una función **`apply_layout(window)`** que recibe la instancia de `StemPlayer` una vez construida:

```python
# app/ext/themes/mi-tema/layout.py
from PySide6.QtWidgets import QLabel, QVBoxLayout


def apply_layout(window):
    """Añade una sección de bienvenida al panel central."""
    label = QLabel("¡Bienvenido! Este texto lo agregó el theme.")
    label.setStyleSheet(f"color: {window.theme.TEXT_PRIMARY}; font-size: 18px;")

    # Los widgets existentes son accesibles como atributos de window
    # Ej: window.stems_layout, window.library_widget, etc.
    window.stems_layout.insertWidget(0, label)
```

### Añadir componentes nuevos

Si el layout introduce funcionalidades nuevas (no solo reordenar), los componentes deben definirse en módulos separados dentro de la misma carpeta del theme y ser importados por `layout.py`:

```
app/ext/themes/mi-tema/
├── theme.py
├── layout.py
├── equalizer_panel.py        ← Nuevo widget
└── equalizer_engine.py       ← Lógica del nuevo widget
```

```python
# app/ext/themes/mi-tema/layout.py
from PySide6.QtWidgets import QGroupBox, QVBoxLayout
from equalizer_panel import EqualizerPanel  # import del módulo local


def apply_layout(window):
    panel = EqualizerPanel(window.theme)
    # Agregarlo al panel derecho (right_layout existe como atributo)
    right_layout = window.centralWidget().layout().itemAt(2).widget().layout()
    right_layout.insertWidget(0, panel)
```

**Nota:** Los archivos `.py` adicionales del theme se importan con `import nombre_modulo` directamente porque `loader.py` agrega la carpeta del tema a `sys.path`.

---

## Cómo usar un theme

```bash
# Sin theme (usa DARK_THEME por defecto)
python main.py

# Con un tema específico
python main.py -theme theme2
python main.py -theme theme3
```

Si el nombre indicado no existe, se muestra un aviso en consola y se usa `DARK_THEME`.

---

## Cómo crear un theme nuevo

1. Crea la carpeta: `app/ext/themes/nombre-del-theme/`
2. Dentro, crea `theme.py` con una instancia de `Theme`:
   ```python
   from app.ui.theme import Theme

   theme = Theme(
       BG_PRIMARY="#1a1a2e",
       ACCENT_PRIMARY="#e94560",
       custom_qss="""
           QPushButton { border-radius: 8px; }
           QGroupBox  { border-radius: 10px; }
       """,
       icons_dir=...,
   )
   ```
3. (Opcional) Crea `layout.py` si necesitas modificar la distribución.
4. (Opcional) Agrega módulos extra para los nuevos componentes.
5. Ejecuta: `python main.py -theme nombre-del-theme`

---

## Consideraciones importantes

- Los widgets importan `current` (un proxy dinámico) desde `app.ui.theme`. No es necesario pasarles el tema explícitamente; el proxy refleja automáticamente el tema activo.
- `StemPlayer` guarda el tema como `self.theme` (instancia real de `Theme`). En `main_window.py` se usa `self.theme.ATRIBUTO` directamente.
- No uses hexcodes hardcodeados en los widgets. Siempre referencia `theme.ATRIBUTO` o `self.theme.ATRIBUTO`.
- Si un atributo de color no existe en `Theme`, agrégalo a la dataclass.
- `loader.py` agrega la carpeta del tema a `sys.path`, por lo que los módulos del tema pueden importarse entre sí con `import nombre_modulo`.
- Si el layout.py necesita re-aplicar estilos después de agregar widgets, puede llamar a `window.setStyleSheet(window.theme.global_stylesheet())` o usar `window.theme.xxx` directamente.
- El QSS personalizado (`custom_qss`) se concatena al final del stylesheet global. Para anular una regla base, repite el mismo selector con los valores deseados.
- Los iconos SVG en `icons_dir` deben tener `viewBox="0 0 24 24"` para que el coloreado dinámico funcione (el color se aplica con `CompositionMode_SourceIn`).
