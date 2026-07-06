from app.services.providers.base import AIProvider
from app.services.providers.openrouter import OpenRouterProvider
from app.services.providers.google import GoogleAIStudioProvider
from app.services.providers.openai import OpenAIProvider
from app.services.providers.anthropic import AnthropicProvider
from app.services.providers.deepseek import DeepSeekProvider
from app.services.providers.groq import GroqProvider
from app.services.providers.together import TogetherAIProvider


PROVIDER_REGISTRY: dict[str, AIProvider] = {
    "openrouter": OpenRouterProvider(),
    "google": GoogleAIStudioProvider(),
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "deepseek": DeepSeekProvider(),
    "groq": GroqProvider(),
    "together": TogetherAIProvider(),
}


def get_provider(provider_id: str) -> AIProvider:
    provider = PROVIDER_REGISTRY.get(provider_id)
    if provider is None:
        available = ", ".join(PROVIDER_REGISTRY)
        raise ValueError(f"Proveedor '{provider_id}' no encontrado. Disponibles: {available}")
    return provider


def get_available_providers() -> list[AIProvider]:
    return list(PROVIDER_REGISTRY.values())
