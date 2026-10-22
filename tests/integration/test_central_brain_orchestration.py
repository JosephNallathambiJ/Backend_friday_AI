"""Integration tests for Central Brain Orchestrator, Model Diagnostics, and Policy Gating."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.enums import MessageRole
from app.domain.protocols import ChatCompletionResponse, ChatMessage
from app.providers.base import BaseAIProvider
from app.providers.registry import provider_registry
from app.services.brain_service import FridayBrain
from app.services.conversation_service import ConversationService
from app.services.task_service import TaskService


@pytest.mark.asyncio
async def test_model_diagnostics_endpoint(async_client: AsyncClient):
    """Verify GET /api/v1/system/diagnostics/model returns structured diagnostic results."""
    res = await async_client.get("/api/v1/system/diagnostics/model")
    assert res.status_code == 200
    data = res.json()["data"]

    # Verify all 6 required diagnostic capability fields
    checks = data["checks"]
    assert "ollama_reachable" in checks
    assert "model_installed" in checks
    assert "simple_prompt_response" in checks
    assert "structured_tool_calling" in checks
    assert "tool_result_followup" in checks
    assert "timeout_and_error_handling" in checks
    assert "configured_model" in data
    assert "overall_status" in data


@pytest.mark.asyncio
async def test_brain_tool_calling_loop_execution(db_session: AsyncSession):
    """Verify bounded model-tool loop executes proposed tool and returns final synthesized response."""
    # Step 1: Propose list_files tool
    # Step 2: Conclude with summary text
    responses = [
        ChatCompletionResponse(
            content="",
            tool_calls=[
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "list_files",
                        "arguments": {"subpath": "."},
                    },
                }
            ],
            finish_reason="tool_calls",
        ),
        ChatCompletionResponse(
            content="Directory contains project structure with app and tests.",
            tool_calls=None,
            finish_reason="stop",
        ),
    ]

    class SequentialMockProvider(BaseAIProvider):
        name = "mock"
        def __init__(self):
            self.calls = 0
        async def check_health(self):
            return True
        async def list_models(self):
            return ["mock-model"]
        async def chat_complete(self, *args, **kwargs):
            resp = responses[min(self.calls, len(responses) - 1)]
            self.calls += 1
            return resp
        async def stream_chat(self, *args, **kwargs):
            pass

    provider_registry.register(SequentialMockProvider())

    conv = await ConversationService.create_conversation(db_session, title="Brain Test")
    task = await TaskService.create_task(db_session, task_type="hud_command", summary="Inspect files")

    result = await FridayBrain.execute_tool_calling_loop(
        session=db_session,
        initial_prompt="Inspect files in current directory",
        conversation_id=conv.id,
        task_id=task.id,
        max_iterations=5,
    )

    assert result["status"] == "completed"
    assert result["approval_required"] is False
    assert "Directory contains project structure" in result["final_response"]
    assert len(result["executed_tools"]) == 1
    assert result["executed_tools"][0]["tool"] == "list_files"
    assert result["executed_tools"][0]["status"] == "success"


@pytest.mark.asyncio
async def test_brain_anti_loop_duplicate_detection(db_session: AsyncSession):
    """Verify Central Brain detects and blocks repeated identical tool calls."""
    # Provider attempts to call the exact same tool with exact same arguments repeatedly
    duplicate_call = {
        "id": "call_dup",
        "type": "function",
        "function": {
            "name": "list_files",
            "arguments": {"subpath": "logs"},
        },
    }

    class LoopingMockProvider(BaseAIProvider):
        name = "mock"
        def __init__(self):
            self.calls = 0
        async def check_health(self):
            return True
        async def list_models(self):
            return ["mock-model"]
        async def chat_complete(self, *args, **kwargs):
            self.calls += 1
            if self.calls <= 2:
                return ChatCompletionResponse(content="", tool_calls=[duplicate_call])
            return ChatCompletionResponse(content="Stopped loop.", tool_calls=None)
        async def stream_chat(self, *args, **kwargs):
            pass

    provider_registry.register(LoopingMockProvider())

    conv = await ConversationService.create_conversation(db_session, title="Anti-Loop Test")
    task = await TaskService.create_task(db_session, task_type="hud_command", summary="Looping check")

    result = await FridayBrain.execute_tool_calling_loop(
        session=db_session,
        initial_prompt="Check logs directory repeatedly",
        conversation_id=conv.id,
        task_id=task.id,
        max_iterations=5,
    )

    assert result["status"] == "completed"
    # The duplicate should only have been executed once
    assert len(result["executed_tools"]) == 1


@pytest.mark.asyncio
async def test_brain_approval_required_and_resumption(db_session: AsyncSession):
    """Verify tool requiring approval halts the loop and emits approval_required event, then resumes."""
    privileged_call = {
        "id": "call_priv",
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "arguments": {"command": "git", "args": ["status"]},
        },
    }

    class PrivilegedMockProvider(BaseAIProvider):
        name = "mock"
        async def check_health(self):
            return True
        async def list_models(self):
            return ["mock-model"]
        async def chat_complete(self, *args, **kwargs):
            return ChatCompletionResponse(content="", tool_calls=[privileged_call])
        async def stream_chat(self, *args, **kwargs):
            pass

    provider_registry.register(PrivilegedMockProvider())

    conv = await ConversationService.create_conversation(db_session, title="Approval Test")
    task = await TaskService.create_task(db_session, task_type="hud_command", summary="Run git status")

    result = await FridayBrain.execute_tool_calling_loop(
        session=db_session,
        initial_prompt="Run git status in terminal",
        conversation_id=conv.id,
        task_id=task.id,
    )

    assert result["status"] == "waiting_for_approval"
    assert result["approval_required"] is True
    assert result["approval_id"] is not None

    # Test rejection resumption
    rejection_res = await FridayBrain.continue_task(
        session=db_session,
        task_id=task.id,
        approval_resolution=False,
    )
    assert rejection_res["status"] == "cancelled"


@pytest.mark.asyncio
async def test_live_ollama_liquidai_integration():
    """Opt-in integration test with live running Ollama and LiquidAI model.

    Skipped if Ollama is not running locally.
    """
    from app.providers.ollama import OllamaProvider

    provider = OllamaProvider()
    if not await provider.check_health():
        pytest.skip("Local Ollama is not running at http://127.0.0.1:11434")

    installed_models = await provider.list_models()
    matching = any("LiquidAI" in m or "lfm" in m.lower() for m in installed_models)
    if not matching:
        pytest.skip(f"LiquidAI model not installed in Ollama. Found: {installed_models}")

    # 1. Test basic chat completion
    res = await provider.chat_complete(
        messages=[ChatMessage(role=MessageRole.USER, content="Reply with the single word: READY")],
        model=settings.FRIDAY_MODEL_NAME,
        temperature=0.1,
    )
    assert res.content is not None
    assert len(res.content.strip()) > 0

    # 2. Test native tool-calling
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_system_info",
                "description": "Get current host OS, CPU, and memory information.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        }
    ]
    tool_res = await provider.chat_complete(
        messages=[ChatMessage(role=MessageRole.USER, content="Call get_system_info to get my computer status.")],
        model=settings.FRIDAY_MODEL_NAME,
        tools=tools,
        temperature=0.1,
    )
    # The model should either return a tool call or answer with understanding
    assert tool_res.content is not None or tool_res.tool_calls is not None
