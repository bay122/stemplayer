import os
import re
import shutil
import subprocess as sp
import sys
import tempfile
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QWidget, QApplication, QCheckBox
from PySide6.QtGui import QPainter, QImage, QPixmap, QColor
import sounddevice as sd
import soundfile as sf

FADE_DURATION = 500
WIDGET_W, WIDGET_H = 640, 480


def _no_window_kwargs():
    """Argumentos extra para subprocess en Windows que ocultan la ventana CMD.

    En Windows, subprocess.Popen abre una ventana de consola al ejecutar un
    binario aunque redirijamos stdout/stderr. Esto causa parpadeos de CMD
    y posibles AppHang cuando hay varios procesos a la vez.
    Con CREATE_NO_WINDOW la ventana nunca se crea.
    """
    if os.name == "nt":
        return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW
    return {}


def _resolve_ffmpeg_bin(ffmpeg_bin):
    """Resuelve la ruta al binario de ffmpeg.

    Prioriza:
      1. La ruta explícita pasada como argumento.
      2. ffmpeg[.exe] dentro de sys._MEIPASS (binario embebido por PyInstaller).
      3. ffmpeg en PATH del sistema.
    Retorna None si no se encuentra ffmpeg.
    """
    if ffmpeg_bin:
        if os.path.isabs(ffmpeg_bin) and os.path.exists(ffmpeg_bin):
            return ffmpeg_bin
        found = shutil.which(ffmpeg_bin)
        if found:
            return found
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        candidate = os.path.join(meipass, exe_name)
        if os.path.exists(candidate):
            return candidate
    return shutil.which("ffmpeg")


class SplashScreen(QWidget):
    finished = Signal()
    mute_toggled = Signal(bool)

    def __init__(self, video_path=None, image_path=None, parent=None,
                 ffmpeg_bin=None, muted=False):
        super().__init__(
            parent,
            Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint
        )
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self.setFixedSize(WIDGET_W, WIDGET_H)

        self._ffmpeg_bin = _resolve_ffmpeg_bin(ffmpeg_bin)
        self._ffmpeg_proc = None
        self._frame_pixmap = None
        self._muted = muted
        self._video_path = video_path
        self._audio_cache_dir = tempfile.gettempdir()

        # --- Estado del Video ---
        self._fps = 30.0
        self._frame_size = WIDGET_W * WIDGET_H * 3
        self._current_frame = 0  # Lleva la cuenta de qué frame hemos leído
        self._frame_timer = QTimer(self)
        self._frame_timer.timeout.connect(self._read_frame)

        # --- Estado del Audio ---
        self._audio_cache = None
        self._audio_data = None
        self._audio_sr = None
        self._audio_pos = 0  # Se actualiza desde el hilo de audio (reloj maestro)
        self._audio_stream = None

        # --- Fade ---
        self._fade_timer = QTimer(self)
        self._fade_timer.timeout.connect(self._fade_step)
        self._fade_elapsed = 0

        # --- Checkbox ---
        self._mute_checkbox = QCheckBox("Silenciar", self)
        self._mute_checkbox.setChecked(muted)
        self._mute_checkbox.setStyleSheet("""
            QCheckBox {
                color: white; font-size: 11px;
                background: rgba(0,0,0,120);
                padding: 3px 6px; border-radius: 3px;
            }
            QCheckBox::indicator { width: 12px; height: 12px; }
        """)
        self._mute_checkbox.stateChanged.connect(self._on_mute_toggled)
        self._mute_checkbox.move(8, self.height() - 24)

        # --- Pre-cálculos (sin iniciar reproducción aún) ---
        if video_path and os.path.exists(video_path) and self._ffmpeg_bin:
            self._fps = self._get_video_fps(video_path) or 30.0
            self._audio_cache = self._cache_audio(video_path)
        elif image_path and os.path.exists(image_path):
            pix = QPixmap(image_path)
            if not pix.isNull():
                self._frame_pixmap = pix.scaled(
                    WIDGET_W, WIDGET_H, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )

        if QApplication.instance() is not None:
            screen = QApplication.primaryScreen().geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2
            )

    # ═══════════════ INICIO SINCRONIZADO ═══════════════

    def showEvent(self, event):
        super().showEvent(event)
        # Iniciar video y audio EXACTAMENTE al mismo tiempo
        if self._video_path and self._ffmpeg_proc is None:
            self._start_playback()

    def _start_playback(self):
        self._current_frame = 0

        # Si no hay ffmpeg disponible, no podemos reproducir video.
        # Cerramos el splash de inmediato para no bloquear el arranque.
        if not self._ffmpeg_bin:
            QTimer.singleShot(0, self._start_fadeout)
            return

        # 1. Iniciar pipe de video
        try:
            self._ffmpeg_proc = sp.Popen(
                [self._ffmpeg_bin, "-i", self._video_path,
                 "-f", "rawvideo", "-pix_fmt", "rgb24",
                 "-s", f"{WIDGET_W}x{WIDGET_H}", "-"],
                stdout=sp.PIPE, stderr=sp.DEVNULL,
                bufsize=self._frame_size * 4,
                **_no_window_kwargs(),
            )
        except Exception as e:
            print(f"[Splash] Error iniciando ffmpeg: {e}")
            self._ffmpeg_proc = None
            QTimer.singleShot(0, self._start_fadeout)
            return

        # 2. Iniciar audio
        if self._audio_cache:
            self._start_audio()

        # 3. Iniciar timer
        interval = int(1000 / self._fps)
        self._frame_timer.start(interval)

    # ═══════════════ AUDIO (RELOJ MAESTRO) ═══════════════

    def _cache_audio(self, video_path):
        if not self._ffmpeg_bin:
            return None
        # En builds de PyInstaller onefile, _MEIPASS es de sólo lectura, así
        # que escribimos el cache en el directorio temporal. En desarrollo y
        # en builds onedir sí podemos escribir al lado del video.
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass and os.path.normpath(os.path.dirname(video_path)) == os.path.normpath(meipass):
            cache_path = os.path.join(self._audio_cache_dir, "stemplayer_splash_audio.wav")
        else:
            cache_path = os.path.splitext(video_path)[0] + "_audio.wav"
        if not os.path.exists(cache_path):
            try:
                sp.run(
                    [self._ffmpeg_bin, "-i", video_path, "-vn",
                     "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
                     cache_path, "-y"],
                    stdout=sp.DEVNULL, stderr=sp.DEVNULL, check=False,
                    **_no_window_kwargs(),
                )
            except Exception as e:
                print(f"[Splash] Error generando cache de audio: {e}")
                return None
        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 44:
            return cache_path
        return None

    def _start_audio(self):
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

    def _audio_callback(self, outdata, frames, time_info, status):
        if self._audio_data is None:
            outdata.fill(0)
            return
    
        start = self._audio_pos
        end = start + frames
        self._audio_pos = end  # ← Siempre avanza, incluso en mute
    
        if self._muted:
            outdata.fill(0)   # Silencio, pero el reloj ya avanzó
            return
    
        chunk = self._audio_data[start:end]
        if len(chunk) < frames:
            outdata[:len(chunk)] = chunk
            outdata[len(chunk):].fill(0)
        else:
            outdata[:] = chunk

    # ═══════════════ VIDEO (ESCLAVO DEL AUDIO) ═══════════════

    def _get_video_fps(self, video_path):
        try:
            result = sp.run(
                [self._ffmpeg_bin, "-i", video_path, "-f", "null", "-"],
                stdout=sp.DEVNULL, stderr=sp.PIPE, text=True, check=False,
                **_no_window_kwargs(),
            )
            match = re.search(r'(\d+(?:\.\d+)?)\s*fps', result.stderr)
            if match:
                return float(match.group(1))
        except Exception:
            pass
        return None

    def _read_frame(self):
        if self._ffmpeg_proc is None:
            self._end_playback()
            return

        # --- SINCRONIZACIÓN ---
        # Calcular qué frame DEBERÍA mostrarse según el reloj del audio
        if self._audio_data is not None and self._audio_sr > 0:
            elapsed_sec = self._audio_pos / self._audio_sr
            target_frame = int(elapsed_sec * self._fps)
        else:
            # Si no hay audio, avanzar normal
            target_frame = self._current_frame

        # Si el video va adelantado al audio, esperamos (no leemos nuevo frame)
        if self._current_frame > target_frame:
            return

        # Leer frames, saltando los que ya pasaron para alcanzar al audio
        raw = None
        while self._current_frame <= target_frame:
            raw = self._ffmpeg_proc.stdout.read(self._frame_size)
            if len(raw) < self._frame_size:
                self._end_playback()
                return
            self._current_frame += 1

        # Mostrar el frame sincronizado
        if raw is not None:
            image = QImage(raw, WIDGET_W, WIDGET_H, WIDGET_W * 3,
                          QImage.Format_RGB888).copy()
            self._frame_pixmap = QPixmap.fromImage(image)
            self.update()

    # ═══════════════ FIN Y FADE ═══════════════

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

    # ═══════════════ OTROS ═══════════════

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._frame_pixmap is not None:
            painter.drawPixmap(self.rect(), self._frame_pixmap)
        else:
            painter.fillRect(self.rect(), QColor("#0b0f12"))

    def _on_mute_toggled(self, state):
        self._muted = bool(state)
        self.mute_toggled.emit(self._muted)

    def _stop_audio(self):
        if self._audio_stream is not None:
            try:
                self._audio_stream.stop()
            except Exception:
                pass
            try:
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