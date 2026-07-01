# Guía de Usuario — Stem Player

## Índice

1. [Introducción](#1-introducción)
2. [Primeros pasos](#2-primeros-pasos)
3. [La ventana principal](#3-la-ventana-principal)
4. [Panel izquierdo: Librería y Setlists](#4-panel-izquierdo-librería-y-setlists)
5. [Panel central: Mezclador y Transporte](#5-panel-central-mezclador-y-transporte)
6. [Panel derecho: Análisis, Pitch, Tempo y Reproducción](#6-panel-derecho-análisis-pitch-tempo-y-reproducción)
7. [Controles por stem](#7-controles-por-stem)
8. [Flujo completo de trabajo](#8-flujo-completo-de-trabajo)
9. [ChordPro y acordes](#9-chordpro-y-acordes)
10. [Editor de Sync](#10-editor-de-sync)
11. [Modo Live Chords](#11-modo-live-chords)
12. [Streaming a navegador](#12-streaming-a-navegador)
13. [Exportación](#13-exportación)
14. [Undo / Redo](#14-undo--redo)
15. [Configuración](#15-configuración)
16. [Temas](#16-temas)
17. [Atajos de teclado](#17-atajos-de-teclado)
18. [Archivos de configuración](#18-archivos-de-configuración)
19. [Solución de problemas](#19-solución-de-problemas)

---

## 1. Introducción

Stem Player es una aplicación de escritorio para reproducir, mezclar y transponer stems de audio individuales. Está diseñada para músicos, bandas y técnicos de sonido que necesitan:

- Reproducir pistas multipista (stems) con control individual de volumen, paneo, mute y solo.
- Cambiar la tonalidad (pitch shift) en hasta ±3 semitonos.
- Ajustar el tempo (BPM) manteniendo la tonalidad.
- Gestionar una librería de canciones con metadatos y setlists.
- Generar hojas de acordes ChordPro automáticamente con IA.
- Transmitir la letra sincronizada a navegadores en la red local.

### Formatos de audio soportados

WAV, MP3, M4A (AAC), FLAC.

---

## 2. Primeros pasos

### Requisitos

- Python 3.11 o superior
- Pip

### Instalación

```bash
git clone <url-del-repo>
cd stemsplayer
python -m venv penv
source penv/bin/activate      # Linux/Mac
pip install -r requirements.txt
```

### Ejecución

```bash
python main.py                          # Tema oscuro por defecto
python main.py -theme stemdeck          # Tema StemDeck
python main.py -theme theme3            # Tema con layout extendido
```

### Flujo rápido

1. En el panel izquierdo, configura la carpeta de tu librería (botón `"..."`).
2. Haz clic en **"Cargar Carpeta de Stems"** y selecciona una carpeta con archivos de audio.
3. La app detectará automáticamente la tonalidad y el BPM.
4. Ajusta volumen, paneo, pitch y tempo a tu gusto.
5. Presiona **Play** para escuchar.
6. Guarda la canción en la librería con **"Guardar en librería"**.
7. Genera la hoja de acordes con **"Generar Sheet"**.

---

## 3. La ventana principal

La ventana se divide en **tres paneles**:

```
┌──────────────────┬─────────────────────────────────┬──────────────────┐
│   PANEL IZQUIERDO │        PANEL CENTRAL             │  PANEL DERECHO   │
│                   │                                  │                  │
│  ┌─────────────┐ │  ┌─────────────────────────┐    │  ┌────────────┐  │
│  │  Librería   │ │  │  Cargar Carpeta          │    │  │  Análisis  │  │
│  │  ▼ Canciones│ │  │  Canción: ...            │    │  │  Key / BPM │  │
│  │  ★ Favoritos│ │  │  Artista: ...            │    │  └────────────┘  │
│  │  ⏱ Recientes│ │  │  ┌───────────────────┐   │    │  ┌────────────┐  │
│  │             │ │  │  │ Master / Metrónomo │   │    │  │ Pitch Shift│  │
│  └─────────────┘ │  │  └───────────────────┘   │    │  │ -3 -2 -1 0 │  │
│  ┌─────────────┐ │  │  ┌───────────────────┐   │    │  │ +1 +2 +3   │  │
│  │  Setlists   │ │  │  │  Stems (scroll)    │   │    │  └────────────┘  │
│  │  ▼ lista    │ │  │  │  ┌─ Stem 1 ──────┐│   │    │  ┌────────────┐  │
│  │  [↑] [↓] [+]│ │  │  │  │ Vol Pan M S FX││   │    │  │   Tempo    │  │
│  └─────────────┘ │  │  │  └────────────────┘│   │    │  │ BPM: [120] │  │
│                   │  │  │  ┌─ Stem 2 ──────┐│   │    │  └────────────┘  │
│                   │  │  │  │ Vol Pan M S FX││   │    │  ┌────────────┐  │
│                   │  │  │  └────────────────┘│   │    │  │ Undo/Redo/ │  │
│                   │  │  └───────────────────┘   │    │  │  Reset     │  │
│                   │  │                          │    │  └────────────┘  │
│                   │  │  [Guardar][Generar]       │    │  ┌────────────┐  │
│                   │  │  [Live Chords][⋮]        │    │  │Reproducción│  │
│                   │  │                          │    │  │◀⏸⏹▶      │  │
│                   │  │  [Cerrar Canción]         │    │  │ [====o===] │  │
│                   │  │                          │    │  │ 00:00/00:00│  │
│                   │  │  ┌──────────────────┐    │    │  └────────────┘  │
│                   │  │  │ ChordPro Preview │    │    │  ┌────────────┐  │
│                   │  │  │ (right panel)    │    │    │  │ Medidores  │  │
│                   │  │  └──────────────────┘    │    │  │ CPU/RAM/Pk │  │
│                   │  │                          │    │  └────────────┘  │
│                   │  │                          │    │                  │
└──────────────────┴─────────────────────────────────┴──────────────────┘
```

- **Panel izquierdo**: Librería de canciones y setlists.
- **Panel central**: Carga de stems, mezclador, transporte y vista de acordes.
- **Panel derecho**: Análisis tonal, pitch, tempo, undo/redo, controles de reproducción y medidores del sistema.

Puedes colapsar el panel izquierdo con el botón **≡** que flota en la esquina superior izquierda.

---

## 4. Panel izquierdo: Librería y Setlists

### 4.1 Selector de librería

En la parte superior del panel izquierdo puedes gestionar **múltiples librerías**:

| Elemento | Descripción |
|---|---|
| **Combo de librerías** | Selecciona la librería activa |
| **+** (Añadir) | Crea una nueva librería: pide nombre y carpeta |
| **−** (Eliminar) | Elimina la librería seleccionada (no borra archivos) |
| **Ruta** | Muestra la carpeta actual de la librería |
| **⚙** | Abre la configuración global |
| **...** | Cambia la carpeta de la librería activa |

### 4.2 Sección Canciones

- **Buscar**: Filtra canciones por nombre o artista en tiempo real.
- **Lista de canciones**: Muestra todas las canciones de la librería.
  - **Doble clic**: Carga la canción.
  - **Clic derecho**: Abre el menú contextual.

#### Menú contextual de una canción

| Opción | Acción |
|---|---|
| **Cargar** | Carga la canción seleccionada |
| **Añadir a favoritos / Quitar de favoritos** | Marca/desmarca como favorita |
| **Renombrar** | Cambia el nombre de la canción |
| **Eliminar** | Borra la carpeta de la canción del disco (con confirmación) |
| **Exportar...** | Submenú de exportación (ver [Exportación](#13-exportación)) |
| **Borrar cache...** | Muestra las carpetas de cache de la canción y permite borrarlas selectivamente |
| **Detalles** | Muestra información: artista, duración, stems individuales, entradas de cache |

### 4.3 Sección Favoritos

Canciones marcadas como favoritas. Doble clic para cargar.

### 4.4 Sección Recientes

Últimas 20 canciones reproducidas. Doble clic para cargar.

### 4.5 Setlists

Un setlist es una lista ordenada de canciones para una presentación.

| Elemento | Descripción |
|---|---|
| **Combo de setlists** | Selecciona un setlist guardado |
| **+** (Nuevo) | Crea un nuevo setlist (pide nombre y canción inicial) |
| **✎** (Renombrar) | Cambia el nombre del setlist |
| **−** (Eliminar) | Elimina el setlist con confirmación |
| **↑ / ↓** | Reordenan la canción seleccionada en el setlist |
| **+** (Añadir canción) | Abre el diálogo para buscar y añadir canciones de la librería |
| **✕** (Cerrar) | Deselecciona el setlist actual |
| **💾** (Guardar) | Guarda el orden actual del setlist (se habilita tras reordenar) |

**La lista de canciones del setlist** soporta:
- **Doble clic**: Carga la canción.
- **Clic derecho**: Menú con "Mover Arriba", "Mover Abajo", "Eliminar del setlist".

---

## 5. Panel central: Mezclador y Transporte

### 5.1 Carga de stems

- **"Cargar Carpeta de Stems"**: Abre un selector de carpeta. La app buscará archivos de audio (WAV, MP3, M4A, FLAC) y los cargará concurrentemente (hasta 4 hilos en paralelo).
- Los stems se ordenan automáticamente: primero los de clic/metrónomo, luego los de guía/cue, y después el resto.
- Cada stem se analiza para detectar su frecuencia de sampleo y se normaliza a 44100 Hz.

### 5.2 Información de la canción

- **"Canción:"** — Nombre de la canción cargada.
- **"Artista:"** — Campo editable. Los cambios se registran en el historial undo/redo.
- **Estado**: Muestra mensajes como "Listo", "Cargando stems...", "Cargando desde caché...".
- **Barra de progreso**: Visible durante carga o procesamiento pesado.

### 5.3 Master y Metrónomo

| Control | Descripción |
|---|---|
| **Master** | Volumen general de salida. Escala no lineal con marcas en -∞, -20dB, -6dB, 0dB, +6dB |
| **Metrónomo ☐** | Activa/desactiva el clic persistente durante la reproducción |
| **🔔 (icono)** | Volumen del metrónomo (visible solo cuando está activado) |
| **Pan del metrónomo** | Paneo izquierda/derecha del clic (visible solo cuando está activado) |

### 5.4 Área de stems (mezclador)

Cada stem se muestra como un widget individual con sus propios controles (ver [Controles por stem](#7-controles-por-stem)). El área tiene scroll vertical.

### 5.5 Botones de acción

Estos botones aparecen condicionalmente según el contexto:

| Botón | Cuándo aparece | Descripción |
|---|---|---|
| **Guardar en librería** | Canción cargada desde carpeta (no estaba en librería) | Copia los stems a la librería y guarda metadatos |
| **Guardar Cambios** | Canción cargada desde librería con cambios sin guardar | Actualiza los metadatos de la canción |
| **Generar Sheet / Regenerar Sheet** | Canción guardada en librería | Genera hoja de acordes ChordPro |
| **Live Chords / Mezclador** | Cuando existe archivo ChordPro | Cambia entre la vista de mezclador y la vista Live Chords |
| **⋮ (Más)** | Canción cargada desde librería | Abre el menú de opciones adicionales |

#### Menú ⋮ (Más opciones)

| Opción | Descripción |
|---|---|
| **Guardar Como...** | Duplica la canción con un nombre nuevo |
| **Editar Acordes** | Abre el editor ChordPro |
| **Regenerar Sync (Whisper)** | Transcribe el audio de guía con Whisper y regenera la sincronización |
| **Editar Sync...** | Abre el editor visual de sincronización |
| **Añadir a Setlist** | Agrega la canción actual al setlist activo (o crea uno nuevo) |
| **Configuración...** | Abre el diálogo de configuración global |

### 5.6 Cerrar Canción

Botón **"Cerrar Canción"** (icono ✕ en rojo). Libera recursos y vuelve al estado inicial. Si hay cambios sin guardar, pide confirmación.

---

## 6. Panel derecho: Análisis, Pitch, Tempo y Reproducción

### 6.1 Análisis

| Indicador | Descripción |
|---|---|
| **Key** | Tonalidad detectada automáticamente (p.ej. "C", "Gm"). El botón **✎** permite editarla manualmente si la detección no fue precisa |
| **BPM** | Tempo detectado automáticamente |

### 6.2 Pitch Shift

Siete botones de un solo clic que cambian la tonalidad en semitonos (-3 a +3). Cuando hay una key detectada, los botones muestran el nombre de la nota resultante (p.ej. "G" en lugar de "+2"). Solo un botón puede estar activo a la vez.

### 6.3 Tempo

| Control | Descripción |
|---|---|
| **Original** | BPM detectado originalmente (solo lectura) |
| **BPM SpinBox** | Ingresa el BPM deseado (rango 20-300) |
| **Aplicar** | Aplica el nuevo tempo |
| **%** | Muestra la relación porcentual entre el BPM actual y el original |

El procesamiento de pitch y tempo se realiza con Rubber Band y se almacena en cache (ver [Caché de audio](#75-caché-de-audio)).

### 6.4 Undo / Redo / Reset

| Botón | Atajo | Descripción |
|---|---|---|
| **↩ (Undo)** | Ctrl+Z | Deshace el último cambio |
| **↪ (Redo)** | Ctrl+Y | Rehace el cambio deshecho |
| **Restablecer** | — | Vuelve a pitch=0, tempo original, count-in=0, metrónomo desactivado |

El historial undo/redo captura: pitch, tempo, volumen master, volumen metrónomo, paneo metrónomo, count-in, click, artista, y todos los parámetros de cada stem (volumen, paneo, mute, solo, FX, categoría).

### 6.5 Reproducción

#### Count-in

| Opción | Descripción |
|---|---|
| **Sin count-in** | La reproducción empieza de inmediato |
| **1 compás** | Suena 1 compás de click antes de empezar |
| **2 compases** | Suenan 2 compases de click antes de empezar |

#### Botones de transporte

| Botón | Atajo | Descripción |
|---|---|---|
| **⏮ (Prev)** | — | Canción anterior en el setlist |
| **▶ / ⏸ (Play/Pause)** | Espacio | Inicia o pausa la reproducción |
| **⏹ (Stop)** | — | Detiene y vuelve al inicio |
| **⏭ (Next)** | — | Siguiente canción en el setlist |
| **🔁 (Auto-Play)** | — | Activa el avance automático: al terminar una canción, empieza la siguiente del setlist |

#### Barra de progreso

- **Slider horizontal**: Arrastra para hacer seek durante la reproducción.
- **Tiempo actual / Total**: Formato `MM:SS` en fuente monospace.
- Durante el arrastre del slider se muestra una previsualización del tiempo.

---

## 7. Controles por stem

Cada stem tiene su propio widget con los siguientes controles:

| Control | Descripción |
|---|---|
| **Nombre** | QLineEdit editable — haz doble clic para renombrar el stem |
| **Categoría** | ComboBox con 12 categorías: Vocals, Guitars, Bass, Drums, Keys, Strings, Brass, Winds, Percussion, Synths, FX, Other |
| **Vol** | VolumeSlider — arrastre horizontal. Escala no lineal con marcas (-∞, -20dB, -6dB, 0dB, +6dB). Máximo +6dB de gain |
| **Pan** | PanSlider — arrastre horizontal. L (izquierda) a R (derecha) |
| **🔇 (Mute)** | Silencia el stem. Se ilumina en rojo cuando está activo |
| **🔊 (Solo)** | Aísla el stem. Se ilumina en naranja cuando está activo |
| **FX** | Activa/desactiva el procesamiento de pitch y tempo en este stem. Útil para baterías y percusiones que no deben ser transpuestas |
| **▲ / ▼** | Mueve el stem hacia arriba o abajo en el orden |
| **🗑 (Eliminar)** | Borra el stem de la sesión (con confirmación) |

### 7.1 Comportamiento de Solo

Al activar Solo en uno o más stems, los demás se silencian automáticamente. Al desactivar todos los Solo, se restaura el estado de Mute anterior.

### 7.2 Clasificación automática de stems

Al cargar, los stems se clasifican automáticamente según patrones en el nombre del archivo:

| Patrón | Clasificación |
|---|---|
| `click`, `metro` | **Click/Metronome** — se usa para detectar el offset del click |
| `guide`, `cue`, `guia` | **Guide/Cue** — se usa para transcripción Whisper |
| `drum`, `drums`, `bateria`, `batería` | **No FX** — se excluyen del pitch shift |

Estos patrones son configurables en Settings.

### 7.3 Caché de audio

El procesamiento de audio se almacena en dos niveles de caché dentro de la carpeta de la canción:

- **Nivel 1**: `44100_mono/` — stems convertidos a mono a 44100 Hz (evita reconversión).
- **Nivel 2**: `cache/{key}-{bpm}bpm/` — stems con pitch y tempo aplicados.

Esto permite recargar canciones rápidamente sin reprocesar.

---

## 8. Flujo completo de trabajo

### 8.1 Desde carpeta local

1. Abre la app.
2. Haz clic en **"Cargar Carpeta de Stems"**.
3. Selecciona la carpeta con tus archivos de audio.
4. Espera a que se carguen y analicen (key + BPM).
5. Ajusta volúmenes, paneo, mute/solo.
6. Cambia pitch o tempo si es necesario.
7. Presiona **Play**.
8. Guarda en librería: pon nombre a la canción y se copiará a la carpeta de la librería.

### 8.2 Desde la librería

1. Selecciona una canción en la lista (doble clic).
2. Se carga con toda su configuración guardada.
3. Haz cambios, guarda cambios si deseas persistirlos.
4. Genera sheet de acordes, edita sync, o activa Live Chords.

### 8.3 Con setlist

1. Crea un setlist con el botón **+** en la sección de setlists.
2. Añade canciones desde la librería.
3. Navega con **⏮ / ⏭** o con doble clic.
4. Activa **Auto-Play** para que las canciones se sucedan automáticamente.
5. La siguiente canción se precarga en segundo plano mientras suena la actual.

---

## 9. ChordPro y acordes

### 9.1 Generación automática con IA

La app puede generar hojas de acordes ChordPro automáticamente usando IA (OpenRouter o Google AI Studio).

**Flujo:**

1. La canción debe estar guardada en la librería.
2. Presiona **"Generar Sheet"**.
3. Si es la primera vez, se te pedirá configurar el proveedor IA:
   - Selecciona proveedor (OpenRouter o Google AI Studio).
   - Ingresa tu API Key.
   - Opcionalmente especifica un modelo.
4. Se te preguntará cómo obtener la letra:
   - **Sí**: La IA buscará la letra automáticamente.
   - **No**: Pegarás la letra manualmente.
   - **Cancelar**: Genera solo acordes, sin letra.
5. La app analizará el audio (detección de acordes vía CREMA/chroma) y luego la IA generará la estructura ChordPro.
6. El resultado se guarda como `.chopro` + `.sync.json` en la carpeta de la canción.

### 9.2 Vista previa

Cuando existe un archivo `.chopro`, aparece un panel de previsualización en la parte inferior del área central. Muestra el contenido ChordPro renderizado como HTML. Desde ahí puedes:

- **⛶ (Maximizar)**: Ver el sheet a pantalla completa en el panel central.
- **Live Chords**: Cambiar al modo Live Chords en vivo.
- **✎ (Editar)**: Abrir el editor ChordPro.

### 9.3 Editor ChordPro

El editor tiene tres secciones:

- **Lista de secciones** (izquierda): Haz clic en una sección para editarla.
- **Editor de texto** (superior derecha): Edita el contenido ChordPro de la sección seleccionada.
- **Vista previa** (inferior derecha): Renderizado en vivo del ChordPro.

**Barra de herramientas:**

- Botones de acordes comunes (C, G, D, A, E, Am, Em, Dm, F, B) — insertan `[Acorde]` en la posición del cursor.
- **"Exportar PDF"** — Exporta la hoja de acordes a PDF.
- **"Guardar Archivo"** — Guarda los cambios al archivo `.chopro`.

### 9.4 Regenerar Sync con Whisper

Desde el menú **⋮ > "Regenerar Sync (Whisper)"**:

1. Selecciona el stem que contiene la guía vocal (pista guía).
2. Whisper transcribirá el audio a nivel de palabra.
3. Opcionalmente, la IA refinará los timestamps para alinearlos con las secciones del ChordPro.
4. El resultado se guarda como `.sync.json`.

---

## 10. Editor de Sync

El editor de sincronización permite ajustar manualmente los timestamps de cada sección del ChordPro.

**Cómo abrirlo**: Menú **⋮ > "Editar Sync..."**.

### Componentes

| Área | Descripción |
|---|---|
| **Barra de reproducción** | Botón play/pausa, slider con waveform y marcadores de sección, tiempo actual/total, botón para copiar tiempo al portapapeles 📋 |
| **Tabla de secciones** | 4 columnas: nombre de sección (editable), tiempo de inicio, tiempo de fin, eliminar (✕) |
| **Editor ChordPro** | Panel derecho: contenido ChordPro de la sección seleccionada, editable |
| **Vista completa** | Panel inferior derecho: archivo ChordPro completo con la sección activa resaltada |

### Interacciones

- **Editar tiempos**: Los spinboxes de inicio/fin tienen botones +/− que ajustan en incrementos de 0.5s. También puedes escribir directamente en formato `mm:ss.ss`.
- **Añadir sección**: Botón **"+ Añadir sección"** — elige la posición (al principio, después de X, al final).
- **Eliminar sección**: Botón ✕ en la última columna de la tabla.
- **Deshacer/Rehacer**: Ctrl+Z / Ctrl+Y (historial independiente del de la app).
- **Copiar tiempo actual**: Durante la reproducción, haz clic en 📋 para copiar el timestamp y pegarlo en el campo de inicio/fin.
- **Guardar**: El botón verde **"Guardar"** escribe el `.sync.json` y el `.chopro` reordenado.

---

## 11. Modo Live Chords

### 11.1 Vista Live Chords en la app

Presiona el botón **"Live Chords"** (o **"Live Chords"** en el panel ChordPro). El panel central cambia a la vista de Live Chords en vivo:

| Elemento | Descripción |
|---|---|
| **Título de sección** | Nombre de la sección actual (p.ej. "Coro", "Verso 1") |
| **Contenido** | Letra con acordes de la sección actual |
| **Barra de marcadores** | Línea de progreso con marcadores de cada sección |
| **Tiempo** | Tiempo transcurrido / total |
| **Countdown** | "Próxima sección en X.Xs → Nombre" (visible cerca del cambio) |

**Interacciones:**

- **Doble clic** en cualquier parte → pantalla completa.
- **Ctrl + Rueda del ratón** → Aumenta/disminuye el tamaño de letra.
- Botón **⛶** → Elige entre pantalla completa o streaming web.
- Botón **✕ Cerrar Live Chords** → Vuelve al mezclador.

### 11.2 Pantalla completa

Ventana frameless (sin bordes) que ocupa toda la pantalla:

- Muestra sección actual en grande (32px bold).
- Contenido con letra y acordes.
- Barra de marcadores de sección.
- Tiempo transcurrido y total.
- Countdown a la siguiente sección.
- Transiciones suaves (fade) entre secciones.
- Presiona **Escape** para cerrar.

### 11.3 Streaming a navegador

Desde el botón ⛶ en la vista Live Chords, selecciona **"Stream to browser (Web)"**.

Se inicia un servidor HTTP en el puerto configurado (predeterminado: 8080). Aparece un diálogo con:

- **URL**: `http://<ip-local>:<puerto>` — ábrela en cualquier navegador de la red.
- **Código QR**: Escanea con el teléfono para abrir la URL.
- **"Detener Stream"**: Detiene el servidor HTTP.

La página web se actualiza cada 200ms mostrando:
- Nombre de la canción y sección actual.
- Letra con acordes.
- Barra de progreso con marcadores.
- Countdown a la siguiente sección.
- Transiciones con fade.

---

## 12. Streaming a navegador

El streaming envía el estado del Live Chords (no el audio) a navegadores en la red local. Es útil para que los músicos vean la letra y los acordes en sus dispositivos móviles durante una presentación.

**Configuración del puerto**: En Settings > Streaming, puedes cambiar el puerto (1024-65535). El cambio se aplica al iniciar el stream.

**Requisito**: La biblioteca `qrcode` es opcional pero recomendada para mostrar el código QR.

---

## 13. Exportación

Desde el menú contextual de una canción en la librería (clic derecho > "Exportar..."):

| Opción | Descripción |
|---|---|
| **Como Stems (.zip) - Originales** | Comprime los stems originales sin procesar |
| **Como Stems (.zip) - Con Configuración** | Comprime los stems con pitch/tempo/volumen aplicados |
| **Como Mezcla (.wav) - Original** | Mezcla estéreo de los stems originales |
| **Como Mezcla (.wav) - Con Configuración** | Mezcla estéreo con pitch/tempo/volumen aplicados. El nombre incluye sufijo `_P{pitch}_T{tempo}` |

Se abre un diálogo para elegir la ubicación y nombre del archivo de salida.

---

## 14. Undo / Redo

La app mantiene un historial completo de cambios. Se registra un snapshot del estado cada vez que:

- Cambias el pitch.
- Cambias el tempo.
- Ajustas el volumen master o del metrónomo.
- Cambias el paneo del metrónomo.
- Modificas el count-in o el click.
- Editas el artista.
- Cambias cualquier parámetro de un stem (volumen, paneo, mute, solo, FX, categoría).

Los botones **Undo** y **Redo** se habilitan/deshabilitan según si hay o no acciones disponibles.

El botón **"Guardar Cambios"** se muestra solo cuando hay cambios sin guardar respecto al último guardado en la librería.

---

## 15. Configuración

**Cómo abrir**: Botón ⚙ en la librería o menú ⋮ > "Configuración...".

### 15.1 Pestaña Filtros de Stems

Configura los patrones de nombre de archivo para clasificación automática:

| Grupo | Propósito | Valores por defecto |
|---|---|---|
| **Pistas de clic / metrónomo** | Stems que contienen el click (se usan para detectar offset) | `click`, `metro` |
| **Pistas de guía / cue** | Stems de referencia (se usan para transcripción Whisper) | `guide`, `cue`, `guia` |
| **Pistas sin efectos de pitch** | Stems que no deben ser transpuestos (baterías, percusiones) | `drum`, `drums`, `bateria`, `batería` |

Cada grupo tiene:
- Campo de texto para nuevo patrón.
- Botón **+** para agregar.
- Botón **−** para eliminar el seleccionado.
- Lista de patrones actuales.

### 15.2 Pestaña Streaming

| Control | Descripción |
|---|---|
| **Puerto** | Puerto del servidor HTTP de Live Chords (1024-65535, por defecto 8080) |

### 15.3 Pestaña IA

| Control | Descripción |
|---|---|
| **Proveedor** | Selecciona OpenRouter o Google AI Studio |
| **API Key** | Campo de contraseña. Botón 👁 para mostrar/ocultar |
| **Modelo** | Opcional. Vacío = usa el modelo por defecto del proveedor |

Las API keys se almacenan por proveedor en QSettings (no en archivos de configuración).

---

## 16. Temas

La app soporta un sistema de temas externos. Los temas se cargan desde `app/ext/themes/` y pueden cambiar colores, estilos QSS, iconos SVG y la distribución de la UI.

### Temas disponibles

| Nombre | Descripción |
|---|---|
| *(ninguno, por defecto)* | Tema oscuro estándar (DARK_THEME) |
| `-theme stemdeck` | Tema StemDeck con paleta dorada/oscura y ~8KB de QSS personalizado |
| `-theme theme2` | Tema solo visual (actualmente vacío, usa el DARK_THEME por defecto) |
| `-theme theme3` | Tema con layout extendido (actualmente vacío, usa el DARK_THEME por defecto) |

Para cargar un tema:

```bash
python main.py -theme stemdeck
```

Si el tema no existe, se muestra un aviso en consola y se usa el tema oscuro por defecto.

---

## 17. Atajos de teclado

| Atajo | Acción |
|---|---|
| **Espacio** | Play / Pause |
| **Ctrl+Z** | Undo |
| **Ctrl+Y** | Redo |
| **Ctrl+Z** (en SyncEditor) | Undo (historial del editor) |
| **Ctrl+Y** (en SyncEditor) | Redo (historial del editor) |
| **Ctrl+Scroll** (en Live Chords) | Cambiar tamaño de letra |
| **Escape** (en pantalla completa Live Chords) | Cerrar pantalla completa |
| **Doble clic** (en lista de librería/setlist) | Cargar canción |
| **Doble clic** (en live display) | Alternar pantalla completa |

---

## 18. Archivos de configuración

### config.json (raíz del proyecto)

Almacena la configuración global de la app:

```json
{
  "libraries": [
    {
      "name": "Mi Librería",
      "path": "/ruta/a/mis/canciones",
      "last_used": true,
      "last_setlist": "Concierto Domingo",
      "recent_played": ["Canción 1 - Artista", "Canción 2 - Artista"],
      "favorites": ["Canción 1 - Artista"],
      "setlists": [
        {
          "name": "Concierto Domingo",
          "songs": ["Canción 1 - Artista", "Canción 2 - Artista"]
        }
      ],
      "collapsed_sections": {
        "songs": false,
        "favorites": true,
        "recent": true,
        "setlists": false
      }
    }
  ],
  "window": { "width": 1400, "height": 800 },
  "stem_filters": {
    "click_patterns": ["click", "metro"],
    "guide_patterns": ["guide", "cue", "guia"],
    "no_fx_patterns": ["drum", "drums", "bateria", "batería"]
  },
  "stream_port": 8080
}
```

### QSettings

Las API keys de los proveedores IA se almacenan en QSettings (registro del sistema), no en archivos.

### Metadata por canción (carpeta de la canción)

Cada canción guarda en su carpeta:

- **`{nombre}.json`**: Metadatos con parámetros de mezcla (volúmenes, pitch, tempo, etc.).
- **`{nombre}.chopro`**: Archivo ChordPro.
- **`{nombre}.sync.json`**: Sincronización de secciones con timestamps.
- **`44100_mono/`**: Caché nivel 1 (mono 44100 Hz).
- **`cache/`**: Caché nivel 2 (pitch/tempo).

---

## 19. Solución de problemas

### La app no arranca

```bash
python3 -m py_compile main.py
python3 -m py_compile app/main_window.py
```

Verifica que no haya errores de sintaxis.

### Error "QThread: Destroyed while thread is still running"

Este error fue resuelto con el `ThreadManager`. Si vuelve a aparecer, asegúrate de usar `safe_replace()` y `safe_start()` en lugar de asignar directamente al crear threads.

### La detección de key no es precisa

Puedes editar manualmente la key detectada con el botón **✎** junto a "Key:" en el panel derecho.

### No se genera el sheet ChordPro

1. Asegúrate de que la canción esté guardada en la librería.
2. Verifica que la API Key esté configurada (Settings > IA).
3. Comprueba la conexión a internet.
4. Revisa la consola por mensajes de error.

### El stream Live Chords no se conecta

1. Verifica que el puerto no esté bloqueado por el firewall.
2. Asegúrate de que los dispositivos estén en la misma red.
3. Prueba con el puerto por defecto (8080).

### El audio se escucha distorsionado

- Reduce el volumen master o de stems individuales.
- El VolumeSlider permite hasta +6dB de ganancia — valores altos pueden saturar.

### No aparecen stems al cargar

- Verifica que los archivos sean WAV, MP3, M4A o FLAC.
- Revisa los filtros de stems en Settings por si están clasificando incorrectamente algún archivo.
