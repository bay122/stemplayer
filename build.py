#!/usr/bin/env python3
import argparse
import os
import random
import re
import shutil
import string
import subprocess
import sys
import zipfile

VERSION_FILE = os.path.join(os.path.dirname(__file__), "app", "version.py")
SPEC_FILE = os.path.join(os.path.dirname(__file__), "StemPlayer.spec")
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
ICON_PNG = os.path.join(ASSETS_DIR, "icons", "icon.png")
ICON_ICO = os.path.join(ASSETS_DIR, "icons", "icon.ico")


def read_version():
    with open(VERSION_FILE, encoding="utf-8") as f:
        content = f.read()
    m = re.search(r'^APP_VERSION\s*=\s*"([^"]+)"', content, re.MULTILINE)
    if not m:
        print("Error: no se pudo leer APP_VERSION desde app/version.py")
        sys.exit(1)
    return m.group(1)


def write_version(new_version: str):
    with open(VERSION_FILE, encoding="utf-8") as f:
        content = f.read()
    content = re.sub(
        r'^APP_VERSION\s*=\s*"[^"]+"',
        f'APP_VERSION = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Version actualizada a {new_version}")


def bump_version(current: str, part: str) -> str:
    major, minor, patch = map(int, current.split("."))
    if part == "major":
        return f"{major + 1}.0.0"
    elif part == "minor":
        return f"{major}.{minor + 1}.0"
    elif part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        print(f"Error: parte desconocida '{part}'. Usa: patch, minor, major")
        sys.exit(1)


def cmd_bump(args):
    current = read_version()
    new_version = bump_version(current, args.part)
    write_version(new_version)


def cmd_version(args):
    print(read_version())


def clean_build():
    for d in ("build", "dist"):
        path = os.path.join(os.path.dirname(__file__), d)
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"Limpiado {d}/")


def clean_dist_stemplayer():
    path = os.path.join(os.path.dirname(__file__), "dist", "StemPlayer")
    if not os.path.exists(path):
        return
    print("Limpiando dist/StemPlayer/...")
    try:
        shutil.rmtree(path)
        return
    except Exception as e:
        print(f"  shutil.rmtree falló: {e}")

    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    tmp = path + "_old_" + suffix
    try:
        os.rename(path, tmp)
        print(f"  Directorio renombrado a: {tmp}")
    except Exception as e:
        print(f"  No se pudo limpiar ni renombrar: {e}")
        print("  (Se continuará de todas formas)")


def run_pyinstaller():
    print("Ejecutando PyInstaller...")
    clean_dist_stemplayer()
    subprocess.check_call(
        [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", SPEC_FILE],
        cwd=os.path.dirname(__file__),
    )


def package_linux(version: str, out_dir: str):
    print("Empaquetando para Linux (.deb)...")
    base_dir = os.path.dirname(__file__)
    dist_dir = os.path.join(base_dir, "dist", "StemPlayer")
    deb_dir = os.path.join(base_dir, "dist", "debian")

    if not os.path.isdir(dist_dir):
        print("Error: no se encuentra dist/StemPlayer. Compila primero.")
        sys.exit(1)

    debian_dir = os.path.join(deb_dir, "DEBIAN")
    opt_dir = os.path.join(deb_dir, "opt", "stemplayer")
    bin_dir = os.path.join(deb_dir, "usr", "bin")
    apps_dir = os.path.join(deb_dir, "usr", "share", "applications")
    icons_dir = os.path.join(deb_dir, "opt", "stemplayer", "icons")

    os.makedirs(debian_dir, exist_ok=True)
    os.makedirs(opt_dir, exist_ok=True)
    os.makedirs(bin_dir, exist_ok=True)
    os.makedirs(apps_dir, exist_ok=True)
    os.makedirs(icons_dir, exist_ok=True)

    shutil.copytree(dist_dir, opt_dir, dirs_exist_ok=True)

    shutil.copy2(ICON_PNG, os.path.join(icons_dir, "icon.png"))

    control = f"""Package: stemplayer
Version: {version}
Section: sound
Priority: optional
Architecture: amd64
Depends: libc6
Maintainer: Pablo Jiménez <pablo.jimenez@users.noreply.github.com>
Description: StemPlayer - Reproductor y mezclador de stems de audio
"""
    with open(os.path.join(debian_dir, "control"), "w", encoding="utf-8") as f:
        f.write(control)

    launcher = "#!/bin/sh\nexec /opt/stemplayer/StemPlayer \"$@\"\n"
    launcher_path = os.path.join(bin_dir, "stemplayer")
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write(launcher)
    os.chmod(launcher_path, 0o755)

    desktop = f"""[Desktop Entry]
Name=StemPlayer
Exec=/usr/bin/stemplayer
Type=Application
Categories=AudioVideo;Audio;Player;
Comment=Reproductor y mezclador de stems de audio
Terminal=false
Icon=/opt/stemplayer/icons/icon.png
"""
    with open(os.path.join(apps_dir, "stemplayer.desktop"), "w", encoding="utf-8") as f:
        f.write(desktop)

    for root, dirs, files in os.walk(deb_dir):
        for d in dirs:
            os.chmod(os.path.join(root, d), 0o755)

    deb_name = f"stemplayer_{version}_amd64.deb"
    deb_path = os.path.join(out_dir, deb_name)
    subprocess.check_call(
        ["dpkg-deb", "--build", deb_dir, deb_path],
        cwd=base_dir,
    )
    shutil.rmtree(deb_dir)
    print(f"Paquete .deb creado: {deb_path}")


def package_windows(version: str, out_dir: str):
    print("Empaquetando para Windows (.zip)...")
    base_dir = os.path.dirname(__file__)
    dist_dir = os.path.join(base_dir, "dist", "StemPlayer")

    if not os.path.isdir(dist_dir):
        print("Error: no se encuentra dist/StemPlayer. Compila primero.")
        sys.exit(1)

    icon_png_dest = os.path.join(dist_dir, "icon.png")
    if os.path.exists(ICON_PNG) and not os.path.exists(icon_png_dest):
        shutil.copy2(ICON_PNG, icon_png_dest)

    icon_ico_dest = os.path.join(dist_dir, "icon.ico")
    if os.path.exists(ICON_ICO) and not os.path.exists(icon_ico_dest):
        shutil.copy2(ICON_ICO, icon_ico_dest)

    zip_name = f"StemPlayer-v{version}-win64.zip"
    zip_path = os.path.join(out_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, dist_dir)
                zf.write(file_path, arcname)
    print(f"ZIP creado: {zip_path}")


def cmd_build(args):
    version = read_version()
    base_dir = os.path.dirname(__file__)
    out_dir = os.path.join(base_dir, args.out) if not os.path.isabs(args.out) else args.out
    os.makedirs(out_dir, exist_ok=True)

    if args.clean:
        clean_build()

    run_pyinstaller()

    if sys.platform == "win32":
        package_windows(version, out_dir)
    else:
        package_linux(version, out_dir)


def main():
    parser = argparse.ArgumentParser(description="StemPlayer - Build & version tool")
    sub = parser.add_subparsers(dest="command", required=True)

    build_p = sub.add_parser("build", help="Compila y empaqueta para la plataforma actual")
    build_p.add_argument("--out", default="dist", help="Directorio de salida (default: dist/)")
    build_p.add_argument("--clean", action="store_true", help="Limpia build/ y dist/ antes de compilar")
    build_p.set_defaults(func=cmd_build)

    bump_p = sub.add_parser("bump", help="Incrementa la versión")
    bump_p.add_argument("part", choices=["patch", "minor", "major"], help="Qué parte incrementar")
    bump_p.set_defaults(func=cmd_bump)

    ver_p = sub.add_parser("version", help="Muestra la versión actual")
    ver_p.set_defaults(func=cmd_version)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
