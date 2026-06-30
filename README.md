# Stem Player

Aplicación de escritorio para reproducir, mezclar y transponer stems de audio individuales. Detecta automáticamente la tonalidad y el tempo, permite ajustar pitch y tempo, gestiona una librería de canciones y setlists, y genera sheets de acordes con IA (OpenRouter o Google AI Studio).

## Características principales

- **Carga de stems**: Importa múltiples archivos de audio (WAV, MP3, M4A, FLAC) desde una carpeta.
- **Detección automática**: Analiza el mix para detectar tonalidad (key) y tempo (BPM).
- **Pitch shift**: Cambia la tonalidad en semitonos (-3 a +3).
- **Tempo**: Ajusta el BPM con Rubber Band.
- **FX por stem**: Activa/desactiva el procesamiento de pitch/tempo por stem.
- **Controles por stem**: Volumen, paneo, mute, solo, categoría, renombrar, eliminar y reordenar.
- **Count-in y Metrónomo**: Compases de entrada configurables, metrónomo persistente.
- **Librería persistente**: Guarda canciones con metadatos JSON.
- **Exportación**: 4 modalidades — ZIP o WAV, con configuración actual o stems originales.
- **Setlists**: Listas de reproducción con auto-avance, pre-carga y reordenación.
- **Undo/Redo**: Historial completo de ajustes con detección de cambios no guardados.
- **ChordPro**: Vista previa, editor con botones de acordes, exportación a PDF, modo karaoke.
- **Editor de Sync**: Editor visual con waveform, tabla de tiempos y previsualización ChordPro.
- **Streaming karaoke**: Transmite la letra sincronizada a cualquier navegador en la red local vía HTTP + QR.
- **Procesamiento en hilos**: Sin bloquear la UI + centralización con ThreadManager.
- **Temas externos**: Sistema de temas plugin con colores, QSS, iconos SVG y layout extensible (`-theme`).
- **Múltiples librerías**: Varias carpetas de canciones con favoritos, recientes y búsqueda.
- **Proveedores IA**: OpenRouter y Google AI Studio con registro extensible.
- **Sync con Whisper**: Regeneración de timestamps vía faster-whisper + refinamiento con IA.
- **Filtros de stems**: Clasificación automática (click, guía, sin FX) por patrón de nombre.
- **Caché de audio**: Dos niveles (mono WAV + pitch/tempo) para recarga rápida.
- **Medidores de sistema**: CPU, RAM y pico de audio en tiempo real.
- **Configuración**: Diálogo de settings con pestañas (Filtros, Streaming, IA).

## Stack Técnico

| Componente | Tecnología |
|---|---|
| **Lenguaje** | Python 3.11+ |
| **GUI** | PySide6 (Qt6) |
| **Audio I/O** | soundfile, sounddevice |
| **Procesamiento** | librosa, pyrubberband, numpy |
| **IA / LLM** | OpenRouter API, Google AI Studio |

## Instalación

### Requisitos

- Python 3.11 o superior
- Pip

### Pasos

```bash
git clone <url-del-repo>
cd stemsplayer
python -m venv penv
source penv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## Uso

```bash
python main.py                  # Tema oscuro por defecto
python main.py -theme stemdeck  # Tema StemDeck
python main.py -theme theme3    # Tema con layout extendido
```

### Argumentos CLI

| Flag | Descripción |
|---|---|
| `-theme <nombre>` | Carga un tema desde `app/ext/themes/<nombre>/` |

### Primeros pasos

1. **Configurar librería**: En el panel izquierdo, configura la carpeta de canciones.
2. **Cargar stems**: Haz clic en "Cargar Carpeta de Stems".
3. **Ajustar mezcla**: Modifica volumen, paneo, mute/solo.
4. **Pitch/Tempo**: Usa los botones de semitonos o BPM personalizado.
5. **Reproducir**: Presiona Play.
6. **Guardar**: En la librería para persistir configuración.
7. **Setlists**: Crea listas y navega con Prev/Next.
8. **ChordPro**: Desde el menú "⋮" genera sheets, edita sync o abre el editor.
9. **Stream karaoke**: En el panel de acordes, elige "Stream to browser (Web)" para compartir en la red.

## Documentación

| Documento | Descripción |
|---|---|---|
| [`docs/user_guide.md`](docs/user_guide.md) | **Guía de usuario completa** — todas las vistas, controles y flujos |
| [`docs/architecture.md`](docs/architecture.md) | Arquitectura, flujo de datos, estructura del proyecto |
| [`docs/theming.md`](docs/theming.md) | Sistema de temas centralizado y guía para crear nuevos temas |
| [`docs/threading.md`](docs/threading.md) | Gestión de hilos y Thread Safety |
| [`docs/api.md`](docs/api.md) | API de proveedores IA (OpenRouter, Google AI Studio) |
| [`docs/building.md`](docs/building.md) | Compilación con PyInstaller |
| [`docs/SESSION_STATE.md`](docs/SESSION_STATE.md) | Estado de desarrollo del sistema de temas |
| [`docs/new_theme/layout.md`](docs/new_theme/layout.md) | Layout ASCII del diseño StemDeck |
| [`docs/new_theme/stemdeck-design-guide.md`](docs/new_theme/stemdeck-design-guide.md) | Guía de diseño completa del tema StemDeck |
| [`docs/new_theme/svgs.md`](docs/new_theme/svgs.md) | Referencia de SVG inline para temas |
| [`docs/new_theme/waveform-technical.md`](docs/new_theme/waveform-technical.md) | Detalles técnicos de waveform |

## Licencia

Proyecto personal. Sin licencia específica.
