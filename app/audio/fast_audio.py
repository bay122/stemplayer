import warnings
import numpy as np

warnings.filterwarnings("ignore", category=UserWarning, message="PySoundFile failed")
warnings.filterwarnings("ignore", category=FutureWarning, message="librosa.core.audio.__audioread_load")


def fast_audio_load(file_path: str, target_sr: int = 44100):
    """Carga de audio optimizada usando soundfile nativo antes de librosa.
    Siempre retorna float32.
    """
    try:
        import soundfile as sf
        data, sr = sf.read(file_path, dtype=np.float32)
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        if sr != target_sr:
            import librosa
            data = librosa.resample(data, orig_sr=sr, target_sr=target_sr)
        return data, target_sr
    except Exception:
        import librosa
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=FutureWarning)
            data, sr = librosa.load(file_path, sr=target_sr, mono=True)
        return data.astype(np.float32), sr
