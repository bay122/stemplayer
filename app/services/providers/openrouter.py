import requests
from app.services.providers.base import AIProvider
from app.services import _log


DEFAULT_MODEL = "anthropic/claude-sonnet-4.6"
FALLBACK_MODEL = "openrouter/auto"


class OpenRouterProvider(AIProvider):
    @property
    def id(self) -> str:
        return "openrouter"

    @property
    def display_name(self) -> str:
        return "OpenRouter"

    @property
    def default_model(self) -> str:
        return DEFAULT_MODEL

    @property
    def supports_web_search(self) -> bool:
        return True

    def chat_completion(
        self,
        prompt: str,
        model: str,
        api_key: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 2500,
        use_web_search: bool = False,
        timeout: tuple[int, int] = (20, 300),
    ) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost/stemsplayer",
            "X-Title": "Stem Player",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if use_web_search:
            payload["plugins"] = [{"id": "web", "max_results": 5}]

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(self.format_error(response.status_code, response.text))

        content = response.json()["choices"][0]["message"]["content"].strip()
        if not content:
            raise RuntimeError("OpenRouter devolvio una respuesta vacia.")

        return content

    def format_error(self, status_code: int, response_text: str) -> str:
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


AVAILABLE_MODELS = [
    "anthropic/claude-sonnet-4.6",
    "anthropic/claude-sonnet-4-20250514",
    "google/gemini-2.5-flash-lite-preview-05-2025",
    "google/gemini-2.5-pro-preview-05-2025",
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openrouter/auto",
]
