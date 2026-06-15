import json
import time
import traceback
import requests
from PySide6.QtCore import QThread, Signal
from app.services import _log


DEFAULT_OPENROUTER_MODEL = "anthropic/claude-sonnet-4.6"
FALLBACK_OPENROUTER_MODEL = "openrouter/auto"


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


def build_openrouter_chordpro_prompt(song_title: str, artist: str, sections: list,
                                     chords_by_section: dict, global_key: str, bpm: int,
                                     lyrics_text: str = ""):
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


def _parse_openrouter_response(response_text: str) -> dict:
    response_text = response_text.strip()

    try:
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
            "temperature": 0.1,
            "max_tokens": 1000,
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

    _log("OpenRouter", "[Solicitud 2] No se pudo generar sync.json, devolviendo ChordPro sin sincronización")
    return chordpro_content, {"sections": []}


class OpenRouterLLMThread(QThread):
    progress = Signal(str)
    finished_chordpro = Signal(str)
    finished_chordpro_and_sync = Signal(str, dict)
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

            self.finished_chordpro_and_sync.emit(chordpro, sync_data)
            self.finished_chordpro.emit(chordpro)
        except Exception:
            _log("OpenRouter", "Excepcion no controlada durante la generacion")
            traceback.print_exc()
            if not self._is_cancelled:
                self.error.emit("Ocurrio un error inesperado al generar el sheet de acordes.")
