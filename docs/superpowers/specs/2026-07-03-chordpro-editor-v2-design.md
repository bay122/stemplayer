# ChordPro Editor v2 — Design

**Date:** 2026-07-03
**Status:** Approved
**Author:** Brainstorming session

## Summary

Reescribir el editor de ChordPro actual (`app/ui/chordpro_editor.py`) con una
arquitectura limpia, modelo de datos separado, panel de teoría musical con
detección de escala, undo/redo robusto, sincronización con la reproducción
de la canción, y UI moderna. Conserva el parser y el formato de archivo
`.chopro` (ChordPro estándar) para mantener compatibilidad hacia atrás.

## Goals

- Edición rápida post-generación IA: corregir errores tipográficos, añadir o
  quitar acordes, ajustar secciones.
- Edición completa desde cero: transcribir una canción manualmente con
  herramientas potentes.
- Sugerencia inteligente de acordes según la tonalidad de la canción.
- Undo/redo granular con Ctrl+Z / Ctrl+Y.
- Sincronización con la reproducción: resaltar la sección actual mientras
  la canción suena, y permitir saltar a una sección con un click.

## Non-goals (YAGNI)

- Diagrama de tablatura o partitura tipo Guitar Pro.
- Reconocimiento de acordes desde audio (chord recognition).
- Inversión/voicings de acordes (queda para v3).
- Auto-transposición del audio (pitch shift) — ya existe en main_window.

## Affected files

- Eliminar: `app/ui/chordpro_editor.py` (reemplazado por el paquete).
- Crear paquete `app/ui/chordpro_editor/` con:
  - `__init__.py`
  - `editor_window.py` (QMainWindow)
  - `model.py` (dataclasses)
  - `parser.py` (load/save/validate)
  - `view.py` (layout principal)
  - `section_list.py` (lista con drag&drop + botones)
  - `text_editor.py` (QPlainTextEdit con highlighting)
  - `preview.py` (QTextBrowser)
  - `theory_panel.py` (panel de teoría musical)
  - `chord_chart.py` (diagramas SVG)
  - `commands.py` (QUndoCommands)
  - `highlight.py` (QSyntaxHighlighter)
  - `sync_bridge.py` (sync con playback)
  - `constants.py` (notas, intervalos, posiciones de acordes)
- Modificar: `app/controllers/chordpro_generation.py` (usar
  `ChordProEditorWindow` en vez de `ChordProEditor`).
- Crear tests: `tests/test_chordpro_parser.py`,
  `tests/test_chordpro_constants.py`.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ EditorWindow (QMainWindow)                                            │
│ ┌────────────────────────────────────────────────────────────────┐   │
│ │ Header: Title | Artist | Key ▼ | Transpose ▼ | Save            │   │
│ ├────────────┬─────────────────────────────┬─────────────────────┤   │
│ │ Section    │ TextEditor (highlight)      │ TheoryPanel         │   │
│ │ List       │                             │                     │   │
│ │ + buttons  │ Preview                     │ - Diatónicos        │   │
│ │ ✚ 📋 🗑 ↕  │ (split horizontal)          │ - Secundarios       │   │
│ │            │                             │ - Cercanos          │   │
│ │            │                             │ - Buscar [__] 🔍    │   │
│ │            │                             │ - Plantillas [V][C] │   │
│ ├────────────┴─────────────────────────────┴─────────────────────┤   │
│ │ Status: 5 secciones · 0 issues · BPM 120 · 00:42                │   │
│ └────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

El documento (`ChordProDocument`) es la fuente de verdad. La vista lee del
documento y emite `documentChanged` cuando se modifica. El `QUndoStack`
opera sobre el documento con comandos específicos.

## Components

### 1. Model (`model.py`)

```python
@dataclass
class ChordProMetadata:
    title: str = ""
    artist: str = ""
    key: str = ""                # "C", "Am", "F#", "Bb"

@dataclass
class Section:
    name: str                    # "Verse 1", "Chorus", "Bridge"
    kind: str                    # "verse", "chorus", "bridge", "intro",
                                # "outro", "pre-chorus", "comment", "other"
    lines: list[str]             # contenido raw ChordPro
    tag: str                     # start_of_verse, c, etc. (para serializar)

@dataclass
class ChordProDocument:
    metadata: ChordProMetadata
    sections: list[Section]
    source_path: str | None
```

### 2. Parser (`parser.py`)

Funciones:

- `parse(file_path: str) -> ChordProDocument`
- `serialize(doc: ChordProDocument) -> str`
- `validate(doc: ChordProDocument) -> list[ValidationIssue]`

Conserva la lógica actual de parsing de directivas `{title:}`, `{artist:}`,
`{key:}`, `{start_of_X}`, `{end_of_X}`, `{c:}` (comment). Usa regex
compiladas a nivel de módulo. La validación no bloquea el guardado: solo
alimenta la status bar.

Reglas de validación:

- Línea con `[` o `]` sin par correctamente balanceado → warning.
- Sección `start_of_X` sin su `end_of_X` correspondiente → warning.
- Acorde no parseable (regex `^[\[A-G][#b]?(maj7|m7|7|sus[24]|dim|aug|m|6|9|add9|/[A-G][#b]?)*\]$`
  como heurística laxa) → info.

### 3. UI Layout (`view.py`)

- **Header** (top, ~50px): campos editables para title/artist, combo de
  key, spinner de transposición, botón Guardar.
- **Section list** (izquierda, 220px, redimensionable): `QListWidget` con
  drag&drop interno, botón play por sección.
- **Editor** (centro, expansible): `QPlainTextEdit` con
  `ChordHighlighter`. Split vertical con `Preview` abajo.
- **Theory panel** (derecha, 240px, redimensionable, colapsable).
- **Status bar** (abajo, 24px): count secciones, count issues, BPM, posición.

Atajos de teclado:

- `Ctrl+S` — guardar.
- `Ctrl+Z` / `Ctrl+Y` — undo/redo.
- `Ctrl+B` — añadir sección (abre diálogo de posición y tipo).
- `Ctrl+D` — duplicar sección actual.
- `Delete` (con foco en lista) — eliminar sección.
- `Alt+↑` / `Alt+↓` — mover sección arriba/abajo.
- `Tab` en el text editor — inserta 4 espacios (no cambia de foco).
- `F1` — ayuda rápida.

### 4. Section List (`section_list.py`)

`SectionListPanel(QWidget)` contiene:

- `QListWidget` con drag&drop interno (InternalMove).
- Botones: ✚ Añadir, 📋 Duplicar, 🗑 Eliminar, ↑, ↓.
- Cada item muestra el nombre + ícono según `kind` (V, C, B, I, O).
- Botón ▶ a la derecha de cada item: salta a esa sección en la reproducción.

**Botón Añadir abre un diálogo modal** (`AddSectionDialog`) con dos campos:

1. **Posición** (radio buttons): Inicio / Antes de la actual / Después de la
   actual / Al final.
2. **Tipo** (combo): Verso / Estribillo / Puente / Intro / Outro / Pre-coro
   / Otro. Al elegir, el campo de nombre se auto-rellena con el siguiente
   número disponible (ej: "Verse 2" si ya hay "Verse 1").
3. **Nombre** (QLineEdit, editable).

Si no hay sección actual seleccionada, "Antes de la actual" y "Después de
la actual" se deshabilitan, sugiriendo "Al final" como default.

### 5. Text Editor (`text_editor.py` + `highlight.py`)

`ChordProTextEditor(QPlainTextEdit)` configura:

- Font: Consolas 12pt.
- Tab → 4 espacios.
- `setLineWrapMode(QPlainTextEdit.NoWrap)`.
- Margen de línea numerada (no implementado en v1 si requiere custom
  paint; usar `showLineNumbers` built-in en futuro).

`ChordHighlighter(QSyntaxHighlighter)` aplica formato a cada bloque:

- Directivas `{\w+:...}` → color muted, italic.
- `\[chord\]` → color success, bold.
- Si el acorde NO está en `scale_chords(current_key)` → background
  warning (color sutil, sin bold, sin cambio de foreground).
- Comentarios `{c:...}` → muted italic.
- Líneas vacías dentro de una sección → mantener color de fondo de la
  sección si se quiere (fuera de scope v1).

El resaltado se recalcula con debounce de 100ms tras `textChanged`.

### 6. Theory Panel (`theory_panel.py`)

`MusicTheoryPanel(QWidget)` con:

- **Label "Escala: {key}"** + combo para cambiar manualmente.
- **Group "Diatónicos"**: 7 botones con I, ii, iii, IV, V, vi, vii°
  (notación musical: C, Dm, Em, F, G, Am, B°). Click → inserta en el
  cursor del editor.
- **Group "Secundarios comunes"**: sus2, sus4, aug, 6, m7, maj7 — solo los
  que aplican a la escala actual.
- **Group "Cercanos"**: bII, bIII, bVI, bVII (acordes prestados típicos).
- **Buscador**: `QLineEdit` con `QCompleter` que sugiere acordes mientras
  se escribe. Soporta: notación sharp/flat, slash chords (C/G), tipos
  (m, 7, maj7, m7, sus2, sus4, dim, aug, 6, 9, add9). Enter → inserta.
- **Plantillas de sección**: botones [V] [C] [B] [I] [O] (verso, coro,
  puente, intro, outro). Click → mismo flujo que el botón ✚ Añadir, con
  tipo prefijado y posición por defecto "después de la actual".
- **Transpose controls**: botones +1 / -1 semitono + spinner de -12 a +12.
  Aplicar transposición = reescribir todos los acordes del documento
  (push a undo stack). Si el documento tiene cambios sin guardar, pedir
  confirmación.

### 7. Chord Chart (`chord_chart.py`)

`render_chord_svg(chord_name: str, size: int = 80) -> str` retorna un SVG
inline de un diagrama simplificado de guitarra (6 cuerdas × 4 trastes).
Usa la tabla `CHORD_POSITIONS` en `constants.py` para ~30 acordes
comunes. Si el acorde no está, devuelve un placeholder "—".

Se muestra en un `QToolTip` con HTML cuando el usuario hace hover sobre
un chord bracket `[X]` en el editor. Implementación: subclase de
`QPlainTextEdit` que detecta posición del cursor, extrae el chord más
cercano, y muestra el tooltip.

### 8. Undo/Redo (`commands.py`)

`QUndoStack` con:

- `InsertChordCommand(text_editor, pos, chord)`
- `AddSectionCommand(doc, idx, section)`
- `RemoveSectionCommand(doc, idx)`
- `MoveSectionCommand(doc, from_idx, to_idx)`
- `RenameSectionCommand(section, old_name, new_name)`
- `EditMetadataCommand(doc, field, old_value, new_value)`
- `TransposeCommand(doc, semitones)`
- `TextEditCommand(text_editor, old_text, new_text, cursor_pos)` —
  envoltorio sobre cambios del text editor; se push-ea tras cada
  `textChanged` salvo que el último comando del stack sea también un
  `TextEditCommand` Y hayan pasado menos de 500ms desde el push
  anterior, en cuyo caso se mergea con el último (se descarta el `old_text`
  del nuevo y se conserva el `new_text` actualizado). Esto agrupa
  escrituras rápidas (typing) en un solo undo.

Atajos: `Ctrl+Z` (undo), `Ctrl+Y` o `Ctrl+Shift+Z` (redo).

### 9. Sync Bridge (`sync_bridge.py`)

`SyncBridge` recibe:

- `sync_path: str` (camino al sync.json de la canción, opcional).
- Referencia a `main_window` (para acceder al `playback_thread` o al
  `deck_layout`).
- Referencia al `SectionListPanel` y al `text_editor`.

Comportamiento:

- Si `sync_path` no existe o no se puede parsear → bridge inactivo (no
  error, no warning).
- Polling: usar `QTimer` con intervalo 200ms que lee la posición actual
  del playback (vía `playback_thread.position_samples` o equivalente).
  Se eligió polling porque el `PlaybackThread` actual no emite signals
  de posición pública; modificar ese hilo queda fuera del scope de
  esta feature.
- Mapear tiempo (segundos) → nombre de sección via sync.json → resaltar
  en `SectionListPanel` (background color).
- Auto-scroll si la sección sale del viewport.
- Click en ▶ de una sección → `main_window.seek_to_section(name)`.

### 10. Constants (`constants.py`)

```python
NOTE_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_NAMES_FLAT  = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
CHORD_TYPES = ["", "m", "7", "maj7", "m7", "sus2", "sus4", "dim", "aug", "6", "m6", "9", "add9"]
SCALE_INTERVALS = {"major": [0,2,4,5,7,9,11], "minor": [0,2,3,5,7,8,10]}
SECTION_TYPES = ["verse", "chorus", "bridge", "intro", "outro", "pre-chorus", "other"]
SECTION_LABELS = {"verse": "Verse", "chorus": "Chorus", "bridge": "Bridge",
                  "intro": "Intro", "outro": "Outro", "pre-chorus": "Pre-Chorus",
                  "comment": "Comment", "other": "Other"}

CHORD_POSITIONS = {
    "C":  [(0,0),(2,1),(1,2),(0,3)],
    "G":  [(2,0),(3,1),(0,2),(0,3),(0,4),(3,5)],
    "D":  [(3,0),(2,1),(0,2),(0,3),(0,4)],
    "A":  [(0,0),(1,1),(2,2),(2,3)],
    "E":  [(0,0),(0,1),(1,2),(2,3),(2,4),(0,5)],
    "F":  [(1,0),(1,1),(2,2),(3,3),(3,4),(1,5)],
    "Am": [(0,0),(1,1),(2,2),(2,3)],
    "Em": [(0,0),(0,1),(0,2),(2,3),(2,4),(0,5)],
    "Dm": [(3,0),(2,1),(0,2),(0,3),(0,4)],
    # ... ~30 más
}
```

Funciones puras:

- `parse_chord_name(name: str) -> tuple[int, str, int | None]`
  ("F#m7/A" → (6, "m7", 9))
- `format_chord(root: int, type: str, bass: int | None = None, use_flats: bool = False) -> str`
- `scale_chords(key: str, mode: str = "major", use_flats: bool = False) -> list[str]`
- `transpose_chord_name(name: str, semitones: int, use_flats: bool = False) -> str`
- `detect_key_preference(root: int) -> bool` (decide flats vs sharps según
  la raíz: F#/G#/A#/E#/B# → sharps; F/Bb/Eb/Ab/Db → flats; resto → sharps).

### 11. Preview (`preview.py`)

`ChordProPreview(QTextBrowser)` mantiene el render HTML actual con dos
mejoras:

- Cache del último HTML + última key para evitar re-render si nada
  cambió.
- Render con theme-aware (usa `theme.ACCENT_SUCCESS` actual).

Mantiene la firma actual `load_chopro_content(path)`.

### 12. Integration

`app/controllers/chordpro_generation.py:_on_edit_chordpro_clicked` cambia:

```python
def _on_edit_chordpro_clicked(self):
    if not self.state.current_song_name:
        return
    song_folder = os.path.join(self.lib_mgr.library_path, self.state.current_song_name)
    chopro_path = os.path.join(song_folder, f"{self.state.current_song_name}.chopro")
    sync_path  = os.path.join(song_folder, f"{self.state.current_song_name}.sync.json")
    if not os.path.exists(chopro_path):
        QMessageBox.warning(self, "Error", "No se encontro el archivo ChordPro.")
        return
    self.chordpro_window = ChordProEditorWindow(
        chopro_path=chopro_path,
        sync_path=sync_path if os.path.exists(sync_path) else None,
        main_window=self,
        parent=self,
    )
    self.chordpro_window.saved.connect(self._on_chordpro_saved)
    self.chordpro_window.show()
```

### 13. PDF Export

`export_pdf` en el editor usa la misma lógica actual (HTML → QTextDocument
→ QPrinter). Migrado al nuevo paquete sin cambios funcionales, solo
adaptado a leer del nuevo modelo.

## Data flow

```
User types in TextEditor
    → textChanged signal
    → ChordHighlighter updates highlight (debounced 100ms)
    → TextEditCommand pushed to QUndoStack
    → document.lines[current_section] updated
    → Preview re-renders

User clicks chord in TheoryPanel
    → emits chordSelected(chord_name)
    → TextEditor inserts [chord_name] at cursor

User clicks Transpose +1
    → TransposeCommand(semitones=+1)
    → all chords in document.sections[*].lines transformed
    → TextEditor reloaded
    → Preview re-rendered

Playback position changes
    → SyncBridge maps time → section
    → SectionListPanel highlights current row
    → if not visible, scrolls to it

User clicks Save
    → serialize(doc) → write to disk
    → emits saved signal
    → main_window._load_chordpro_preview() reloads
```

## Error handling

- Archivo `.chopro` no existe al abrir → mostrar QMessageBox y cerrar el
  editor (comportamiento actual ya lo hace el main_window).
- ChordPro malformado al parsear → `parse()` retorna documento con
  secciones vacías, `validate()` reporta issues. No se cierra el editor.
- Sync.json malformado → `SyncBridge` se desactiva silenciosamente (no
  bloquea la edición).
- Transposición con acordes no reconocibles (regex no matchea) → dejar
  el texto tal cual, agregar un issue "X acordes no transpuestos" en la
  status bar.

## Testing

Tests unitarios (pytest):

- `tests/test_chordpro_parser.py`:
  - `parse` lee un archivo válido, devuelve documento con metadata y
    secciones correctas.
  - `parse` tolera archivos vacíos o con solo directivas.
  - `parse` maneja directivas cortas (`{t:}`) y largas (`{title:}`).
  - `serialize` produce un archivo que al re-parsear da el mismo
    documento (round-trip).
  - `validate` detecta secciones sin cerrar.
- `tests/test_chordpro_constants.py`:
  - `parse_chord_name` para casos básicos: C, Am, F#m7, C/G, Bb.
  - `transpose_chord_name` round-trip: `transpose(transpose(x, n), -n) == x`.
  - `scale_chords("C")` → ["C", "Dm", "Em", "F", "G", "Am", "B°"].
  - `scale_chords("A", mode="minor")` → ["Am", "Bm", "C", "Dm", "Em", "F", "G"].

Tests de UI: smoke test manual (abrir, editar, guardar, reabrir, ver
que el preview es correcto).

## Out of scope (explícito)

- Diagrama de tablatura / partitura tipo Guitar Pro.
- Reconocimiento de acordes desde audio.
- Inversión/voicings (queda para v3).
- Auto-transposición del audio (ya existe en main_window).
- Render del preview en PDF con imágenes (solo texto por ahora).
- Colaboración multi-usuario.
- Auto-save (queda para v3, se puede añadir con QTimer + flag sucio).
