import threading
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QThread, Signal


class PlaybackThread(QThread):
    """Hilo para reproducir audio en tiempo real."""

    update_progress = Signal(float)
    peak_level = Signal(float)

    def __init__(self, stems: dict, bpm: int, mix_sr: int = 44100,
                 count_in_bars: int = 0, click_during_playback: bool = False,
                 master_volume: float = 1.0, metronome_volume: float = 0.5,
                 metronome_pan: float = 0.0, click_offset_samples: int = 0):
        super().__init__()
        self.stems = stems
        self.bpm = bpm if bpm > 0 else 120
        self.mix_sr = mix_sr
        self.count_in_bars = count_in_bars
        self.click_during_playback = click_during_playback
        self.master_volume = master_volume
        self.metronome_volume = metronome_volume
        self.metronome_pan = metronome_pan
        self.click_offset_samples = click_offset_samples
        self.is_playing = False
        self._stop = False
        self._seek_pos = None
        self._seek_lock = threading.Lock()
        self.current_pos = 0

    def seek(self, new_pos_samples: int):
        with self._seek_lock:
            self._seek_pos = max(0, new_pos_samples)

    def set_master_volume(self, vol: float):
        self.master_volume = vol

    def set_metronome_volume(self, vol: float):
        self.metronome_volume = vol

    def set_metronome_pan(self, pan: float):
        self.metronome_pan = pan

    def _is_beat(self, pos: int, beat_sample: int, click_samples: int) -> bool:
        shifted_pos = pos - self.click_offset_samples
        return shifted_pos % beat_sample < click_samples

    def _generate_click(self, click_samples, sr):
        t = np.arange(click_samples) / sr
        freq = 440
        envelope = np.exp(-t * 80)
        wave = np.sin(2 * np.pi * freq * t)
        click = wave * envelope
        click = np.convolve(click, np.ones(15)/15, mode='same')
        click = click / np.max(np.abs(click)) * 0.4
        return click

    def run(self):
        if not self.stems:
            return

        max_len = max(len(s["audio"]) for s in self.stems.values())
        beats_per_bar = 4
        count_in_beats = self.count_in_bars * beats_per_bar
        count_in_samples = int(count_in_beats * self.mix_sr * 60 / self.bpm) if count_in_beats > 0 else 0

        total_samples = max_len + count_in_samples
        click_track = np.zeros(total_samples)
        beat_sample = int(self.mix_sr * 60 / self.bpm)

        click_duration = 0.13
        click_samples = int(click_duration * self.mix_sr)
        click_base = self._generate_click(click_samples, self.mix_sr)

        for i in range(0, total_samples, beat_sample):
            end_idx = min(i + click_samples, total_samples)
            segment_len = end_idx - i
            click_track[i:end_idx] = click_base[:segment_len]

        blocksize = 1024
        pos = 0
        self.is_playing = True

        with sd.OutputStream(samplerate=self.mix_sr, channels=2, blocksize=blocksize) as stream:
            while self.is_playing and not self._stop and pos < total_samples:
                with self._seek_lock:
                    if self._seek_pos is not None:
                        pos = self._seek_pos
                        self._seek_pos = None

                self.current_pos = pos

                out = np.zeros((blocksize, 2))
                end = min(pos + blocksize, total_samples)

                if self.click_during_playback or pos < count_in_samples:
                    segment = click_track[pos:end]

                    pan = self.metronome_pan
                    pan_l = 1.0 - pan if pan >= 0 else 1.0
                    pan_r = 1.0 if pan >= 0 else 1.0 + pan

                    out[:len(segment), 0] += segment * self.metronome_volume * pan_l
                    out[:len(segment), 1] += segment * self.metronome_volume * pan_r

                if end > count_in_samples:
                    start_stem = max(0, pos - count_in_samples)
                    end_stem = min(start_stem + blocksize, max_len)

                    any_solo = any(s["solo"] for s in self.stems.values())

                    for s in self.stems.values():
                        if s["muted"] or (any_solo and not s["solo"]):
                            continue

                        audio = s["audio"]
                        if start_stem < len(audio):
                            seg_end = min(end_stem, len(audio))
                            segment = audio[start_stem:seg_end] * s["volume"]

                            pan = s.get("pan", 0.0)
                            pan_l = 1.0 - pan if pan >= 0 else 1.0
                            pan_r = 1.0 if pan >= 0 else 1.0 + pan

                            out[:len(segment), 0] += segment * pan_l * self.master_volume
                            out[:len(segment), 1] += segment * pan_r * self.master_volume

                stream.write(out.astype(np.float32))

                peak = np.max(np.abs(out))
                self.peak_level.emit(float(peak))

                pos += blocksize
                self.update_progress.emit(min(1.0, pos / total_samples))

        self.is_playing = False

    def stop(self):
        self._stop = True
        self.is_playing = False
