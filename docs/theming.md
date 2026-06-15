# Sistema de Temas

La aplicación usa un **sistema de temas centralizado** en `app/ui/theme.py`.  
Toda la configuración visual (colores, bordes, tipografía) vive en una única clase `Theme`.

## Cómo funciona

1. **Clase `Theme`** (`app/ui/theme.py`):
   - `dataclass` inmutable con **todos los colores y geometrías** como atributos con nombre.
   - Métodos helper que generan QSS reutilizable (`global_stylesheet()`, `playback_slider_qss()`, `menu_qss()`, `action_button_qss()`).
   - Instancia por defecto: `DARK_THEME = Theme()`.

2. **Aplicación del tema**:
   - `main_window.py` llama `apply_theme(self, DARK_THEME)`.
   - Los widgets importan `DARK_THEME as theme` y referencian `theme.COLOR_ATTR` en lugar de hexcodes hardcodeados.

3. **Patrón de uso en widgets**:
   ```python
   from app.ui.theme import DARK_THEME as theme

   # En vez de:
   # label.setStyleSheet("color: #888888; font-size: 11px;")

   label.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; font-size: 11px;")
   ```

## Cómo crear un nuevo tema

1. Abre `app/ui/theme.py`.
2. Crea una nueva instancia de `Theme` con los valores que quieras cambiar:

```python
LIGHT_THEME = Theme(
    BG_PRIMARY="#F5F5F5",
    BG_SECONDARY="#FFFFFF",
    TEXT_PRIMARY="#222222",
    TEXT_SECONDARY="#666666",
    ACCENT_PRIMARY="#0066CC",
    ...
)
```

3. En `main_window.py`, cambia la llamada de `apply_theme(self, DARK_THEME)` a `apply_theme(self, LIGHT_THEME)`.

Si el nuevo tema necesita estilos que no existen en `Theme`, agrega nuevos atributos a la dataclass y úsalos en los widgets.

## Atributos de Theme disponibles

| Grupo | Atributo | Default | Uso |
|---|---|---|---|
| **Fondos** | `BG_PRIMARY` | `#121212` | Fondo principal |
| | `BG_SECONDARY` | `#1E1E1E` | Paneles, inputs |
| | `BG_TERTIARY` | `#2A2A2A` | Widgets de stems, menús |
| | `BG_DARK` | `#111111` | Karaoke / live display |
| | `BG_INPUT` | `#1E1E1E` | QLineEdit, QComboBox |
| | `BG_EDITOR` | `#1e1e1e` | Editor ChordPro |
| **Texto** | `TEXT_PRIMARY` | `#FFFFFF` | Labels principales |
| | `TEXT_DEFAULT` | `#CCCCCC` | Texto general |
| | `TEXT_SECONDARY` | `#888888` | Texto secundario, timestamps |
| | `TEXT_MUTED` | `#AAAAAA` | Texto deshabilitado |
| | `TEXT_EDITOR` | `#d4d4d4` | Texto en editor |
| | `TEXT_DISABLED` | `#666666` | Next chord label |
| **Acentos** | `ACCENT_PRIMARY` | `#0078D7` | Azul principal (botones checked, slider) |
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
| | `FONT_MONO` | monospace | Timestamps, editor de código |
| **SVG** | `SVG_ICON_DEFAULT` | `#AAAAAA` | Icono por defecto |
| | `SVG_ICON_DANGER` | `#FF5555` | Icono de peligro |
| | `SVG_ICON_SOLO` | `#FFAA00` | Icono de solo activo |
| | `SVG_ICON_ACTIVE` | `#FFFFFF` | Icono activo |

## Consideraciones

- No uses `setStyleSheet` con hexcodes hardcodeados en los widgets. Siempre referencia `theme.ATRIBUTO`.
- Si un widget necesita un estilo que no existe en `Theme`, **agrega el nuevo atributo a la dataclass**.
- Los SVG icons usan su propio color; cambia `SVG_ICON_*` para mantener consistencia.
- Los métodos `global_stylesheet()` y helpers devuelven QSS generado con f-strings; si agregas nuevos selectores, hazlo dentro de estos métodos.
