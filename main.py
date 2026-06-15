import sys
import os
import argparse
from PySide6.QtWidgets import QApplication
from app.main_window import StemPlayer
from app.ext.loader import load_theme, load_layout


def main():
    parser = argparse.ArgumentParser(description="Stem Player")
    parser.add_argument(
        "-theme", type=str, default=None,
        help="Nombre del theme a usar (subcarpeta dentro de app/ext/themes/)"
    )
    args = parser.parse_args()

    theme = load_theme(args.theme) if args.theme else None
    layout_mod = load_layout(args.theme) if args.theme else None

    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ""
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

    try:
        app = QApplication(sys.argv)
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
