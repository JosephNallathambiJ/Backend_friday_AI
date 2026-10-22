"""Unit tests for Central Brain, Ollama Model Adapter, and Specialist Orchestration."""

from unittest.mock import patch

import httpx
import pytest

from app.agents.specialists.specialists import SpecialistRegistry
from app.core.config import settings
from app.core.exceptions import (
    ModelNotInstalledError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from app.domain.enums import MessageRole
from app.domain.protocols import ChatMessage
from app.providers.ollama import OllamaProvider
from app.services.brain_service import FridayBrain


@pytest.mark.asyncio
async def test_installed_model_verification_success():
    """Verify exact and normalized tag resolution succeeds."""
    provider = OllamaProvider(base_url="http://127.0.0.1:11434")

    with patch.object(provider, "check_health", return_value=True), \
         patch.object(provider, "list_models", return_value=["hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M", "llama3.2:1b"]):
        resolved = await provider.resolve_installed_model_name("LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M")
        assert resolved == "hf.co/LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M"

        exact = await provider.resolve_installed_model_name("llama3.2:1b")
        assert exact == "llama3.2:1b"


@pytest.mark.asyncio
async def test_installed_model_verification_not_installed():
    """Verify actionable error is raised when model is not installed."""
    provider = OllamaProvider(base_url="http://127.0.0.1:11434")

    with patch.object(provider, "check_health", return_value=True), \
         patch.object(provider, "list_models", return_value=["llama3.2:1b"]):
        with pytest.raises(ModelNotInstalledError) as exc_info:
            await provider.resolve_installed_model_name("LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M")
        assert "is not installed in Ollama" in str(exc_info.value)
        assert "ollama run" in str(exc_info.value)


@pytest.mark.asyncio
async def test_installed_model_verification_unreachable():
    """Verify ModelUnavailableError when Ollama service is unreachable."""
    provider = OllamaProvider(base_url="http://127.0.0.1:11434")

    with patch.object(provider, "check_health", return_value=False):
        with pytest.raises(ModelUnavailableError) as exc_info:
            await provider.resolve_installed_model_name("LiquidAI/LFM2.5-2.6B-GGUF:Q4_K_M")
        assert "unreachable" in str(exc_info.value)


def test_tool_call_argument_normalization():
    """Verify OllamaProvider._normalize_tool_calls parses JSON string arguments."""
    provider = OllamaProvider()

    raw_calls = [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "list_files",
                "arguments": "{\"subpath\": \"src\", \"recursive\": false}",
            },
        },
        {
            "id": "call_2",
            "type": "function",
            "function": {
                "name": "read_file",
                "arguments": {"file_path": "README.md"},
            },
        },
    ]

    normalized = provider._normalize_tool_calls(raw_calls)
    assert len(normalized) == 2
    assert normalized[0]["function"]["arguments"] == {"subpath": "src", "recursive": False}
    assert normalized[1]["function"]["arguments"] == {"file_path": "README.md"}


@pytest.mark.asyncio
async def test_least_privilege_tool_selection():
    """Verify brain selects tools scoped to intent rather than exposing all tools."""
    # Read-only file intent
    file_tools = await FridayBrain.select_tools(task_type="filesystem", user_request="list all files in directory")
    names = {t["function"]["name"] for t in file_tools}
    assert "list_files" in names
    assert "read_file" in names
    assert "run_terminal_command" not in names
    assert "delete_contact" not in names

    # Web search intent
    search_tools = await FridayBrain.select_tools(task_type="research", user_request="search the web for python news")
    search_names = {t["function"]["name"] for t in search_tools}
    assert "web_search" in search_names
    assert "run_terminal_command" not in search_names


def test_tool_result_sanitization_and_bounding():
    """Verify tool results are bounded to prevent context overflow and treated as untrusted."""
    short_data = {"status": "ok", "count": 3}
    sanitized = FridayBrain.sanitize_tool_result("test_tool", short_data, max_chars=100)
    assert sanitized["is_partial"] is False
    assert "untrusted_data_notice" in sanitized

    long_data = "X" * 500
    sanitized_long = FridayBrain.sanitize_tool_result("test_tool", long_data, max_chars=100)
    assert sanitized_long["is_partial"] is True
    assert len(sanitized_long["structured_output"]) < 200
    assert "truncated" in sanitized_long["structured_output"]


@pytest.mark.asyncio
async def test_ollama_timeout_handling():
    """Verify ModelTimeoutError is raised on HTTP timeout."""
    provider = OllamaProvider(base_url="http://127.0.0.1:11434", timeout=0.01)

    with patch.object(provider, "resolve_installed_model_name", return_value="test_model"):
        with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("Read timed out")):
            with pytest.raises(ModelTimeoutError) as exc_info:
                await provider.chat_complete(
                    messages=[ChatMessage(role=MessageRole.USER, content="Hello")],
                    model="test_model",
                )
            assert "timed out" in str(exc_info.value)


def test_no_unauthorized_cloud_fallback():
    """Verify that CLOUD_AI_ENABLED defaults to False and provider registry never selects cloud by default."""
    from app.providers.registry import ProviderRegistry

    reg = ProviderRegistry()
    assert settings.CLOUD_AI_ENABLED is False
    # Without mock registered, default provider should be ollama
    default_provider = reg.get()
    assert default_provider.name == "ollama"


def test_specialist_agent_registry_resolution():
    """Verify specialist agents are registered and resolve correctly."""
    all_specialists = SpecialistRegistry.list_all()
    assert len(all_specialists) >= 8

    keys = set(SpecialistRegistry._specialists.keys())
    expected_core_keys = {
        "research",
        "files",
        "browser",
        "terminal",
        "contacts",
        "device",
        "voice",
        "workflow",
    }
    assert expected_core_keys.issubset(keys)

    # Test keyword matching
    assert SpecialistRegistry.resolve_for_task("general", "read project file").name == "Filesystem Specialist"
    assert "Terminal" in SpecialistRegistry.resolve_for_task("general", "execute git commit in terminal").name or "Coding" in SpecialistRegistry.resolve_for_task("general", "execute git commit in terminal").name
    assert SpecialistRegistry.resolve_for_task("general", "look up phone number for Alice in contacts").name == "Contacts Specialist"
