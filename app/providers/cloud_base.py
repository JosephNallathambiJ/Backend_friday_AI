"""Cloud AI provider adapter with strict opt-in enforcement."""

from collections.abc import AsyncIterator
from typing import Any

from app.core.config import settings
from app.core.exceptions import SecurityPolicyError
from app.domain.protocols import (
    ChatCompletionResponse,
    ChatMessage,
    StreamChunk,
)
from app.providers.base import BaseAIProvider


class CloudAIProvider(BaseAIProvider):
    """Cloud provider adapter requiring explicit configuration and authorization."""

    name = "cloud"

    def __init__(self):
        if not settings.CLOUD_AI_ENABLED:
            raise SecurityPolicyError(
                "Cloud AI routing is disabled by default. Set CLOUD_AI_ENABLED=true and provide credentials to enable."
            )
        self.provider = settings.CLOUD_PROVIDER
        self.api_key = settings.CLOUD_API_KEY
        self.model = settings.CLOUD_MODEL

    async def check_health(self) -> bool:
        return bool(settings.CLOUD_AI_ENABLED and self.api_key)

    async def list_models(self) -> list[str]:
        if not settings.CLOUD_AI_ENABLED:
            return []
        return [self.model] if self.model else ["cloud-default"]

    async def chat_complete(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatCompletionResponse:
        if not settings.CLOUD_AI_ENABLED:
            raise SecurityPolicyError("Cloud AI execution blocked: CLOUD_AI_ENABLED is false.")
        # Standard placeholder for cloud provider implementation (e.g. Gemini, OpenAI, Claude)
        return ChatCompletionResponse(
            content="[Cloud AI response]",
            finish_reason="stop",
        )

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        if not settings.CLOUD_AI_ENABLED:
            raise SecurityPolicyError("Cloud AI streaming blocked: CLOUD_AI_ENABLED is false.")
        yield StreamChunk(content_delta="[Cloud AI streaming response]", finish_reason="stop")
