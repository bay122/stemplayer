# Stem Player

Aplicación de escritorio para reproducir, mezclar y transponer stems de audio individuales. Detecta automáticamente la tonalidad y el tempo, permite ajustar pitch y tempo, gestiona una librería de canciones y setlists, y ofrece un diseño estilo DAW.

## Características

- **Carga de stems**: Importa múltiples archivos de audio (WAV, MP3, M4A, FLAC) desde una carpeta.
- **Detección automática**: Analiza el mix para detectar la tonalidad (key) y el tempo (BPM).
- **Pitch shift**: Cambia la tonalidad de toda la canción en semitonos mediante botones visuales (-3 a +3).
- **Tempo**: Ajusta el tempo ingresando el BPM deseado; el factor de tempo se calcula automáticamente.
- **FX por stem**: Activa/desactiva efectos de pitch de forma individual para cada stem.
- **Controles por stem**: Volumen vertical, paneo horizontal, mute, solo, etiqueta por categoría, renombrar y eliminar.
- **Count-in mejorado y Metrónomo**: Configurable en 0, 1 o 2 compases. Opción de metrónomo persistente con controles independientes de volumen y paneo.
- **Librería persistente**: Guarda canciones con metadatos JSON (artista, tonalidad, tempo, configuración de stems, etc.).
- **Gestión Avanzada**: Permite guardar en la librería, guardar cambios (sobrescribir) o guardar como (duplicar), así como renombrar canciones directamente en el panel.
- **Setlists**: Crea listas de reproducción desde la librería. Navegación rápida y capacidad de reordenar canciones (subir/bajar) en el listado y renombrar los setlists.
- **Deshacer/Rehacer**: Historial integrado (Undo/Redo) para todos los ajustes de la mezcla de stems, pitch y tempo.
- **Diseño moderno**: Interfaz oscura estilo DAW con botones SVG. Botón flotante para ocultar/mostrar el panel lateral y área de stems scrolleable.
- **Procesamiento en hilos**: La carga de stems y los cambios de pitch/tempo se ejecutan en segundo plano sin bloquear la interfaz.

## Stack Técnico

- **Python 3.11+**
- **GUI**: PySide6 (Qt6)
- **Procesamiento de audio**: librosa, pyrubberband (Rubber Band), soundfile, sounddevice
- **Matemáticas**: numpy

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

### Primeros pasos

1. Configura la carpeta de **librería** en el panel izquierdo (o déjala vacía para usar solo carga manual).
2. Carga stems desde una carpeta manualmente, o selecciona una canción de la librería.
3. Ajusta pitch, tempo, count-in y click según necesites.
4. Controla el volumen, mute, solo y FX de cada stem.
5. Presiona **Play** para escuchar.
6. Guarda la canción en la librería para persistir sus ajustes.

### Setlists

1. Crea un setlist desde el panel de setlists.
2. Añade canciones de la librería.
3. Al abrir un setlist, sus canciones se muestran en la lista.
4. Usa los botones **Prev** / **Next** para navegar entre canciones del setlist.

## Estructura del proyecto

```
stemsplayer/
├── main.py             # Punto de entrada
├── gui.py              # Ventana principal y controles globales
├── audio_engine.py     # Carga, análisis, pitch/tempo, playback
├── stem_widgets.py     # Widgets personalizados por stem
├── utils.py            # Constantes y funciones auxiliares
├── config_manager.py   # Configuración global persistente
├── library_manager.py  # Gestión de librería y metadatos JSON
├── config.json         # Archivo de configuración global (se crea automáticamente)
├── requirements.txt    # Dependencias
├── README.md           # Este archivo
└── icons/svgs/         # Iconos SVG (fontaudio)
```

## Licencia

Proyecto personal.


## Activar Python venv:
& z:/home/drelthand/workspace/stemsplayer/penv/Scripts/Activate.ps1

## Otros iconos que se pueden usar:
- https://www.svgrepo.com/collection/gentlecons-interface-icons/