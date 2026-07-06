# -*- mode: python ; coding: utf-8 -*-
import os
import sys

# Embeber ffmpeg para que el splash funcione en builds sin depender
# de que el usuario lo tenga instalado en el sistema.
#   - Windows: colocar ffmpeg.exe en bin/ffmpeg.exe (descargable desde
#     https://github.com/BtbN/FFmpeg-Builds/releases, build gpl-shared
#     o gpl, solo el .exe esencial).
#   - Linux: usar el binario del sistema (/usr/bin/ffmpeg) o uno estático
#     colocado en bin/ffmpeg.
# PyInstaller expone el path del spec actual en la variable global SPEC.
try:
    _spec_dir = os.path.dirname(os.path.abspath(SPEC))
except NameError:
    _spec_dir = os.path.dirname(os.path.abspath('StemPlayer.spec'))
_ffmpeg_name = 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg'
_local_ffmpeg = os.path.join(_spec_dir, 'bin', _ffmpeg_name)
_system_ffmpeg = '/usr/bin/ffmpeg' if sys.platform != 'win32' else None

_binaries = []
if os.path.exists(_local_ffmpeg):
    _binaries.append((_local_ffmpeg, '.'))
elif _system_ffmpeg and os.path.exists(_system_ffmpeg):
    _binaries.append((_system_ffmpeg, '.'))


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=_binaries,
    datas=[
        ('assets/icons/icon.png', 'assets/icons'),
        ('assets/icons/fav/apple-icon-180x180.png', 'assets/icons/fav'),
        ('assets/icons/fav/android-icon-192x192.png', 'assets/icons/fav'),
        ('assets/icons/fav/favicon-96x96.png', 'assets/icons/fav'),
        ('assets/icons/fav/ms-icon-144x144.png', 'assets/icons/fav'),
        ('assets/splash/splash.mp4', 'assets/splash'),
        ('assets/splash/splash.png', 'assets/splash'),
        ('assets/splash/splash_audio.wav', 'assets/splash'),
        ('icons/svgs', 'icons'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tensorflow', 'tensorflow_hub',
        'torch', 'torchvision', 'torchaudio',
        'timm',
        'transformers',
        'onnxruntime', 'onnx',
        'pandas',
        'sklearn',
        'h5py',
        'cv2',
        'yt_dlp',
        'openpyxl',
        'lxml',
        'jinja2',
        'rich',
        'tqdm',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StemPlayer',
	icon='assets/icons/icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StemPlayer',
)
