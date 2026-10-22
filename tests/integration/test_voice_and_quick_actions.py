"""Integration tests for Voice Services, Quick Actions, and Validated Settings."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_voice_capabilities_and_voices(async_client: AsyncClient):
    """Verify voice capability and voice listing endpoints return engine statuses."""
    caps_res = await async_client.get("/api/v1/voice/capabilities")
    assert caps_res.status_code == 200
    caps = caps_res.json()["data"]
    assert "status" in caps
    assert "stt" in caps
    assert "tts" in caps

    voices_res = await async_client.get("/api/v1/voice/voices")
    assert voices_res.status_code == 200
    voices = voices_res.json()["data"]
    assert "voices" in voices
    assert len(voices["voices"]) >= 1


@pytest.mark.asyncio
async def test_voice_speech_synthesis(async_client: AsyncClient):
    """Verify speech synthesis returns audio stream with appropriate content type."""
    res = await async_client.post(
        "/api/v1/voice/speech",
        json={"text": "Tactical defense HUD systems initialized.", "voice": "default"},
    )
    assert res.status_code == 200
    assert "audio/" in res.headers["content-type"]
    assert len(res.content) > 0


@pytest.mark.asyncio
async def test_list_and_execute_quick_actions(async_client: AsyncClient):
    """Verify listing and executing HUD quick-actions."""
    # 1. List actions
    list_res = await async_client.get("/api/v1/quick-actions")
    assert list_res.status_code == 200
    actions = list_res.json()["data"]["actions"]
    assert len(actions) >= 8
    action_ids = [a["id"] for a in actions]
    assert "system.status_summary" in action_ids
    assert "diagnostics.run" in action_ids
    assert "assistant.explain" in action_ids
    assert "assistant.help" in action_ids

    # 2. Execute status summary
    status_exec = await async_client.post("/api/v1/quick-actions/system.status_summary/execute")
    assert status_exec.status_code == 200
    assert status_exec.json()["data"]["action_id"] == "system.status_summary"
    assert "components" in status_exec.json()["data"]["result"]

    # 3. Execute assistant help
    help_exec = await async_client.post("/api/v1/quick-actions/assistant.help/execute")
    assert help_exec.status_code == 200
    assert "supported_interfaces" in help_exec.json()["data"]["result"]

    # 4. Execute assistant explain
    explain_exec = await async_client.post("/api/v1/quick-actions/assistant.explain/execute")
    assert explain_exec.status_code == 200
    assert "Tactical Defense HUD" in explain_exec.json()["data"]["result"]["identity"]


@pytest.mark.asyncio
async def test_settings_get_patch_and_options(async_client: AsyncClient):
    """Verify validated settings inspection, partial updates, and options listing."""
    # 1. Get options
    options_res = await async_client.get("/api/v1/settings/options")
    assert options_res.status_code == 200
    options = options_res.json()["data"]
    assert "en" in options["languages"]
    assert "stark_cyan" in options["themes"]
    assert "system_check" in options["terminal_profiles"]

    # 2. Patch settings
    patch_res = await async_client.patch(
        "/api/v1/settings",
        json={
            "language": "es",
            "locale": "es-ES",
            "theme": "tactical_dark",
            "speech_speed": 1.2,
        },
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()["data"]
    assert updated["language"] == "es"
    assert updated["locale"] == "es-ES"
    assert updated["theme"] == "tactical_dark"
    assert updated["speech_speed"] == 1.2

    # 3. Invalid setting validation
    bad_res = await async_client.patch("/api/v1/settings", json={"language": "invalid_lang"})
    assert bad_res.status_code == 422
