# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('icons/svgs', 'icons/svgs')],
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
