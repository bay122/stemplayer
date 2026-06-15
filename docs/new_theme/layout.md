# StemDeck — Esquema de layout (vista al iniciar)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│  TOPBAR (70px)                                                                │
│  ┌──────────┬────────────────────────────────────────────────────┬────────┐   │
│  │  BRAND   │  IMPORT FORM                                       │  ️🔔    │   │
│  │  StemDeck│  [ URL input    🖹 ] [All][V][D][B][G][P][O] [⚡SplitStems ]│   │
│  └──────────┴────────────────────────────────────────────────────┴────────┘   │
├────────┬──────────────────────────────────────────────────────────────────────┤
│SIDEBAR │  MAIN AREA                                                           │
│(370px) │                                                                      │
│ ┌────┐ │  ┌──────────────────────────────────────────────────────────────┐    │
│ │ ≡  │ │  │  METADATA CARDS (KEY │ BPM │ LUFS │ DURATION │ SCALE │ DR)   │    │
│ │ ⚲  │ │  │  "—" en todas (sin track cargado)                            │    │
│ │ ♥  │ │  ├──────────────────────────────────────────────────────────────┤    │
│ │ 🗑  │ │  │  STEM PRESENCE (6 columnas: VOCALS │ DRUMS │ BASS │ ... )    │    │
│ │    │ │  │  "—" en todas                                                │   │
│ │ ⚙  │ │  ├──────────────────────────────────────────────────────────────┤   │
│ │ 📺 │ │  │  SECTIONS RIBBON                                             │   │
│ │ ?  │ │  │  [Sections] [Add] │ <vacío>                                  │   │
│ │    │ │  ├──────────────────────────────────────────────────────────────┤   │
│ │ 🔍 │ │  │  MIXER HEADER                                                │   │
│ │    │ │  │  [Mixer] [Drag fader · M/S] │ <ruler con playhead>           │   │
│ │    │ │  ├──────────────────────────────────────────────────────────────┤   │
│ │ 📋 │ │  │  MIXER COLUMN (300px) │ WAVEFORM PANEL                       │   │
│ │    │ │  │  ┌──────────┐        ┌──────────────────────┐                │   │
│ │    │ │  │  │Original  │╌╌╌╌╌╌╌╌│ ╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶ │                │   │
│ │    │ │  │  │  ════════╡        │                      │                │   │
│ │    │ │  │  │Vocals    │╌╌╌╌╌╌╌╌│ ╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶ │                │   │
│ │    │ │  │  │  ════════╡        │                      │                │   │
│ │    │ │  │  │Drums     │╌╌╌╌╌╌╌╌│ ╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶ │                │   │
│ │    │ │  │  │  ════════╡        │  (placeholder tracks │                │   │
│ │    │ │  │  │Bass      │╌╌╌╌╌╌╌╌│   sin waveform)      │                │   │
│ │    │ │  │  │  ════════╡        │                      │                │   │
│ │    │ │  │  │Guitar    │╌╌╌╌╌╌╌╌│                      │                │   │
│ │    │ │  │  │  ════════╡        │                      │                │   │
│ │    │ │  │  │Piano     │╌╌╌╌╌╌╌╌│                      │                │   │
│ │    │ │  │  │  ════════╡        │                      │                │   │
│ │    │ │  │  │Other     │╌╌╌╌╌╌╌╌│                      │                │   │
│ │    │ │  │  └──────────┘        └──────────────────────┘                │   │
├────────┴─────────────────────────────────────────────────────────────────────┤
│  FOOTER (96px)                                                               │
│  ┌──────────────────────┬────────────────────────┬────────────────────────┐  │
│  │  TRACK INFO          │  TRANSPORT             │  EXPORT                │  │
│  │  — (sin track)       │  ◼ [▶] 🔄             │  [Export Mix ▼]        │  │
│  │                      │  0:00 / 0:00           │                        │  │
│  └──────────────────────┴────────────────────────┴────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  FOOTER WAVEFORM (40px)                                                 │ │
│  │  ╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶╶ │ │
│  └─────────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘
```

> **Nota:** Al cargar un track, el sidebar muestra la librería (catalog) con la lista de tracks procesados.
> El área principal se llena con los datos reales del track: metadata, waveform, stems, etc.
> La import form en la topbar permanece siempre visible.

---

## 1. TOPBAR — Barra superior

**Archivos:** `daw.css:44-376`, `widgets.css:80-261`, `appbar.css`

Es la barra fija de 70px en la parte superior. Contiene 3 zonas:

### 1.1 Brand (marca)

| Elemento        | Descripción                                                              |
|-----------------|--------------------------------------------------------------------------|
| Logo            | SVG horizontal con waveform dorado + texto "StemDeck"                    |
| Beta badge      | Etiqueta dorada "BETA" (solo en versión completa, no en collapsed strip) |
| Versión         | Número de versión (oculto en topbar, visible en about dialog)            |

### 1.2 Import Form (zona central — siempre visible)

Es el corazón de la app: desde aquí se importan tracks para separar stems.

| Elemento               | Descripción                                                                                             |
|------------------------|---------------------------------------------------------------------------------------------------------|
| `#url` (input)         | Campo de texto para pegar URL de YouTube o SoundCloud. Placeholder: *"Paste a YouTube or SoundCloud link, or drop an audio file…"* |
| Botón upload (`🖹`)    | Botón cuadrado 30x30 con icono de upload. Abre el file picker para seleccionar .mp3/.wav/.flac.        |
| File pill (oculto)     | Cuando se arrastra/selecciona un archivo, aparece una píldora verde con nombre, tamaño y botón × para quitar. |
| Stem chips             | 7 botones toggle: **All**, Vocals, Drums, Bass, Guitar, Piano, Other. `All` selecciona/deselecciona todos. Los chips individuales tienen color del stem. Comportamiento: primer click selecciona SOLO ese stem; clicks siguientes agregan. Si se vacía, vuelve a "todos". |
| `#submit` (botón)      | Botón dorado "**Split stems**" con icono de rayo. Ejecuta el pipeline de separación. Muestra spinner mientras procesa. |

### 1.3 Notification Bell (`🔔`)

| Elemento              | Descripción                                                                 |
|----------------------|-----------------------------------------------------------------------------|
| Campana              | Icono de notificaciones. Muestra un badge (punto dorado de 7px) cuando hay novedades. |
| Dropdown (280px)     | Panel de notificaciones con lista de cards. Cada card tiene icono, título, descripción y botón de dismiss. |
| Release card         | Card especial con borde dorado para anunciar nuevas versiones.              |

---

## 2. SIDEBAR — Barra lateral izquierda

**Archivos:** `daw.css:389-705`, `catalog.css`, `widgets.css:337-566`

Sidebar de 370px colapsable a 78px. Contiene:

### 2.1 Rail (66-72px)

Columna de iconos vertical. Botones de 40x40px con icono + label de 9px.

| Botón              | Icono | Descripción                                                       |
|--------------------|-------|-------------------------------------------------------------------|
| ≡ (Toggle)         | 3 líneas | Colapsa/expande el sidebar                                    |
| 📋 Library         | Rectángulo | Vista de librería (activo por defecto). Muestra todos los tracks. |
| ♥ Favorites        | Corazón | Filtra solo tracks favoritos                                      |
| 🗑 Trash            | Papelera | Muestra tracks eliminados (con botón "Empty trash")              |
| Espaciador         | —     | Empuja los botones inferiores hacia abajo                         |
| ⚙ Settings         | Engranaje | Abre editor de librería (modal)                                   |
| 📺 Supporters       | Monitor | Abre dialog con supporters (grid de fotos + logos)                |
| ? Help             | Círculo con ? | Abre about dialog con versión, links, redes sociales              |

### 2.2 Sidebar Body (resto del ancho)

| Elemento          | Descripción                                                                  |
|-------------------|------------------------------------------------------------------------------|
| Search            | Input con icono de lupa, placeholder "Search or #tag…", shortcut `⌘K`.      |
| Sugerencias tags  | Dropdown de autocompletado para tags (`.tag-suggest`, oculto por defecto).   |
| Clear bin         | Botón rojo "Empty trash" (solo visible en vista trash).                      |
| Catalog list      | Lista de tracks procesados. Cada item (`lib-item`): cover 36x36px, título, subtítulo, dot de estado (verde=disponible, dorado=procesando, gris=no disponible). Soporta drag & drop a carpetas. |
| Carpetas          | Agrupaciones colapsables con icono, nombre editable, color dot. Anidamiento con indentación. |
| Collapsed strip   | Cuando el sidebar está colapsado (78px): miniaturas de 40x40px de los tracks, solo el rail de iconos es visible. |

---

## 3. MAIN AREA — Zona principal

**Archivos:** `daw.css:793-1689`, `widgets.css:38-77`, `transport.css:376-527`

Ocupa todo el espacio restante. Contiene 5 secciones verticales:

### 3.1 Metadata Cards (fila 1)

7 tarjetas en fila horizontal que muestran análisis del track:

| Card          | Contenido                                               | Color        |
|---------------|---------------------------------------------------------|--------------|
| KEY           | Tonalidad detectada (Camelot) + confidence ring         | `--fg`       |
| BPM           | Beats per minute                                        | `--accent`   |
| LUFS          | Loudness (integradrated) + Peak                         | `--fg`       |
| DURATION      | Duración total en mm:ss                                 | `--fg`       |
| SCALE         | Escala (Major/Minor)                                    | `--fg`       |
| DYNAMIC RANGE | DR value + label (e.g. "Excellent")                     | `--fg`       |
| TEMPO STABILITY| % + label (e.g. "Very Stable")                        | `--fg` / verde si alto |

Cada card tiene: label uppercase 10px, valor grande (22px bold mono), sub-label 11px.
Sin track: todo muestra `—`.

### 3.2 Stem Presence Cards (fila 2)

Grid de 6 columnas, una por stem. Muestra el porcentaje de presencia de cada stem en la canción.

| Stem    | Color    | Descripción                       |
|---------|----------|-----------------------------------|
| VOCAL   | `--vocals` | Presencia vocal en %            |
| DRUM    | `--drums`  | Intensidad de batería           |
| BASS    | `--bass`   | Profundidad de bajo             |
| GUITAR  | `--guitar` | Presencia de guitarra           |
| PIANO   | `--piano`  | Presencia de piano              |
| OTHER   | `--other`  | Otros instrumentos              |

Sin track: todas muestran `—` y clase `inactive`.

### 3.3 Sections Ribbon

| Elemento            | Descripción                                                              |
|--------------------|--------------------------------------------------------------------------|
| "Sections" label   | Label + botón "Add" para agregar secciones.                              |
| Save indicator     | Spinner/checkmark que indica estado de guardado.                         |
| Section blocks     | Bloques de colores en la línea de tiempo (arrastrables, redimensionables). Cada bloque representa una sección (Intro, Verse, Chorus...). Bordes con color dinámico `--sc`. |
| Drag handles       | Zonas de 6px a izquierda/derecha para redimensionar.                     |

### 3.4 Waveform Header

| Elemento          | Descripción                                                                |
|-------------------|----------------------------------------------------------------------------|
| "Mixer" label     | Label + sublabel "Drag fader · M/S"                                       |
| Ruler             | Línea de tiempo con ticks numerados (formato mm:ss). Playhead marker (triángulo dorado + línea vertical roja `#e54e4e` con glow). Sincronizado con zoom horizontal. |

### 3.5 Content Area (stems panel + waveform panel)

Dividido en dos columnas: **Stems Panel (300px)** | **Waveform Panel (flex 1)**

#### 3.5.1 Stems Panel (izquierda, 300px)

Contiene las filas del mixer horizontal, una por stem + original. Cada fila:

| Elemento              | Descripción                                                                 |
|-----------------------|-----------------------------------------------------------------------------|
| Icono                 | SVG del stem (16x16px, color del stem). Oculta por defecto; se muestra en widget. |
| Nombre                | Texto 12.5px, truncado con ellipsis.                                        |
| Fader horizontal      | Track de 4px altura, knob circular 14px. Color del stem. Arrastre horizontal (ew-resize). |
| VU Meter              | Barra horizontal de 8px altura. Gradiente: verde (`#4a8c44`) → amarillo (`#b8a83b`) → rojo (`#d65a4a`). |
| Valor dB              | Número monoespaciado 11px, ej: "-6.3".                                      |
| M (Mute)              | Botón 26x26px. Rojo (`#e85d4f`) cuando mute activo.                         |
| S (Solo)              | Botón 26x26px. Dorado cuando solo activo.                                    |
| Download button       | Botón 26x26px con color del stem. Descarga el stem individual en WAV.        |

Estados:
- `muted`: opacidad 0.55, nombre tachado.
- `unavailable`: opacidad 0.34, gris, sin interacción.
- `disabled`: controles no funcionales (antes de cargar track).

#### 3.5.2 Waveform Panel (derecha)

| Elemento              | Descripción                                                                 |
|-----------------------|-----------------------------------------------------------------------------|
| Waveform lanes        | Canvas de WaveSurfer (multitrack library). Cada stem ocupa 70px + 2px separador. Barras: 3px ancho, 2px gap, 2px radius. Color del stem. |
| Overview SVG overlay  | Capa SVG superpuesta con rects (mismo aspecto que WaveSurfer). Usado cuando el Web Audio Engine es el fuente de playback. |
| Loop region           | Overlay semi-transparente dorado entre dos bordes dorados. Marco de loop A-B. |
| Loading overlay       | Overlay con glow pulsante + 6 barras animadas (stagger). Cubre el waveform mientras se carga. |
| Waveform loading      | Líneas animadas con shimmer effect (barrido de luz). 6 stems con colores distintos y delays escalonados. |
| Zoom slider           | Slider horizontal (116px) con thumb dorado. Controla el zoom horizontal del waveform. Botones +/− para zoom in/out. |
| Grid                  | Líneas verticales tenues en el waveform para referencia temporal.            |

---

## 4. FOOTER — Barra inferior

**Archivos:** `widgets.css:1502-1589`, `daw.css:1786-1951`

Altura fija de 96px, sticky al fondo. Layout: 3 columnas.

### 4.1 Columna izquierda — Track Info

| Elemento              | Descripción                                                              |
|-----------------------|--------------------------------------------------------------------------|
| Track title           | Nombre del track (bold, truncado).                                       |
| Fav button            | Corazón. Relleno rojo `#e54e4e` cuando activo.                           |
| Cover art             | Thumbnail 56x56px con placeholder SVG (nota musical).                    |
| Track meta            | Tiempo extraído, fuente, calidad.                                        |
| Time                  | Ej: "3:45"                                                               |
| Stems count           | Ej: "6 Stems"                                                            |

Sin track: muestra `—`.

### 4.2 Columna central — Transporte

| Elemento       | Descripción                                                                                          |
|---------------|------------------------------------------------------------------------------------------------------|
| Stop (◼)      | Botón 58x58 (icono cuadrado). Glow rojo cuando el transporte está detenido al inicio.                |
| Play/Pause (▶) | Botón circular 58x58. Play: triángulo. Pause: dos rectángulos. Fondo verde con glow cuando suena.   |
| Loop (🔄)     | Botón 58x58 con icono de flechas circulares. Azul con glow cuando loop activo. Tecla L.             |
| Tiempo        | Elapsed (17px bold) + "/" + Total (13px muted).                                                      |

**Atajos de teclado:**
- `Space`: Play/Pause
- `[` / `]`: Retroceder / avanzar 5s
- `L`: Toggle loop
- `I` / `O`: Set loop start/end en la posición actual

### 4.3 Columna derecha — Export

| Elemento         | Descripción                                                                    |
|------------------|--------------------------------------------------------------------------------|
| Export button    | Botón dorado "Export Mix" con icono de download y caret ▼.                     |
| Dropdown panel   | Panel que aparece al hacer click:                                              |
| └ Formato        | Toggle WAV / MP3 / FLAC en el header.                                          |
| └ Export Mix     | Exporta el mix actual respetando mute/solo/fader.                              |
| └ Export All Stems | Exporta todos los stems como .zip.                                           |
| └ Export Current Region | Exporta solo la región seleccionada (disabled si no hay loop activo).   |

### 4.4 Footer Waveform Bar

Barra de 40px altura en la base del footer. Canvas con waveform de la pista completa.
- Barras grises (`rgba(255,255,255,0.13)`) para secciones no reproducidas.
- Barras doradas (`#f4b740`) para secciones ya reproducidas.
- Dot circular dorado en la posición actual de playback.
- Click/arrastre para seek (scrub).

---

## 5. MODALES Y DIALOGS

### 5.1 About Dialog

Activado por el botón `?` del rail.

| Elemento         | Descripción                                                              |
|------------------|--------------------------------------------------------------------------|
| Backdrop         | Fondo oscuro semitransparente con `backdrop-filter: blur(2px)`.          |
| Waveform icon    | SVG de 5 barras (icono de la app) en gradiente violeta-dorado.          |
| Título           | "StemDeck".                                                              |
| Tagline          | "Open source. No subscriptions. Built by musicians, for musicians."      |
| Version badge    | Badge con número de versión (borde redondeado).                          |
| Links            | Website + GitHub (botones con hover dorado).                             |
| Sociales         | Discord, Reddit, Instagram, X — iconos en botones cuadrados.             |

### 5.2 Supporters Dialog

| Elemento         | Descripción                                                              |
|------------------|--------------------------------------------------------------------------|
| Grid masonry     | Columnas flexibles con tiles de supporters. Cada tile tiene logo, avatar, nombre y rol. |
| Tilt aleatorio   | Cada tile tiene un pequeño ángulo de rotación que se endereza al hover.  |

### 5.3 Folder Editor

| Elemento         | Descripción                                                              |
|------------------|--------------------------------------------------------------------------|
| Input nombre     | Campo de texto para renombrar carpeta.                                   |
| Color picker     | Círculos de color (22px) para elegir color de carpeta.                   |
| Botones          | Cancel (borde gris) / Save (borde dorado).                               |

### 5.4 Library Editor

| Elemento         | Descripción                                                              |
|------------------|--------------------------------------------------------------------------|
| Tabla            | Lista de todos los tracks con nombre, ubicación, estado.                 |
| Sync button      | Botón dorado para resincronizar librería.                                |
| Status           | Indicador de sincronización (out-of-sync en rojo).                       |

---

## 6. WAVEFORM LOADING OVERLAY

Aparece mientras se cargan los stems y se renderiza el waveform.

| Elemento          | Descripción                                                              |
|-------------------|--------------------------------------------------------------------------|
| Glow              | Círculo pulsante dorado (80x80px, animación daw-pulse).                  |
| Loading bars      | 6 barras verticales (3px ancho, altura variable) con animation stagger.  |
| Stalled message   | Si tarda >20s, muestra "Still loading waveform…".                        |
| Phrase            | Mensaje opcional sobre el estado actual de carga.                        |
| Timeout           | Se oculta forzosamente a los 60s.                                        |

---

## 7. ESTADOS DE LA APP

La app maneja 3 estados principales, controlados por clases CSS en `.app`:

| Clase          | Qué muestra                                                                 |
|----------------|-----------------------------------------------------------------------------|
| `no-track`     | Estado inicial. Metadata cards vacías, mixer lanes deshabilitados, placeholder waveforms. |
| `is-import`    | (Legacy) Muestra página de import separada. Oculta now-playing y lanes.     |
| *(ninguna)*    | Track cargado. Todo el DAW activo con datos reales.                         |

Otras clases de estado:
- `cat-collapsed`: Sidebar colapsado a solo rail.
- `appbar-collapsed`: Topbar colapsado (solo icon strip).
- `engine-waveforms`: Usa SVG overlay en vez de WaveSurfer canvas (Web Audio Engine activo).
- `no-track`: Export button deshabilitado con opacidad 0.35.

---

## 8. FLUJO DE USO TÍPICO

```
1. USUARIO ABRE LA APP
   ↓
2. VE: Topbar + Sidebar vacío + Main area vacío + Footer vacío
   ↓
3. PEGA URL (YouTube/SoundCloud) o ARRASTRA archivo de audio
   ↓
4. SELECCIONA stems a extraer (por defecto todos)
   ↓
5. CLICK "Split stems"
   ↓
6. VE: Loading overlay en waveform panel + barra de progreso
   ↓
7. ESPERA mientras el backend: descarga → analiza → separa (Demucs) → recolecta
   ↓
8. VE: Track cargado con metadata, waveform, mixer, stems listos
   ↓
9. PUEDE: reproducir, mute/solo stems, ajustar volumen, loop, exportar
```
