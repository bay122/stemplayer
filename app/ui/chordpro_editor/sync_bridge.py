import json
import os

from PySide6.QtCore import QObject, QTimer


class SyncBridge(QObject):
    """Polls playback position and highlights the current section.

    The bridge is inactive (no errors) if sync_path is missing or the
    sync.json cannot be parsed.
    """

    def __init__(self, section_panel, main_window, sync_path: str | None):
        super().__init__()
        self._section_panel = section_panel
        self._main = main_window
        self._sync_path = sync_path
        self._sections = []  # list of {"name": str, "start": float, "end": float}
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._tick)
        self._load_sync()

    def _load_sync(self):
        if not self._sync_path or not os.path.exists(self._sync_path):
            return
        try:
            with open(self._sync_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        sections = data.get("sections") or data.get("data") or []
        for sec in sections:
            name = sec.get("name") or sec.get("title") or ""
            start = sec.get("start") or sec.get("start_time") or 0.0
            end = sec.get("end") or sec.get("end_time") or start
            try:
                start = float(start)
                end = float(end)
            except (TypeError, ValueError):
                continue
            if name:
                self._sections.append({"name": name, "start": start, "end": end})

    def start(self):
        if self._sections:
            self._timer.start()

    def stop(self):
        self._timer.stop()

    def _current_position_seconds(self) -> float:
        m = self._main
        thread = getattr(m, "threads", None)
        playback = getattr(thread, "playback_thread", None) if thread else None
        if playback is None:
            return 0.0
        pos_samples = getattr(playback, "position_samples", 0) or 0
        sr = getattr(m.state, "mix_sr", 44100) or 44100
        return pos_samples / sr

    def _tick(self):
        if not self._sections:
            return
        t = self._current_position_seconds()
        idx = -1
        for i, sec in enumerate(self._sections):
            if sec["start"] <= t <= sec["end"]:
                idx = i
                break
            if sec["start"] > t:
                break
        if idx < 0:
            return
        if self._section_panel.current_index() != idx:
            self._section_panel.set_current_index(idx)
        self._section_panel.highlight_index(idx)
