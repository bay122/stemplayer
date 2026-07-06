import requests
from app.services.providers.base import AIProvider
from app.services import _log


DEFAULT_MODEL = "meta-llama/Llama-3.3-70B-Instruct-Turbo"


class TogetherAIProvider(AIProvider):
    @property
    def id(self) -> str:
        return "together"

    @property
    def display_name(self) -> str:
        return "Together AI"

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
            "https://api.together.xyz/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )

        if response.status_code != 200:
            raise RuntimeError(self.format_error(response.status_code, response.text))

        choices = response.json().get("choices", [])
        if not choices:
            raise RuntimeError("Together AI devolvio una respuesta vacia.")

        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            raise RuntimeError("Together AI devolvio una respuesta vacia.")

        return content

    def format_error(self, status_code: int, response_text: str) -> str:
        lowered = (response_text or "").lower()

        if status_code == 401:
            return "La API key de Together AI no es valida."
        if status_code == 402:
            return "Together AI no tiene credito suficiente para completar la solicitud."
        if status_code == 429:
            return "Together AI alcanzo el limite de solicitudes. Espera un momento e intenta otra vez."
        if status_code >= 500:
            return "Together AI devolvio un error temporal del servidor. Intenta nuevamente en unos minutos."
        return f"No se pudo generar el sheet de acordes (HTTP {status_code})."


AVAILABLE_MODELS = [
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "meta-llama/Llama-3.2-90B-Vision-Instruct-Turbo",
    "meta-llama/Llama-4-Scout-17B-16E-Instruct-Turbo",
    "deepseek-ai/DeepSeek-V3-0324",
    "deepseek-ai/DeepSeek-R1",
    "Qwen/Qwen3-235B-A22B-Turbo",
    "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
]
