# Tests de StemPlayer

## Scripts de prueba

Estos scripts permiten probar por separado las funcionalidades del motor de análisis y generación ChordPro.

## Requisitos

Los scripts intentan resolver una canción conocida usando:

1. Variable de entorno `STEMS_TEST_SONG_DIR`
2. Variable `STEMS_TEST_SONG_NAME` + `config.json`
3. La primera canción del primer setlist de `config.json`

## Variables de entorno útiles

```bash
export STEMS_TEST_SONG_DIR="/ruta/a/tu/cancion"
export STEMS_TEST_SONG_NAME="Nombre de la canción"
export OPENROUTER_API_KEY="sk-or-v1-..."
export STEMS_TEST_LYRICS_FILE="/ruta/lyrics.txt"
```

## Scripts disponibles

### `test_whisper_transcription.py`
- Busca una pista Guide/Guia/Cue/Vocal
- Ejecuta la transcripción de secciones con Whisper
- Guarda JSON/TXT en `test/output/whisper_transcription`

### `test_crema_downmix.py`
- Carga los stems de una canción
- Hace downmix excluyendo click/guide/drums
- Intenta pasar ese mix al worker de CREMA
- Guarda resultados en `test/output/crema_downmix`

### `test_section_mapping.py`
- Ejecuta transcripción de secciones
- Ejecuta downmix + análisis de acordes
- Agrupa acordes por sección
- Guarda JSON consolidado en `test/output/section_mapping`

### `test_crema.py`
- Prueba unitaria del análisis de acordes con CREMA

### `test_lyrics.py`
- Prueba unitaria del procesamiento de letras

### `test_whisper.py`
- Prueba unitaria de transcripción Whisper

## Notas

- Los scripts son de diagnóstico manuales; no son tests automatizados de pytest
- Si una dependencia externa falla, el script intenta dejar evidencia útil en la carpeta `output`
- Ejecutar con: `python test/test_<nombre>.py`
