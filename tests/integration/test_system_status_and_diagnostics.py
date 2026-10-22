"""Integration tests for System Status, Health, Diagnostics, Capabilities, and Info."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_system_status_structure(async_client: AsyncClient):
    """Verify GET /api/v1/system/status returns all required HUD system component indicators."""
    res = await async_client.get("/api/v1/system/status")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True

    payload = data["data"]
    assert "status" in payload
    assert payload["status"] in {"online", "degraded", "offline"}

    # Application metadata
    app_meta = payload["application"]
    assert app_meta["name"] == "FRIDAY-AI-Backend"
    assert "version" in app_meta
    assert "uptime_seconds" in app_meta

    # Components
    components = payload["components"]
    assert "database" in components
    assert components["database"]["status"] == "online"
    assert components["database"]["engine"] == "sqlite"

    assert "ai_provider" in components
    assert "status" in components["ai_provider"]

    assert "voice_provider" in components
    assert components["voice_provider"]["status"] in {"online", "degraded", "not_configured"}

    assert "browser_integration" in components
    assert "terminal_tool" in components
    assert "filesystem_tool" in components
    assert "websocket_service" in components
    assert components["websocket_service"]["status"] == "online"


@pytest.mark.asyncio
async def test_system_diagnostics(async_client: AsyncClient):
    """Verify GET /api/v1/system/diagnostics returns deep component latencies and advice."""
    res = await async_client.get("/api/v1/system/diagnostics")
    assert res.status_code == 200
    data = res.json()["data"]

    assert "overall_status" in data
    assert "uptime_seconds" in data
    assert "component_diagnostics" in data
    assert "actionable_recommendations" in data
    assert isinstance(data["actionable_recommendations"], list)


@pytest.mark.asyncio
async def test_system_capabilities(async_client: AsyncClient):
    """Verify GET /api/v1/system/capabilities lists registered tool permissions and risks."""
    res = await async_client.get("/api/v1/system/capabilities")
    assert res.status_code == 200
    data = res.json()["data"]

    assert data["total"] >= 1
    assert "capabilities" in data
    tool_names = [c["name"] for c in data["capabilities"]]
    assert "list_files" in tool_names
    assert "read_file" in tool_names


@pytest.mark.asyncio
async def test_system_info(async_client: AsyncClient):
    """Verify GET /api/v1/system/info returns identity branding without sensitive details."""
    res = await async_client.get("/api/v1/system/info")
    assert res.status_code == 200
    info = res.json()["data"]

    assert info["application_name"] == "FRIDAY-AI-Backend"
    assert "FRIDAY AI" in info["assistant_identity"]
    assert "supported_features" in info
    assert "tactical_command_execution" in info["supported_features"]
    assert "central_ai_visualizer_telemetry" in info["supported_features"]
    assert "controlled_terminal_sessions" in info["supported_features"]


@pytest.mark.asyncio
async def test_health_endpoints(async_client: AsyncClient):
    """Verify lightweight liveness and readiness probes."""
    for path in ["/health", "/api/v1/health", "/health/live"]:
        res = await async_client.get(path)
        assert res.status_code == 200
        assert res.json()["status"] == "alive"
