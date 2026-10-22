"""Integration tests for Real-Time HUD WebSocket Events and Reconnect Recovery."""

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

from app.main import app
from app.realtime.event_bus import event_bus


def test_hud_websocket_lifecycle_and_ping():
    """Verify WebSocket connection, initial connection greeting, and ping/pong message loop."""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/events?user_id=hud_tester") as websocket:
        # Initial greeting event
        init_evt = websocket.receive_json()
        assert init_evt["type"] == "system.connected"
        payload = init_evt["payload"]
        assert payload["user_id"] == "hud_tester"
        assert "agent_state" in payload

        # Send ping
        websocket.send_json({"type": "ping", "timestamp": "12:00:00"})
        pong_evt = websocket.receive_json()
        assert pong_evt["type"] == "pong"
        assert pong_evt["timestamp"] == "12:00:00"

        # Request state
        websocket.send_json({"type": "get_state"})
        state_evt = websocket.receive_json()
        assert "agent." in state_evt["type"]


@pytest.mark.asyncio
async def test_event_bus_publishing_and_history(async_client: AsyncClient):
    """Verify publishing events records in history ring buffer and is queryable."""
    evt = await event_bus.publish(
        event_type="system.status",
        payload={"status": "online", "subsystem": "test_suite"},
    )
    assert evt.type == "system.status"
    assert evt.event_id is not None

    # Query history endpoint
    res = await async_client.get("/api/v1/events/history?limit=10")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["count"] >= 1
    event_types = [e["type"] for e in data["events"]]
    assert "system.status" in event_types
