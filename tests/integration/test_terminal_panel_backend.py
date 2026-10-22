"""Integration tests for Controlled Terminal Backend Panel."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_terminal_session(async_client: AsyncClient):
    """Verify terminal session creation within approved directory roots."""
    res = await async_client.post(
        "/api/v1/terminal/sessions",
        json={"profile_name": "system_check"},
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert "session_id" in data
    assert data["profile_name"] == "system_check"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_unapproved_working_directory_rejected(async_client: AsyncClient):
    """Verify directory traversal outside approved roots is rejected."""
    res = await async_client.post(
        "/api/v1/terminal/sessions",
        json={"working_directory": "/etc", "profile_name": "system_check"},
    )
    assert res.status_code in {400, 403}


@pytest.mark.asyncio
async def test_execute_terminal_command(async_client: AsyncClient):
    """Verify execution of permitted command returns separated stdout, stderr, and exit code."""
    # 1. Create session
    session_res = await async_client.post(
        "/api/v1/terminal/sessions",
        json={"profile_name": "system_check"},
    )
    session_id = session_res.json()["data"]["session_id"]

    # 2. Execute allowlisted command
    exec_res = await async_client.post(
        f"/api/v1/terminal/sessions/{session_id}/commands",
        json={"command": "pwd"},
    )
    assert exec_res.status_code == 200
    res_data = exec_res.json()["data"]
    assert res_data["executable"] == "pwd"
    assert res_data["exit_code"] == 0
    assert len(res_data["stdout"]) > 0

    # 3. Retrieve session history
    hist_res = await async_client.get(f"/api/v1/terminal/sessions/{session_id}/history")
    assert hist_res.status_code == 200
    history = hist_res.json()["data"]
    assert len(history) >= 1
    assert history[0]["executable"] == "pwd"

    # 4. Cancel & Close session
    cancel_res = await async_client.post(f"/api/v1/terminal/sessions/{session_id}/cancel")
    assert cancel_res.status_code == 200

    del_res = await async_client.delete(f"/api/v1/terminal/sessions/{session_id}")
    assert del_res.status_code == 200
    assert del_res.json()["data"]["closed"] is True


@pytest.mark.asyncio
async def test_forbidden_command_rejected(async_client: AsyncClient):
    """Verify unallowed command or executable not in profile returns error."""
    # 1. Create session with system_check profile
    session_res = await async_client.post(
        "/api/v1/terminal/sessions",
        json={"profile_name": "system_check"},
    )
    session_id = session_res.json()["data"]["session_id"]

    # 2. Try executing an unapproved command
    exec_res = await async_client.post(
        f"/api/v1/terminal/sessions/{session_id}/commands",
        json={"command": "curl http://malicious-site.example"},
    )
    assert exec_res.status_code in {400, 403}
