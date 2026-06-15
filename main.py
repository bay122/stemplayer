import sys
import traceback
import os
from PySide6.QtWidgets import QApplication
from gui import StemPlayer

if __name__ == "__main__":
    # Asegura que Qt use el plugin correcto
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = ""
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
    
    try:
        app = QApplication(sys.argv)
        
        # Forzar el tamaño inicial antes de mostrar
        player = StemPlayer()
        player.resize(1400, 800)
        
        # Centrar la ventana en la pantalla activa
        screen_geometry = app.primaryScreen().availableGeometry()
        window_geometry = player.frameGeometry()
        window_geometry.moveCenter(screen_geometry.center())
        
        # Asegurarnos de que no aparezca en coordenadas negativas si la pantalla es muy chica
        x = max(0, window_geometry.topLeft().x())
        y = max(0, window_geometry.topLeft().y())
        player.move(x, y)
        
        player.show()
        player.activateWindow()
        player.raise_()
        
        sys.exit(app.exec())
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        input("Presiona Enter para salir...")
        sys.exit(1)
