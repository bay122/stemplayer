import json
import requests
from app.services.providers.base import AIProvider
from app.services import _log


DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AnthropicProvider(AIProvider):
    @property
    def id(self) -> str:
        return "anthropic"

    @property
    def display_name(self) -> str:
        return "Anthropic"

    @property
    def default_model(self) -> str:
        return DEFAULT_MODEL

    @property
    def supports_web_search(self) -> bool:
        return False

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
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(self.format_error(response.status_code, response.text))

        data = response.json()
        content_blocks = data.get("content", [])
        if not content_blocks:
            raise RuntimeError("Anthropic devolvio una respuesta vacia.")

        text = "".join(block.get("text", "") for block in content_blocks if block.get("type") == "text")
        if not text.strip():
            raise RuntimeError("Anthropic devolvio una respuesta vacia.")

        return text.strip()

    def format_error(self, status_code: int, response_text: str) -> str:
        lowered = (response_text or "").lower()

        if status_code == 401:
            return "La API key de Anthropic no es valida."
        if status_code == 429:
            return "Anthropic alcanzo el limite de solicitudes. Espera un momento e intenta otra vez."
        if status_code == 400 and "too many tokens" in lowered:
            return "La solicitud supera el limite de tokens del modelo."
        if status_code >= 500:
            return "Anthropic devolvio un error temporal del servidor. Intenta nuevamente en unos minutos."
        return f"No se pudo generar el sheet de acordes (HTTP {status_code})."


AVAILABLE_MODELS = [
    "claude-sonnet-4-20250514",
    "claude-sonnet-4.6",
    "claude-3-5-haiku-20241022",
    "claude-3-opus-20240229",
]
