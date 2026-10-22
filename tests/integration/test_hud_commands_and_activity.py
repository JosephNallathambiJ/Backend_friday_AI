"""Integration tests for Tactical Commands and Central AI Visualizer State."""

import pytest
from httpx import AsyncClient

from app.services.activity_service import activity_service


@pytest.mark.asyncio
async def test_submit_command_sync(async_client: AsyncClient):
    """Verify synchronous command execution produces plan and completed result."""
    res = await async_client.post(
        "/api/v1/commands",
        json={
            "command": "Inspect workspace files and report status",
            "response_mode": "sync",
            "locale": "en-US",
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert "command_id" in data
    assert "task_id" in data
    assert "run_id" in data
    assert data["status"] in {"completed", "waiting_for_approval"}
    assert "event_ref" in data


@pytest.mark.asyncio
async def test_submit_command_async(async_client: AsyncClient):
    """Verify asynchronous command returns accepted status immediately with tracking references."""
    res = await async_client.post(
        "/api/v1/commands",
        json={
            "command": "Perform background deep index verification",
            "response_mode": "async",
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "accepted"
    assert data["command_id"] is not None
    assert data["task_id"] is not None
    assert "/api/v1/events" in data["event_ref"]


@pytest.mark.asyncio
async def test_command_idempotency(async_client: AsyncClient):
    """Verify identical request_id returns cached idempotent result."""
    req_id = "test-idempotent-key-12345"
    res1 = await async_client.post(
        "/api/v1/commands",
        json={"command": "Check system files", "request_id": req_id},
    )
    assert res1.status_code == 200
    cmd_id1 = res1.json()["data"]["command_id"]

    res2 = await async_client.post(
        "/api/v1/commands",
        json={"command": "Check system files", "request_id": req_id},
    )
    assert res2.status_code == 200
    cmd_id2 = res2.json()["data"]["command_id"]
    assert cmd_id1 == cmd_id2


@pytest.mark.asyncio
async def test_agent_visualizer_state(async_client: AsyncClient):
    """Verify visualizer state endpoint returns truthful telemetry and activity description."""
    await activity_service.set_state(
        state="thinking",
        description="Tactical neural matrix evaluating inputs...",
        current_step=1,
        total_steps=5,
    )

    for endpoint in ["/api/v1/agent/state", "/api/v1/agents/state"]:
        res = await async_client.get(endpoint)
        assert res.status_code == 200
        state_data = res.json()["data"]
        assert state_data["state"] == "thinking"
        assert state_data["current_step"] == 1
        assert state_data["total_steps"] == 5
        assert "Tactical neural matrix" in state_data["description"]

    # Reset to idle
    await activity_service.set_state(state="idle")
