"""Voice speech-to-text and text-to-speech endpoints."""

from fastapi import APIRouter, Depends, File, Response, UploadFile
from pydantic import BaseModel

from app.api.dependencies import verify_api_key
from app.domain.schemas import APIResponse
from app.voice.synthesis import voice_synthesis_adapter
from app.voice.transcription import voice_transcription_adapter

router = APIRouter(
    prefix="/api/v1/voice",
    tags=["Voice Services"],
    dependencies=[Depends(verify_api_key)],
)


class SynthesizeRequest(BaseModel):
    text: str
    voice: str | None = None


@router.post("/transcribe", response_model=APIResponse)
async def transcribe_audio(
    file: UploadFile = File(...),
):
    """Convert audio file to text using local speech recognition engine."""
    audio_bytes = await file.read()
    mime = file.content_type or "audio/wav"
    transcript = await voice_transcription_adapter.transcribe(audio_bytes, mime)
    return APIResponse(data={"transcript": transcript})


@router.post("/synthesize")
async def synthesize_speech(payload: SynthesizeRequest):
    """Convert text into audio speech stream."""
    audio_bytes = await voice_synthesis_adapter.synthesize(payload.text, payload.voice)
    return Response(content=audio_bytes, media_type="audio/wav")
