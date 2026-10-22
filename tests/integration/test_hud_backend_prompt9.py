"""Master Prompt 9: Comprehensive Integration Tests for HUD Terminal, Chatbot, Quick Actions, and Telemetry."""

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient

from app.main import app
from app.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_hud_topbar_telemetry_endpoint(async_client: AsyncClient):
    """Verify GET /api/system/telemetry returns tactical HUD status and metrics."""
    res = await async_client.get("/api/system/telemetry")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    payload = data["data"]

    assert payload["frequency"] == "1420.405 MHz"
    assert payload["quantum_matrix"] == "SYNCED"
    assert payload["grid_protocol"] == "v8.4"
    assert payload["systems_status"] in {"ONLINE", "DEGRADED"}
    assert payload["mic_state"] == "MIC OFF"
    assert payload["swipe_state"] == "SWIPE ON"
    assert "cpu_percent" in payload
    assert "uptime_seconds" in payload
    assert "dual_brain" in payload
    assert payload["dual_brain"]["left_model"] is not None
    assert payload["dual_brain"]["right_model"] is not None


@pytest.mark.asyncio
async def test_hud_quick_actions_four_buttons(async_client: AsyncClient):
    """Verify the 4 tactical quick-action buttons from the HUD screenshot."""
    # 1. Arc Telemetry
    res_arc = await async_client.post("/api/quick-actions/arc_telemetry/execute")
    assert res_arc.status_code == 200
    arc_data = res_arc.json()["data"]["result"]
    assert arc_data["frequency"] == "1420.405 MHz"
    assert arc_data["quantum_matrix"] == "SYNCED"
    assert arc_data["grid_protocol"] == "v8.4"

    # Case-insensitive label query
    res_arc_label = await async_client.post("/api/quick-actions/Arc Telemetry/execute")
    assert res_arc_label.status_code == 200
    assert res_arc_label.json()["data"]["action_id"] == "arc_telemetry"

    # 2. Who Made You?
    res_who = await async_client.post("/api/quick-actions/who_made_you/execute")
    assert res_who.status_code == 200
    who_data = res_who.json()["data"]["result"]
    assert who_data["creator"] == "GOJO"
    assert "Enterprise Edition" in who_data["system"]
    assert "Dual-Brain" in who_data["architecture"]

    # 3. Blue Team
    res_blue = await async_client.post("/api/quick-actions/blue_team/execute")
    assert res_blue.status_code == 200
    blue_data = res_blue.json()["data"]["result"]
    assert blue_data["status"] == "completed"
    assert blue_data["posture"] == "defensive"
    assert len(blue_data["actionable_recommendations"]) > 0

    # 4. Nmap Recon (Unauthorized target scope enforcement)
    res_nmap_blocked = await async_client.post(
        "/api/quick-actions/nmap_recon/execute",
        json={"parameters": {"target": "unauthorized-external-scan.net"}},
    )
    assert res_nmap_blocked.status_code == 200
    nmap_data = res_nmap_blocked.json()["data"]["result"]
    assert nmap_data["status"] == "authorization_required"
    assert nmap_data["policy_compliant"] is True


@pytest.mark.asyncio
async def test_terminal_api_and_builtins(async_client: AsyncClient):
    """Verify controlled terminal session lifecycle and emulated Linux commands."""
    # 1. Create session
    create_res = await async_client.post(
        "/api/terminal/sessions",
        json={"profile_name": "hud_interactive"},
    )
    assert create_res.status_code == 201
    session_id = create_res.json()["data"]["session_id"]

    # 2. Execute `free`
    free_res = await async_client.post(
        f"/api/terminal/sessions/{session_id}/commands",
        json={"command": "free"},
    )
    assert free_res.status_code == 200
    free_out = free_res.json()["data"]["stdout"]
    assert "Mem:" in free_out
    assert "Swap:" in free_out
    assert "total" in free_out

    # 3. Execute `help`
    help_res = await async_client.post(
        f"/api/terminal/sessions/{session_id}/commands",
        json={"command": "help"},
    )
    assert help_res.status_code == 200
    help_out = help_res.json()["data"]["stdout"]
    assert "FRIDAY Tactical HUD Terminal" in help_out

    # 4. Interrupt endpoint
    int_res = await async_client.post(f"/api/terminal/sessions/{session_id}/interrupt")
    assert int_res.status_code == 200
    assert int_res.json()["data"]["cancelled"] is True


def test_terminal_websocket_streaming():
    """Verify interactive WebSocket stream for HUD terminal panel."""
    client = TestClient(app)

    # Create session via test client
    init_res = client.post("/api/terminal/sessions", json={"profile_name": "hud_interactive"})
    assert init_res.status_code == 201
    session_id = init_res.json()["data"]["session_id"]

    with client.websocket_connect(f"/api/terminal/sessions/{session_id}/stream") as ws:
        # Receive initial MOTD and session greeting
        conn_msg = ws.receive_json()
        assert conn_msg["event"] == "terminal.connected"
        assert "Linux fridey-os" in conn_msg["motd"]
        assert "GOJO OS v8.4.2" in conn_msg["motd"]

        # Run command `free`
        ws.send_json({"command": "free"})
        out_msg = ws.receive_json()
        assert out_msg["event"] == "terminal.output"
        assert "Mem:" in out_msg["stdout"]

        exit_msg = ws.receive_json()
        assert exit_msg["event"] == "terminal.exit"
        assert exit_msg["exit_code"] == 0

        # Attempt `sudo su` (must return graceful policy denial without disconnecting)
        ws.send_json({"command": "sudo su"})
        sudo_out = ws.receive_json()
        assert sudo_out["event"] == "terminal.output"
        assert "sudo: elevation to root requires administrative policy authorization" in sudo_out["stderr"]
        assert sudo_out["exit_code"] == 1

        sudo_exit = ws.receive_json()
        assert sudo_exit["event"] == "terminal.exit"
        assert sudo_exit["exit_code"] == 1


@pytest.mark.asyncio
async def test_chatbot_rest_and_conversation_retrieval(async_client: AsyncClient, db_session):
    """Verify POST /api/chat and conversation retrieval aliases."""
    conv = await ConversationService.create_conversation(db_session, title="HUD Chatbot Test")

    # 1. Ask identity in chat
    chat_res = await async_client.post(
        "/api/chat",
        json={
            "conversation_id": conv.id,
            "message": "Who made you?",
        },
    )
    assert chat_res.status_code == 200
    chat_data = chat_res.json()["data"]
    assert "GOJO" in chat_data["content"]
    assert chat_data["routing"]["primary_agent"] == "identity"

    # 2. Retrieve conversation details
    get_conv = await async_client.get(f"/api/chat/conversations/{conv.id}")
    assert get_conv.status_code == 200
    assert get_conv.json()["data"]["id"] == conv.id

    # 3. Retrieve conversation messages
    get_msgs = await async_client.get(f"/api/chat/conversations/{conv.id}/messages")
    assert get_msgs.status_code == 200
    msgs = get_msgs.json()["data"]
    assert len(msgs) >= 2  # user + assistant


def test_chatbot_websocket_streaming():
    """Verify bidirectional streaming chat over WebSocket for 'ASK ANYTHING · FRIDAY A.I.'."""
    client = TestClient(app)

    with client.websocket_connect("/api/chat/stream") as ws:
        # Receive greeting
        greeting = ws.receive_json()
        assert greeting["event"] == "chat.connected"
        assert greeting["status"] == "online"

        # Send math calculation
        ws.send_json({
            "message": "Calculate (50 * 4) + 12",
            "conversation_id": "test-ws-conv",
        })

        start_msg = ws.receive_json()
        assert start_msg["event"] == "chat.started"

        delta_msg = ws.receive_json()
        assert delta_msg["event"] == "chat.delta"
        assert "212" in delta_msg["delta"]

        comp_msg = ws.receive_json()
        assert comp_msg["event"] == "chat.completed"
        assert comp_msg["routing"]["primary_agent"] == "math_engine"


@pytest.mark.asyncio
async def test_audio_status_and_speech_alias(async_client: AsyncClient):
    """Verify GET /api/audio/status and POST /api/audio/speech alias."""
    res_status = await async_client.get("/api/audio/status")
    assert res_status.status_code == 200
    status_data = res_status.json()["data"]
    assert status_data["voice_capture_status"] == "paused"
    assert status_data["browser_mic_permission_required"] is True
    assert "audio/wav" in status_data["supported_formats"]

    res_speech = await async_client.post(
        "/api/audio/speech",
        json={"text": "Tactical defense status nominal.", "speed": 1.0},
    )
    assert res_speech.status_code == 200
    assert res_speech.headers["content-type"] == "audio/wav"
    assert len(res_speech.content) >= 44
