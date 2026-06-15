# StemDeck — Guía de diseño / Design Guide

> Documento de referencia para replicar el estilo visual de StemDeck.
> StemDeck es una app web (FastAPI + vanilla JS/HTML/CSS) envuelta en Tauri para desktop.
> No usa PyQt6; es 100% CSS moderno con tema oscuro tipo DAW.

---

## 1. Filosofía visual

- **Flat dark DAW** — Interfaz oscura tipo Ableton/FL Studio, basada en superficies planas con sutiles gradientes, sin sombras duras.
- **Acento dorado (#f4b740)** como color principal de llamada a la acción.
- **Colores de stem** (vocals, drums, bass, guitar, piano, other) — paleta saturada pero ligeramente polvorienta, tipo FL Studio channel rack.
- **Fondo con ambient glow** — radial-gradients dorados sutiles sobre fondo oscuro para dar profundidad sin romper el flat design.
- **Border-radius consistente:** 10px (paneles), 8px (widgets secundarios), 6px (elementos pequeños).
- **Fuentes:** Inter (UI) + JetBrains Mono (datos numéricos, monoespaciada).

---

## 2. Sistema de colores — Design Tokens

### 2.1 Superficies (fondos)

| Token        | Hex       | Uso                                         |
|-------------|-----------|---------------------------------------------|
| `--bg`      | `#0b0f12` | Fondo principal del DAW                     |
| `--bg-2`    | `#0f1418` | Topbar, sidebar, paneles secundarios         |
| `--panel`   | `#131a1f` | Paneles elevados                            |
| `--panel-2` | `#182026` | Paneles más elevados, hover states          |
| `--panel-3` | `#1d262d` | Hover intenso, border de elementos activos  |
| `--border`  | `#232c34` | Bordes estándar                             |
| `--border-strong` | `#2e3942` | Bordes fuertes (inputs, botones)      |

### 2.2 Texto

| Token      | Hex       | Uso                          |
|-----------|-----------|------------------------------|
| `--fg`    | `#e8ecf0` | Texto principal              |
| `--fg-2`  | `#c2c9d1` | Texto secundario             |
| `--muted` | `#8a939c` | Texto apagado, labels        |
| `--muted-2` | `#5d666e` | Texto muy apagado, placeholders |

### 2.3 Acento (Gold)

| Token          | Hex       | Uso                                              |
|---------------|-----------|--------------------------------------------------|
| `--accent`    | `#f4b740` | Botón primary, acentos, playhead                 |
| `--accent-2`  | `#d99a2b` | Degradado del botón primary                      |
| `--gold-bright` | `#f8c054` | Versión más brillante, hover, logos            |
| `--gold-soft` | `rgba(244,183,64,0.16)` | Background sutil dorado          |
| `--gold-line` | `rgba(244,183,64,0.28)` | Bordes dorados semitransparentes |

### 2.4 Colores de Stem (pistas de audio)

| Stem    | Hex       | Uso                                           |
|---------|-----------|-----------------------------------------------|
| Vocals  | `#ef4444` | Rojo — botones stem, barras de energía        |
| Drums   | `#f97316` | Naranja                                       |
| Bass    | `#eab308` | Amarillo                                      |
| Guitar  | `#22c55e` | Verde                                         |
| Piano   | `#a855f7` | Púrpura                                       |
| Other   | `#9ca3af` | Gris                                          |

Versión JS usada en el mixer (`STEM_COLORS` en `constants.js:32-40`):

| Stem     | Hex       |
|----------|-----------|
| vocals   | `#e85f6f` |
| drums    | `#e89048` |
| bass     | `#e8b848` |
| guitar   | `#88d878` |
| piano    | `#b88fe8` |
| other    | `#88a8c8` |
| original | `#a8b0bd` |

### 2.5 Estados

| Token         | Hex       | Uso                                    |
|--------------|-----------|----------------------------------------|
| `--danger`   | `#d65a4a` | Errores, mute activo, delete           |
| `--focus-ring` | `rgba(236,236,236,0.55)` | Focus visible outline |
| Green (success) | `#4caf7d` | Play activo, saved indicator         |
| Red (playhead) | `#e54e4e` | Playhead vertical line               |

### 2.6 Background del body (import page)

```css
background:
  radial-gradient(circle at 50% 0%, rgba(216,168,74,0.1), transparent 34rem),
  radial-gradient(circle at 0% 45%, rgba(216,168,74,0.055), transparent 28rem),
  radial-gradient(circle at 100% 45%, rgba(216,168,74,0.055), transparent 28rem),
  linear-gradient(180deg, #081016 0%, #050a0f 100%);
```

---

## 3. Tipografía

| Propiedad        | Valor                                                    |
|-----------------|----------------------------------------------------------|
| Font UI         | `'Inter', -apple-system, system-ui, sans-serif`          |
| Font Mono       | `'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace` |
| Tamaño base     | `13px` (DAW), `14px` (import page)                       |
| Line-height     | `1.4` (DAW), `1.5` (import)                              |
| Letter-spacing  | `-0.005em` (general)                                     |
| Labels          | `10px`, `font-weight: 600`, `letter-spacing: 0.12em`, `text-transform: uppercase` |

---

## 4. Layout — Grid principal

### 4.1 App shell (widgets.css:7-36)

```css
.app {
  display: grid;
  grid-template-columns: var(--cat-w, 370px) 1fr;  /* sidebar | main */
  grid-template-rows: 74px minmax(0, 1fr);          /* topbar | content */
  width: 100vw;
  height: 100vh;
  padding: 12px;
  gap: 12px;
}
```

- Sidebar colapsable: `--cat-w` pasa de `370px` a `78px`.
- Topbar: `70px` de alto, `border-radius: 12px`.

### 4.2 Topbar (2 columnas internas)

```css
.appbar-body-inner {
  grid-template-columns: 270px minmax(0, 1fr);  /* brand | import form */
  gap: 18px;
}
```

- Brand: logo horizontal SVG (190px) + beta badge.
- Form: URL input + stem chips + primary button.

### 4.3 Sidebar (rail + content)

```css
.catalog {
  grid-template-columns: 72px minmax(0, 1fr);  /* icon rail | content */
}
```

- Rail: 72px, botones verticales con icono + texto.
- Content: search + folder tree + track list.
- Colapsado: solo el rail (72px).

### 4.4 Main area (#lanes — contenido variable)

```css
#lanes {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
```

Contiene widgets colapsables tipo Grafana:
- Información del track (now-playing card).
- Mixer horizontal.
- Waveform.

### 4.5 Footer / Transporte

```css
.transport-footer {
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  /* track info | transport buttons | export chips */
  height: 96px;
  padding: 16px 18px;
  border-radius: 12px;
}
```

---

## 5. Catálogo de componentes

### 5.1 Topbar (`.daw-topbar` / `.topbar.appbar`)

- **Altura:** 70px (compacta) / 77px (full).
- **Background:** `--bg-2` con `border-bottom: 1px solid var(--border)`.
- **Brand:** Logo SVG horizontal + nombre "StemDeck" (Stem en `--fg`, Deck en `--accent`).
- **URL Input:** Píldora tipo "composer pill" con borde strong, border-radius 9-11px, fondo oscuro.
- **Stem chips:** Botones toggle con `aria-pressed`, color dinámico vía `--color` CSS var.
- **Process button:** Gradiente dorado vertical, texto oscuro `#1a1206`, borde-left `#b97f1c`.
- **Notificación:** Icono de campana con badge de punto dorado, dropdown panel de 280px.

### 5.2 Sidebar (`.sidebar` / `.catalog`)

- **Rail (`.sidebar-rail`):** 66-72px, botones de 40x40px con icono + label 9px.
  - Botón activo: color `--accent`, background `--panel`.
  - Botones: Library, Favorites, Trash, Settings, Supporters, Help.
- **Search:** Input con icono de lupa, placeholder gris, indicador `⌘K`.
- **Track list (`.lib-item`):** Padding 8px, border-radius 8px, hover `--panel`.
  - Item activo: gradiente izquierdo `rgba(244,183,64,0.10)` + barra lateral de 3px `--accent`.
  - Cover: 36x36px, border-radius 6px.
- **Folder:** Chevron rotable, icono 13px, nombre editable, dot de color 13px.
- **Drag indicators:** `drop-before`/`drop-after`/`drop-into` con sombra `--accent`.

### 5.3 Track Info Header (`.daw-track-header`)

- **Row 1 — Metadata cards (`.daw-meta-card`):** Flex row de tarjetas con label uppercase, valor grande (22px, mono), sub-label.
  - KEY, BPM (acento dorado), LUFS, DURATION, SCALE, DYNAMIC RANGE, TEMPO STABILITY.
  - Camelot ring: 28px círculo con borde dorado para key confidence.
- **Row 2 — Stem presence (`.stem-presence-panel`):** Grid 6-columnas.
  - Cada stem: label uppercase 10px, porcentaje 28px bold mono, color del stem.
  - Inactive: color `--muted`.

### 5.4 Sections Ribbon (`.daw-section-ribbon`)

- **Altura:** 36px.
- **Mixer label:** 300px fijo, fondo `--bg-2`.
- **Sections area:** Scroll horizontal con bloques de sección.
  - `.section-block`: Posición absoluta, border-color vía `--sc`, border-radius 4px.
  - Drag handles laterales de 6px, rename input inline, delete button on hover.
  - Save indicator spinner.

### 5.5 Mixer / Stems Panel (`.daw-stems-panel`)

- **Ancho:** 300px.
- **Mixer rows (`.lane-header.mx-row`):** Altura dinámica `--lane-h` (~72px).
  - Grid interno: icon(24) | name(60) | fader(1fr) | VU(90) | val(50) | M(28) | S(28) | dl(28).
  - Fader horizontal: track 4px, knob 14px circular, color del stem.
  - VU meter: 8px altura, gradiente verde→amarillo→rojo.
  - Mute/Solo: botones 22x20px, M rojo cuando activo, S dorado cuando activo.
  - Download: botón con color del stem.

### 5.6 Waveform Panel (`.daw-wave-panel`)

- **Ruler (`.lanes-ruler-time`):** Tick marks con time labels, playhead marker.
- **Waveform lanes:** Canvas de WaveSurfer (multitrack library) con barras 3x2px.
  - Cada stem: `--stem-color`, altura 70px + 2px separador.
  - Playhead vertical: línea roja `#e54e4e` con glow.
- **Loop region:** Overlay semi-transparente con bordes dorados.
- **Zoom slider:** control horizontal, thumb dorado.

### 5.7 Transport Footer (`.transport-footer`)

- **Play button (`.btn-transport`):** 58x58px, circular.
  - Idle: fondo translúcido.
  - Playing: gradiente verde `#4ade80 → #16a34a`, glow verde.
  - Stopped: gradiente rojo `#f87171 → #dc2626`, glow rojo.
  - Loop active: gradiente dorado.
- **Stop button:** glow rojo cuando al inicio.
- **Loop button:** glow azul cuando activo.
- **Export button (`.footer-chip-primary`):** Dorado, con dropdown panel para formato (WAV/MP3/FLAC) y opciones.
- **Footer waveform bar:** Canvas de 40px, barras con peaks, color dorado para lo reproducido, gris translúcido para el resto.
- **Time display:** Elapsed (17px bold) / Total (13px muted).

### 5.8 Botones — Patrones reutilizables

| Tipo               | Altura | Border-radius | Background                                                   | Texto           |
|--------------------|--------|---------------|--------------------------------------------------------------|-----------------|
| `.btn-primary`     | 56px   | 10px          | Gradiente `--gold-bright` → `--gold`                        | `#17130c` bold  |
| `.daw-process-btn` | auto   | 0 (borde izq) | Gradiente `--accent` → `--accent-2`                         | `#1a1206`       |
| `.stem-choice`     | 30px   | 6px           | Transparente, border `--border`                              | `--muted-2`     |
| `.stem-choice[aria-pressed="true"]` | — | —    | `color-mix(in srgb, var(--color) 14%, transparent)`          | `--color`       |
| `.daw-iconbtn`     | 30x30  | 8px           | Transparente                                                 | `--fg-2`        |
| `.daw-upload-btn`  | 30x30  | 6px           | Transparente, border `--border`                              | `--muted`       |
| `.cancel-btn`      | 30px   | 8px           | `--panel-2`, border `--border-strong`                        | `--fg-2`        |
| `.rail-btn`        | 40x40  | 8px           | Transparente                                                 | `--muted`       |
| `.mx-btn` (M/S)    | 22x20  | 5px           | Transparente, border `--border-strong`                       | `--muted`       |

### 5.9 Modales y Dialogs

- **Backdrop:** `rgba(3,8,13,0.42)`, `backdrop-filter: blur(2px)`.
- **Card:** `width: min(300px, calc(100vw - 32px))`, border `--border-strong`, border-radius 10px, background gradiente oscuro, `--shadow-panel`.
- **Folder editor:** Input con focus border dorado, selectores de color circulares 22px.
- **About dialog:** Logo waveform SVG, versión badge, links sociales con hover dorado.
- **Friends dialog:** Grid masonry de tiles con soportes, hover "endereza" el tilt.

### 5.10 Widgets colapsables (tipo Grafana)

- `.widget`: Border-radius 12px, border `--glass-line`, background gradiente oscuro.
- `.widget-head`: Click para colapsar, chevron rotable.
- `.widget-body`: `grid-template-rows: 1fr` → `0fr` cuando colapsado, con transición.
- Widgets: "Now Playing", "Mixer", "Waveform".

---

## 6. Visualización de audio / Waveform

### 6.1 Estrategia dual

1. **Streaming path** (por defecto para tracks largos): WaveSurfer canvas con barras.
   - `barWidth: 3`, `barGap: 2`, `barRadius: 2`, `height: 70`.
   - `waveColor`: color del stem, `progressColor`: `#3a3a3a`.
   - `trackBackground: transparent`, `trackBorderColor: rgba(148,163,184,0.08)`.

2. **Web Audio Engine path** (para tracks < ~10 min): Decodifica a AudioBuffers.
   - Renderiza SVG overlay con `<rect>` bars (3px bar + 2px gap).
   - Mismo aspecto visual que WaveSurfer.
   - Playback desde `AudioContext` único (sample-accurate, sin drift).

### 6.2 Overview waveform SVG

```javascript
// En player.js:274-311
OVERVIEW_BAR_SLOT_PX = 5; // 3px bar + 2px gap
OVERVIEW_BAR_FRAC = 0.6;  // bar width / slot
```

- SVG `viewBox="0 ${bars} 48"`, `preserveAspectRatio="none"`.
- Cada barra: `<rect x="..." y="..." width="0.6" height="..." rx="0.3">`.
- Normalización global (cross-stem) para preservar relaciones de volumen reales.

### 6.3 Footer waveform (canvas 2D)

- Canvas de 40px de alto, ~300 barras.
- `ctx.fillStyle = i < playedIdx ? "#f4b740" : "rgba(255,255,255,0.13)"`.
- Playhead dot circular en la posición actual.

### 6.4 Loading overlay

- Glow pulsante dorado (`radial-gradient` animado).
- 6 líneas verticales con animation stagger (bar loading effect).
- `waveLoadLane`, `waveLoadBars`, `waveLoadTravel` keyframes.

### 6.5 VU Meters

- **Mini-meter vertical** (sidebar): 20x34px, gradiente verde/amarillo/rojo.
- **Horizontal meter** (mixer): 8px altura, gradiente `#4a8c44 → #b8a83b → #d65a4a`.
- Peak-hold con decay gradual, 30ms transition.
- Actualización vía `requestAnimationFrame` a ~30fps.

### 6.6 Stem Energy panel

- Barras horizontales por stem, height 6px, border-radius 3px.
- Color del stem via `--stem-color`, ancho vía `--v` (JS actualiza).
- Baseline desde RMS de toda la pista; playback sobreescribe en tiempo real.

### 6.7 Presence bars (grid de actividad temporal)

- Grid 6 filas × 8 columnas, patrones de máscara únicos por fila.
- Cada celda: gradiente del color del stem con opacidad variable.
- Playhead overlay: línea dorada delgada con glow.

---

## 7. Animaciones y motion

| Animación              | Propiedades                                       | Uso                  |
|-----------------------|---------------------------------------------------|----------------------|
| `--t-fast`            | `80ms`                                            | Hover transitions    |
| `--t-base`            | `120ms`                                           | Transiciones generales |
| `--easing`            | `cubic-bezier(0.2,0.8,0.2,1)`                   | Easing estándar      |
| `daw-spin`            | `0.85s linear`                                    | Loading spinner      |
| `daw-bar`             | `1.2s ease-in-out` (staggered)                   | Waveform loading     |
| `cat-pulse`           | `1.4s infinite`                                   | Processing status dot|
| `sections-spin`       | `600ms linear`                                    | Save indicator       |
| Sidebar collapse      | `width 0.28s cubic-bezier(0.4,0,0.2,1)`          |                     |
| Widget collapse       | `grid-template-rows 220ms ease, opacity 180ms`    |                     |
| Scrollbar appear      | Solo en hover/focus-within                        |                     |

**`prefers-reduced-motion: reduce`** — anula todas las animaciones a `0.001ms`.

---

## 8. Scrollbars personalizados

### 8.1 Estilo DAW (auto-hide)

```css
scrollbar-width: thin;
scrollbar-color: transparent transparent;
/* En hover: */
scrollbar-color: rgba(148, 163, 184, 0.4) transparent;
```

### 8.2 Waveform scrollbar (dorado)

```css
scrollbar-color: rgba(216, 168, 74, 0.65) rgba(148, 163, 184, 0.12);
/* Thumb: gradiente dorado horizontal */
background: linear-gradient(90deg, rgba(216,168,74,0.55), rgba(245,203,110,0.9));
```

---

## 9. SVG Assets — Iconos y rutas

### 9.1 Logos

- **Icono app (512x512):** `imgs/stemdeck-svg-assets/stemdeck-icon.svg`
  - Fondo gradiente `#16212A → #081018`, rectángulo con borde `#263744`.
  - Waveform dorado: 9 barras de altura variable con `rx` redondeado.
  - Gradiente dorado: `#FFE38A → #F2B53D → #C98512`.
- **Logo horizontal:** SVG con símbolo waveform (mismo gradiente dorado) + texto "Stem" `#F4F6F8` + "Deck" `#F2B53D`.
- **Wordmark:** Solo texto.
- **Stacked:** Versión apilada del logo.

### 9.2 Iconos inline (inline SVG en HTML)

Usados directamente en el HTML sin archivos externos:

| Icono              | ViewBox      | Descripción                                    |
|--------------------|-------------|------------------------------------------------|
| Link/URL           | `0 0 24 24` | Link chain, stroke-width 1.8                   |
| Upload             | `0 0 24 24` | Flecha hacia arriba (M12 3v12 M7 8l5-5 5 5)   |
| Music note (file)  | `0 0 24 24` | Nota musical con círculos (M9 18V5l12-2v13...)|
| Notification bell  | `0 0 24 24` | Campana, stroke-width 1.6                      |
| Star (favorites)   | `0 0 24 24` | Corazón/estrella                               |
| Heart (fav active) | `0 0 24 24` | Relleno `#e54e4e`                              |
| Trash              | `0 0 24 24` | Papelera (M3 6h18 M8 6V4h8v2...)               |
| Settings gear      | `0 0 24 24` | Engranaje                                      |
| TV/supporters      | `0 0 24 24` | Monitor (rect + antena)                        |
| Help (?)           | `0 0 24 24` | Círculo con ?                                  |
| Search             | `0 0 24 24` | Lupa                                           |
| Menu (hamburger)   | `0 0 24 24` | 3 líneas horizontales                          |
| Close (X)          | `0 0 24 24` | X (M18 6 6 18...)                              |
| Play               | `0 0 24 24` | Triángulo play                                 |
| Pause              | `0 0 24 24` | 2 rectángulos                                  |
| Stop               | `0 0 24 24` | Cuadrado relleno                               |
| Loop               | `0 0 24 24` | Flechas de loop                                |
| Download/Export    | `0 0 24 24` | Flecha hacia abajo con línea                   |
| Plus (add section) | `0 0 24 24` | Cruz (M12 5v14 M5 12h14)                      |
| Chevron down       | `0 0 24 24` | Flecha abajo (polyline 6 9 12 15 18 9)        |

### 9.3 Stem icons (inline SVG por tipo)

| Stem     | SVG path (stroke, viewBox 0 0 24 24)                          |
|---------|---------------------------------------------------------------|
| Original | Nota musical con círculos (`M9 18V5l12-2v13...`)            |
| Vocals   | Micrófono (`M12 2a3 3 0 0 0-3 3v7...`)                     |
| Drums    | Tambor (`M7 13.5a5 5 0 0 0 10 0...`)                        |
| Bass     | Bajo/guitarra (`M16.5 3h4v5h-3...`)                          |
| Guitar   | Guitarra (`M16 4.5 20 2l2 2-2.5 4...`)                      |
| Piano    | Teclado/piano (`rect x3 y5 w18 h14 rx2...`)                 |
| Other    | Barras ecualizador (`M4 13v-2 M8 17V7...`)                  |

---

## 10. Sombras y efectos

| Token              | Valor                                              |
|--------------------|----------------------------------------------------|
| `--shadow-panel`   | `0 4px 24px rgba(0,0,0,0.4)`                      |
| Panel inset        | `inset 0 1px 0 rgba(255,255,255,0.045)`           |
| Botón primario     | `inset 0 1px 0 rgba(255,255,255,0.38), 0 16px 36px rgba(216,168,74,0.18)` |
| Play button glow   | `0 16px 34px rgba(...)`                            |
| Notification panel | `0 8px 32px rgba(0,0,0,0.5)`                      |
| Folder editor      | `--shadow-panel`                                   |
| Import card        | `inset 0 1px 0 rgba(255,255,255,0.035)`           |
| Waveform bars glow | `drop-shadow(0 0 7px color-mix(in srgb, var(--stem-color) 30%, transparent))` |
| Stem icon glow     | `drop-shadow(0 0 8px color-mix(in srgb, currentColor 26%, transparent))` |

---

## 11. Cómo lograr el mismo estilo visual (resumen técnico)

### 11.1 Si usas Qt (PyQt6 / PySide6)

1. **QSS (Qt Style Sheets):** Traduce el CSS directamente a QSS.
   - Las variables CSS no existen en QSS; define los colores como constantes Python y úsalos inline.
   - `border-radius` funciona igual.
   - Los gradientes lineales con `qlineargradient`.
   - `color-mix()` no existe en QSS — reemplaza con valores fijos.

2. **Layout:** usa `QGridLayout` o `QHBoxLayout`/`QVBoxLayout` con proporciones similares.
   - Sidebar: 370px fijo (o 78px colapsado).
   - Topbar: 70px altura.
   - Main area: stretch.

3. **Botones:** `QPushButton` con QSS para gradientes, border-radius, hover/active states.
   - Botón primario: gradiente dorado, texto oscuro.
   - Stem choice: toggle con `setProperty('pressed', ...)` o `setCheckable(True)`.

4. **Waveform:** Necesitarás un widget personalizado.
   - Opción 1: Usar `QCustomPlot`, `pyqtgraph`, o un `QLabel` con SVG generado.
   - Opción 2: Embed un WebView con WaveSurfer (como hace Tauri).
   - Opción 3: Canvas 2D con `QPainter` en `paintEvent`.

5. **VU Meters:** `QProgressBar` estilizado con gradientes, o widget personalizado con `QPainter`.

6. **Scrollbars:** QSS con `QScrollBar:horizontal`, `::handle`, etc.

### 11.2 Si usas web (HTML/CSS/JS)

- Usa exactamente el CSS de este proyecto.
- `variables.css` → tus custom properties.
- `daw.css` + `widgets.css` → layout y componentes.
- WaveSurfer.js + multitrack plugin para waveform.

### 11.3 Paleta de colores rápida (para copiar)

```css
:root {
  --bg: #0b0f12;  --bg-2: #0f1418;
  --panel: #131a1f;  --panel-2: #182026;  --panel-3: #1d262d;
  --border: #232c34;  --border-strong: #2e3942;
  --fg: #e8ecf0;  --fg-2: #c2c9d1;  --muted: #8a939c;  --muted-2: #5d666e;
  --accent: #f4b740;  --accent-2: #d99a2b;
  --gold-bright: #f8c054;  --danger: #d65a4a;
  --vocals: #ef4444;  --drums: #f97316;  --bass: #eab308;
  --guitar: #22c55e;  --piano: #a855f7;  --other: #9ca3af;
  --radius: 10px;  --radius-sm: 8px;  --radius-xs: 6px;
  --font-sans: 'Inter', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  --shadow-panel: 0 4px 24px rgba(0,0,0,0.4);
}
```

---

## 12. Archivos fuente clave

| Archivo                        | Contenido                                        |
|-------------------------------|--------------------------------------------------|
| `static/css/variables.css`    | Design tokens (colores, tipografía, layout, motion) |
| `static/css/base.css`         | Reset, body gradients, layout shell `.app`       |
| `static/css/daw.css`          | DAW layout completo (topbar, sidebar, mixer, waveform) |
| `static/css/widgets.css`      | Widgets colapsables, horizontal mixer, transport footer |
| `static/css/waves.css`        | Waveform, presence bars, zoom controls           |
| `static/css/mixer.css`        | Mixer column, faders, VU meters, M/S buttons    |
| `static/css/transport.css`    | Import page, now-playing card, transport controls |
| `static/css/catalog.css`      | Catalog sidebar, folders, track items            |
| `static/css/appbar.css`       | Topbar appbar, brand, collapsed strip            |
| `static/css/master.css`       | Master fader vertical con tick marks             |
| `static/css/responsive.css`   | Breakpoints 1100/900/640/480px + touch           |
| `static/index.html`           | HTML estructura completa                         |
| `static/js/constants.js`      | `STEM_COLORS`, `STEM_NAMES`                      |
| `static/js/player.js`         | Waveform rendering, overview SVG, VU loop        |
| `static/js/audioEngine.js`    | Web Audio playback engine                        |
| `static/js/mixer.js`          | Mixer row rendering, fader logic                 |
| `static/js/transport.js`      | Ruler, playhead, loop region                     |
| `desktop/ui/setup.css`        | Tauri setup wizard theme (dark minimal)          |
