"""Voice speech-to-text and text-to-speech endpoints for the tactical HUD."""

import shutil

from fastapi import APIRouter, Depends, File, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, verify_api_key
from app.domain.schemas import APIResponse
from app.realtime.event_bus import event_bus
from app.services.activity_service import activity_service
from app.voice.synthesis import voice_synthesis_adapter
from app.voice.transcription import SUPPORTED_AUDIO_MIMES, voice_transcription_adapter

router = APIRouter(
    prefix="/api/v1/voice",
    tags=["Voice Services"],
    dependencies=[Depends(verify_api_key)],
)


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str | None = None
    speed: float | None = Field(default=1.0, ge=0.5, le=2.0)


@router.get("/capabilities", response_model=APIResponse)
async def get_voice_capabilities():
    """Return speech recognition and text-to-speech capabilities and engine statuses."""
    whisper_available = shutil.which("whisper") is not None
    tts_command = shutil.which("say") or shutil.which("espeak")
    tts_available = tts_command is not None

    status_str = "online" if (whisper_available and tts_available) else (
        "degraded" if (whisper_available or tts_available) else "not_configured"
    )

    return APIResponse(
        success=True,
        data={
            "status": status_str,
            "stt": {
                "available": whisper_available,
                "engine": "whisper" if whisper_available else "none",
                "supported_formats": list(SUPPORTED_AUDIO_MIMES),
                "max_size_bytes": 25 * 1024 * 1024,
            },
            "tts": {
                "available": tts_available,
                "engine": tts_command or "none",
                "formats": ["audio/wav"],
            },
        },
    )


@router.get("/voices", response_model=APIResponse)
async def list_available_voices():
    """List available TTS voices configured on the system."""
    voices = ["default"]
    if shutil.which("say"):
        voices.extend(["Samantha", "Alex", "Victoria", "Fred", "Karen"])
    return APIResponse(success=True, data={"total": len(voices), "voices": voices})


@router.post("/transcribe", response_model=APIResponse)
@router.post("/transcriptions", response_model=APIResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
):
    """Convert uploaded audio file to text transcript."""
    await activity_service.set_state(
        state="transcribing",
        description="Transcribing audio input stream...",
    )
    await event_bus.publish(event_type="voice.listening_started")

    try:
        audio_bytes = await file.read()
        mime = file.content_type or "audio/wav"
        transcript = await voice_transcription_adapter.transcribe(audio_bytes, mime)

        await event_bus.publish(
            event_type="voice.transcription_final",
            payload={"transcript": transcript, "mime_type": mime},
        )
        await activity_service.set_state(
            state="idle",
            description="Transcription completed. Systems standing by.",
        )
        return APIResponse(success=True, data={"transcript": transcript})
    except Exception as e:
        await event_bus.publish(event_type="voice.error", payload={"error": str(e)})
        await activity_service.set_state(state="error", error_category=str(e))
        raise


@router.post("/synthesize")
@router.post("/speech")
async def synthesize_speech(payload: SynthesizeRequest):
    """Convert text into synthesized speech audio stream."""
    await activity_service.set_state(
        state="speaking",
        description=f"Synthesizing vocal speech: '{payload.text[:30]}...'",
    )
    await event_bus.publish(
        event_type="voice.speech_started",
        payload={"text": payload.text[:100], "voice": payload.voice},
    )

    try:
        audio_bytes = await voice_synthesis_adapter.synthesize(payload.text, payload.voice)
        await event_bus.publish(event_type="voice.speech_completed")
        await activity_service.set_state(
            state="idle",
            description="Vocal synthesis completed. Systems standing by.",
        )
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        await event_bus.publish(event_type="voice.error", payload={"error": str(e)})
        await activity_service.set_state(state="error", error_category=str(e))
        raise


class VoiceCommandRequest(BaseModel):
    command: str = Field(..., min_length=1, description="Transcribed voice command")
    conversation_id: str | None = None


@router.post("/command", response_model=APIResponse)
async def execute_voice_command(
    payload: VoiceCommandRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(verify_api_key),
):
    """Route voice-transcribed command into the single authoritative execution pipeline."""
    from app.services.command_service import CommandService

    result = await CommandService.process_command(
        session=db,
        command_text=payload.command,
        conversation_id=payload.conversation_id,
        context={"channel": "voice", "locale": "en-US"},
    )
    return APIResponse(success=True, data=result)

