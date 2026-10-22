"""Integration tests for AI orchestration loop, tool calling, and approvals."""

import pytest
from httpx import AsyncClient

from app.providers.registry import provider_registry
from tests.conftest import MockAIProvider


@pytest.mark.asyncio
async def test_chat_simple_response(async_client: AsyncClient):
    # Set mock provider response
    mock_provider = MockAIProvider(response_text="FRIDAY at your service.")
    provider_registry.register(mock_provider)

    # 1. Create conversation
    conv_res = await async_client.post("/api/v1/conversations", json={"title": "Chat Test"})
    conv_id = conv_res.json()["data"]["id"]

    # 2. Chat
    chat_res = await async_client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "Who are you?"},
    )
    assert chat_res.status_code == 200
    data = chat_res.json()["data"]
    assert data["content"] == "FRIDAY at your service."
    assert data["approval_required"] is None


@pytest.mark.asyncio
async def test_chat_tool_call_execution(async_client: AsyncClient):
    # Setup mock provider to propose list_files tool call
    mock_provider = MockAIProvider(
        response_text="Here are the files in your directory.",
        tool_calls=[
            {
                "function": {
                    "name": "list_files",
                    "arguments": {"subpath": "."},
                }
            }
        ],
    )
    provider_registry.register(mock_provider)

    conv_res = await async_client.post("/api/v1/conversations", json={"title": "Tool Test"})
    conv_id = conv_res.json()["data"]["id"]

    chat_res = await async_client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "List current project files."},
    )
    assert chat_res.status_code == 200
    data = chat_res.json()["data"]
    assert data["approval_required"] is None


@pytest.mark.asyncio
async def test_chat_tool_call_requiring_approval(async_client: AsyncClient):
    # Model proposes consequential tool run_terminal_command
    mock_provider = MockAIProvider(
        response_text="",
        tool_calls=[
            {
                "function": {
                    "name": "run_terminal_command",
                    "arguments": {"command": "git", "args": ["status"]},
                }
            }
        ],
    )
    provider_registry.register(mock_provider)

    conv_res = await async_client.post("/api/v1/conversations", json={"title": "Approval Test"})
    conv_id = conv_res.json()["data"]["id"]

    chat_res = await async_client.post(
        "/api/v1/chat",
        json={"conversation_id": conv_id, "message": "Run git status in terminal."},
    )
    assert chat_res.status_code == 200
    data = chat_res.json()["data"]
    assert data["approval_required"] is not None
    approval_id = data["approval_required"]["approval_id"]

    # Verify approval exists in pending approvals list
    approvals_res = await async_client.get("/api/v1/approvals")
    assert approvals_res.status_code == 200
    pending = approvals_res.json()["data"]
    assert any(a["id"] == approval_id for a in pending)

    # Approve request
    decision_res = await async_client.post(
        f"/api/v1/approvals/{approval_id}/decision",
        json={"decision": "approved", "reason": "Authorized by user"},
    )
    assert decision_res.status_code == 200
    assert decision_res.json()["data"]["status"] == "approved"


@pytest.mark.asyncio
async def test_chat_sse_stream(async_client: AsyncClient):
    mock_provider = MockAIProvider()
    provider_registry.register(mock_provider)

    conv_res = await async_client.post("/api/v1/conversations", json={"title": "SSE Test"})
    conv_id = conv_res.json()["data"]["id"]

    stream_res = await async_client.post(
        "/api/v1/chat/stream",
        json={"conversation_id": conv_id, "message": "Stream hello"},
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers.get("content-type", "")

    content = stream_res.text
    assert "event: message_start" in content
    assert "event: text_delta" in content
    assert "event: message_completed" in content
