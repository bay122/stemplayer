import os
import re
import subprocess as sp
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QWidget, QApplication, QCheckBox
from PySide6.QtGui import QPainter, QImage, QPixmap, QColor
import sounddevice as sd
import soundfile as sf
import numpy as np


FADE_DURATION = 1000


class SplashScreen(QWidget):
    finished = Signal()
    mute_toggled = Signal(bool)

    def __init__(self, video_path=None, image_path=None, parent=None,
                 ffmpeg_bin="ffmpeg", muted=False):
        super().__init__(
            parent,
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setFixedSize(640, 480)

        self._ffmpeg_bin = ffmpeg_bin
        self._ffmpeg_proc = None
        self._frame_pixmap = None
        self._audio_cache = None
        self._muted = muted
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._read_frame)
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._fade_step)
        self._fade_elapsed = 0

        self._audio_data = None
        self._audio_sr = None
        self._audio_pos = 0
        self._audio_stream = None

        self._mute_checkbox = QCheckBox("Silenciar", self)
        self._mute_checkbox.setChecked(muted)
        self._mute_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 11px;
                background: rgba(0, 0, 0, 120);
                padding: 3px 6px;
                border-radius: 3px;
            }
            QCheckBox::indicator {
                width: 12px;
                height: 12px;
            }
        """)
        self._mute_checkbox.stateChanged.connect(self._on_mute_toggled)
        self._mute_checkbox.move(8, self.height() - 24)

        if video_path and os.path.exists(video_path):
            self._start_video_pipe(video_path)
            self._audio_cache = self._cache_audio(video_path)
        elif image_path and os.path.exists(image_path):
            pix = QPixmap(image_path)
            if not pix.isNull():
                self._frame_pixmap = pix.scaled(
                    640, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )

        if QApplication.instance() is not None:
            screen = QApplication.primaryScreen().geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2
            )

    def showEvent(self, event):
        super().showEvent(event)
        if self._audio_cache:
            QTimer.singleShot(0, self._start_audio)

    def _on_mute_toggled(self, state):
        self._muted = bool(state)
        self.mute_toggled.emit(self._muted)

    def _cache_audio(self, video_path):
        cache_path = os.path.splitext(video_path)[0] + "_audio.wav"
        if not os.path.exists(cache_path):
            sp.run(
                [self._ffmpeg_bin, "-i", video_path, "-vn",
                 "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
                 cache_path, "-y"],
                stdout=sp.DEVNULL, stderr=sp.DEVNULL, check=False
            )
        return cache_path if os.path.getsize(cache_path) > 44 else None

    def _start_audio(self):
        if self._audio_cache is None:
            return
        try:
            self._audio_data, self._audio_sr = sf.read(self._audio_cache)
        except Exception as e:
            print(f"[Splash] Error cargando audio: {e}")
            return
        self._audio_pos = 0
        self._audio_stream = sd.OutputStream(
            samplerate=self._audio_sr,
            channels=self._audio_data.shape[1] if self._audio_data.ndim > 1 else 1,
            callback=self._audio_callback,
            blocksize=4096,
        )
        self._audio_stream.start()

    def _audio_callback(self, outdata, frames, time, status):
        if status:
            print(status)
        if self._muted or self._audio_data is None:
            outdata.fill(0)
            return
        start = self._audio_pos
        end = start + frames
        chunk = self._audio_data[start:end]
        self._audio_pos = end
        if len(chunk) < frames:
            outdata[:len(chunk)] = chunk
            outdata[len(chunk):].fill(0)
        else:
            outdata[:] = chunk

    def _get_video_fps(self, video_path):
        try:
            result = sp.run(
                [self._ffmpeg_bin, "-i", video_path, "-f", "null", "-"],
                stdout=sp.DEVNULL, stderr=sp.PIPE,
                text=True, check=False
            )
            match = re.search(r'(\d+(?:\.\d+)?)\s*fps', result.stderr)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return None

    def _start_video_pipe(self, video_path):
        try:
            fps = self._get_video_fps(video_path)
            interval = int(1000 / fps) if fps else 33
            self._frame_timer.start(interval)
            self._ffmpeg_proc = sp.Popen(
                [self._ffmpeg_bin, "-i", video_path, "-f", "rawvideo",
                 "-pix_fmt", "rgb24", "-s", "640x480", "-"],
                stdout=sp.PIPE, stderr=sp.DEVNULL,
                bufsize=640 * 480 * 3 * 4
            )
            self._frame_size = 640 * 480 * 3
        except Exception as e:
            print(f"[Splash] Error al iniciar ffmpeg: {e}")
            self._ffmpeg_proc = None

    def _read_frame(self):
        if self._ffmpeg_proc is None or self._ffmpeg_proc.stdout is None:
            self._end_playback()
            return

        raw = self._ffmpeg_proc.stdout.read(self._frame_size)

        if len(raw) < self._frame_size:
            self._end_playback()
            return

        image = QImage(raw, 640, 480, 640 * 3, QImage.Format_RGB888).copy()
        self._frame_pixmap = QPixmap.fromImage(image)
        self.update()

    def _end_playback(self):
        self._frame_timer.stop()
        if self._ffmpeg_proc:
            try:
                self._ffmpeg_proc.terminate()
                self._ffmpeg_proc.wait(2)
            except Exception:
                pass
            self._ffmpeg_proc = None
        self._stop_audio()
        self._start_fadeout()

    def _start_fadeout(self):
        self._fade_elapsed = 0
        self._fade_timer.start(16)

    def _fade_step(self):
        self._fade_elapsed += 16
        progress = min(self._fade_elapsed / FADE_DURATION, 1.0)
        self.setWindowOpacity(max(0.0, 1.0 - progress))
        if progress >= 1.0:
            self._fade_timer.stop()
            self.finished.emit()
            self.close()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._frame_pixmap is not None:
            painter.drawPixmap(self.rect(), self._frame_pixmap)
        else:
            painter.fillRect(self.rect(), QColor("#0b0f12"))

    def _stop_audio(self):
        if self._audio_stream is not None:
            try:
                self._audio_stream.stop()
                self._audio_stream.close()
            except Exception:
                pass
            self._audio_stream = None

    def close_splash(self):
        self._fade_timer.stop()
        self._frame_timer.stop()
        if self._ffmpeg_proc:
            try:
                self._ffmpeg_proc.terminate()
                self._ffmpeg_proc.wait(2)
            except Exception:
                pass
            self._ffmpeg_proc = None
        self._stop_audio()
        self.setWindowOpacity(1.0)
        self.close()
