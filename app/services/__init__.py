import json
import os
import time


def _log(scope: str, message: str):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}][{scope}] {message}", flush=True)


def create_sync_file(sections: list, output_path: str) -> bool:
    try:
        sync_data = {
            "sections": [
                {
                    "label": sec.get("label", ""),
                    "start": float(sec.get("start", 0.0)),
                    "end": float(sec.get("end", sec.get("start", 0.0) + 10.0)),
                    "duration": float(sec.get("end", sec.get("start", 0.0) + 10.0)) - float(sec.get("start", 0.0))
                }
                for sec in sections
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(sync_data, f, indent=2, ensure_ascii=False)

        _log("SyncFile", f"Archivo de sincronización guardado: {output_path}")
        return True
    except Exception as exc:
        _log("SyncFile", f"Error al guardar sync.json: {exc}")
        return False
