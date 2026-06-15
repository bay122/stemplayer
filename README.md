# Stem Player

Aplicación de escritorio para reproducir, mezclar y transponer stems de audio individuales. Detecta automáticamente la tonalidad y el tempo, permite ajustar pitch y tempo, gestiona una librería de canciones y setlists, y genera sheets de acordes con IA vía OpenRouter.

## Características principales

- **Carga de stems**: Importa múltiples archivos de audio (WAV, MP3, M4A, FLAC) desde una carpeta.
- **Detección automática**: Analiza el mix para detectar tonalidad (key) y tempo (BPM).
- **Pitch shift**: Cambia la tonalidad en semitonos (-3 a +3).
- **Tempo**: Ajusta el BPM con Rubber Band.
- **FX por stem**: Activa/desactiva el procesamiento de pitch/tempo por stem.
- **Controles por stem**: Volumen, paneo, mute, solo, categoría, renombrar, eliminar y reordenar.
- **Count-in y Metrónomo**: Compases de entrada configurables, metrónomo persistente.
- **Librería persistente**: Guarda canciones con metadatos JSON.
- **Exportación**: WAV estéreo o ZIP multicanal.
- **Setlists**: Listas de reproducción con auto-avance y pre-carga.
- **Undo/Redo**: Historial completo de ajustes.
- **ChordPro**: Vista previa, editor, modo karaoke y generación con IA.
- **Modo karaoke**: Letra sincronizada con acordes.
- **Procesamiento en hilos**: Sin bloquear la UI.

## Stack Técnico

| Componente | Tecnología |
|---|---|
| **Lenguaje** | Python 3.11+ |
| **GUI** | PySide6 (Qt6) |
| **Audio I/O** | soundfile, sounddevice |
| **Procesamiento** | librosa, pyrubberband, numpy |
| **IA / LLM** | OpenRouter API |

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
python main.py
```

### Primeros pasos

1. **Configurar librería**: En el panel izquierdo, configura la carpeta de canciones.
2. **Cargar stems**: Haz clic en "Cargar Carpeta de Stems".
3. **Ajustar mezcla**: Modifica volumen, paneo, mute/solo.
4. **Pitch/Tempo**: Usa los botones de semitonos o BPM personalizado.
5. **Reproducir**: Presiona Play.
6. **Guardar**: En la librería para persistir configuración.
7. **Setlists**: Crea listas y navega con Prev/Next.

## Documentación

| Documento | Descripción |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Arquitectura, flujo de datos, estructura del proyecto |
| [`docs/theming.md`](docs/theming.md) | Sistema de temas centralizado y guía para crear nuevos temas |
| [`docs/threading.md`](docs/threading.md) | Gestión de hilos y Thread Safety |
| [`docs/api.md`](docs/api.md) | API de OpenRouter para generación de sheets |
| [`docs/building.md`](docs/building.md) | Compilación con PyInstaller |

## Licencia

Proyecto personal. Sin licencia específica.
