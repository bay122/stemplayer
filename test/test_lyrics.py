import os
import sys
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.services.chord_analysis import ChordAnalysisThread
from PySide6.QtCore import QCoreApplication

def test():
    app = QCoreApplication([])
    
    # Simular stems dict (sin audio real por ahora para ver si el thread inicializa)
    stems = {
        "Guide": {"audio": np.zeros(44100*10), "category": "Other"},
        "Vocals": {"audio": np.zeros(44100*10), "category": "Other"}
    }
    
    thread = ChordAnalysisThread("test_folder", stems, 44100)
    
    def on_progress(msg):
        print(f"PROGRESS: {msg}")
        
    def on_finished(result):
        print("FINISHED!")
        print("Sections:", result["sections"])
        app.quit()
        
    def on_error(msg):
        print("ERROR:", msg)
        app.quit()
        
    thread.progress.connect(on_progress)
    thread.finished_analysis.connect(on_finished)
    thread.error.connect(on_error)
    
    thread.start()
    app.exec()

if __name__ == "__main__":
    test()
