import requests
from app.services.providers.base import AIProvider
from app.services import _log


DEFAULT_MODEL = "gemini-2.5-flash-lite"


class GoogleAIStudioProvider(AIProvider):
    @property
    def id(self) -> str:
        return "google"

    @property
    def display_name(self) -> str:
        return "Google AI Studio"

    @property
    def default_model(self) -> str:
        return DEFAULT_MODEL

    @property
    def supports_web_search(self) -> bool:
        return True

    def _native_chat_completion(
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
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if use_web_search:
            payload["tools"] = [{"googleSearch": {}}]

        response = requests.post(url, headers=headers, json=payload, timeout=timeout)

        if response.status_code != 200:
            raise RuntimeError(self.format_error(response.status_code, response.text))

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Google AI Studio no devolvio candidatos.")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise RuntimeError("Google AI Studio devolvio una respuesta vacia.")

        return parts[0].get("text", "").strip()

    def _openai_compat_chat_completion(
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
        url = f"https://generativelanguage.googleapis.com/v1beta/openai/chat/completions?key={api_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        response = requests.post(url, headers=headers, json=payload, timeout=timeout)

        if response.status_code != 200:
            raise RuntimeError(self.format_error(response.status_code, response.text))

        choices = response.json().get("choices", [])
        if not choices:
            raise RuntimeError("Google AI Studio devolvio una respuesta vacia.")

        content = choices[0].get("message", {}).get("content", "").strip()
        if not content:
            raise RuntimeError("Google AI Studio devolvio una respuesta vacia.")

        return content

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
        if use_web_search:
            return self._native_chat_completion(
                prompt=prompt, model=model, api_key=api_key,
                temperature=temperature, max_tokens=max_tokens,
                use_web_search=True, timeout=timeout,
            )
        return self._openai_compat_chat_completion(
            prompt=prompt, model=model, api_key=api_key,
            temperature=temperature, max_tokens=max_tokens,
            use_web_search=False, timeout=timeout,
        )

    def format_error(self, status_code: int, response_text: str) -> str:
        lowered = (response_text or "").lower()

        if status_code in (400, 403):
            if "api key not valid" in lowered or "invalid" in lowered:
                return "La API key de Google AI Studio no es valida."
            if "not found" in lowered or "not found for" in lowered:
                return "El modelo especificado no existe o no esta disponible en tu cuenta."
            if "query is too long" in lowered:
                return "La solicitud supera el limite de tokens de Google AI Studio."
            return f"Google AI Studio rechazo la solicitud (HTTP {status_code})."
        if status_code == 429:
            return "Google AI Studio alcanzo el limite de solicitudes. Espera un momento e intenta otra vez."
        if status_code >= 500:
            return "Google AI Studio devolvio un error temporal del servidor. Intenta nuevamente en unos minutos."
        return f"No se pudo generar el sheet de acordes (HTTP {status_code})."


AVAILABLE_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]
