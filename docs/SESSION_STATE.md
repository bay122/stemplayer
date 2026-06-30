# Session State — Stage 1 & 2 Complete

> Documento de referencia para retomar el desarrollo en una nueva sesión.
> Creado: 2026-06-12

---

## 1. Resumen de lo construido

Sistema de **temas autocontenidos** que permiten cambiar colores, estilos QSS, iconos SVG y (opcionalmente) el layout completo de la app. Cada tema vive en su propia carpeta dentro de `app/ext/themes/`.

---

## 2. Archivos modificados/creados

### Etapa 1 — Infraestructura base

| Archivo | Acción | Propósito |
|---|---|---|
| `app/ui/theme.py` | Modificado | Se agregó `_ThemeProxy`, `current`, `_current_theme` + `apply_theme()` ahora actualiza `_current_theme` |
| `app/ui/__init__.py` | Modificado | Exporta `current` además de `DARK_THEME` |
| `app/main_window.py` | Modificado | `__init__(self, theme=None)` → `self.theme`. Las 14 referencias `DARK_THEME.XXX` pasaron a `self.theme.XXX`. `self.icons_dir` usa `self.theme.icons_dir` si existe |
| `main.py` | Modificado | Envuelto en `def main()`, usa `argparse` con flag `-theme`, llama a `load_theme()` y `load_layout()` |
| `app/ext/__init__.py` | **Creado** | Paquete vacío |
| `app/ext/loader.py` | **Creado** | `load_theme(name)` → importa dinámicamente `theme.py` vía `importlib`; `load_layout(name)` → carga `layout.py` si existe |
| `app/controllers/undo_redo.py` | Modificado | `DARK_THEME as theme` → `current as theme` |
| `app/ui/library_panel.py` | Modificado | Mismo cambio de import |
| `app/ui/setlist_panel.py` | Modificado | Mismo cambio de import |
| `app/ui/chordpro_editor.py` | Modificado | Mismo cambio de import |
| `app/ui/chordpro_preview.py` | Modificado | Mismo cambio de import |
| `app/ui/meters_panel.py` | Modificado | Mismo cambio de import |
| `app/ui/live_display.py` | Modificado | Mismo cambio de import |
| `app/ui/stem_item_widget.py` | Modificado | Mismo cambio de import |
| `docs/theming.md` | Reescrito | Documentación completa del sistema de temas externos |

### Etapa 2 — Theme StemDeck + extensiones

| Archivo | Acción | Propósito |
|---|---|---|
| `app/ui/theme.py` | Modificado | Se agregaron `custom_qss: str = ""` y `icons_dir: str = ""` a la dataclass |
| `app/main_window.py` | Modificado | `self.icons_dir` prioriza `self.theme.icons_dir` |
| `app/ext/themes/stemdeck/theme.py` | **Creado** | Tema StemDeck completo con 8228 chars de QSS personalizado |
| `app/ext/themes/stemdeck/icons/*.svg` (33 archivos) | **Creados** | Iconos SVG rediseñados estilo StemDeck |
| `docs/theming.md` | Modificado | Documentación de `custom_qss` e `icons_dir` |
| `docs/SESSION_STATE.md` | **Creado** | Este archivo |

---

## 3. Arquitectura del tema

### 3.1 Proxy dinámico (`app/ui/theme.py`)

```python
_current_theme = DARK_THEME

class _ThemeProxy:
    def __getattr__(self, name):
        return getattr(_current_theme, name)

current = _ThemeProxy()
```

- Los widgets importan `from app.ui.theme import current as theme`
- Usan `theme.TEXT_PRIMARY` (se ve igual que antes con `DARK_THEME`)
- Cuando `apply_theme()` cambia `_current_theme`, el proxy automáticamente refleja el nuevo tema
- `main_window.py` usa `self.theme` (instancia real de Theme, no el proxy)

### 3.2 Carga dinámica (`app/ext/loader.py`)

```python
def load_theme(name: str) -> Theme:
    # Busca app/ext/themes/<name>/theme.py
    # Usa importlib.util.spec_from_file_location() + exec_module()
    # Agrega la carpeta del tema a sys.path para imports relativos
    # Valida que exista mod.theme y sea isinstance(Theme)
    # Fallback: DARK_THEME con mensaje en consola

def load_layout(name: str):
    # Busca app/ext/themes/<name>/layout.py
    # Valida que exista apply_layout(window)
    # Retorna el módulo o None
```

### 3.3 Ciclo de carga en `main.py`

```python
args = argparse...("-theme")
theme = load_theme(args.theme) if args.theme else None
layout_mod = load_layout(args.theme) if args.theme else None

player = StemPlayer(theme=theme)

if layout_mod is not None:
    layout_mod.apply_layout(player)
```

### 3.4 Contrato de `theme.py`

Debe exponer una variable `theme` que sea instancia de `Theme`:

```python
from app.ui.theme import Theme

theme = Theme(
    BG_PRIMARY="#0b0f12",
    ACCENT_PRIMARY="#f4b740",
    # ... todos los atributos son opcionales (defaults de DARK_THEME)
    custom_qss="""...""",           # Opcional: QSS adicional
    icons_dir=os.path.join(..., "icons"),  # Opcional: iconos propios
)
```

Atributos clave de `Theme`:
- 7 colores de fondo (`BG_*`)
- 6 colores de texto (`TEXT_*`)
- 10 acentos (`ACCENT_*`)
- 5 bordes (`BORDER_*`)
- 5 geometría (`BORDER_RADIUS_*`, `FONT_*`, `FONT_SIZE_BASE`)
- 3 estados (`HOVER_*`, `PRESSED_DARKEN`)
- 5 colores SVG (`SVG_ICON_*`)
- 2 overrides: `custom_qss: str`, `icons_dir: str`

### 3.5 Contrato de `layout.py` (para Stage 3)

Debe exponer `apply_layout(window)` que recibe `StemPlayer`. Puede:
- Acceder a widgets existentes: `window.library_widget`, `window.stems_layout`, etc.
- Agregar/quitar widgets en cualquier layout
- Importar módulos locales de la misma carpeta del theme
- Usar `window.theme` para obtener colores/estilos
- Llamar `window.setStyleSheet(window.theme.global_stylesheet())` para re-aplicar QSS

---

## 4. Theme StemDeck existente

```
app/ext/themes/stemdeck/
├── theme.py          # Theme + 8.2KB custom_qss
└── icons/            # 33 SVG rediseñados estilo StemDeck
    ├── fad-play.svg
    ├── fad-pause.svg
    ├── fad-stop.svg
    ├── fad-close-x.svg
    ├── fad-open.svg (upload)
    ├── fad-save.svg (download)
    ├── fad-plus.svg
    ├── fad-search.svg
    ├── fad-microphone.svg (vocals mic)
    ├── fad-undo.svg
    ├── fad-redo.svg
    ├── fad-prev.svg (chevron left)
    ├── fad-next.svg (chevron right)
    ├── fad-edit.svg (pencil)
    ├── fad-preset-ab.svg (loop arrows)
    ├── fad-h-expand.svg / fad-h-expand.svg (hamburger)
    ├── fad-saveas.svg
    ├── fad-history.svg (clock)
    ├── fad-file-code.svg
    ├── fad-metronome.svg
    ├── fad-mute.svg
    ├── fad-solo.svg
    ├── fad-caret-up.svg / fad-caret-down.svg
    ├── fad-eraser.svg (trash)
    ├── fad-pen.svg
    ├── fad-speaker.svg
    ├── fad-v-expand.svg
    ├── fad-cpu.svg / fad-ram.svg
    └── fad-logo-audacity.svg
```

Paleta StemDeck:
- Fondos: `#0b0f12` (main), `#0f1418` (panels), `#131a1f` (elevated), `#182026` (hover)
- Texto: `#e8ecf0` (primary), `#c2c9d1` (secondary), `#8a939c` (muted), `#5d666e` (disabled)
- Acento: `#f4b740` (gold), `#d99a2b` (hover), `#d65a4a` (danger), `#4caf7d` (success)
- Bordes: `#232c34` (std), `#2e3942` (strong), `#1d262d` (dark)
- Tipografía: Inter (UI) + JetBrains Mono (mono), 13px base
- Border-radius: 6px (SM), 8px (MD), 10px (GroupBox)

---

## 5. Lo que existe pero está vacío (para Stage 3)

```
app/ext/themes/theme2/theme.py     # Vacío — diseño para theme solo visual
app/ext/themes/theme3/theme.py     # Vacío — diseño para theme con layout
app/ext/themes/theme3/layout.py    # Vacío — layout extendido
```

`loader.py` maneja gracefulmente los módulos vacíos (no tienen `theme` → fallback a DARK_THEME).

---

## 6. Documentos de diseño disponibles

```
docs/new_theme/
├── layout.md               → Layout ASCII de StemDeck (topbar, sidebar, main, footer)
├── stemdeck-design-guide.md → Guía de diseño completa (colors, typography, components, animations)
├── svgs.md                 → Todos los SVG inline: iconos navegación, transporte, stems, etc.
└── waveform-technical.md   → Technical: waveform rendering, peaks, VU, etc.
```

---

## 7. Pendiente para Stage 3

Crear un **theme que cambie estilos Y layout** (tema 3), añadiendo secciones nuevas:

### 7.1 Requisitos funcionales

- `theme.py` con colores/estilos propios (puede reusar/reinventar la paleta StemDeck)
- `layout.py` que modifique la distribución de la UI actual:
  - No necesariamente mantener las 3 columnas actuales
  - Añadir secciones nuevas: por ejemplo una topbar, un footer, un sidebar rail, etc.
  - Los componentes nuevos deben estar en módulos `.py` separados dentro del theme
- El flag `-theme theme3` debe cargarlo correctamente

### 7.2 Consideraciones técnicas conocidas

- `layout.py` se ejecuta **después** de `StemPlayer.__init__()` y `apply_theme()`, así que la UI ya está construida
- `layout.apply_layout(window)` tiene acceso completo a `window` (StemPlayer)
- Puede destruir layouts existentes y reconstruirlos
- Los módulos extra del theme se importan directamente (`import mi_modulo`) porque `loader.py` agrega la carpeta del theme a `sys.path`
- Si se añaden widgets nuevos, quizá haya que re-aplicar el stylesheet: `window.setStyleSheet(window.theme.global_stylesheet())`
- Los widgets añadidos por layout.py pueden recibir el theme vía `window.theme` o usar `from app.ui.theme import current as theme`

### 7.3 Posibles dificultades

- Muchos widgets se crean en métodos privados de `StemPlayer` (`_left_panel`, `_center_panel`, `_right_panel`, etc.) — el layout.py necesitará acceder a estos o reemplazarlos
- El `QStackedWidget` `self.center_stack` contiene varios widgets (scroll de stems, live display, chordpro fullscreen)
- Las referencias a `self.*` son abundantes; `layout.py` necesita conocer los nombres exactos de los atributos
- Los SVG icons se referencian con `os.path.join(self.icons_dir, "fad-xxx.svg")` — si se reestructura la UI, mantener esto igual

---

## 8. Comandos útiles

```bash
# Sin theme
python main.py

# Con theme stemdeck
python main.py -theme stemdeck

# Con theme2 (actualmente vacío → DARK_THEME)
python main.py -theme theme2

# Syntax check
python3 -m py_compile app/ext/themes/*/theme.py
python3 -m py_compile app/main_window.py
python3 -m py_compile main.py

# Listar todos los temas disponibles
ls app/ext/themes/
```
