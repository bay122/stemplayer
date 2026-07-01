import sys
import os
import argparse
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.main_window import StemPlayer
from app.ext.loader import load_theme, load_layout


SPLASH_VIDEO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets", "splash", "splash3.mp4"
)
SPLASH_IMAGE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets", "splash", "splash.png"
)
ICON_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets", "icons", "icon.png"
)
ICON_FAV_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "assets", "icons", "fav"
)


def main():
    parser = argparse.ArgumentParser(description="Stem Player")
    parser.add_argument(
        "-theme", type=str, default=None,
        help="Nombre del theme a usar (subcarpeta dentro de app/ext/themes/)"
    )
    parser.add_argument(
        "-no-splash", action="store_true",
        help="Desactivar la pantalla de splash inicial"
    )
    args = parser.parse_args()

    theme = load_theme(args.theme) if args.theme else None
    layout_mod = load_layout(args.theme) if args.theme else None

    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ""
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

    try:
        app = QApplication(sys.argv)

        # Configurar icono de la app desde assets/icons/fav
        for fname in ("apple-icon-180x180.png", "android-icon-192x192.png",
                      "icon.png", "favicon-96x96.png", "ms-icon-144x144.png"):
            candidate = (
                os.path.join(ICON_FAV_DIR, fname)
                if fname != "icon.png" else ICON_PATH
            )
            if os.path.exists(candidate):
                app.setWindowIcon(QIcon(candidate))
                break

        # Mostrar splash screen
        splash = None
        if not args.no_splash:
            try:
                from app.ui.splash_screen import SplashScreen
                from app.data.config_manager import ConfigManager
                config = ConfigManager()
                splash_muted = config.get_splash_muted()
                if os.path.exists(SPLASH_VIDEO):
                    splash = SplashScreen(
                        video_path=SPLASH_VIDEO,
                        image_path=SPLASH_IMAGE,
                        muted=splash_muted,
                    )
                elif os.path.exists(SPLASH_IMAGE):
                    splash = SplashScreen(image_path=SPLASH_IMAGE)
                if splash is not None:
                    splash.mute_toggled.connect(
                        lambda m: config.set_splash_muted(m)
                    )
                    splash.show()
                    app.processEvents()
            except Exception as e:
                print(f"No se pudo cargar splash: {e}")
                splash = None

        # Cerrar splash: video termina (con fadeout) o fallback de seguridad
        if splash is not None:
            splash.finished.connect(splash.close_splash)
            QTimer.singleShot(12000, splash.close_splash)

        player = StemPlayer(theme=theme)
        player.resize(1400, 800)

        if layout_mod is not None:
            layout_mod.apply_layout(player)

        screen_geometry = app.primaryScreen().availableGeometry()
        window_geometry = player.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())

        x = max(0, window_geometry.topLeft().x())
        y = max(0, window_geometry.topLeft().y())
        player.move(x, y)

        player.show()
        player.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        player.destroyed.connect(splash.close_splash)
        player.activateWindow()
        player.raise_()

        sys.exit(app.exec())
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("Presiona Enter para salir...")
        sys.exit(1)


if __name__ == "__main__":
    main()
