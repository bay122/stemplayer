# Arquitectura

## Principios de diseño

1. **Separación de responsabilidades**: Cada módulo tiene un propósito único.
2. **Mixins para la lógica del controlador**: `main_window.py` hereda de 11 mixins en `controllers/`, cada uno agrupando métodos por dominio.
3. **Inyección de dependencias**: Los módulos reciben sus dependencias en lugar de importar directamente.
4. **Centralización**: `ThreadManager` unifica el ciclo de vida de hilos; `StateManager` centraliza undo/redo.
5. **Consolidación de constantes**: `KEY_MAP`, `NOTES`, `STEM_CATEGORIES` en `constants.py`.

## Flujo de datos

```
Usuario interactúa con UI
        │
        ▼
  _build_ui() (señales Qt)
        │
        ├──► Mixin methods (controllers/*) ──► StateManager.push() ──► undo/redo
        │                                          │
        │                                          ▼
        ├──► ThreadManager.register(thread)  ──► ConfigManager / LibraryManager
        │                                          │
        │                                          ▼
        └──► Audio threads (loader/pitch_tempo/playback/export)
                │
                ▼
          Señales Qt de vuelta a la UI
```

## Estructura del proyecto

```
stemsplayer/
├── main.py                          # Punto de entrada
├── config.json                      # Config global (se crea automáticamente)
├── requirements.txt
├── README.md
│
├── app/
│   ├── __init__.py
│   ├── main_window.py               # StemPlayer: orquesta todo (solo _build_ui + __init__)
│   ├── state_manager.py             # StateManager (undo/redo history)
│   ├── thread_manager.py            # ThreadManager (ciclo de vida de QThreads)
│   │
│   ├── controllers/                 # Mixins que separan la lógica de main_window
│   │   ├── __init__.py
│   │   ├── song_loading.py          # Carga de stems, precarga, caché
│   │   ├── save_library.py          # Guardar en librería, cambios, exportar
│   │   ├── stem_ui.py               # Reconstrucción UI de stems, mute/solo/vol
│   │   ├── master_metronome.py      # Master volume, metrónomo, artista
│   │   ├── count_in_click.py        # Count-in, click persistente
│   │   ├── undo_redo.py             # Undo/Redo, snapshots, botones de guardado
│   │   ├── layout.py                # Panel colapsable, close song, close event
│   │   ├── pitch_tempo.py           # Pitch shift, tempo, reset, caché NPY
│   │   ├── playback.py              # Play/Pause/Stop, seek, progreso
│   │   ├── chordpro_preview.py      # Vista previa ChordPro, fullscreen
│   │   └── chordpro_generation.py   # Análisis de acordes + OpenRouter LLM
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── theme.py                 # Sistema de temas centralizado
│   │   ├── svg_icon.py              # svg_icon()
│   │   ├── volume_slider.py         # VolumeSlider (vertical)
│   │   ├── pan_slider.py            # PanSlider (horizontal)
│   │   ├── stem_item_widget.py      # Widget individual de cada stem
│   │   ├── chordpro_preview.py      # ChordProPreviewWidget
│   │   ├── live_display.py          # LiveChordWidget (karaoke)
│   │   ├── chordpro_editor.py       # ChordProEditor
│   │   ├── meters_panel.py          # MeterBar + SystemMetersPanel
│   │   ├── library_panel.py         # LibraryPanel
│   │   ├── setlist_panel.py         # SetlistPanel
│   │   ├── add_song_dialog.py       # AddSongToSetlistDialog
│   │   ├── collapsible_section.py   # CollapsibleSection widget
│   │   ├── karaoke_streamer.py      # Live Chords HTTP streamer (web)
│   │   ├── settings_dialog.py       # Settings dialog (3 tabs)
│   │   └── sync_editor.py           # Sync editor con waveform
│   │
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── fast_audio.py            # fast_audio_load()
│   │   ├── stem_loader.py           # StemLoaderThread
│   │   ├── pitch_tempo.py           # PitchTempoThread
│   │   ├── playback.py              # PlaybackThread
│   │   └── exporter.py              # ExportThread
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── config_manager.py        # ConfigManager
│   │   ├── library_manager.py       # LibraryManager
│   │   └── metadata.py              # build_metadata()
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── chord_analysis.py        # ChordAnalysisThread
│   │   ├── openrouter_service.py    # OpenRouterLLMThread
│   │   ├── whisper.py               # transcribe_guide_audio
│   │   └── providers/               # Sistema de proveedores IA (registro)
│   │       ├── __init__.py
│   │       ├── base.py              # Clase base Provider
│   │       ├── google.py            # Google AI Studio
│   │       └── openrouter.py        # OpenRouter
│   │
│   └── utils/
│       ├── __init__.py
│       ├── constants.py             # KEY_MAP, STEM_CATEGORIES, NOTES
│       └── paths.py                 # get_base_path(), get_icons_dir()
│
├── icons/                           # Iconos SVG
├── build/                           # Build output
├── dist/                            # Distribución
├── tests/                           # Tests
└── OTROS/                           # Archivos auxiliares
```
