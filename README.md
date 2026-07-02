<div align="center">
  <img src="https://raw.githubusercontent.com/bay122/stemplayer/main/assets/icons/icon.png" width="120" alt="StemPlayer Logo">
  <h1>StemPlayer</h1>
  <p><strong>Reproductor y mezclador de stems de audio &mdash; con detección de tono, ajuste de pitch/tempo, generación ChordPro con IA y streaming de letras sincronizadas.</strong></p>
</div>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-CC%20BY--NC--SA%204.0-blue" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"></a>
  <a href="https://github.com/bay122/stemplayer/releases"><img src="https://img.shields.io/github/v/release/bay122/stemplayer" alt="Release"></a>
  <a href="https://github.com/bay122/stemplayer/releases"><img src="https://img.shields.io/github/downloads/bay122/stemplayer/total" alt="Downloads"></a>
  <a href="https://github.com/bay122/stemplayer"><img src="https://img.shields.io/github/stars/bay122/stemplayer?style=social" alt="Stars"></a>
  <a href="https://github.com/bay122/stemplayer/issues"><img src="https://img.shields.io/github/issues/bay122/stemplayer" alt="Issues"></a>
</p>

<p align="center">
  <a href="#-features">Features</a> &bull;
  <a href="#-descargar">Descargar</a> &bull;
  <a href="#-compilar-desde-código">Compilar</a> &bull;
  <a href="#-cómo-usar">Cómo usar</a> &bull;
  <a href="#-documentación">Docs</a> &bull;
  <a href="#-licencia">Licencia</a>
</p>

<!--
TODO: Agregar captura de pantalla aquí
![StemPlayer screenshot](docs/imgs/screenshot.png)
-->

> StemPlayer es un reproductor multi-pista diseñado para músicos, bandas y técnicos de sonido. Carga tus stems (WAV, MP3, FLAC), ajusta el pitch y tempo por pista, genera sheets de acordes con IA, y transmite las letras sincronizadas a cualquier navegador en la red local.

---

## ✨ Features

### Reproducción y mezcla
- **Carga de stems** &mdash; Importa múltiples archivos de audio (WAV, MP3, M4A, FLAC) desde una carpeta
- **Detección automática** &mdash; Analiza el mix para detectar tonalidad (key) y tempo (BPM)
- **Pitch shift** &mdash; Cambia la tonalidad en semitonos (-3 a +3) por stem o global
- **Tempo** &mdash; Ajusta el BPM con Rubber Band
- **Controles por stem** &mdash; Volumen, paneo, mute, solo, categoría, renombrar y reordenar
- **Count-in y Metrónomo** &mdash; Compases de entrada configurables, metrónomo persistente
- **Exportación** &mdash; ZIP o WAV, con configuración actual o stems originales

### Librería y organización
- **Librería persistente** &mdash; Guarda canciones con metadatos JSON y múltiples librerías
- **Setlists** &mdash; Listas de reproducción con auto-avance, pre-carga y reordenación
- **Filtros de stems** &mdash; Clasificación automática (click, guía, sin FX) por patrón de nombre
- **Undo/Redo** &mdash; Historial completo de ajustes con detección de cambios no guardados

### ChordPro y sincronización
- **ChordPro** &mdash; Vista previa, editor con botones de acordes, exportación a PDF, modo Live Chords
- **Editor de Sync** &mdash; Editor visual con waveform, tabla de tiempos y previsualización ChordPro
- **Streaming Live Chords** &mdash; Transmite la letra sincronizada a cualquier navegador en la red local vía HTTP + QR
- **Proveedores IA** &mdash; OpenRouter y Google AI Studio para generación de acordes y sincronización
- **Sync con Whisper** &mdash; Regeneración de timestamps vía faster-whisper + refinamiento con IA

### Extras
- **Temas externos** &mdash; Sistema de temas plugin con colores, QSS, iconos SVG y layout extensible
- **Caché de audio** &mdash; Dos niveles (mono WAV + pitch/tempo) para recarga rápida
- **Medidores de sistema** &mdash; CPU, RAM y pico de audio en tiempo real

---

## 📥 Descargar

Descarga la última versión desde [Releases](https://github.com/bay122/stemplayer/releases).

| Plataforma | Archivo | Requisitos |
|------------|---------|------------|
| **Linux** | `StemPlayer-v0.1.0-linux-x86_64.tar.gz` | Ninguno (autocontenido, ~800 MB) |
| **Windows** | Compilar manualmente (ver instrucciones abajo) | Python 3.10+ |

> **Nota:** El binario Linux incluye TensorFlow completo (~800 MB). Para un tamaño menor, compila desde código.

---

## 🛠 Compilar desde código

### Requisitos
- Python 3.10 o superior
- pip
- FFmpeg (para algunas funciones de audio)

### Instalación

```bash
git clone https://github.com/bay122/stemplayer.git
cd stemplayer
python -m venv penv
source penv/bin/activate        # Linux/Mac
# .\penv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
```

### Uso

```bash
python main.py                  # Tema oscuro por defecto
python main.py -theme stemdeck  # Tema StemDeck
python main.py -theme theme3    # Tema con layout extendido
```

### Compilar ejecutable

```bash
pip install pyinstaller
pyinstaller StemPlayer.spec
```

El binario se genera en `dist/StemPlayer/`.

### Flags CLI

| Flag | Descripción |
|------|-------------|
| `-theme <nombre>` | Carga un tema desde `app/ext/themes/<nombre>/` |
| `-no-splash` | Desactiva la pantalla de splash inicial |

---

## 🎯 Cómo usar

1. **Configurar librería** &mdash; En el panel izquierdo, configura la carpeta de canciones
2. **Cargar stems** &mdash; Haz clic en "Cargar Carpeta de Stems" y selecciona una carpeta con pistas de audio
3. **Ajustar mezcla** &mdash; Modifica volumen, paneo, mute/solo de cada pista
4. **Pitch/Tempo** &mdash; Usa los botones de semitonos o ingresa BPM personalizado
5. **Reproducir** &mdash; Presiona Play
6. **Guardar** &mdash; En la librería para persistir la configuración
7. **Setlists** &mdash; Crea listas de reproducción y navega con Prev/Next
8. **ChordPro** &mdash; Desde el menú &vellip; genera sheets, edita sync o abre el editor
9. **Stream Live Chords** &mdash; En el panel de acordes, elige "Stream to browser (Web)" para compartir en la red

---

## ⚙️ Configuración

### API Keys (requerido para generación ChordPro)

1. Copia `.env_example` a `.env`
2. Obtén una API key de [OpenRouter](https://openrouter.ai/) o [Google AI Studio](https://aistudio.google.com/)
3. Colócala en `.env`:

```ini
OPENROUTER_APIKEY=tu-api-key-aqui
```

4. Desde la app: Settings &rarr; IA &rarr; ingresa tu API key y selecciona el proveedor

### Variables de entorno

| Variable | Descripción |
|----------|-------------|
| `OPENROUTER_APIKEY` | API Key de OpenRouter |
| `GOOGLE_APIKEY` | API Key de Google AI Studio |

---

## 📚 Documentación

| Documento | Descripción |
|-----------|-------------|
| [`docs/user_guide.md`](docs/user_guide.md) | Guía de usuario completa &mdash; todas las vistas, controles y flujos |
| [`docs/architecture.md`](docs/architecture.md) | Arquitectura, flujo de datos, estructura del proyecto |
| [`docs/theming.md`](docs/theming.md) | Sistema de temas centralizado y guía para crear nuevos temas |
| [`docs/threading.md`](docs/threading.md) | Gestión de hilos y Thread Safety |
| [`docs/api.md`](docs/api.md) | API de proveedores IA (OpenRouter, Google AI Studio) |
| [`docs/building.md`](docs/building.md) | Compilación con PyInstaller |
| [`docs/tests.md`](docs/tests.md) | Tests y scripts de prueba |

---

## 🧪 Tests

```bash
python -m pytest test/ -v
```

Los tests requieren archivos de audio de ejemplo. Consulta [`docs/tests.md`](docs/tests.md) para más detalles.

---

## 🛠 Stack técnico

| Componente | Tecnología |
|------------|------------|
| **Lenguaje** | Python 3.10+ |
| **GUI** | PySide6 (Qt6) |
| **Audio I/O** | soundfile, sounddevice |
| **Procesamiento** | librosa, pyrubberband, numpy, scipy |
| **IA / LLM** | OpenRouter API, Google AI Studio, faster-whisper |
| **ChordPro** | python-chordpro |
| **Empaquetado** | PyInstaller |

---

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Haz [fork](https://github.com/bay122/stemplayer/fork) del proyecto
2. Crea una rama: `git checkout -b feature/nueva-funcionalidad`
3. Haz commit: `git commit -m 'feat: agregar nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abre un [Pull Request](https://github.com/bay122/stemplayer/pulls)

Lee [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) para más detalles.

---

## 💖 Apoyar

Si StemPlayer te es útil, considera:

- **Dar una estrella** &mdash; en [GitHub](https://github.com/bay122/stemplayer)
- **Reportar bugs** &mdash; abre un [issue](https://github.com/bay122/stemplayer/issues)
- **Compartir** &mdash; recomienda el proyecto a otros músicos
- **Donar** &mdash; activa las GitHub Sponsors para apoyar el desarrollo continuo

---

## 📄 Licencia

Este proyecto está bajo licencia **CC BY-NC-SA 4.0**.

**Puedes:**
- Compartir &mdash; copiar y redistribuir el material
- Adaptar &mdash; remezclar, transformar y construir sobre el material

**Siempre que:**
- **Atribución** &mdash; des crédito adecuado
- **No comercial** &mdash; no uses el material para fines comerciales
- **Compartir igual** &mdash; distribuyas tus contribuciones bajo la misma licencia

Lee el archivo [`LICENSE`](LICENSE) para los términos completos.

---

## 👤 Autor

**Pablo Jiménez**  
[GitHub](https://github.com/bay122) · [Web](https://pablo-jimenez.site) · [Email](mailto:pablo.jimenez@users.noreply.github.com)

---

<p align="center">
  <sub>Hecho con ❤️ para músicos</sub>
</p>
