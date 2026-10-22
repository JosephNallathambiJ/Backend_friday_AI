"""Protocol interfaces for FRIDAY AI components."""

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from app.domain.enums import MessageRole


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    tool_call_id: str | None = None
    name: str | None = None


class ChatCompletionResponse(BaseModel):
    content: str
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None


class StreamChunk(BaseModel):
    content_delta: str = ""
    tool_call_delta: dict[str, Any] | None = None
    finish_reason: str | None = None


@runtime_checkable
class AIProviderProtocol(Protocol):
    """Protocol for local or cloud AI model inference providers."""

    name: str

    async def check_health(self) -> bool:
        """Verify provider availability."""
        ...

    async def list_models(self) -> list[str]:
        """List available model names."""
        ...

    async def chat_complete(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatCompletionResponse:
        """Perform non-streaming chat completion."""
        ...

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream chat tokens and tool calls."""
        ...


@runtime_checkable
class VoiceTranscriptionProtocol(Protocol):
    """Protocol for speech-to-text audio processing."""

    async def transcribe(self, audio_bytes: bytes, mime_type: str) -> str:
        """Convert audio to text."""
        ...


@runtime_checkable
class VoiceSynthesisProtocol(Protocol):
    """Protocol for text-to-speech audio synthesis."""

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        """Convert text into speech audio bytes."""
        ...
