"""Integration tests for Agent Runtime, Capabilities, Contacts, and Integrations APIs."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_agent_run_lifecycle_api(async_client: AsyncClient):
    # 1. Create run with execution
    create_res = await async_client.post(
        "/api/v1/agents/runs?execute_now=true",
        json={
            "goal": "list files in current directory",
            "agent_type": "orchestrator",
            "max_steps": 10,
        },
    )
    assert create_res.status_code == 201
    run_data = create_res.json()["data"]
    run_id = run_data["id"]
    assert run_data["goal"] == "list files in current directory"
    assert run_data["status"] in ["completed", "running", "waiting_for_approval"]

    # 2. Inspect run details
    get_res = await async_client.get(f"/api/v1/agents/runs/{run_id}")
    assert get_res.status_code == 200
    assert get_res.json()["data"]["id"] == run_id

    # 3. Retrieve run events
    events_res = await async_client.get(f"/api/v1/agents/runs/{run_id}/events")
    assert events_res.status_code == 200
    events = events_res.json()["data"]
    assert len(events) >= 1
    event_types = [e["event_type"] for e in events]
    assert "run_created" in event_types


@pytest.mark.asyncio
async def test_agent_run_cancellation(async_client: AsyncClient):
    # Create run without immediate execution
    create_res = await async_client.post(
        "/api/v1/agents/runs?execute_now=false",
        json={"goal": "long running task", "agent_type": "workflow"},
    )
    assert create_res.status_code == 201
    run_id = create_res.json()["data"]["id"]

    # Cancel run
    cancel_res = await async_client.post(f"/api/v1/agents/runs/{run_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["data"]["status"] == "cancelled"


@pytest.mark.asyncio
async def test_capabilities_api_lifecycle(async_client: AsyncClient):
    # 1. List capabilities
    list_res = await async_client.get("/api/v1/capabilities")
    assert list_res.status_code == 200
    caps = list_res.json()["data"]
    cap_names = [c["capability"] for c in caps]
    assert "filesystem.read" in cap_names
    assert "browser.navigate" in cap_names

    # 2. Grant explicit capability
    grant_res = await async_client.post(
        "/api/v1/capabilities/grant",
        json={
            "capability": "filesystem.delete",
            "scope_type": "directory",
            "scope_value": "/tmp",
        },
    )
    assert grant_res.status_code == 200
    assert grant_res.json()["data"]["capability"] == "filesystem.delete"

    # 3. Revoke capability
    revoke_res = await async_client.post(
        "/api/v1/capabilities/revoke",
        json={
            "capability": "filesystem.delete",
            "scope_type": "directory",
            "scope_value": "/tmp",
        },
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["data"]["revoked"] is True


@pytest.mark.asyncio
async def test_contacts_api_lifecycle(async_client: AsyncClient):
    # 1. Create contact
    create_res = await async_client.post(
        "/api/v1/contacts",
        json={
            "display_name": "Tony Stark",
            "organization": "Stark Industries",
            "emails": ["tony@stark.com"],
            "phones": ["+1-555-0199"],
            "labels": ["VIP", "Avenger"],
        },
    )
    assert create_res.status_code == 201
    contact = create_res.json()["data"]
    contact_id = contact["id"]
    assert contact["display_name"] == "Tony Stark"

    # 2. Search contacts
    search_res = await async_client.get("/api/v1/contacts?query=Stark")
    assert search_res.status_code == 200
    results = search_res.json()["data"]
    assert len(results) >= 1
    assert any(c["id"] == contact_id for c in results)

    # 3. Delete contact
    del_res = await async_client.delete(f"/api/v1/contacts/{contact_id}")
    assert del_res.status_code == 200
    assert del_res.json()["data"]["deleted"] is True


@pytest.mark.asyncio
async def test_device_integrations_api(async_client: AsyncClient):
    res = await async_client.get("/api/v1/integrations")
    assert res.status_code == 200
    data = res.json()["data"]
    assert "os_name" in data
    assert "cpu_count" in data
    assert "supported_adapters" in data
