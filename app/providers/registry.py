"""Provider registry managing active AI providers."""

from app.core.config import settings
from app.providers.base import BaseAIProvider
from app.providers.ollama import OllamaProvider


class ProviderRegistry:
    """Registry maintaining active AI provider adapters."""

    def __init__(self):
        self._providers: dict[str, BaseAIProvider] = {}
        # Register local Ollama by default
        self._providers["ollama"] = OllamaProvider()

    def register(self, provider: BaseAIProvider):
        self._providers[provider.name] = provider

    def get(self, name: str | None = None) -> BaseAIProvider:
        if name:
            return self._providers.get(name, self._providers["ollama"])
        if "mock" in self._providers:
            return self._providers["mock"]
        provider_name = "cloud" if settings.CLOUD_AI_ENABLED else "ollama"
        return self._providers.get(provider_name, self._providers.get("ollama", OllamaProvider()))


provider_registry = ProviderRegistry()
