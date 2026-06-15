import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import traceback
import librosa
import scipy.signal

import numpy as np
import requests
import soundfile as sf
from PySide6.QtCore import QThread, Signal


DEFAULT_OPENROUTER_MODEL = "anthropic/claude-sonnet-4.6"
FALLBACK_OPENROUTER_MODEL = "openrouter/auto"


def _log(scope: str, message: str):
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}][{scope}] {message}", flush=True)


def create_sync_file(sections: list, output_path: str) -> bool:
    """
    Crea un archivo sync.json con los timestamps de las secciones detectadas.
    Este archivo se usa para sincronizar el display en modo Karaoke/Live.
    
    Args:
        sections: Lista de secciones con 'label', 'start', 'end'
        output_path: Ruta donde guardar el sync.json
    
    Returns:
        True si se guardó exitosamente, False en caso de error
    """
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


def _load_whisper_model_class():
    try:
        from faster_whisper import WhisperModel
        return WhisperModel
    except Exception as exc:
        _log("Whisper", f"No se pudo importar faster_whisper: {exc!r}")
        return None


def _clean_chordpro_response(content: str) -> str:
    if not content:
        return ""

    cleaned = content.strip()
    if "```" in cleaned:
        parts = cleaned.split("```")
        for part in parts:
            candidate = part.strip()
            if not candidate:
                continue
            if candidate.startswith(("chordpro", "pro", "txt")):
                candidate = candidate.split("\n", 1)[1] if "\n" in candidate else ""
            if candidate:
                cleaned = candidate.strip()
                break

    return cleaned.strip()


def _friendly_openrouter_error(status_code: int, response_text: str) -> str:
    lowered = (response_text or "").lower()

    if status_code in (401, 403):
        return "La API key de OpenRouter no es valida o no tiene permisos para este modelo."
    if status_code == 402:
        return "OpenRouter no tiene credito disponible para completar esta solicitud."
    if status_code == 404 and "no endpoints found" in lowered:
        return "El modelo seleccionado no tiene proveedores disponibles en este momento."
    if status_code >= 500:
        return "OpenRouter devolvio un error temporal del servidor. Intenta nuevamente en unos minutos."
    if "rate limit" in lowered or status_code == 429:
        return "OpenRouter alcanzo el limite de solicitudes. Espera un momento e intenta otra vez."
    return f"No se pudo generar el sheet de acordes (HTTP {status_code})."


def find_guide_audio(stems: dict):
    for name, data in stems.items():
        fname = name.lower()
        if any(token in fname for token in ["guide", "guia", "cue", "vocal"]):
            return name, data["audio"]
    return None, None

def build_harmonic_mix(stems: dict):
    _log("Harmonic Mix", f"Iniciando la fusión de stems")
    mixed_audio = None
    included = []
    skipped = []

    for name, data in stems.items():
        cat = data.get("category", "").lower()
        fname = name.lower()
        
        should_skip = (
            "click" in cat or
            "click" in fname or
            "guide" in fname or
            "cue" in fname or
            "drum" in cat or
            "bateria" in fname or
            "drum" in fname
        )
        if should_skip:
            skipped.append(name)
            continue

        included.append(name)
        if mixed_audio is None:
            mixed_audio = data["audio"].copy()
        else:
            length = max(len(mixed_audio), len(data["audio"]))
            new_mixed = np.zeros(length, dtype=np.float32)
            new_mixed[:len(mixed_audio)] += mixed_audio
            new_mixed[:len(data["audio"])] += data["audio"]
            mixed_audio = new_mixed

    return mixed_audio, included, skipped


def extract_chords(y: np.ndarray, sr: int):
    _log("Extract Chords", f"Iniciando la extracción de acordes")
    sr_proc = 22050
    y_resampled = librosa.resample(y, orig_sr=sr, target_sr=sr_proc)
    y_harmonic, _ = librosa.effects.hpss(y_resampled)
    tuning = librosa.estimate_tuning(y=y_harmonic, sr=sr_proc)
    
    hop_length = 2048
    chroma = librosa.feature.chroma_cqt(y=y_harmonic, sr=sr_proc, tuning=tuning, hop_length=hop_length)
    
    NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    templates = []
    labels = []

    for i, root in enumerate(NOTES):
        t_maj = np.zeros(12); t_maj[i] = t_maj[(i+4)%12] = t_maj[(i+7)%12] = 1.0
        templates.append(t_maj / np.linalg.norm(t_maj))
        labels.append(root)

        t_min = np.zeros(12); t_min[i] = t_min[(i+3)%12] = t_min[(i+7)%12] = 1.0
        templates.append(t_min / np.linalg.norm(t_min))
        labels.append(f"{root}m")
        
        t_dom7 = np.zeros(12); t_dom7[i] = t_dom7[(i+4)%12] = t_dom7[(i+7)%12] = t_dom7[(i+10)%12] = 1.0
        templates.append(t_dom7 / np.linalg.norm(t_dom7))
        labels.append(f"{root}7")
        
        t_min7 = np.zeros(12); t_min7[i] = t_min7[(i+3)%12] = t_min7[(i+7)%12] = t_min7[(i+10)%12] = 1.0
        templates.append(t_min7 / np.linalg.norm(t_min7))
        labels.append(f"{root}m7")
        
        t_maj7 = np.zeros(12); t_maj7[i] = t_maj7[(i+4)%12] = t_maj7[(i+7)%12] = t_maj7[(i+11)%12] = 1.0
        templates.append(t_maj7 / np.linalg.norm(t_maj7))
        labels.append(f"{root}maj7")

    templates = np.array(templates)
    similarity = np.dot(templates, chroma)
    best_matches = np.argmax(similarity, axis=0)
    smoothed_matches = scipy.signal.medfilt(best_matches, kernel_size=15).astype(int)

    chords = []
    current_chord = labels[smoothed_matches[0]]
    start_frame = 0

    for i in range(1, len(smoothed_matches)):
        chord = labels[smoothed_matches[i]]
        if chord != current_chord:
            dur_frames = i - start_frame
            start_time = librosa.frames_to_time(start_frame, sr=sr_proc, hop_length=hop_length)
            dur_time = librosa.frames_to_time(dur_frames, sr=sr_proc, hop_length=hop_length)

            if dur_time >= 0.5:
                chords.append({
                    "time": round(start_time, 2),
                    "duration": round(dur_time, 2),
                    "chord": current_chord
                })

            current_chord = chord
            start_frame = i

    dur_frames = len(smoothed_matches) - start_frame
    start_time = librosa.frames_to_time(start_frame, sr=sr_proc, hop_length=hop_length)
    dur_time = librosa.frames_to_time(dur_frames, sr=sr_proc, hop_length=hop_length)
    if dur_time >= 0.5:
        chords.append({
            "time": round(start_time, 2),
            "duration": round(dur_time, 2),
            "chord": current_chord
        })

    return chords

def map_chords_to_sections(sections: list, all_chords: list):
    chords_by_section = {}
    if sections and all_chords:
        for i, sec in enumerate(sections):
            sec_name = sec["label"]
            start = sec["start"]
            end = sections[i + 1]["start"] if i + 1 < len(sections) else (all_chords[-1]["time"] + 10)
            sec["end"] = end

            sec_chords = [c for c in all_chords if start <= c["time"] < end]
            simplified = []
            for chord in sec_chords:
                if not simplified or simplified[-1]["chord"] != chord["chord"]:
                    simplified.append(chord)

            chords_by_section[sec_name] = simplified
    else:
        chords_by_section["Global"] = all_chords

    return chords_by_section


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
    
    # Activamos word_timestamps para controlar los cortes mediante puntuacion
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

            # Cortamos el bloque unicamente cuando Whisper detecta un punto final
            if texto.endswith("."):
                texto_completo = " ".join(palabras_bloque)
                
                # Normalizacion de los errores comunes del modelo
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

    # Agrupamos cualquier remanente que haya quedado al final del audio sin punto
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


def build_openrouter_chordpro_prompt(song_title: str, artist: str, sections: list, chords_by_section: dict, global_key: str, bpm: int, lyrics_text: str = ""):
    """Prompt para generar el archivo ChordPro (Primera solicitud)"""
    sections_text = json.dumps(sections, ensure_ascii=False, separators=(',', ':'))
    chords_text = json.dumps(chords_by_section, ensure_ascii=False, separators=(',', ':'))

    if lyrics_text:
        lyrics_instruction = (
            "LETRA PROPORCIONADA POR EL USUARIO:\n"
            f"{lyrics_text}\n\n"
            "Debes usar esta letra como fuente principal. "
            "No la reemplaces por otra version ni inventes versos nuevos."
        )
        task_1 = "1. Usa la letra proporcionada por el usuario."
        extra_rule = "- No busques ni sustituyas la letra proporcionada por el usuario."
    else:
        lyrics_instruction = (
            "No se proporciono letra manualmente. "
            "Debes buscar la letra oficial mas precisa posible antes de generar el archivo."
        )
        task_1 = "1. Busca la letra oficial mas precisa de esta cancion."
        extra_rule = "- Si haces busqueda web, prioriza fuentes oficiales o ampliamente reconocidas."

    return f"""Eres un experto en transcripcion musical y formato ChordPro.

Cancion: {song_title}
Artista: {artist}

INFORMACION DETECTADA:
- Tonalidad global: {global_key}
- BPM: {bpm}

SECCIONES DETECTADAS (con timestamps aproximados):
{sections_text}

ACORDES DETECTADOS POR SECCION:
{chords_text}

CONTEXTO DE LETRA:
{lyrics_instruction}

Tarea:
{task_1}
2. Alinea la letra con las secciones detectadas.
3. Coloca los acordes de forma musicalmente coherente encima de la letra.
4. Genera un archivo completo en formato ChordPro valido.

Reglas importantes:
- Usa las secciones detectadas como base estructural, pero ajusta sus nombres si encuentras inconsistencias (ej: "goro" → "coro").
- Usa los acordes detectados donde sea posible.
- Si hace falta, ajusta ligeramente los acordes para que fluyan mejor con la letra.
- Incluye {{title: {song_title}}}, {{artist: {artist}}} y {{key: {global_key}}}.
- Usa etiquetas como {{start_of_verse}}, {{start_of_chorus}}, {{start_of_bridge}}, etc.
- Si una seccion detectada no coincide exactamente con una etiqueta canonica, usa {{c: Nombre de la seccion}}.
{extra_rule}

Devuelve SOLO el contenido del archivo .chopro, sin explicaciones ni bloques markdown.
"""


def build_openrouter_sync_prompt(song_title: str, artist: str, sections: list, chordpro_content: str):
    """Prompt para generar el archivo de sincronización (Segunda solicitud)"""
    sections_text = json.dumps(sections, ensure_ascii=False, separators=(',', ':'))
    
    return f"""Eres un experto en sincronización musical.

Cancion: {song_title}
Artista: {artist}

SECCIONES DETECTADAS POR WHISPER (con timestamps aproximados):
{sections_text}

ARCHIVO CHORDPRO GENERADO:
```
{chordpro_content}
```

Tarea:
Analiza el archivo ChordPro generado y los timestamps de Whisper para crear un archivo de sincronización preciso.

Reglas:
- Extrae los nombres exactos de secciones del ChordPro (deben coincidir perfectamente).
- Utiliza los timestamps de Whisper como referencia, pero optimizalos considerando:
  - La estructura musical del ChordPro
  - La duración estimada de cada sección basada en la cantidad de líneas
  - Asegurate de que la suma de duraciones sea coherente
- Si el ChordPro tiene secciones que no están en Whisper, estima sus tiempos basándote en las duraciones musicales típicas.
- Asegurate de que no haya solapamientos de tiempo entre secciones.

FORMATO DE RESPUESTA (JSON válido, sin markdown, sin explicaciones):
{{
  "sections": [
    {{"label": "nombre de seccion", "start": 0.0, "end": 15.5}},
    {{"label": "nombre de seccion", "start": 15.5, "end": 35.2}}
  ]
}}

IMPORTANTE:
- Los nombres en "label" deben coincidir EXACTAMENTE con los nombres en el ChordPro.
- Los valores "start" y "end" deben ser números con decimales (ej: 15.5, no "15.5").
- Todos los nombres de secciones del ChordPro deben estar incluidos.
"""


def _build_openrouter_payload(model_name: str, prompt: str, use_web_search: bool):
    """Deprecated: Los payloads se crean inline en request_openrouter_chordpro para control fino"""
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 2000,
    }
    if use_web_search:
        payload["plugins"] = [{"id": "web", "max_results": 5}]
    return payload


def _parse_openrouter_response(response_text: str) -> tuple:
    """
    Parsea la respuesta JSON de OpenRouter para el sync.json (segunda solicitud).
    
    Returns:
        tuple: (sync_data: dict)
    """
    response_text = response_text.strip()
    
    try:
        # Limpiar markdown si existe
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        data = json.loads(response_text)
        
        if "sections" not in data:
            raise ValueError("No se encontró campo 'sections' en la respuesta")
        
        _log("OpenRouter", "Sync.json parseado correctamente como JSON")
        return data
        
    except json.JSONDecodeError as e:
        _log("OpenRouter", f"Error al parsear sync.json: {e}")
        _log("OpenRouter", f"Respuesta recibida: {response_text[:200]}")
        raise RuntimeError(
            "OpenRouter devolvió un formato inválido para sync.json. Intenta nuevamente."
        )


def request_openrouter_chordpro(
    song_title: str,
    artist: str,
    sections: list,
    chords_by_section: dict,
    global_key: str,
    bpm: int,
    api_key: str,
    lyrics_text: str = "",
    use_web_search: bool = True,
    preferred_model: str = DEFAULT_OPENROUTER_MODEL,
    progress_callback=None,
    cancelled_callback=None,
):
    """
    Realiza dos solicitudes a OpenRouter:
    1. Primera: Generar el archivo ChordPro
    2. Segunda: Generar el archivo de sincronización
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost/stemsplayer",
        "X-Title": "Stem Player",
    }

    model_candidates = []
    for candidate in [preferred_model, FALLBACK_OPENROUTER_MODEL]:
        if candidate and candidate not in model_candidates:
            model_candidates.append(candidate)

    # ============ PRIMERA SOLICITUD: Generar ChordPro ============
    _log("OpenRouter", "PRIMERA SOLICITUD: Generando archivo ChordPro...")
    if progress_callback:
        progress_callback("Generando sheet de acordes...")
    
    prompt_chordpro = build_openrouter_chordpro_prompt(
        song_title=song_title,
        artist=artist,
        sections=sections,
        chords_by_section=chords_by_section,
        global_key=global_key,
        bpm=bpm,
        lyrics_text=lyrics_text,
    )

    chordpro_content = None
    last_response_text = ""
    last_status_code = 0

    for index, model_name in enumerate(model_candidates):
        if cancelled_callback and cancelled_callback():
            _log("OpenRouter", "Solicitud 1 cancelada antes de enviar")
            return "", {}

        _log("OpenRouter", f"[Solicitud 1] Enviando con modelo '{model_name}'")
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt_chordpro}],
            "temperature": 0.2,
            "max_tokens": 2500,
        }
        if use_web_search and not lyrics_text:
            payload["plugins"] = [{"id": "web", "max_results": 5}]

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=(20, 300),
        )

        if cancelled_callback and cancelled_callback():
            _log("OpenRouter", "Solicitud 1 cancelada después de recibir respuesta HTTP")
            return "", {}

        last_status_code = response.status_code
        last_response_text = response.text
        _log("OpenRouter", f"[Solicitud 1] HTTP {response.status_code} recibido para modelo '{model_name}'")

        if response.status_code == 200:
            response_data = response.json()
            chordpro_content = response_data["choices"][0]["message"]["content"].strip()
            
            if not chordpro_content:
                _log("OpenRouter", "[Solicitud 1] Respuesta vacía")
                no_endpoints = response.status_code == 404 and "no endpoints found" in response.text.lower()
                if no_endpoints and index < len(model_candidates) - 1:
                    continue
                break
            
            _log("OpenRouter", f"[Solicitud 1] ChordPro generado correctamente ({len(chordpro_content)} caracteres)")
            break

        _log("OpenRouter", f"[Solicitud 1] Intento fallido con modelo '{model_name}'")
        no_endpoints = response.status_code == 404 and "no endpoints found" in response.text.lower()
        if no_endpoints and index < len(model_candidates) - 1:
            continue
        break

    if not chordpro_content:
        raise RuntimeError(_friendly_openrouter_error(last_status_code, last_response_text))

    # ============ SEGUNDA SOLICITUD: Generar Sync.json ============
    if cancelled_callback and cancelled_callback():
        _log("OpenRouter", "Solicitud 2 cancelada antes de enviar")
        return "", {}

    _log("OpenRouter", "SEGUNDA SOLICITUD: Generando archivo de sincronización...")
    if progress_callback:
        progress_callback("Generando sincronización de secciones...")

    prompt_sync = build_openrouter_sync_prompt(
        song_title=song_title,
        artist=artist,
        sections=sections,
        chordpro_content=chordpro_content,
    )

    sync_data = None
    for index, model_name in enumerate(model_candidates):
        if cancelled_callback and cancelled_callback():
            _log("OpenRouter", "Solicitud 2 cancelada antes de enviar")
            return chordpro_content, {}

        _log("OpenRouter", f"[Solicitud 2] Enviando con modelo '{model_name}'")
        
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt_sync}],
            "temperature": 0.1,  # Menor temperatura para más precisión
            "max_tokens": 1000,  # Menos tokens necesarios para sync
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=(20, 300),
        )

        if cancelled_callback and cancelled_callback():
            _log("OpenRouter", "Solicitud 2 cancelada después de recibir respuesta HTTP")
            return chordpro_content, {}

        last_status_code = response.status_code
        last_response_text = response.text
        _log("OpenRouter", f"[Solicitud 2] HTTP {response.status_code} recibido para modelo '{model_name}'")

        if response.status_code == 200:
            response_data = response.json()
            sync_response = response_data["choices"][0]["message"]["content"].strip()
            
            if not sync_response:
                _log("OpenRouter", "[Solicitud 2] Respuesta vacía")
                no_endpoints = response.status_code == 404 and "no endpoints found" in response.text.lower()
                if no_endpoints and index < len(model_candidates) - 1:
                    continue
                break
            
            # Parsear el JSON de sync
            sync_data = _parse_openrouter_response(sync_response)
            _log("OpenRouter", f"[Solicitud 2] Sync.json generado correctamente ({len(sync_data.get('sections', []))} secciones)")
            
            if progress_callback:
                progress_callback("Sincronización completada.")
            
            return chordpro_content, sync_data

        _log("OpenRouter", f"[Solicitud 2] Intento fallido con modelo '{model_name}'")
        no_endpoints = response.status_code == 404 and "no endpoints found" in response.text.lower()
        if no_endpoints and index < len(model_candidates) - 1:
            continue
        break

    # Si falla la segunda solicitud, al menos devolvemos el ChordPro con un sync vacío
    _log("OpenRouter", "[Solicitud 2] No se pudo generar sync.json, devolviendo ChordPro sin sincronización")
    return chordpro_content, {"sections": []}


class ChordAnalysisThread(QThread):
    """
    Hilo para realizar el analisis de acordes (CREMA) y extraccion de secciones (Whisper).
    """

    progress = Signal(str)
    progress_pct = Signal(int)
    finished_analysis = Signal(dict)
    error = Signal(str)

    def __init__(self, song_folder: str, stems: dict, mix_sr: int = 44100):
        super().__init__()
        self.song_folder = song_folder
        self.stems = stems
        self.mix_sr = mix_sr
        self._is_cancelled = False
        self._worker_process_holder = {"process": None}

    def cancel(self):
        self._is_cancelled = True
        process = self._worker_process_holder.get("process")
        if process and process.poll() is None:
            _log("ChordAnalysis", "Cancelando worker de CREMA...")
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                _log("ChordAnalysis", "El worker no respondio al terminate(); forzando kill()")
                process.kill()

    def run(self):
        start_time = time.perf_counter()
        try:
            _log("ChordAnalysis", f"Inicio de analisis para '{self.song_folder}' con {len(self.stems)} stems")
            self.progress.emit("Iniciando analisis de IA (puede tomar un momento)...")
            self.progress_pct.emit(5)

            guide_name, guide_audio = find_guide_audio(self.stems)
            sections = []

            if guide_audio is not None:
                _log("ChordAnalysis", f"Guide detectado: {guide_name}")
                self.progress.emit("Cargando modelo Whisper...")
                self.progress_pct.emit(8)
                if self._is_cancelled:
                    return

                self.progress.emit("Transcribiendo secciones con Whisper...")
                self.progress_pct.emit(10)
                try:
                    sections = transcribe_guide_audio(guide_audio, self.mix_sr)
                except Exception as exc:
                    _log("Whisper", f"Fallo durante la transcripcion: {exc!r}")
                    traceback.print_exc()
                    sections = []
            else:
                _log("ChordAnalysis", "No se encontro pista guide; se usara agrupacion Global")

            if self._is_cancelled:
                return

            self.progress.emit("Mezclando instrumentos para deteccion de acordes...")
            self.progress_pct.emit(40)
            mixed_audio, included_stems, skipped_stems = build_harmonic_mix(self.stems)
            _log("ChordAnalysis", f"Stems incluidos para analisis armonico: {included_stems}")
            _log("ChordAnalysis", f"Stems omitidos: {skipped_stems}")

            all_chords = []
            if mixed_audio is not None:
                self.progress.emit("Detectando acordes con DSP (Librosa)...")
                self.progress_pct.emit(50)

                if self._is_cancelled:
                    return

                all_chords = extract_chords(mixed_audio, self.mix_sr)
                _log("Extract Chords", f"Total de acordes detectados: {len(all_chords)}")
            else:
                _log("ChordAnalysis", "No hubo stems aptos para analizar acordes")

            if self._is_cancelled:
                return

            self.progress.emit("Consolidando resultados...")
            self.progress_pct.emit(90)
            chords_by_section = map_chords_to_sections(sections, all_chords)

            result = {
                "sections": sections,
                "chords_by_section": chords_by_section,
                "raw_chords": all_chords,
            }

            elapsed = time.perf_counter() - start_time
            _log(
                "ChordAnalysis",
                f"Analisis completado en {elapsed:.2f}s | secciones={len(sections)} | acordes={len(all_chords)}",
            )
            self.progress.emit("Analisis completado.")
            self.progress_pct.emit(100)
            self.finished_analysis.emit(result)

        except Exception:
            _log("ChordAnalysis", "Excepcion no controlada durante el analisis")
            traceback.print_exc()
            if not self._is_cancelled:
                self.error.emit("No se pudo completar el analisis musical necesario para generar el sheet.")


class OpenRouterLLMThread(QThread):
    """
    Hilo para enviar los datos a OpenRouter y obtener el ChordPro y su sincronización.
    """

    progress = Signal(str)
    finished_chordpro = Signal(str)  # Deprecated: Usa finished_chordpro_and_sync
    finished_chordpro_and_sync = Signal(str, dict)  # Emite (chordpro, sync_data)
    error = Signal(str)

    def __init__(
        self,
        song_title: str,
        artist: str,
        sections: list,
        chords_by_section: dict,
        global_key: str,
        bpm: int,
        api_key: str,
        lyrics_text: str = "",
        use_web_search: bool = True,
        preferred_model: str = DEFAULT_OPENROUTER_MODEL,
    ):
        super().__init__()
        self.song_title = song_title
        self.artist = artist
        self.sections = sections
        self.chords_by_section = chords_by_section
        self.global_key = global_key
        self.bpm = bpm
        self.api_key = api_key
        self.lyrics_text = (lyrics_text or "").strip()
        self.use_web_search = use_web_search
        self.preferred_model = preferred_model or DEFAULT_OPENROUTER_MODEL
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        start_time = time.perf_counter()
        try:
            if self._is_cancelled:
                return

            self.progress.emit("Preparando datos para generar el sheet de acordes...")
            _log("OpenRouter", f"Inicio de generacion para '{self.song_title}'")

            chordpro, sync_data = request_openrouter_chordpro(
                song_title=self.song_title,
                artist=self.artist,
                sections=self.sections,
                chords_by_section=self.chords_by_section,
                global_key=self.global_key,
                bpm=self.bpm,
                api_key=self.api_key,
                lyrics_text=self.lyrics_text,
                use_web_search=self.use_web_search,
                preferred_model=self.preferred_model,
                progress_callback=self.progress.emit,
                cancelled_callback=lambda: self._is_cancelled,
            )

            if self._is_cancelled:
                return

            elapsed = time.perf_counter() - start_time
            _log("OpenRouter", f"Sheet generado correctamente en {elapsed:.2f}s")
            
            # Emitir ambos datos
            self.finished_chordpro_and_sync.emit(chordpro, sync_data)
            # Mantener compatibilidad con código antiguo
            self.finished_chordpro.emit(chordpro)
        except Exception:
            _log("OpenRouter", "Excepcion no controlada durante la generacion")
            traceback.print_exc()
            if not self._is_cancelled:
                self.error.emit("Ocurrio un error inesperado al generar el sheet de acordes.")
