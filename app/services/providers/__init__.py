from app.services.providers.base import AIProvider
from app.services.providers.openrouter import OpenRouterProvider
from app.services.providers.google import GoogleAIStudioProvider


PROVIDER_REGISTRY: dict[str, AIProvider] = {
    "openrouter": OpenRouterProvider(),
    "google": GoogleAIStudioProvider(),
}


def get_provider(provider_id: str) -> AIProvider:
    provider = PROVIDER_REGISTRY.get(provider_id)
    if provider is None:
        available = ", ".join(PROVIDER_REGISTRY)
        raise ValueError(f"Proveedor '{provider_id}' no encontrado. Disponibles: {available}")
    return provider


def get_available_providers() -> list[AIProvider]:
    return list(PROVIDER_REGISTRY.values())
