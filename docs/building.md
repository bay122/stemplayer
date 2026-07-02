# Compilación de StemPlayer

Este documento detalla los pasos para compilar StemPlayer en un ejecutable para Windows y Linux usando PyInstaller.

## Requisitos

- Python 3.10 o superior
- PyInstaller (`pip install pyinstaller`)
- Todas las dependencias del proyecto (`pip install -r requirements.txt`)

## Compilación (Linux)

```bash
# Activar entorno virtual
python -m venv penv
source penv/bin/activate
pip install -r requirements.txt
pip install pyinstaller

# Compilar
pyinstaller StemPlayer.spec

# El binario se genera en dist/StemPlayer/
```

## Compilación (Windows)

```powershell
# Activar entorno virtual
python -m venv penv
.\penv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller

# Compilar
pyinstaller StemPlayer.spec

# El ejecutable se genera en dist/StemPlayer/StemPlayer.exe
```

## Compilación manual

Si prefieres personalizar la compilación:

```bash
pyinstaller --name "StemPlayer" --windowed --add-data "icons/svgs:icons/svgs" main.py
```

### Parámetros:
- `--name "StemPlayer"`: Nombre del ejecutable
- `--windowed`: Evita la ventana de terminal (solo Windows)
- `--add-data "icons/svgs:icons/svgs"`: Incluye los iconos SVG en el empaquetado

## Notas

- El archivo `StemPlayer.spec` contiene la configuración exacta de compilación usada oficialmente.
- Para Linux se genera un binario en `dist/StemPlayer/`.
- Para Windows se genera `dist/StemPlayer/StemPlayer.exe`.
- La carpeta `dist/StemPlayer/` es portátil y se puede distribuir.
