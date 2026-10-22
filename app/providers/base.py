"""AI Provider base classes and types."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from app.domain.protocols import (
    ChatCompletionResponse,
    ChatMessage,
    StreamChunk,
)


class BaseAIProvider(ABC):
    """Abstract base class for model providers."""

    name: str

    @abstractmethod
    async def check_health(self) -> bool:
        """Check if provider is running and reachable."""
        pass

    @abstractmethod
    async def list_models(self) -> list[str]:
        """List available model names."""
        pass

    @abstractmethod
    async def chat_complete(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatCompletionResponse:
        """Execute chat completion."""
        pass

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream chat tokens."""
        pass
