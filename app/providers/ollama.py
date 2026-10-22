"""Ollama local AI provider implementation."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import ProviderError
from app.core.logging import logger
from app.domain.protocols import (
    ChatCompletionResponse,
    ChatMessage,
    StreamChunk,
)
from app.providers.base import BaseAIProvider


class OllamaProvider(BaseAIProvider):
    """Local inference provider communicating with Ollama REST API."""

    name = "ollama"

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.OLLAMA_REQUEST_TIMEOUT

    async def check_health(self) -> bool:
        """Check if Ollama is running and responding."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> list[str]:
        """Fetch list of pulled models from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    return models
                return []
        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return []

    async def chat_complete(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
    ) -> ChatCompletionResponse:
        """Execute non-streaming chat completion with optional tool calls."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                    "content": m.content,
                }
                for m in messages
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                res = await client.post(f"{self.base_url}/api/chat", json=payload)
                if res.status_code != 200:
                    raise ProviderError(
                        f"Ollama returned HTTP {res.status_code}: {res.text}",
                        details={"status_code": res.status_code},
                    )

                data = res.json()
                msg = data.get("message", {})
                content = msg.get("content", "")
                tool_calls = msg.get("tool_calls")

                return ChatCompletionResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason=data.get("done_reason", "stop"),
                    usage={
                        "total_duration": data.get("total_duration"),
                        "eval_count": data.get("eval_count"),
                    },
                )
        except httpx.ConnectError as e:
            raise ProviderError(
                f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama is running.",
                details={"error": str(e)},
            )
        except httpx.TimeoutException as e:
            raise ProviderError(
                f"Ollama request timed out after {self.timeout}s.",
                details={"error": str(e)},
            )
        except Exception as e:
            if isinstance(e, ProviderError):
                raise
            raise ProviderError(f"Ollama execution error: {str(e)}", details={"error": str(e)})

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float = 0.7,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response chunks from Ollama."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {
                    "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                    "content": m.content,
                }
                for m in messages
            ],
            "stream": True,
            "options": {"temperature": temperature},
        }
        if tools:
            payload["tools"] = tools

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as response:
                    if response.status_code != 200:
                        content = await response.aread()
                        raise ProviderError(
                            f"Ollama returned HTTP {response.status_code}: {content.decode('utf-8', errors='ignore')}"
                        )

                    async for line in response.aiter_lines():
                        if not line or not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            msg = data.get("message", {})
                            delta = msg.get("content", "")
                            tool_calls = msg.get("tool_calls")
                            done = data.get("done", False)

                            yield StreamChunk(
                                content_delta=delta,
                                tool_call_delta={"tool_calls": tool_calls} if tool_calls else None,
                                finish_reason="stop" if done else None,
                            )
                        except json.JSONDecodeError:
                            continue
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise ProviderError(f"Ollama streaming connection error: {str(e)}")
