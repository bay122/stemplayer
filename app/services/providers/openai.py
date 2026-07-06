import requests
from app.services.providers.base import AIProvider
from app.services import _log


DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(AIProvider):
    @property
    def id(self) -> str:
        return "openai"

    @property
    def display_name(self) -> str:
        return "OpenAI"

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
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(self.format_error(response.status_code, response.text))

        choices = response.json().get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI devolvio una respuesta vacia.")

        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            raise RuntimeError("OpenAI devolvio una respuesta vacia.")

        return content

    def format_error(self, status_code: int, response_text: str) -> str:
        lowered = (response_text or "").lower()

        if status_code == 401:
            return "La API key de OpenAI no es valida."
        if status_code == 429:
            return "OpenAI alcanzo el limite de solicitudes. Espera un momento e intenta otra vez."
        if status_code == 400 and "context_length_exceeded" in lowered:
            return "La solicitud supera el limite de tokens del modelo."
        if status_code >= 500:
            return "OpenAI devolvio un error temporal del servidor. Intenta nuevamente en unos minutos."
        return f"No se pudo generar el sheet de acordes (HTTP {status_code})."


AVAILABLE_MODELS = [
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "o3",
    "o4-mini",
]
