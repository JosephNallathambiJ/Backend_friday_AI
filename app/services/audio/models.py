"""Data models and validation schemas for audio ingestion and speech processing."""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.enums import AudioFormat


class AudioTranscriptionRequest(BaseModel):
    """Metadata parameters accompanying audio transcription upload."""

    format: AudioFormat = AudioFormat.WAV
    language: str | None = None
    save_audio: bool = False
    context_hint: str | None = None


class AudioTranscriptionResponse(BaseModel):
    """Transcription response returned to frontend."""

    transcript_id: str = Field(default_factory=lambda: f"stt-{uuid4().hex[:8]}")
    transcript: str
    duration_seconds: float | None = None
    format: str
    audio_size_bytes: int
    confidence: float = 0.95
    is_mock_fallback: bool = False
    retained_on_disk: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @property
    def text(self) -> str:
        return self.transcript


class AudioSynthesisRequest(BaseModel):
    """Text-to-speech synthesis parameters."""

    text: str = Field(..., min_length=1, max_length=5000)
    voice: str | None = None
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    format: str = "audio/wav"


class AudioStreamChunkEvent(BaseModel):
    """WebSocket event sent during audio streaming."""

    event_type: str = Field(..., description="chunk_received, partial_transcript, final_transcript, error")
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
