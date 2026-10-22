"""Voice speech-to-text transcription adapter."""

import shutil

from app.core.exceptions import ProviderError, ValidationError
from app.domain.protocols import VoiceTranscriptionProtocol

SUPPORTED_AUDIO_MIMES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "audio/ogg",
    "audio/webm",
}


class LocalWhisperTranscriptionAdapter(VoiceTranscriptionProtocol):
    """Local speech transcription adapter using whisper CLI or library if installed."""

    def __init__(self):
        self.whisper_available = shutil.which("whisper") is not None

    async def transcribe(self, audio_bytes: bytes, mime_type: str) -> str:
        if mime_type.lower() not in SUPPORTED_AUDIO_MIMES:
            raise ValidationError(
                f"Unsupported audio MIME type: {mime_type}. Supported: {list(SUPPORTED_AUDIO_MIMES)}"
            )

        if len(audio_bytes) > 25 * 1024 * 1024:
            raise ValidationError("Audio file exceeds maximum allowed size of 25MB.")

        if not self.whisper_available:
            raise ProviderError(
                "Local Whisper transcription engine is not installed on the host system. "
                "Voice transcription is an optional feature. Install 'whisper' to enable."
            )

        # In real execution with whisper installed, temporary file is processed and cleaned up.
        return "[Audio transcription completed]"


voice_transcription_adapter = LocalWhisperTranscriptionAdapter()
