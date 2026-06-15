"""Estado centralizado de la aplicación."""


class StateManager:
    """Mantiene y notifica cambios en el estado global de la aplicación."""

    def __init__(self):
        self.mix_sr = 44100
        self.stems = {}
        self.originals = {}
        self.detected_key = "C"
        self.detected_bpm = 120
        self.current_pitch_shift = 0
        self.current_tempo_ratio = 1.0
        self.count_in_bars = 0
        self.click_during_playback = False
        self.metronome_volume = 0.5
        self.metronome_pan = 0.0
        self.master_volume = 1.0
        self.current_song_name = ""
        self.current_song_artist = ""
        self.has_unsaved_changes = False
        self.history = []
        self.history_idx = -1
        self.saved_history_idx = -1
        self.current_song_source = ""
        self.is_playing = False
        self.current_pos = 0

    @property
    def current_song_folder(self) -> str:
        return getattr(self, '_current_song_folder', '')

    @current_song_folder.setter
    def current_song_folder(self, val: str):
        self._current_song_folder = val

    @property
    def stem_order(self) -> list:
        return getattr(self, '_stem_order', [])

    @stem_order.setter
    def stem_order(self, val: list):
        self._stem_order = val

    @property
    def click_offset_samples(self) -> int:
        return getattr(self, '_click_offset_samples', 0)

    @click_offset_samples.setter
    def click_offset_samples(self, val: int):
        self._click_offset_samples = val

    def reset_song(self):
        self.stems = {}
        self.originals = {}
        self.detected_key = "C"
        self.detected_bpm = 120
        self.current_pitch_shift = 0
        self.current_tempo_ratio = 1.0
        self.count_in_bars = 0
        self.click_during_playback = False
        self.metronome_volume = 0.5
        self.metronome_pan = 0.0
        self.master_volume = 1.0
        self.current_song_name = ""
        self.current_song_artist = ""
        self.has_unsaved_changes = False
        self.history = []
        self.history_idx = -1
        self.saved_history_idx = -1
        self.current_song_source = ""
        self.is_playing = False
        self.current_pos = 0
        self._current_song_folder = ''
        self._stem_order = []
        self._click_offset_samples = 0
