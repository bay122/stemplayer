import numpy as np
from app.services import _log


def _load_whisper_model_class():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel
    except Exception as exc:
        _log("Whisper", f"No se pudo importar faster_whisper: {exc!r}")
        return None


def transcribe_guide_audio(guide_audio: np.ndarray, mix_sr: int, language: str = "es", model_size: str = "small"):
    _log("Whisper", f"Iniciando transcripción")
    whisper_model_cls = _load_whisper_model_class()
    if whisper_model_cls is None:
        raise RuntimeError("faster-whisper no esta instalado o no pudo importarse.")

    import librosa

    _log("Whisper", f"Remuestreando guide a 16000 Hz desde {mix_sr} Hz")
    audio_16k = librosa.resample(guide_audio, orig_sr=mix_sr, target_sr=16000)

    _log("Whisper", f"Cargando modelo '{model_size}' en CPU")
    model = whisper_model_cls(model_size, device="cpu", compute_type="int8", cpu_threads=4)

    _log("Whisper", "Transcribiendo guia con agrupacion semantica...")

    segments, _info = model.transcribe(
        audio_16k,
        language=language,
        beam_size=5,
        word_timestamps=True
    )

    sections = []
    palabras_bloque = []
    tiempo_inicio = None

    for segment in segments:
        for word in segment.words:
            texto = word.word.strip()
            if not texto:
                continue

            if tiempo_inicio is None:
                tiempo_inicio = float(word.start)

            palabras_bloque.append(texto)

            if texto.endswith("."):
                texto_completo = " ".join(palabras_bloque)
                texto_completo = texto_completo.replace("Pre -corro", "Pre-coro")
                texto_completo = texto_completo.replace("Pre -coro", "Pre-coro")
                texto_completo = texto_completo.replace("Precuro", "Pre-coro")
                texto_completo = texto_completo.replace("Pursos", "verso")
                texto_completo = texto_completo.replace("Corro", "Coro")

                sections.append({
                    "start": tiempo_inicio,
                    "end": float(word.end),
                    "label": texto_completo.strip(),
                })

                palabras_bloque = []
                tiempo_inicio = None

    if palabras_bloque:
        texto_completo = " ".join(palabras_bloque)
        texto_completo = texto_completo.replace("Pre -corro", "Pre-coro").replace("Corro", "Coro")
        sections.append({
            "start": tiempo_inicio,
            "end": float(word.end),
            "label": texto_completo.strip(),
        })

    _log("Whisper", f"Se detectaron {len(sections)} segmentos de seccion optimizados")
    return sections
