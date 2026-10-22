"""Ollama local AI provider implementation with native tool calling and LiquidAI support."""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import (
    ModelNotInstalledError,
    ModelTimeoutError,
    ModelUnavailableError,
    ProviderError,
)
from app.core.logging import logger
from app.domain.protocols import (
    ChatCompletionResponse,
    ChatMessage,
    StreamChunk,
)
from app.providers.base import BaseAIProvider


class OllamaProvider(BaseAIProvider):
    """Local inference provider communicating with Ollama REST API.

    Features native tool-calling, model tag normalization, parameter overrides,
    and structured error reporting without unauthorized cloud fallbacks.
    """

    name = "ollama"

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout or settings.MODEL_REQUEST_TIMEOUT

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
        """Fetch list of pulled model tags from Ollama."""
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

    async def resolve_installed_model_name(self, configured_model: str) -> str:
        """Verify model is installed and return exact Ollama tag name.

        Handles tags like 'LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M' matching
        'hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M' or case-insensitive suffixes.
        Raises ModelNotInstalledError with setup instructions if absent.
        """
        if not await self.check_health():
            raise ModelUnavailableError(
                f"Ollama service is unreachable at {self.base_url}. "
                "Ensure Ollama is started with 'ollama serve'."
            )

        installed_models = await self.list_models()
        if not installed_models:
            raise ModelNotInstalledError(
                f"No models are installed in Ollama. Expected '{configured_model}'. "
                f"Run: 'ollama run {configured_model}'"
            )

        # 1. Exact match
        if configured_model in installed_models:
            return configured_model

        # 2. Suffix or prefix normalization (e.g. hf.co/...)
        norm_cfg = configured_model.lower().strip()
        for installed in installed_models:
            inst_lower = installed.lower()
            if inst_lower == norm_cfg:
                return installed
            if inst_lower.endswith(norm_cfg) or norm_cfg.endswith(inst_lower):
                return installed
            # Check without namespace
            cfg_base = norm_cfg.split("/")[-1]
            inst_base = inst_lower.split("/")[-1]
            if cfg_base == inst_base:
                return installed

            # 3. Handle GGUF suffix differences (e.g. lfm2.5-2.6b vs lfm2.5-2.6b-gguf)
            clean_cfg = norm_cfg.replace("-gguf", "").replace(".gguf", "")
            clean_inst = inst_lower.replace("-gguf", "").replace(".gguf", "")
            if clean_cfg in clean_inst or clean_inst in clean_cfg:
                return installed
            clean_cfg_base = cfg_base.replace("-gguf", "").replace(".gguf", "")
            clean_inst_base = inst_base.replace("-gguf", "").replace(".gguf", "")
            if clean_cfg_base == clean_inst_base:
                return installed

        raise ModelNotInstalledError(
            f"Configured model '{configured_model}' is not installed in Ollama. "
            f"Installed models: {installed_models}. "
            f"To install, run: 'ollama run {configured_model}'",
            details={"configured_model": configured_model, "installed_models": installed_models},
        )

    async def chat_complete(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
        options_override: dict[str, Any] | None = None,
    ) -> ChatCompletionResponse:
        """Execute non-streaming chat completion with native tool calling."""
        resolved_model = await self.resolve_installed_model_name(model)

        options: dict[str, Any] = {
            "temperature": temperature if temperature is not None else settings.MODEL_TEMPERATURE,
            "num_predict": max_tokens if max_tokens is not None else settings.MODEL_MAX_TOKENS,
            "num_ctx": settings.MODEL_CONTEXT_LIMIT,
        }
        if options_override:
            options.update(options_override)

        formatted_messages = []
        for m in messages:
            role_str = m.role.value if hasattr(m.role, "value") else str(m.role)
            item: dict[str, Any] = {"role": role_str, "content": m.content}
            # Attach tool calls or tool call responses if present
            if hasattr(m, "tool_calls") and m.tool_calls:
                item["tool_calls"] = m.tool_calls
            if hasattr(m, "tool_call_id") and m.tool_call_id:
                item["tool_call_id"] = m.tool_call_id
            formatted_messages.append(item)

        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": formatted_messages,
            "stream": False,
            "options": options,
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
                raw_tool_calls = msg.get("tool_calls")

                # Normalize tool_calls arguments if returned as JSON strings
                normalized_tool_calls = self._normalize_tool_calls(raw_tool_calls)

                return ChatCompletionResponse(
                    content=content,
                    tool_calls=normalized_tool_calls,
                    finish_reason=data.get("done_reason", "stop"),
                    usage={
                        "total_duration": data.get("total_duration"),
                        "eval_count": data.get("eval_count"),
                        "prompt_eval_count": data.get("prompt_eval_count"),
                    },
                )
        except httpx.ConnectError as e:
            raise ModelUnavailableError(
                f"Cannot connect to Ollama at {self.base_url}. Ensure Ollama is running.",
                details={"error": str(e)},
            )
        except httpx.TimeoutException as e:
            raise ModelTimeoutError(
                f"Ollama request timed out after {self.timeout}s.",
                details={"error": str(e)},
            )
        except Exception as e:
            if isinstance(e, (ProviderError, ModelNotInstalledError, ModelUnavailableError, ModelTimeoutError)):
                raise
            raise ProviderError(f"Ollama execution error: {str(e)}", details={"error": str(e)})

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        model: str,
        temperature: float | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Stream response chunks from Ollama."""
        resolved_model = await self.resolve_installed_model_name(model)

        payload: dict[str, Any] = {
            "model": resolved_model,
            "messages": [
                {
                    "role": m.role.value if hasattr(m.role, "value") else str(m.role),
                    "content": m.content,
                }
                for m in messages
            ],
            "stream": True,
            "options": {
                "temperature": temperature if temperature is not None else settings.MODEL_TEMPERATURE,
                "num_ctx": settings.MODEL_CONTEXT_LIMIT,
            },
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
                            tool_calls = self._normalize_tool_calls(msg.get("tool_calls"))
                            done = data.get("done", False)

                            yield StreamChunk(
                                content_delta=delta,
                                tool_call_delta={"tool_calls": tool_calls} if tool_calls else None,
                                finish_reason="stop" if done else None,
                            )
                        except json.JSONDecodeError:
                            continue
        except httpx.TimeoutException as e:
            raise ModelTimeoutError(f"Ollama streaming timed out after {self.timeout}s: {str(e)}")
        except httpx.ConnectError as e:
            raise ModelUnavailableError(f"Ollama streaming connection error: {str(e)}")

    @staticmethod
    def _normalize_tool_calls(raw_calls: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
        """Ensure tool_calls structure and arguments are consistently parsed."""
        if not raw_calls:
            return None

        normalized = []
        for call in raw_calls:
            fn = call.get("function", {})
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:
                    args = {"raw_arguments": args}
            normalized.append({
                "id": call.get("id"),
                "type": call.get("type", "function"),
                "function": {
                    "name": fn.get("name"),
                    "arguments": args,
                },
            })
        return normalized
