import json
import time
import traceback
import requests
from PySide6.QtCore import QThread, Signal
from app.services import _log
from app.services.providers.base import AIProvider
from app.services.providers import get_provider


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


def build_chordpro_prompt(song_title: str, artist: str, sections: list,
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


def build_sync_prompt(song_title: str, artist: str, sections: list, chordpro_content: str):
    sections_text = json.dumps(sections, ensure_ascii=False, separators=(',', ':'))

    return f"""Eres un experto en sincronizacion musical.

Cancion: {song_title}
Artista: {artist}

SECCIONES DETECTADAS POR WHISPER (con timestamps aproximados):
{sections_text}

ARCHIVO CHORDPRO GENERADO:
```
{chordpro_content}
```

Tarea:
Analiza el archivo ChordPro generado y los timestamps de Whisper para crear un archivo de sincronizacion preciso.

Reglas:
- Extrae los nombres exactos de secciones del ChordPro (deben coincidir perfectamente).
- Utiliza los timestamps de Whisper como referencia, pero optimizalos considerando:
  - La estructura musical del ChordPro
  - La duracion estimada de cada seccion basada en la cantidad de lineas
  - Asegurate de que la suma de duraciones sea coherente
- Si el ChordPro tiene secciones que no estan en Whisper, estima sus tiempos basandote en las duraciones musicales tipicas.
- Asegurate de que no haya solapamientos de tiempo entre secciones.

FORMATO DE RESPUESTA (JSON valido, sin markdown, sin explicaciones):
{{
  "sections": [
    {{"label": "nombre de seccion", "start": 0.0, "end": 15.5}},
    {{"label": "nombre de seccion", "start": 15.5, "end": 35.2}}
  ]
}}

IMPORTANTE:
- Los nombres en "label" deben coincidir EXACTAMENTE con los nombres en el ChordPro.
- Los valores "start" y "end" deben ser numeros con decimales (ej: 15.5, no "15.5").
- Todos los nombres de secciones del ChordPro deben estar incluidos.
"""


def _parse_sync_response(response_text: str) -> dict:
    response_text = response_text.strip()

    try:
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        data = json.loads(response_text)

        if "sections" not in data:
            raise ValueError("No se encontro campo 'sections' en la respuesta")

        _log("OpenRouter", "Sync.json parseado correctamente como JSON")
        return data

    except json.JSONDecodeError as e:
        _log("OpenRouter", f"Error al parsear sync.json: {e}")
        _log("OpenRouter", f"Respuesta recibida: {response_text[:200]}")
        raise RuntimeError(
            "El proveedor de IA devolvio un formato invalido para sync.json. Intenta nuevamente."
        )


def request_ai_chordpro(
    provider: AIProvider,
    song_title: str,
    artist: str,
    sections: list,
    chords_by_section: dict,
    global_key: str,
    bpm: int,
    api_key: str,
    model: str,
    lyrics_text: str = "",
    use_web_search: bool = True,
    progress_callback=None,
    cancelled_callback=None,
):
    _log("OpenRouter", "PRIMERA SOLICITUD: Generando archivo ChordPro...")
    if progress_callback:
        progress_callback("Generando sheet de acordes...")

    prompt_chordpro = build_chordpro_prompt(
        song_title=song_title,
        artist=artist,
        sections=sections,
        chords_by_section=chords_by_section,
        global_key=global_key,
        bpm=bpm,
        lyrics_text=lyrics_text,
    )

    chordpro_content = None
    last_error = None

    for attempt_label, attempt_model, attempt_web in _attempts(
        provider, model, use_web_search, lyrics_text
    ):
        if cancelled_callback and cancelled_callback():
            _log("OpenRouter", "Solicitud 1 cancelada antes de enviar")
            return "", {}

        _log("OpenRouter", f"[Solicitud 1] Enviando con modelo '{attempt_model}' (web={attempt_web})")
        if progress_callback:
            progress_callback(f"Generando sheet de acordes ({attempt_label})...")

        try:
            content = provider.chat_completion(
                prompt=prompt_chordpro,
                model=attempt_model,
                api_key=api_key,
                temperature=0.2,
                max_tokens=2500,
                use_web_search=attempt_web,
                timeout=(20, 300),
            )
            chordpro_content = _clean_chordpro_response(content)

            if not chordpro_content:
                _log("OpenRouter", "[Solicitud 1] Respuesta vacia")
                continue

            _log("OpenRouter", f"[Solicitud 1] ChordPro generado correctamente ({len(chordpro_content)} caracteres)")
            break

        except RuntimeError as e:
            last_error = str(e)
            _log("OpenRouter", f"[Solicitud 1] Intento fallido: {last_error}")
            continue

    if not chordpro_content:
        if last_error:
            raise RuntimeError(last_error)
        raise RuntimeError("No se pudo generar el sheet de acordes.")

    if cancelled_callback and cancelled_callback():
        _log("OpenRouter", "Solicitud 2 cancelada antes de enviar")
        return "", {}

    _log("OpenRouter", "SEGUNDA SOLICITUD: Generando archivo de sincronizacion...")
    if progress_callback:
        progress_callback("Generando sincronizacion de secciones...")

    prompt_sync = build_sync_prompt(
        song_title=song_title,
        artist=artist,
        sections=sections,
        chordpro_content=chordpro_content,
    )

    sync_data = None
    for attempt_label, attempt_model, attempt_web in _attempts(
        provider, model, use_web_search, lyrics_text
    ):
        if cancelled_callback and cancelled_callback():
            _log("OpenRouter", "Solicitud 2 cancelada antes de enviar")
            return chordpro_content, {}

        _log("OpenRouter", f"[Solicitud 2] Enviando con modelo '{attempt_model}'")
        if progress_callback:
            progress_callback(f"Generando sincronizacion ({attempt_label})...")

        try:
            content = provider.chat_completion(
                prompt=prompt_sync,
                model=attempt_model,
                api_key=api_key,
                temperature=0.1,
                max_tokens=1000,
                use_web_search=False,
                timeout=(20, 300),
            )

            if not content:
                _log("OpenRouter", "[Solicitud 2] Respuesta vacia")
                continue

            sync_data = _parse_sync_response(content)
            _log("OpenRouter", f"[Solicitud 2] Sync.json generado correctamente ({len(sync_data.get('sections', []))} secciones)")

            if progress_callback:
                progress_callback("Sincronizacion completada.")

            return chordpro_content, sync_data

        except RuntimeError as e:
            last_error = str(e)
            _log("OpenRouter", f"[Solicitud 2] Intento fallido: {last_error}")
            continue

    _log("OpenRouter", "[Solicitud 2] No se pudo generar sync.json, devolviendo ChordPro sin sincronizacion")
    return chordpro_content, {"sections": []}


def _attempts(provider, model, use_web_search, lyrics_text):
    candidates = [model]
    if provider.id == "openrouter":
        if FALLBACK_OPENROUTER_MODEL not in candidates:
            candidates.append(FALLBACK_OPENROUTER_MODEL)

    web_variants = [False]
    if use_web_search and not lyrics_text:
        web_variants = [True, False]

    for m in candidates:
        for w in web_variants:
            label = m
            if w:
                label = f"{m} + web"
            yield label, m, w


class OpenRouterLLMThread(QThread):
    progress = Signal(str)
    finished_chordpro = Signal(str)
    finished_chordpro_and_sync = Signal(str, dict)
    error = Signal(str)

    def __init__(
        self,
        provider: AIProvider,
        song_title: str,
        artist: str,
        sections: list,
        chords_by_section: dict,
        global_key: str,
        bpm: int,
        api_key: str,
        model: str = None,
        lyrics_text: str = "",
        use_web_search: bool = True,
    ):
        super().__init__()
        self.provider = provider
        self.song_title = song_title
        self.artist = artist
        self.sections = sections
        self.chords_by_section = chords_by_section
        self.global_key = global_key
        self.bpm = bpm
        self.api_key = api_key
        self.model = model or provider.default_model
        self.lyrics_text = (lyrics_text or "").strip()
        self.use_web_search = use_web_search
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

            chordpro, sync_data = request_ai_chordpro(
                provider=self.provider,
                song_title=self.song_title,
                artist=self.artist,
                sections=self.sections,
                chords_by_section=self.chords_by_section,
                global_key=self.global_key,
                bpm=self.bpm,
                api_key=self.api_key,
                model=self.model,
                lyrics_text=self.lyrics_text,
                use_web_search=self.use_web_search,
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
