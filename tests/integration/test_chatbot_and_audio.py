"""Integration tests for ChatbotAgent routing and Audio/Microphone services."""

import io

import pytest
from starlette.testclient import TestClient

from app.agents.chatbot_agent import ChatbotAgent, chatbot_agent
from app.core.exceptions import ValidationError
from app.services.audio import (
    AudioSynthesisRequest,
    audio_service,
)
from app.services.conversation_service import ConversationService


@pytest.mark.asyncio
async def test_chatbot_intent_classification():
    """Verify that ChatbotAgent accurately classifies user intents."""
    agent = ChatbotAgent()

    # 1. Math routing
    math_dec = agent.classify_intent("Calculate 2 * (15 + 45) / 3")
    assert math_dec.primary_agent == "math_engine"
    assert math_dec.intent_category == "mathematical_computation"

    # 2. Cyber routing
    cyber_dec = agent.classify_intent("Perform OSINT recon and check security headers on target.org")
    assert cyber_dec.primary_agent == "cyber_agent"
    assert cyber_dec.recommended_brain == "right"

    # 3. Diagnostics routing
    diag_dec = agent.classify_intent("Diagnose backend routes and run database health checks")
    assert diag_dec.primary_agent == "backend_diagnostics"

    # 4. General routing
    gen_dec = agent.classify_intent("Please plan a schedule for writing documentation")
    assert gen_dec.primary_agent == "orchestrator"


@pytest.mark.asyncio
async def test_chatbot_message_handling(db_session):
    """Test ChatbotAgent multi-turn coordinator execution with verified facts."""
    conv = await ConversationService.create_conversation(db_session, title="Coordinator Test")

    # Math computation through chatbot
    res_math = await chatbot_agent.handle_message(
        message="Calculate 125 * 8",
        conversation_id=conv.id,
        session=db_session,
    )
    assert res_math.routing.primary_agent == "math_engine"
    assert "1000" in res_math.content
    assert len(res_math.verified_facts) > 0

    # Diagnostics through chatbot
    res_diag = await chatbot_agent.handle_message(
        message="Diagnose backend system health",
        conversation_id=conv.id,
        session=db_session,
    )
    assert res_diag.routing.primary_agent == "backend_diagnostics"
    assert "FRIDAY Backend Diagnostics Completed" in res_diag.content


@pytest.mark.asyncio
async def test_audio_service_validation_and_ephemeral_cleanup():
    """Verify audio file validation, transcription, and immediate tempfile deletion."""
    # Create valid dummy WAV bytes
    wav_bytes = audio_service._create_dummy_wav()
    assert len(wav_bytes) > 44

    # 1. Successful transcription
    res = await audio_service.transcribe(wav_bytes, "audio/wav")
    assert res.format == "wav"
    assert res.audio_size_bytes == len(wav_bytes)
    assert len(res.transcript) > 0
    assert res.retained_on_disk is False

    # Verify no temp files remain in audio_temp directory
    temp_dir = audio_service.temp_dir
    active_temp_files = list(temp_dir.glob("*.wav"))
    assert len(active_temp_files) == 0

    # 2. Unsupported format rejection
    with pytest.raises(ValidationError, match="Unsupported audio format"):
        audio_service.validate_audio(wav_bytes, "video/mp4")

    # 3. Empty content rejection
    with pytest.raises(ValidationError, match="Audio content is empty"):
        audio_service.validate_audio(b"", "audio/wav")


@pytest.mark.asyncio
async def test_audio_synthesize():
    """Verify speech synthesis returns valid WAV audio bytes."""
    req = AudioSynthesisRequest(text="FRIDAY standing by.", speed=1.0)
    audio_data, mime = await audio_service.synthesize(req)
    assert mime == "audio/wav"
    assert len(audio_data) >= 44
    assert audio_data[:4] == b"RIFF"


def test_audio_endpoints_via_test_client():
    """Test REST API audio upload and synthesis endpoints."""
    from app.main import app

    client = TestClient(app)
    wav_bytes = audio_service._create_dummy_wav()

    # POST /api/audio/transcriptions
    resp = client.post(
        "/api/audio/transcriptions",
        files={"file": ("test.wav", io.BytesIO(wav_bytes), "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "transcript" in data["data"]

    # POST /api/v1/audio/transcriptions (v1 path)
    resp_v1 = client.post(
        "/api/v1/audio/transcriptions",
        files={"file": ("test.wav", io.BytesIO(wav_bytes), "audio/wav")},
    )
    assert resp_v1.status_code == 200

    # POST /api/audio/synthesize
    resp_tts = client.post(
        "/api/audio/synthesize",
        json={"text": "All diagnostic monitors operational."},
    )
    assert resp_tts.status_code == 200
    assert resp_tts.headers["content-type"] == "audio/wav"
    assert len(resp_tts.content) >= 44


def test_websocket_audio_streaming():
    """Test real-time WebSocket audio streaming, chunk buffering, and finalization."""
    from app.main import app

    client = TestClient(app)
    wav_bytes = audio_service._create_dummy_wav()

    with client.websocket_connect("/api/v1/audio/stream") as ws:
        # Send audio bytes chunk
        ws.send_bytes(wav_bytes)
        chunk_ack = ws.receive_json()
        assert chunk_ack["event"] == "chunk_received"
        assert chunk_ack["chunk_bytes"] == len(wav_bytes)

        # Send finalize action
        ws.send_text('{"action": "finalize"}')
        final_msg = ws.receive_json()
        assert final_msg["event"] == "final_transcript"
        assert len(final_msg["transcript"]) > 0
